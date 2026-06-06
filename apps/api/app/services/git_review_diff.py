from __future__ import annotations

import json
from typing import Any


def summarize_gitlab_change(change: dict[str, Any]) -> dict[str, Any]:
    diff_lines = str(change.get("diff") or "").splitlines()
    additions = sum(1 for line in diff_lines if line.startswith("+") and not line.startswith("+++"))
    deletions = sum(1 for line in diff_lines if line.startswith("-") and not line.startswith("---"))
    return {
        "path": change.get("new_path") or change.get("old_path") or "-",
        "additions": additions,
        "deletions": deletions,
    }


def summarize_github_file(file_item: dict[str, Any]) -> dict[str, Any]:
    return {
        "path": file_item.get("filename") or "-",
        "additions": int(file_item.get("additions") or 0),
        "deletions": int(file_item.get("deletions") or 0),
    }


def changed_file_path(item: dict[str, Any]) -> str:
    return str(
        item.get("path")
        or item.get("file_path")
        or item.get("filename")
        or item.get("new_path")
        or item.get("old_path")
        or "-"
    )


def summarize_changed_files_for_review(
    changed_files_summary: list[dict[str, Any]],
) -> dict[str, Any]:
    file_tree: dict[str, dict[str, Any]] = {}
    total_additions = 0
    total_deletions = 0
    largest_file: dict[str, Any] | None = None
    for item in changed_files_summary:
        path = changed_file_path(item)
        additions = int(item.get("additions") or 0)
        deletions = int(item.get("deletions") or 0)
        line_count = additions + deletions
        total_additions += additions
        total_deletions += deletions
        if largest_file is None or line_count > int(largest_file.get("line_count") or 0):
            largest_file = {
                "additions": additions,
                "deletions": deletions,
                "line_count": line_count,
                "path": path,
            }
        root = path.split("/", 1)[0] if "/" in path else path
        node = file_tree.setdefault(
            root,
            {"additions": 0, "deletions": 0, "file_count": 0, "path": root},
        )
        node["additions"] += additions
        node["deletions"] += deletions
        node["file_count"] += 1
    file_count = len(changed_files_summary)
    total_changed_lines = total_additions + total_deletions
    if file_count > 30 or total_changed_lines > 1200:
        risk_level = "high"
    elif file_count > 10 or total_changed_lines > 400:
        risk_level = "medium"
    else:
        risk_level = "low"
    return {
        "diff_file_tree": sorted(
            file_tree.values(),
            key=lambda item: (-int(item["file_count"]), str(item["path"])),
        ),
        "review_checklist": [
            "确认变更文件归属目标需求和技术方案范围",
            "重点检查高变更量文件的异常处理、权限和数据一致性",
            "确认测试覆盖包含主要路径、边界场景和回归风险",
            "确认不包含密钥、凭据、调试输出或无关格式化变更",
        ],
        "risk_summary": {
            "file_count": file_count,
            "largest_file": largest_file,
            "risk_level": risk_level,
            "total_additions": total_additions,
            "total_changed_lines": total_changed_lines,
            "total_deletions": total_deletions,
        },
    }


def enrich_code_review_preview(preview: dict[str, Any]) -> dict[str, Any]:
    changed_files_summary = [
        item for item in preview.get("changed_files_summary", []) if isinstance(item, dict)
    ]
    return {**preview, **summarize_changed_files_for_review(changed_files_summary)}


def diff_payload(preview: dict[str, Any]) -> str:
    return json.dumps(
        {
            "mr_iid": preview["mr_iid"],
            "base_sha": preview["base_sha"],
            "head_sha": preview["head_sha"],
            "files": preview["changed_files_summary"],
        },
        sort_keys=True,
        ensure_ascii=False,
    )
