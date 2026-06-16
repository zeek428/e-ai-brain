from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from time import perf_counter
from typing import Any
from urllib.parse import urlparse

from app.api.deps import api_error
from app.services.code_inspections import sync_product_git_repository_store

NATIVE_CODE_SCAN_MODE = "native_full_scan"
NATIVE_CODE_SCANNER_NAME = "ai_brain_builtin_static"
NATIVE_CODE_SCANNER_VERSION = "2026.06.16"
NATIVE_CODE_RULES_VERSION = "builtin-2026.06.16"

DEFAULT_SCAN_RULES = ("secrets", "internal_addresses")
EXCLUDED_DIR_NAMES = {
    ".git",
    ".idea",
    ".next",
    ".umi",
    ".venv",
    ".vscode",
    "__pycache__",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "venv",
}
TEXT_FILE_MAX_BYTES = 1024 * 1024
DEFAULT_FAILED_CHECKOUT_RETENTION_DAYS = 3
DEFAULT_MAX_CHECKOUT_BYTES = 20 * 1024 * 1024 * 1024
DEFAULT_EXTERNAL_SCANNER_TIMEOUT_SECONDS = 180

SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)\b(api[_-]?key|access[_-]?key|secret|token|password)\b\s*[:=]\s*['\"]([^'\"]{8,})['\"]"
)
INTERNAL_ADDRESS_RE = re.compile(
    r"\bhttps?://(?:localhost|127\.0\.0\.1|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|"
    r"192\.168\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})"
    r"(?::\d+)?[^\s'\"<)]*",
    re.IGNORECASE,
)

SEVERITY_RANK = {
    "critical": 4,
    "high": 3,
    "medium": 2,
    "low": 1,
    "info": 0,
}


def code_inspection_uses_native_scan(job_or_payload: Any) -> bool:
    config = getattr(job_or_payload, "config_json", None)
    if config is None and isinstance(job_or_payload, dict):
        config = job_or_payload.get("config_json")
    if not isinstance(config, dict):
        return False
    return str(config.get("scan_mode") or "").strip() == NATIVE_CODE_SCAN_MODE


def _git(args: list[str], *, cwd: Path | None = None, timeout: int = 60) -> str:
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    completed = subprocess.run(
        ["git", *args],
        cwd=str(cwd) if cwd else None,
        env=env,
        check=True,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return completed.stdout.strip()


def _scan_workdir() -> Path:
    configured = os.getenv("CODE_SCAN_WORKDIR")
    path = (
        Path(configured).expanduser()
        if configured
        else Path(tempfile.gettempdir()) / "ai-brain-code-scan-workdir"
    )
    path.mkdir(parents=True, exist_ok=True)
    (path / "mirrors").mkdir(parents=True, exist_ok=True)
    (path / "checkouts").mkdir(parents=True, exist_ok=True)
    return path.resolve()


def _safe_slug(value: str, *, fallback: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", value.strip()).strip("-._")
    return slug[:96] or fallback


def _remote_url_hash(remote_url: str) -> str:
    return sha256(remote_url.encode("utf-8")).hexdigest()


def _remote_url_summary(remote_url: str) -> str:
    parsed = urlparse(remote_url)
    digest = _remote_url_hash(remote_url)[:12]
    if parsed.scheme in {"http", "https", "ssh", "git"}:
        host = parsed.hostname or "unknown-host"
        path_name = Path(parsed.path or "").name or digest
        return f"{parsed.scheme}://{host}/{path_name}#{digest}"
    if parsed.scheme == "file":
        path_name = Path(parsed.path or "").name or digest
        return f"file://{path_name}#{digest}"
    if "@" in remote_url and ":" in remote_url:
        host_part, path_part = remote_url.rsplit(":", 1)
        host = host_part.rsplit("@", 1)[-1]
        path_name = Path(path_part).name or digest
        return f"ssh://{host}/{path_name}#{digest}"
    path_name = Path(remote_url).name or digest
    return f"file://{path_name}#{digest}"


def _checkout_artifact_ref(checkout_path: Path, workdir: Path) -> str:
    try:
        relative = checkout_path.relative_to(workdir)
    except ValueError:
        return f"workdir://{checkout_path.name}"
    return f"workdir://{relative.as_posix()}"


def _directory_size(path: Path) -> int:
    total = 0
    for item in path.rglob("*"):
        try:
            if item.is_file() or item.is_symlink():
                total += item.stat().st_size
        except OSError:
            continue
    return total


def _int_env(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        return int(raw_value)
    except ValueError:
        return default


def _external_scanner_timeout() -> int:
    return max(
        10,
        _int_env(
            "CODE_SCAN_EXTERNAL_SCANNER_TIMEOUT_SECONDS",
            DEFAULT_EXTERNAL_SCANNER_TIMEOUT_SECONDS,
        ),
    )


def _cleanup_scan_workdir(workdir: Path) -> None:
    checkouts_dir = workdir / "checkouts"
    if not checkouts_dir.exists():
        return
    retention_days = max(
        0,
        _int_env(
            "CODE_SCAN_FAILED_CHECKOUT_RETENTION_DAYS",
            DEFAULT_FAILED_CHECKOUT_RETENTION_DAYS,
        ),
    )
    cutoff_ts = datetime.now(UTC).timestamp() - retention_days * 24 * 60 * 60
    for checkout in checkouts_dir.iterdir():
        if not checkout.is_dir():
            continue
        try:
            if checkout.stat().st_mtime < cutoff_ts:
                shutil.rmtree(checkout, ignore_errors=True)
        except OSError:
            continue
    max_bytes = max(0, _int_env("CODE_SCAN_MAX_CHECKOUT_BYTES", DEFAULT_MAX_CHECKOUT_BYTES))
    checkout_dirs = [item for item in checkouts_dir.iterdir() if item.is_dir()]
    total_size = sum(_directory_size(item) for item in checkout_dirs)
    if total_size <= max_bytes:
        return
    checkout_dirs.sort(key=lambda item: item.stat().st_mtime if item.exists() else 0)
    for checkout in checkout_dirs:
        if total_size <= max_bytes:
            break
        checkout_size = _directory_size(checkout)
        shutil.rmtree(checkout, ignore_errors=True)
        total_size -= checkout_size


def _ensure_mirror(
    *,
    mirror_path: Path,
    remote_url: str,
) -> bool:
    if mirror_path.exists():
        _git(["fetch", "--prune", "--tags"], cwd=mirror_path, timeout=180)
        return True
    mirror_path.parent.mkdir(parents=True, exist_ok=True)
    _git(["clone", "--mirror", remote_url, str(mirror_path)], timeout=300)
    return False


def _resolve_mirror_branch_commit(mirror_path: Path, branch: str) -> str:
    refs = [
        f"refs/heads/{branch}",
        branch,
        f"origin/{branch}",
    ]
    for ref in refs:
        try:
            return _git(["rev-parse", ref], cwd=mirror_path, timeout=30)
        except subprocess.CalledProcessError:
            continue
    raise api_error(
        400,
        "CODE_SCAN_BRANCH_NOT_FOUND",
        f"Repository branch not found: {branch}",
    )


def _checkout_commit(
    *,
    checkout_path: Path,
    commit_sha: str,
    mirror_path: Path,
) -> None:
    _git(["clone", "--no-tags", str(mirror_path), str(checkout_path)], timeout=180)
    _git(["checkout", "--detach", commit_sha], cwd=checkout_path, timeout=60)


def _scan_root(repo_dir: Path, root_path: Any) -> Path:
    raw_root = str(root_path or "/").strip()
    if raw_root in {"", "/"}:
        return repo_dir
    normalized_root = raw_root.lstrip("/")
    root = (repo_dir / normalized_root).resolve()
    if repo_dir.resolve() not in [root, *root.parents]:
        raise api_error(400, "VALIDATION_ERROR", "Repository root_path is outside clone")
    if not root.exists() or not root.is_dir():
        raise api_error(
            400,
            "CODE_SCAN_ROOT_NOT_FOUND",
            f"Repository root_path not found: {raw_root}",
        )
    return root


def _iter_source_files(root: Path, *, ignored_dir_names: set[str] | None = None) -> list[Path]:
    files: list[Path] = []
    excluded_dir_names = set(EXCLUDED_DIR_NAMES)
    if ignored_dir_names:
        excluded_dir_names.update(ignored_dir_names)
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in excluded_dir_names for part in path.parts):
            continue
        try:
            if path.stat().st_size > TEXT_FILE_MAX_BYTES:
                continue
        except OSError:
            continue
        files.append(path)
    files.sort(key=lambda item: str(item))
    return files


def _read_text_lines(path: Path) -> list[str] | None:
    try:
        raw = path.read_bytes()
    except OSError:
        return None
    if b"\0" in raw:
        return None
    try:
        return raw.decode("utf-8").splitlines()
    except UnicodeDecodeError:
        try:
            return raw.decode("latin-1").splitlines()
        except UnicodeDecodeError:
            return None


def _blame_committer(repo_dir: Path, relative_path: str, line_number: int) -> dict[str, str | None]:
    try:
        output = _git(
            [
                "blame",
                "--line-porcelain",
                "-L",
                f"{line_number},{line_number}",
                "--",
                relative_path,
            ],
            cwd=repo_dir,
            timeout=20,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return {"email": None, "name": None, "username": None}
    name: str | None = None
    email: str | None = None
    for line in output.splitlines():
        if line.startswith("author "):
            name = line.removeprefix("author ").strip() or None
        elif line.startswith("author-mail "):
            email = line.removeprefix("author-mail ").strip().strip("<>") or None
    username = email.split("@", 1)[0] if email and "@" in email else None
    return {"email": email, "name": name, "username": username}


def _finding(
    *,
    branch: str,
    category: str,
    commit_sha: str,
    description: str,
    file_path: str,
    line_number: int,
    raw_evidence: dict[str, Any],
    recommendation: str,
    repository_id: str,
    rule_id: str,
    severity: str,
    title: str,
    committer: dict[str, str | None],
    scanner_name: str = NATIVE_CODE_SCANNER_NAME,
) -> dict[str, Any]:
    fingerprint = _native_finding_fingerprint(
        branch=branch,
        committer=committer,
        file_path=file_path,
        line_number=line_number,
        repository_id=repository_id,
        rule_id=rule_id,
    )
    return {
        "branch": branch,
        "category": category,
        "commit_sha": commit_sha,
        "committer_email": committer.get("email"),
        "committer_name": committer.get("name"),
        "committer_username": committer.get("username"),
        "description": description,
        "fingerprint": fingerprint,
        "file_path": file_path,
        "line_number": line_number,
        "raw": {
            **raw_evidence,
            "branch": branch,
            "commit_sha": commit_sha,
            "finding_fingerprint": fingerprint,
            "scan_mode": NATIVE_CODE_SCAN_MODE,
            "scanner_name": scanner_name,
        },
        "recommendation": recommendation,
        "repository_id": repository_id,
        "rule_id": rule_id,
        "scan_mode": NATIVE_CODE_SCAN_MODE,
        "scanner_name": scanner_name,
        "severity": severity,
        "title": title,
    }


def _native_finding_fingerprint(
    *,
    branch: str,
    committer: dict[str, str | None],
    file_path: str,
    line_number: int,
    repository_id: str,
    rule_id: str,
) -> str:
    committer_key = committer.get("email") or committer.get("username") or committer.get("name")
    payload = {
        "branch": branch,
        "committer": committer_key,
        "file_path": file_path,
        "line_number": line_number,
        "repository_id": repository_id,
        "rule_id": rule_id,
    }
    encoded = json_dumps(payload)
    return sha256(encoded.encode("utf-8")).hexdigest()


def json_dumps(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def _risk_level(findings: list[dict[str, Any]]) -> str:
    max_rank = 1
    for finding in findings:
        max_rank = max(max_rank, SEVERITY_RANK.get(str(finding.get("severity")), 1))
    for severity, rank in SEVERITY_RANK.items():
        if rank == max_rank:
            return severity
    return "low"


def _string_set(values: Any) -> set[str]:
    if not isinstance(values, list):
        return set()
    return {str(value).strip() for value in values if str(value or "").strip()}


def _fingerprint_from_finding(finding: dict[str, Any]) -> str | None:
    raw = finding.get("raw") if isinstance(finding.get("raw"), dict) else {}
    value = finding.get("fingerprint") or raw.get("finding_fingerprint")
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _apply_finding_filters(
    findings: list[dict[str, Any]],
    *,
    accepted_risk_fingerprints: set[str],
    baseline_fingerprints: set[str],
    ignored_finding_fingerprints: set[str],
    severity_threshold: str | None,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    threshold_rank = SEVERITY_RANK.get(str(severity_threshold or "").lower())
    kept: list[dict[str, Any]] = []
    summary = {
        "accepted_risk": 0,
        "baseline": 0,
        "ignored": 0,
        "severity_threshold": 0,
    }
    for finding in findings:
        fingerprint = _fingerprint_from_finding(finding)
        if fingerprint and fingerprint in ignored_finding_fingerprints:
            summary["ignored"] += 1
            continue
        if fingerprint and fingerprint in accepted_risk_fingerprints:
            summary["accepted_risk"] += 1
            continue
        if fingerprint and fingerprint in baseline_fingerprints:
            summary["baseline"] += 1
            continue
        if threshold_rank is not None:
            finding_rank = SEVERITY_RANK.get(str(finding.get("severity") or "").lower(), 0)
            if finding_rank < threshold_rank:
                summary["severity_threshold"] += 1
                continue
        kept.append(finding)
    return kept, summary


def _quality_gate_summary(
    findings: list[dict[str, Any]],
    *,
    config: Any,
) -> dict[str, Any]:
    if not isinstance(config, dict) or not config.get("enabled"):
        return {"enabled": False, "status": "skipped", "violations": []}
    counts = {
        "critical": sum(1 for finding in findings if finding.get("severity") == "critical"),
        "high": sum(1 for finding in findings if finding.get("severity") == "high"),
        "medium": sum(1 for finding in findings if finding.get("severity") == "medium"),
        "total": len(findings),
    }
    limit_fields = {
        "critical": "critical_max",
        "high": "high_max",
        "medium": "medium_max",
        "total": "total_max",
    }
    violations: list[dict[str, Any]] = []
    for severity, field in limit_fields.items():
        if field not in config:
            continue
        try:
            limit = int(config[field])
        except (TypeError, ValueError):
            continue
        value = counts[severity]
        if value > limit:
            violations.append({"limit": limit, "severity": severity, "value": value})
    return {
        "counts": counts,
        "enabled": True,
        "status": "failed" if violations else "passed",
        "violations": violations,
    }


def _scan_files(
    *,
    branch: str,
    commit_sha: str,
    repo_dir: Path,
    repository_id: str,
    root: Path,
    ignored_dir_names: set[str],
    ignored_rule_ids: set[str],
    included_relative_paths: set[str] | None,
    rules: list[str],
) -> tuple[list[dict[str, Any]], int, int]:
    findings: list[dict[str, Any]] = []
    files_scanned = 0
    lines_scanned = 0
    enabled_rules = set(rules)
    for path in _iter_source_files(root, ignored_dir_names=ignored_dir_names):
        relative_path = str(path.relative_to(repo_dir))
        if included_relative_paths is not None and relative_path not in included_relative_paths:
            continue
        lines = _read_text_lines(path)
        if lines is None:
            continue
        files_scanned += 1
        lines_scanned += len(lines)
        for line_number, line in enumerate(lines, start=1):
            if (
                "secrets" in enabled_rules
                and "secrets.hardcoded_credential" not in ignored_rule_ids
                and SECRET_ASSIGNMENT_RE.search(line)
            ):
                committer = _blame_committer(repo_dir, relative_path, line_number)
                findings.append(
                    _finding(
                        branch=branch,
                        category="security",
                        commit_sha=commit_sha,
                        committer=committer,
                        description="源代码中存在疑似硬编码敏感凭据。",
                        file_path=relative_path,
                        line_number=line_number,
                        raw_evidence={"evidence": "credential_assignment_redacted"},
                        recommendation="将凭据移入密钥管理或运行时环境变量，并轮换已提交的密钥。",
                        repository_id=repository_id,
                        rule_id="secrets.hardcoded_credential",
                        severity="critical",
                        title="硬编码敏感凭据",
                    ),
                )
            if (
                "internal_addresses" in enabled_rules
                and "metadata.internal_address_exposure" not in ignored_rule_ids
                and INTERNAL_ADDRESS_RE.search(line)
            ):
                committer = _blame_committer(repo_dir, relative_path, line_number)
                findings.append(
                    _finding(
                        branch=branch,
                        category="security",
                        commit_sha=commit_sha,
                        committer=committer,
                        description="源代码或配置中暴露了内部服务地址。",
                        file_path=relative_path,
                        line_number=line_number,
                        raw_evidence={"evidence": "internal_address_redacted"},
                        recommendation="避免在可访问代码中暴露内部地址，改为使用环境配置或服务发现。",
                        repository_id=repository_id,
                        rule_id="metadata.internal_address_exposure",
                        severity="medium",
                        title="内部服务地址暴露",
                    ),
                )
    return findings, files_scanned, lines_scanned


def _external_scanner_command(engine: str, *, executable: str, root: Path) -> list[str]:
    if engine == "semgrep":
        return [executable, "scan", "--json", "--quiet", str(root)]
    if engine == "gitleaks":
        return [
            executable,
            "detect",
            "--source",
            str(root),
            "--no-git",
            "--report-format",
            "json",
            "--redact",
        ]
    if engine == "trivy":
        return [executable, "fs", "--format", "json", "--quiet", str(root)]
    if engine == "npm":
        return [executable, "audit", "--json"]
    if engine == "pip-audit":
        return [executable, "-f", "json", "--path", str(root)]
    if engine == "dependency-check":
        return [executable, "--scan", str(root), "--format", "JSON", "--out", "-"]
    return [executable]


def _json_from_process_output(output: str) -> Any:
    text = output.strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        first_object = text.find("{")
        first_array = text.find("[")
        candidates = [index for index in [first_object, first_array] if index >= 0]
        if not candidates:
            return None
        try:
            return json.loads(text[min(candidates) :])
        except json.JSONDecodeError:
            return None


def _external_severity(engine: str, value: Any) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return "critical" if engine == "gitleaks" else "medium"
    mappings = {
        "blocker": "critical",
        "critical": "critical",
        "error": "high",
        "fatal": "critical",
        "high": "high",
        "info": "info",
        "informational": "info",
        "low": "low",
        "medium": "medium",
        "moderate": "medium",
        "warning": "medium",
    }
    return mappings.get(text, "medium")


def _external_path(
    *,
    path_value: Any,
    repo_dir: Path,
    root: Path,
) -> str | None:
    raw_path = str(path_value or "").strip()
    if not raw_path:
        return None
    candidate = Path(raw_path)
    try:
        if candidate.is_absolute():
            resolved = candidate.resolve()
        elif (repo_dir / candidate).exists():
            resolved = (repo_dir / candidate).resolve()
        else:
            resolved = (root / candidate).resolve()
        return resolved.relative_to(repo_dir.resolve()).as_posix()
    except (OSError, ValueError):
        return raw_path.replace("\\", "/").lstrip("/")


def _external_committer(
    *,
    repo_dir: Path,
    raw: dict[str, Any],
    relative_path: str,
    line_number: int,
) -> dict[str, str | None]:
    email = raw.get("Email") or raw.get("email") or raw.get("author_email")
    name = raw.get("Author") or raw.get("author") or raw.get("name") or raw.get("author_name")
    username = raw.get("Username") or raw.get("username")
    if email or name or username:
        email_text = str(email).strip() if email else None
        name_text = str(name).strip() if name else None
        username_text = (
            str(username).strip()
            if username
            else email_text.split("@", 1)[0]
            if email_text and "@" in email_text
            else None
        )
        return {"email": email_text, "name": name_text, "username": username_text}
    return _blame_committer(repo_dir, relative_path, line_number)


def _is_ignored_external_finding(
    *,
    ignored_dir_names: set[str],
    ignored_rule_ids: set[str],
    included_relative_paths: set[str] | None,
    relative_path: str,
    rule_id: str,
) -> bool:
    if rule_id in ignored_rule_ids:
        return True
    if included_relative_paths is not None and relative_path not in included_relative_paths:
        return True
    path_parts = set(Path(relative_path).parts)
    return bool(path_parts.intersection(ignored_dir_names))


def _semgrep_findings(
    payload: Any,
    *,
    branch: str,
    commit_sha: str,
    ignored_dir_names: set[str],
    ignored_rule_ids: set[str],
    included_relative_paths: set[str] | None,
    repo_dir: Path,
    repository_id: str,
    root: Path,
) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    results = payload.get("results")
    if not isinstance(results, list):
        return []
    findings: list[dict[str, Any]] = []
    for result in results:
        if not isinstance(result, dict):
            continue
        relative_path = _external_path(path_value=result.get("path"), repo_dir=repo_dir, root=root)
        if not relative_path:
            continue
        check_id = str(result.get("check_id") or "semgrep.finding").strip()
        rule_id = f"semgrep.{check_id}"
        start = result.get("start") if isinstance(result.get("start"), dict) else {}
        try:
            line_number = int(start.get("line") or 1)
        except (TypeError, ValueError):
            line_number = 1
        if _is_ignored_external_finding(
            ignored_dir_names=ignored_dir_names,
            ignored_rule_ids=ignored_rule_ids,
            included_relative_paths=included_relative_paths,
            relative_path=relative_path,
            rule_id=rule_id,
        ):
            continue
        extra = result.get("extra") if isinstance(result.get("extra"), dict) else {}
        metadata = extra.get("metadata") if isinstance(extra.get("metadata"), dict) else {}
        category = str(metadata.get("category") or "quality")
        message = str(extra.get("message") or check_id)
        committer = _blame_committer(repo_dir, relative_path, line_number)
        findings.append(
            _finding(
                branch=branch,
                category=category,
                commit_sha=commit_sha,
                committer=committer,
                description=message,
                file_path=relative_path,
                line_number=line_number,
                raw_evidence={
                    "external_engine": "semgrep",
                    "external_rule_id": check_id,
                    "external_severity": extra.get("severity"),
                },
                recommendation="按 Semgrep 规则说明完成代码安全或规范整改。",
                repository_id=repository_id,
                rule_id=rule_id,
                scanner_name="semgrep",
                severity=_external_severity("semgrep", extra.get("severity")),
                title=message,
            )
        )
    return findings


def _gitleaks_findings(
    payload: Any,
    *,
    branch: str,
    commit_sha: str,
    ignored_dir_names: set[str],
    ignored_rule_ids: set[str],
    included_relative_paths: set[str] | None,
    repo_dir: Path,
    repository_id: str,
    root: Path,
) -> list[dict[str, Any]]:
    if not isinstance(payload, list):
        return []
    findings: list[dict[str, Any]] = []
    for result in payload:
        if not isinstance(result, dict):
            continue
        relative_path = _external_path(
            path_value=result.get("File") or result.get("file"),
            repo_dir=repo_dir,
            root=root,
        )
        if not relative_path:
            continue
        rule_key = str(result.get("RuleID") or result.get("rule_id") or "secret").strip()
        rule_id = f"gitleaks.{rule_key}"
        try:
            line_number = int(result.get("StartLine") or result.get("line") or 1)
        except (TypeError, ValueError):
            line_number = 1
        if _is_ignored_external_finding(
            ignored_dir_names=ignored_dir_names,
            ignored_rule_ids=ignored_rule_ids,
            included_relative_paths=included_relative_paths,
            relative_path=relative_path,
            rule_id=rule_id,
        ):
            continue
        description = str(result.get("Description") or "Gitleaks 发现疑似密钥泄露。")
        committer = _external_committer(
            raw=result,
            relative_path=relative_path,
            line_number=line_number,
            repo_dir=repo_dir,
        )
        findings.append(
            _finding(
                branch=branch,
                category="security",
                commit_sha=commit_sha,
                committer=committer,
                description=description,
                file_path=relative_path,
                line_number=line_number,
                raw_evidence={
                    "external_engine": "gitleaks",
                    "external_rule_id": rule_key,
                    "external_severity": "critical",
                },
                recommendation="轮换已提交密钥，并通过密钥管理或运行时环境变量注入。",
                repository_id=repository_id,
                rule_id=rule_id,
                scanner_name="gitleaks",
                severity="critical",
                title=description,
            )
        )
    return findings


def _trivy_findings(
    payload: Any,
    *,
    branch: str,
    commit_sha: str,
    ignored_dir_names: set[str],
    ignored_rule_ids: set[str],
    included_relative_paths: set[str] | None,
    repo_dir: Path,
    repository_id: str,
    root: Path,
) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    results = payload.get("Results")
    if not isinstance(results, list):
        return []
    findings: list[dict[str, Any]] = []
    for result in results:
        if not isinstance(result, dict):
            continue
        relative_path = _external_path(
            path_value=result.get("Target") or "dependency-manifest",
            repo_dir=repo_dir,
            root=root,
        ) or "dependency-manifest"
        vulnerabilities = result.get("Vulnerabilities")
        if not isinstance(vulnerabilities, list):
            continue
        for vulnerability in vulnerabilities:
            if not isinstance(vulnerability, dict):
                continue
            vulnerability_id = str(
                vulnerability.get("VulnerabilityID") or vulnerability.get("ID") or "vulnerability"
            ).strip()
            rule_id = f"trivy.{vulnerability_id}"
            if _is_ignored_external_finding(
                ignored_dir_names=ignored_dir_names,
                ignored_rule_ids=ignored_rule_ids,
                included_relative_paths=included_relative_paths,
                relative_path=relative_path,
                rule_id=rule_id,
            ):
                continue
            title = str(vulnerability.get("Title") or vulnerability_id)
            package_name = str(vulnerability.get("PkgName") or "")
            findings.append(
                _finding(
                    branch=branch,
                    category="dependency",
                    commit_sha=commit_sha,
                    committer=_blame_committer(repo_dir, relative_path, 1),
                    description=title,
                    file_path=relative_path,
                    line_number=1,
                    raw_evidence={
                        "external_engine": "trivy",
                        "external_package": package_name,
                        "external_rule_id": vulnerability_id,
                        "external_severity": vulnerability.get("Severity"),
                    },
                    recommendation="升级受影响依赖版本，并确认运行镜像或锁文件已同步更新。",
                    repository_id=repository_id,
                    rule_id=rule_id,
                    scanner_name="trivy",
                    severity=_external_severity("trivy", vulnerability.get("Severity")),
                    title=title,
                )
            )
    return findings


def _external_findings(
    engine: str,
    payload: Any,
    *,
    branch: str,
    commit_sha: str,
    ignored_dir_names: set[str],
    ignored_rule_ids: set[str],
    included_relative_paths: set[str] | None,
    repo_dir: Path,
    repository_id: str,
    root: Path,
) -> list[dict[str, Any]]:
    if engine == "semgrep":
        return _semgrep_findings(
            payload,
            branch=branch,
            commit_sha=commit_sha,
            ignored_dir_names=ignored_dir_names,
            ignored_rule_ids=ignored_rule_ids,
            included_relative_paths=included_relative_paths,
            repo_dir=repo_dir,
            repository_id=repository_id,
            root=root,
        )
    if engine == "gitleaks":
        return _gitleaks_findings(
            payload,
            branch=branch,
            commit_sha=commit_sha,
            ignored_dir_names=ignored_dir_names,
            ignored_rule_ids=ignored_rule_ids,
            included_relative_paths=included_relative_paths,
            repo_dir=repo_dir,
            repository_id=repository_id,
            root=root,
        )
    if engine == "trivy":
        return _trivy_findings(
            payload,
            branch=branch,
            commit_sha=commit_sha,
            ignored_dir_names=ignored_dir_names,
            ignored_rule_ids=ignored_rule_ids,
            included_relative_paths=included_relative_paths,
            repo_dir=repo_dir,
            repository_id=repository_id,
            root=root,
        )
    return []


def _run_external_scanners(
    *,
    branch: str,
    commit_sha: str,
    engines: list[str],
    ignored_dir_names: set[str],
    ignored_rule_ids: set[str],
    included_relative_paths: set[str] | None,
    repo_dir: Path,
    repository_id: str,
    root: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any], list[str]]:
    findings: list[dict[str, Any]] = []
    status: dict[str, Any] = {
        "configured": engines,
        "executed": [],
        "failed": [],
        "failure_reasons": {},
        "skipped": [],
        "skip_reasons": {},
    }
    warnings: list[str] = []
    timeout = _external_scanner_timeout()
    for engine in engines:
        executable = shutil.which(engine)
        if executable is None:
            status["skipped"].append(engine)
            status["skip_reasons"][engine] = "not_installed"
            warnings.append(f"{engine} 未安装")
            continue
        command = _external_scanner_command(engine, executable=executable, root=root)
        try:
            completed = subprocess.run(
                command,
                cwd=str(root),
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            status["failed"].append(engine)
            status["failure_reasons"][engine] = "timeout"
            warnings.append(f"{engine} 执行超时")
            continue
        payload = _json_from_process_output(completed.stdout)
        if payload is None:
            payload = _json_from_process_output(completed.stderr)
        if payload is None:
            status["failed"].append(engine)
            reason = (
                completed.stderr or completed.stdout or f"exit {completed.returncode}"
            ).strip()
            status["failure_reasons"][engine] = reason[:500] or "empty_output"
            warnings.append(f"{engine} 未返回可解析 JSON")
            continue
        engine_findings = _external_findings(
            engine,
            payload,
            branch=branch,
            commit_sha=commit_sha,
            ignored_dir_names=ignored_dir_names,
            ignored_rule_ids=ignored_rule_ids,
            included_relative_paths=included_relative_paths,
            repo_dir=repo_dir,
            repository_id=repository_id,
            root=root,
        )
        findings.extend(engine_findings)
        status["executed"].append(engine)
    if not status["failure_reasons"]:
        status.pop("failure_reasons")
    if not status["skip_reasons"]:
        status.pop("skip_reasons")
    return findings, status, warnings


def _incremental_changed_files(
    *,
    from_commit: str,
    repo_dir: Path,
    to_commit: str,
) -> set[str]:
    try:
        output = _git(
            [
                "diff",
                "--name-only",
                "--diff-filter=ACMRT",
                from_commit,
                to_commit,
                "--",
            ],
            cwd=repo_dir,
            timeout=30,
        )
    except subprocess.CalledProcessError:
        raise api_error(
            400,
            "CODE_SCAN_INCREMENTAL_BASE_INVALID",
            f"incremental_from_commit is not available: {from_commit}",
        ) from None
    return {line.strip() for line in output.splitlines() if line.strip()}


def run_native_code_scan(
    current_store: Any,
    *,
    job: dict[str, Any],
    run_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    started = perf_counter()
    job_config = job.get("config_json") or {}
    repository_id = str(job_config.get("repository_id") or "").strip()
    if not repository_id:
        raise api_error(400, "CODE_SCAN_REPOSITORY_REQUIRED", "repository_id is required")
    sync_product_git_repository_store(current_store, job.get("product_id"))
    repository = current_store.product_git_repositories.get(repository_id)
    if repository is None:
        raise api_error(404, "NOT_FOUND", "Product Git repository not found")
    if job.get("product_id") and repository.get("product_id") != job.get("product_id"):
        raise api_error(400, "VALIDATION_ERROR", "Repository does not belong to product")
    remote_url = str(repository.get("remote_url") or "").strip()
    if not remote_url:
        raise api_error(400, "CODE_SCAN_REMOTE_URL_REQUIRED", "Repository remote_url is required")
    branch = str(job_config.get("branch") or repository.get("default_branch") or "main").strip()
    rules = [
        str(rule)
        for rule in job_config.get("scan_rules", DEFAULT_SCAN_RULES)
        if str(rule) in DEFAULT_SCAN_RULES
    ]
    if not rules:
        rules = list(DEFAULT_SCAN_RULES)
    ignored_dir_names = {
        str(value).strip().strip("/")
        for value in job_config.get("ignore_dirs", [])
        if str(value or "").strip()
    }
    ignored_rule_ids = {
        str(value).strip()
        for value in job_config.get("ignore_rules", [])
        if str(value or "").strip()
    }
    ignored_finding_fingerprints = _string_set(job_config.get("ignored_finding_fingerprints"))
    accepted_risk_fingerprints = _string_set(job_config.get("accepted_risk_fingerprints"))
    baseline_fingerprints = _string_set(job_config.get("baseline_fingerprints"))
    baseline_config = job_config.get("baseline")
    if isinstance(baseline_config, dict):
        baseline_fingerprints.update(_string_set(baseline_config.get("fingerprints")))
    severity_threshold = str(job_config.get("severity_threshold") or "").strip().lower() or None
    if severity_threshold not in SEVERITY_RANK:
        severity_threshold = None
    scanner_engines = [
        str(value).strip()
        for value in job_config.get("scanner_engines", ["builtin"])
        if str(value or "").strip()
    ]
    if "builtin" not in scanner_engines:
        scanner_engines.insert(0, "builtin")
    external_engines = [engine for engine in scanner_engines if engine != "builtin"]
    external_scanner_status: dict[str, Any] = {
        "configured": external_engines,
        "executed": [],
        "failed": [],
        "skipped": [],
    }
    external_coverage_warnings: list[str] = []
    incremental_from_commit = str(job_config.get("incremental_from_commit") or "").strip() or None
    incremental_file_count: int | None = None

    scan_started_at = datetime.now(UTC).isoformat()
    workdir = _scan_workdir()
    _cleanup_scan_workdir(workdir)
    remote_hash = _remote_url_hash(remote_url)
    remote_summary = _remote_url_summary(remote_url)
    repo_key = _safe_slug(f"{repository_id}-{remote_hash[:16]}", fallback=remote_hash[:16])
    mirror_path = workdir / "mirrors" / f"{repo_key}.git"
    checkout_path: Path | None = None
    artifact_ref: str | None = None
    checkout_path_retained = False
    mirror_cache_hit = False
    try:
        mirror_cache_hit = _ensure_mirror(mirror_path=mirror_path, remote_url=remote_url)
        commit_sha = _resolve_mirror_branch_commit(mirror_path, branch)
        checkout_name = "__".join(
            [
                _safe_slug(run_id, fallback="run"),
                _safe_slug(repository_id, fallback="repo"),
                _safe_slug(branch, fallback="branch"),
                commit_sha[:12],
            ]
        )
        checkout_path = workdir / "checkouts" / checkout_name
        _checkout_commit(
            checkout_path=checkout_path,
            commit_sha=commit_sha,
            mirror_path=mirror_path,
        )
        artifact_ref = _checkout_artifact_ref(checkout_path, workdir)
        root = _scan_root(checkout_path, repository.get("root_path"))
        included_relative_paths = None
        if incremental_from_commit:
            included_relative_paths = _incremental_changed_files(
                from_commit=incremental_from_commit,
                repo_dir=checkout_path,
                to_commit=commit_sha,
            )
            incremental_file_count = len(included_relative_paths)
        findings, files_scanned, lines_scanned = _scan_files(
            branch=branch,
            commit_sha=commit_sha,
            ignored_dir_names=ignored_dir_names,
            ignored_rule_ids=ignored_rule_ids,
            included_relative_paths=included_relative_paths,
            repo_dir=checkout_path,
            repository_id=repository_id,
            root=root,
            rules=rules,
        )
        external_findings, external_scanner_status, external_coverage_warnings = (
            _run_external_scanners(
                branch=branch,
                commit_sha=commit_sha,
                engines=external_engines,
                ignored_dir_names=ignored_dir_names,
                ignored_rule_ids=ignored_rule_ids,
                included_relative_paths=included_relative_paths,
                repo_dir=checkout_path,
                repository_id=repository_id,
                root=root,
            )
        )
        findings.extend(external_findings)
        findings, suppression_summary = _apply_finding_filters(
            findings,
            accepted_risk_fingerprints=accepted_risk_fingerprints,
            baseline_fingerprints=baseline_fingerprints,
            ignored_finding_fingerprints=ignored_finding_fingerprints,
            severity_threshold=severity_threshold,
        )
        quality_gate = _quality_gate_summary(findings, config=job_config.get("quality_gate"))
        retain_success_checkout = bool(job_config.get("retain_success_checkout"))
        if retain_success_checkout:
            checkout_path_retained = True
        elif checkout_path.exists():
            shutil.rmtree(checkout_path, ignore_errors=True)
    except subprocess.TimeoutExpired:
        checkout_path_retained = bool(checkout_path and checkout_path.exists())
        raise api_error(504, "CODE_SCAN_TIMEOUT", "Native code scan timed out") from None
    except subprocess.CalledProcessError as exc:
        checkout_path_retained = bool(checkout_path and checkout_path.exists())
        message = (exc.stderr or exc.stdout or str(exc)).strip()
        raise api_error(502, "CODE_SCAN_GIT_FAILED", message or "Git command failed") from None
    finally:
        scan_finished_at = datetime.now(UTC).isoformat()

    suppressed_finding_count = sum(suppression_summary.values())
    coverage_warning = (
        "；".join(f"外部扫描引擎{message}" for message in external_coverage_warnings)
        if external_coverage_warnings
        else None
    )
    scan_profile = {
        "accepted_risk_fingerprint_count": len(accepted_risk_fingerprints),
        "baseline_fingerprint_count": len(baseline_fingerprints),
        "external_scanner_status": external_scanner_status,
        "ignore_dirs": sorted(ignored_dir_names),
        "ignore_rules": sorted(ignored_rule_ids),
        "ignored_finding_fingerprint_count": len(ignored_finding_fingerprints),
        "scanner_engines": scanner_engines,
        "severity_threshold": severity_threshold,
    }
    output_json = {
        "artifact_ref": artifact_ref,
        "branch": branch,
        "checkout_path": str(checkout_path) if checkout_path_retained and checkout_path else None,
        "checkout_path_retained": checkout_path_retained,
        "commit_sha": commit_sha,
        "coverage_warning": coverage_warning,
        "external_scanner_status": external_scanner_status,
        "files_scanned": files_scanned,
        "finding_count": len(findings),
        "findings": findings,
        "incremental_file_count": incremental_file_count,
        "incremental_from_commit": incremental_from_commit,
        "is_full_scan": incremental_from_commit is None,
        "lines_scanned": lines_scanned,
        "quality_gate": quality_gate,
        "repository_id": repository_id,
        "risk_level": _risk_level(findings),
        "rules_loaded": rules,
        "rules_version": NATIVE_CODE_RULES_VERSION,
        "scan_profile": scan_profile,
        "scan_mode": NATIVE_CODE_SCAN_MODE,
        "scan_finished_at": scan_finished_at,
        "scan_started_at": scan_started_at,
        "scanner_name": NATIVE_CODE_SCANNER_NAME,
        "scanner_version": NATIVE_CODE_SCANNER_VERSION,
        "remote_url_hash": remote_hash,
        "remote_url_summary": remote_summary,
        "suppressed_finding_count": suppressed_finding_count,
        "suppression_summary": suppression_summary,
        "summary": (
            f"本地完整扫描完成：扫描 {files_scanned} 个文件 / "
            f"{lines_scanned} 行，发现 {len(findings)} 个问题，"
            f"过滤 {suppressed_finding_count} 个历史或忽略项。"
        ),
    }
    latency_ms = int((perf_counter() - started) * 1000)
    return {
        "action_id": None,
        "connection_id": None,
        "invocation_log_id": None,
        "latency_ms": latency_ms,
        "request_summary": {
            "branch": branch,
            "processing_mode": NATIVE_CODE_SCAN_MODE,
            "repository_id": repository_id,
            "run_id": run_id,
            "scan_mode": NATIVE_CODE_SCAN_MODE,
            "scan_rules": rules,
            "user_id": user.get("id"),
        },
        "response_summary": {
            "json": output_json,
            "native_scan": {
                "artifact_ref": artifact_ref,
                "branch": branch,
                "checkout_path": (
                    str(checkout_path) if checkout_path_retained and checkout_path else None
                ),
                "checkout_path_retained": checkout_path_retained,
                "commit_sha": commit_sha,
                "files_scanned": files_scanned,
                "finding_count": len(findings),
                "incremental_file_count": incremental_file_count,
                "incremental_from_commit": incremental_from_commit,
                "lines_scanned": lines_scanned,
                "mirror_cache_hit": mirror_cache_hit,
                "quality_gate": quality_gate,
                "remote_url_hash": remote_hash,
                "remote_url_summary": remote_summary,
                "repository_id": repository_id,
                "rules_version": NATIVE_CODE_RULES_VERSION,
                "scan_profile": scan_profile,
                "scan_mode": NATIVE_CODE_SCAN_MODE,
                "scan_finished_at": scan_finished_at,
                "scan_started_at": scan_started_at,
                "scanner_name": NATIVE_CODE_SCANNER_NAME,
                "scanner_version": NATIVE_CODE_SCANNER_VERSION,
                "suppressed_finding_count": suppressed_finding_count,
                "suppression_summary": suppression_summary,
            },
            "status_code": None,
        },
        "status": "succeeded",
    }
