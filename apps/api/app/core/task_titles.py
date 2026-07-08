from __future__ import annotations

from typing import Any

CODE_INSPECTION_REMEDIATION_TITLE_PREFIX = "[Code Inspection Remediation]"
CODE_INSPECTION_REMEDIATION_TITLE_SEPARATOR = " · "


def _clean_code_inspection_title(value: Any) -> str:
    text = str(value or "").strip()
    if text.startswith(CODE_INSPECTION_REMEDIATION_TITLE_PREFIX):
        text = text[len(CODE_INSPECTION_REMEDIATION_TITLE_PREFIX) :].strip()
    if CODE_INSPECTION_REMEDIATION_TITLE_SEPARATOR in text:
        text = text.rsplit(CODE_INSPECTION_REMEDIATION_TITLE_SEPARATOR, 1)[1].strip()
    return text


def code_inspection_remediation_title(
    context: dict[str, Any] | None,
    *,
    fallback_title: Any = None,
) -> str:
    context = context if isinstance(context, dict) else {}
    title = (
        _clean_code_inspection_title(context.get("title"))
        or _clean_code_inspection_title(fallback_title)
        or str(context.get("rule_id") or "Code inspection finding").strip()
    )
    file_path = str(context.get("file_path") or "").strip()
    line_number = context.get("line_number")
    line_text = str(line_number).strip() if line_number not in (None, "") else ""
    if file_path and line_text:
        return (
            f"{CODE_INSPECTION_REMEDIATION_TITLE_PREFIX} "
            f"{file_path}:{line_text}{CODE_INSPECTION_REMEDIATION_TITLE_SEPARATOR}{title}"
        )
    if file_path:
        return (
            f"{CODE_INSPECTION_REMEDIATION_TITLE_PREFIX} "
            f"{file_path}{CODE_INSPECTION_REMEDIATION_TITLE_SEPARATOR}{title}"
        )
    return f"{CODE_INSPECTION_REMEDIATION_TITLE_PREFIX} {title}"
