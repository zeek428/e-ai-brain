from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path, PurePosixPath
from typing import Any
from zipfile import BadZipFile, ZipFile

from app.api.deps import api_error

ALLOWED_SKILL_PACKAGE_SUFFIXES = {".json", ".md", ".txt", ".yaml", ".yml"}
MAX_SKILL_PACKAGE_BYTES = 2 * 1024 * 1024
MAX_SKILL_PACKAGE_FILE_COUNT = 50
MAX_SKILL_PACKAGE_UNCOMPRESSED_BYTES = 5 * 1024 * 1024


@dataclass(frozen=True)
class StoredSkillPackage:
    checksum: str
    entry: str
    entry_content: str
    files: list[str]
    manifest: dict[str, Any]
    package_uri: str
    size_bytes: int


def skill_package_storage_root() -> Path:
    return Path(os.getenv("AI_SKILL_STORAGE_DIR", "/tmp/ai-brain/skills"))


def parse_simple_yaml(raw: str) -> dict[str, Any]:
    manifest: dict[str, Any] = {}
    current_list_key: str | None = None
    for raw_line in raw.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("- ") and current_list_key is not None:
            manifest[current_list_key].append(_parse_scalar(stripped[2:].strip()))
            continue
        current_list_key = None
        if ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        key = key.strip()
        value = value.strip()
        if not value:
            manifest[key] = []
            current_list_key = key
        else:
            manifest[key] = _parse_scalar(value)
    return manifest


def _parse_scalar(value: str) -> Any:
    normalized = value.strip().strip("'\"")
    if normalized.lower() == "true":
        return True
    if normalized.lower() == "false":
        return False
    return normalized


def safe_skill_package_path(member_name: str) -> str:
    normalized = PurePosixPath(member_name)
    if normalized.is_absolute() or ".." in normalized.parts:
        raise api_error(400, "INVALID_SKILL_PACKAGE", "Skill package contains unsafe paths")
    if not normalized.name:
        raise api_error(400, "INVALID_SKILL_PACKAGE", "Skill package contains empty paths")
    suffix = normalized.suffix.lower()
    if suffix not in ALLOWED_SKILL_PACKAGE_SUFFIXES:
        raise api_error(400, "INVALID_SKILL_PACKAGE", "Skill package contains unsupported files")
    return str(normalized)


def store_skill_package(
    *,
    package_bytes: bytes,
    skill_code: str,
    skill_id: str,
    version: str,
) -> StoredSkillPackage:
    if not package_bytes:
        raise api_error(400, "INVALID_SKILL_PACKAGE", "Skill package is required")
    if len(package_bytes) > MAX_SKILL_PACKAGE_BYTES:
        raise api_error(400, "INVALID_SKILL_PACKAGE", "Skill package is too large")

    checksum = hashlib.sha256(package_bytes).hexdigest()
    try:
        with ZipFile(BytesIO(package_bytes)) as package:
            file_infos = [info for info in package.infolist() if not info.is_dir()]
            if len(file_infos) > MAX_SKILL_PACKAGE_FILE_COUNT:
                raise api_error(400, "INVALID_SKILL_PACKAGE", "Skill package has too many files")
            total_size = sum(info.file_size for info in file_infos)
            if total_size > MAX_SKILL_PACKAGE_UNCOMPRESSED_BYTES:
                raise api_error(400, "INVALID_SKILL_PACKAGE", "Skill package content is too large")
            files = [safe_skill_package_path(info.filename) for info in file_infos]
            if "skill.yaml" not in files and "SKILL.md" not in files:
                raise api_error(
                    400,
                    "INVALID_SKILL_PACKAGE",
                    "Skill package must contain skill.yaml or SKILL.md",
                )

            manifest = {}
            if "skill.yaml" in files:
                manifest = parse_simple_yaml(package.read("skill.yaml").decode("utf-8"))
            entry = str(manifest.get("entry") or "SKILL.md")
            if entry not in files:
                raise api_error(400, "INVALID_SKILL_PACKAGE", "Skill package entry file not found")
            entry_content = package.read(entry).decode("utf-8")

            target_dir = (
                skill_package_storage_root()
                / skill_code
                / version
                / checksum[:16]
            )
            target_dir.mkdir(parents=True, exist_ok=True)
            for file_name in files:
                target_path = target_dir / file_name
                target_path.parent.mkdir(parents=True, exist_ok=True)
                target_path.write_bytes(package.read(file_name))
    except BadZipFile as exc:
        raise api_error(400, "INVALID_SKILL_PACKAGE", "Skill package must be a zip file") from exc
    except UnicodeDecodeError as exc:
        raise api_error(
            400,
            "INVALID_SKILL_PACKAGE",
            "Skill package manifest and entry must be UTF-8 text",
        ) from exc

    return StoredSkillPackage(
        checksum=checksum,
        entry=entry,
        entry_content=entry_content,
        files=files,
        manifest=manifest,
        package_uri=f"file://{target_dir}",
        size_bytes=len(package_bytes),
    )


def load_skill_package_snapshot(skill: dict[str, Any]) -> dict[str, Any] | None:
    if skill.get("source_type") != "package":
        return None
    package_uri = skill.get("package_uri")
    entry = skill.get("package_entry") or (skill.get("manifest") or {}).get("entry") or "SKILL.md"
    if not package_uri or not str(package_uri).startswith("file://"):
        raise api_error(400, "INVALID_SKILL_PACKAGE", "Skill package URI is invalid")
    package_dir = Path(str(package_uri).removeprefix("file://"))
    entry_path = package_dir / safe_skill_package_path(str(entry))
    if not entry_path.exists():
        raise api_error(400, "INVALID_SKILL_PACKAGE", "Skill package entry file is missing")
    return {
        "checksum": skill.get("package_checksum"),
        "entry": str(entry),
        "entry_content": entry_path.read_text(encoding="utf-8"),
        "files": list(skill.get("package_files") or []),
        "manifest": dict(skill.get("manifest") or {}),
        "package_uri": package_uri,
    }
