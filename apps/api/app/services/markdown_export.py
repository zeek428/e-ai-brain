from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from app.services.task_access import can_read_task


def _ai_task_rows(current_store: Any) -> dict[str, dict[str, Any]]:
    repository = getattr(current_store, "repository", None)
    load_ai_tasks = getattr(repository, "load_ai_tasks", None)
    if callable(load_ai_tasks):
        payload = load_ai_tasks() or {}
        rows = payload.get("ai_tasks", {})
        return rows if isinstance(rows, dict) else {}
    rows = getattr(current_store, "ai_tasks", {})
    return rows if isinstance(rows, dict) else {}


def _ai_task_by_id(current_store: Any, task_id: Any) -> dict[str, Any] | None:
    if task_id is None:
        return None
    return _ai_task_rows(current_store).get(str(task_id))


def require_markdown_export_task(
    user: dict[str, Any],
    task: dict[str, Any] | None,
) -> dict[str, Any]:
    if task is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": "AI task not found"},
        )
    if not can_read_task(user, task):
        raise HTTPException(
            status_code=403,
            detail={"code": "FORBIDDEN", "message": "Insufficient task permission"},
        )
    if task["status"] != "completed":
        raise HTTPException(
            status_code=409,
            detail={
                "code": "TASK_STATE_INVALID",
                "message": "Only completed tasks can be exported",
            },
        )
    return task


def render_task_markdown(current_store: Any, task: dict[str, Any]) -> str:
    requirement = task["requirement_snapshot"]
    design_task_id = task["input_json"].get("product_detail_design_task_id")
    design_task = _ai_task_by_id(current_store, design_task_id)
    design_output = design_task.get("output_json") if design_task else None
    solution_output = task.get("output_json")
    design_summary = (
        design_output.get("summary", "未找到已确认产品详细设计。")
        if design_output
        else "未找到已确认产品详细设计。"
    )
    solution_summary = (
        solution_output.get("summary", "未找到已确认技术方案。")
        if solution_output
        else "未找到已确认技术方案。"
    )

    sections = [
        f"# {requirement['title']}",
        "",
        "## 需求",
        requirement["content"],
        "",
        "## 产品详细设计",
        design_summary,
        "",
        "## 技术方案",
        solution_summary,
    ]
    if solution_output and solution_output.get("architecture"):
        sections.extend(["", "### 架构要点"])
        sections.extend(f"- {item}" for item in solution_output["architecture"])
    return "\n".join(sections) + "\n"
