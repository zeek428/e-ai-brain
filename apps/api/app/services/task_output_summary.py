from __future__ import annotations

import re
from typing import Any

MAX_OUTPUT_SUMMARY_CHARS = 6000

_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
_CODEX_TOKENS_RE = re.compile(
    r"(?im)^tokens used\s*\n\s*[\d,]+\s*$",
)
_SUMMARY_MARKERS = (
    "**整改状态",
    "整改状态：",
    "整改状态:",
    "## 整改",
    "**整改结果",
    "整改结果：",
    "整改结果:",
    "**执行结果",
    "执行结果：",
    "执行结果:",
    "**修复结果",
    "修复结果：",
    "修复结果:",
    "**处理结果",
    "处理结果：",
    "处理结果:",
    "**验证方式",
    "验证方式：",
    "验证方式:",
)


def _object_record(value: Any) -> dict[str, Any] | None:
    return value if isinstance(value, dict) else None


def _string_at_path(value: Any, *path: str) -> str | None:
    current = value
    for key in path:
        record = _object_record(current)
        if record is None:
            return None
        current = record.get(key)
    if isinstance(current, str):
        text = current.strip()
        return text or None
    return None


def _truncate_summary(text: str) -> str:
    if len(text) <= MAX_OUTPUT_SUMMARY_CHARS:
        return text
    return f"{text[:MAX_OUTPUT_SUMMARY_CHARS].rstrip()}\n\n...（摘要已截断）"


def _strip_codex_token_header(text: str) -> str:
    matches = list(_CODEX_TOKENS_RE.finditer(text))
    if not matches:
        return text
    return text[matches[-1].end() :].strip()


def _extract_output_preview_summary(output_preview: str) -> str | None:
    text = _ANSI_ESCAPE_RE.sub("", output_preview).replace("\r\n", "\n").strip()
    if not text:
        return None

    marker_index = -1
    for marker in _SUMMARY_MARKERS:
        index = text.find(marker)
        if index >= 0 and (marker_index < 0 or index < marker_index):
            marker_index = index
    if marker_index >= 0:
        text = text[marker_index:].strip()
    else:
        text = _strip_codex_token_header(text)

    text = re.sub(r"(?is)^tokens used\s*\n\s*[\d,]+\s*", "", text).strip()
    if not text:
        return None
    if text.startswith(("{", "[")) and "output_preview" in text:
        return None
    return _truncate_summary(text)


def readable_task_output_summary(output_json: Any) -> str | None:
    output = _object_record(output_json)
    if output is None:
        return None

    for path in (
        ("summary",),
        ("output_summary",),
        ("result", "summary"),
        ("result", "output_summary"),
        ("result", "result", "summary"),
        ("result", "result", "output_summary"),
        ("result", "parsed_output", "summary"),
        ("result", "parsed_output", "output_summary"),
        ("result", "parsed_output", "result", "summary"),
    ):
        summary = _string_at_path(output, *path)
        if summary:
            return _truncate_summary(summary)

    for path in (
        ("output_preview",),
        ("result", "output_preview"),
        ("result", "result", "output_preview"),
    ):
        preview = _string_at_path(output, *path)
        if not preview:
            continue
        summary = _extract_output_preview_summary(preview)
        if summary:
            return summary

    return None
