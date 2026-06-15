from __future__ import annotations

import os
import re
import subprocess
import tempfile
from pathlib import Path
from time import perf_counter
from typing import Any

from app.api.deps import api_error
from app.services.code_inspections import sync_product_git_repository_store

NATIVE_CODE_SCAN_MODE = "native_full_scan"
NATIVE_CODE_SCANNER_NAME = "ai_brain_builtin_static"

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


def _checkout_branch(repo_dir: Path, branch: str) -> None:
    try:
        _git(["checkout", branch], cwd=repo_dir)
        return
    except subprocess.CalledProcessError:
        pass
    try:
        _git(["checkout", "-B", branch, f"origin/{branch}"], cwd=repo_dir)
        return
    except subprocess.CalledProcessError:
        raise api_error(
            400,
            "CODE_SCAN_BRANCH_NOT_FOUND",
            f"Repository branch not found: {branch}",
        ) from None


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


def _iter_source_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in EXCLUDED_DIR_NAMES for part in path.parts):
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
) -> dict[str, Any]:
    return {
        "branch": branch,
        "category": category,
        "commit_sha": commit_sha,
        "committer_email": committer.get("email"),
        "committer_name": committer.get("name"),
        "committer_username": committer.get("username"),
        "description": description,
        "file_path": file_path,
        "line_number": line_number,
        "raw": {
            **raw_evidence,
            "branch": branch,
            "commit_sha": commit_sha,
            "scan_mode": NATIVE_CODE_SCAN_MODE,
            "scanner_name": NATIVE_CODE_SCANNER_NAME,
        },
        "recommendation": recommendation,
        "repository_id": repository_id,
        "rule_id": rule_id,
        "scan_mode": NATIVE_CODE_SCAN_MODE,
        "scanner_name": NATIVE_CODE_SCANNER_NAME,
        "severity": severity,
        "title": title,
    }


def _risk_level(findings: list[dict[str, Any]]) -> str:
    max_rank = 1
    for finding in findings:
        max_rank = max(max_rank, SEVERITY_RANK.get(str(finding.get("severity")), 1))
    for severity, rank in SEVERITY_RANK.items():
        if rank == max_rank:
            return severity
    return "low"


def _scan_files(
    *,
    branch: str,
    commit_sha: str,
    repo_dir: Path,
    repository_id: str,
    root: Path,
    rules: list[str],
) -> tuple[list[dict[str, Any]], int, int]:
    findings: list[dict[str, Any]] = []
    files_scanned = 0
    lines_scanned = 0
    enabled_rules = set(rules)
    for path in _iter_source_files(root):
        lines = _read_text_lines(path)
        if lines is None:
            continue
        files_scanned += 1
        lines_scanned += len(lines)
        relative_path = str(path.relative_to(repo_dir))
        for line_number, line in enumerate(lines, start=1):
            if "secrets" in enabled_rules and SECRET_ASSIGNMENT_RE.search(line):
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
            if "internal_addresses" in enabled_rules and INTERNAL_ADDRESS_RE.search(line):
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

    with tempfile.TemporaryDirectory(prefix="ai-brain-native-scan-") as temp_dir:
        repo_dir = Path(temp_dir) / "repo"
        try:
            _git(["clone", "--no-tags", remote_url, str(repo_dir)], timeout=180)
            _checkout_branch(repo_dir, branch)
            commit_sha = _git(["rev-parse", "HEAD"], cwd=repo_dir)
            root = _scan_root(repo_dir, repository.get("root_path"))
            findings, files_scanned, lines_scanned = _scan_files(
                branch=branch,
                commit_sha=commit_sha,
                repo_dir=repo_dir,
                repository_id=repository_id,
                root=root,
                rules=rules,
            )
        except subprocess.TimeoutExpired:
            raise api_error(504, "CODE_SCAN_TIMEOUT", "Native code scan timed out") from None
        except subprocess.CalledProcessError as exc:
            message = (exc.stderr or exc.stdout or str(exc)).strip()
            raise api_error(502, "CODE_SCAN_GIT_FAILED", message or "Git command failed") from None

    output_json = {
        "branch": branch,
        "commit_sha": commit_sha,
        "coverage_warning": None,
        "files_scanned": files_scanned,
        "finding_count": len(findings),
        "findings": findings,
        "is_full_scan": True,
        "lines_scanned": lines_scanned,
        "repository_id": repository_id,
        "risk_level": _risk_level(findings),
        "rules_loaded": rules,
        "scan_mode": NATIVE_CODE_SCAN_MODE,
        "scanner_name": NATIVE_CODE_SCANNER_NAME,
        "summary": (
            f"本地完整扫描完成：扫描 {files_scanned} 个文件 / "
            f"{lines_scanned} 行，发现 {len(findings)} 个问题。"
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
                "branch": branch,
                "commit_sha": commit_sha,
                "files_scanned": files_scanned,
                "finding_count": len(findings),
                "lines_scanned": lines_scanned,
                "scan_mode": NATIVE_CODE_SCAN_MODE,
                "scanner_name": NATIVE_CODE_SCANNER_NAME,
            },
            "status_code": None,
        },
        "status": "succeeded",
    }
