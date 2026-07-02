from __future__ import annotations

from typing import Any


def _step(
    *,
    key: str,
    label: str,
    status: str,
    source: str | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "key": key,
        "label": label,
        "status": status,
    }
    if source:
        item["source"] = source
    if description:
        item["description"] = description
    return item


def _handoff_item(
    *,
    key: str,
    label: str,
    status: str,
    source: str | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "key": key,
        "label": label,
        "status": status,
    }
    if source:
        item["source"] = source
    if description:
        item["description"] = description
    return item


def _with_progress(wizard: dict[str, Any]) -> dict[str, Any]:
    steps = [
        step
        for step in wizard.get("steps") or []
        if isinstance(step, dict)
    ]
    completed_statuses = {"not_used", "ready", "succeeded"}
    blocked_statuses = {"blocked", "failed", "missing"}
    completed_steps = sum(
        1
        for step in steps
        if str(step.get("status") or "") in completed_statuses
    )
    blocked_steps = sum(
        1
        for step in steps
        if str(step.get("status") or "") in blocked_statuses
    )
    total_steps = len(steps)
    pending_steps = max(total_steps - completed_steps - blocked_steps, 0)
    progress_percent = (
        int(round(completed_steps * 100 / total_steps))
        if total_steps
        else 0
    )
    wizard.update(
        {
            "blocked_steps": blocked_steps,
            "completed_steps": completed_steps,
            "pending_steps": pending_steps,
            "progress_label": f"{completed_steps}/{total_steps} 步已就绪",
            "progress_percent": progress_percent,
            "total_steps": total_steps,
        }
    )
    return wizard


def connection_test_reuse_wizard(*, seed_status: str) -> dict[str, Any]:
    ready = seed_status == "ready"
    return _with_progress({
        "can_continue": ready,
        "current_step_label": "连接测试样例",
        "current_step": "connection_test",
        "draft_payload_ready": ready,
        "handoff_summary": [
            _handoff_item(
                key="request_preview",
                label="最终请求",
                source="request_summary" if ready else "not_available",
                status="ready" if ready else "missing",
                description="已保存 URL、Method、Params、Headers 和系统变量替换结果。",
            ),
            _handoff_item(
                key="response_sample",
                label="响应样例",
                source="response_summary" if ready else "not_available",
                status="ready" if ready else "missing",
                description="动作试运行将优先复用本次响应样例，不重复请求第三方。",
            ),
            _handoff_item(
                key="action_template",
                label="动作模板草案",
                source="connection_test" if ready else "not_available",
                status="ready" if ready else "missing",
                description="可复制为动作，继续生成写入预览和作业草稿。",
            ),
        ],
        "missing_requirements": [] if ready else ["connection_test_response"],
        "next_action": "copy_action_template_then_trial" if ready else "fix_connection_test",
        "next_action_description": (
            "复制动作模板并自动使用连接测试响应样例试运行，生成写入预览。"
            if ready
            else "先修复连接测试，确保能拿到最终请求和响应样例。"
        ),
        "primary_action_label": "复制动作模板并试运行" if ready else "修复连接测试",
        "sample_source": "connection_test_response",
        "status": "ready" if ready else "blocked",
        "steps": [
            _step(
                key="connection_test",
                label="连接测试样例",
                source="connection_test_response" if ready else "not_available",
                status="succeeded" if ready else "blocked",
            ),
            _step(
                key="action_trial",
                label="动作写入预览",
                status="ready" if ready else "pending",
            ),
            _step(
                key="scheduled_job_dry_run",
                label="全链路试运行",
                status="pending",
            ),
            _step(
                key="scheduled_job_config",
                label="生成作业配置",
                status="pending",
            ),
        ],
    })


def action_trial_reuse_wizard(
    *,
    has_response_summary: bool,
    has_write_preview: bool,
    sample_source: str,
    trial_status: str,
) -> dict[str, Any]:
    succeeded = trial_status == "succeeded"
    draft_ready = succeeded and has_response_summary
    missing_requirements = []
    if not succeeded:
        missing_requirements.append("action_trial_succeeded")
    if not has_response_summary:
        missing_requirements.append("action_trial_response")
    if not has_write_preview:
        missing_requirements.append("write_preview")
    return _with_progress({
        "can_continue": draft_ready,
        "current_step_label": "动作写入预览",
        "current_step": "action_trial",
        "draft_payload_ready": draft_ready,
        "handoff_summary": [
            _handoff_item(
                key="response_sample",
                label="响应样例",
                source=sample_source if has_response_summary else "not_available",
                status="ready" if has_response_summary else "missing",
                description="定时作业草稿会保留该样例，后续 dry-run 可继续复用。",
            ),
            _handoff_item(
                key="input_mapping",
                label="连接输入映射",
                source="trial_input_payload",
                status="ready" if succeeded else "missing",
                description="已带入本次动作试运行输入，作为作业数据连接输入默认值。",
            ),
            _handoff_item(
                key="output_mapping",
                label="结果映射",
                source="plugin_action_result_mapping",
                status="ready" if succeeded else "missing",
                description="已带入动作结果映射，后续用于计算动作写入预览。",
            ),
            _handoff_item(
                key="write_preview",
                label="写入预览",
                source=sample_source if has_write_preview else "not_available",
                status="ready" if has_write_preview else "missing",
                description="已预估写入目标、写入数量和样例记录。",
            ),
        ],
        "missing_requirements": missing_requirements,
        "next_action": "create_scheduled_job_draft" if draft_ready else "fix_action_trial",
        "next_action_description": (
            "生成定时作业草稿，并带入连接、动作、映射、响应样例和写入预览。"
            if draft_ready
            else "先修复动作试运行，确保响应样例和写入预览都可用。"
        ),
        "primary_action_label": "生成定时作业草稿" if draft_ready else "修复动作试运行",
        "sample_source": sample_source,
        "status": "ready" if draft_ready else "blocked",
        "steps": [
            _step(
                key="connection_test",
                label="连接测试样例",
                source=sample_source,
                status=(
                    "succeeded"
                    if sample_source == "connection_test_response"
                    else "not_used"
                ),
            ),
            _step(
                key="action_trial",
                label="动作写入预览",
                source=sample_source,
                status="succeeded" if succeeded else "failed",
            ),
            _step(
                key="scheduled_job_dry_run",
                label="全链路试运行",
                status="ready" if draft_ready else "pending",
            ),
            _step(
                key="scheduled_job_config",
                label="生成作业配置",
                status="ready" if draft_ready else "pending",
            ),
        ],
    })


def scheduled_job_dry_run_reuse_wizard(
    *,
    action_preview_ready: bool,
    data_connection_sample_source: str,
    output_preview_ready: bool,
    response_available: bool,
    result_action_preview_source: str,
) -> dict[str, Any]:
    missing_requirements = []
    if not response_available:
        missing_requirements.append("data_connection_sample")
    if not output_preview_ready:
        missing_requirements.append("ai_output_preview")
    if not action_preview_ready:
        missing_requirements.append("action_write_preview")
    ready = not missing_requirements
    return _with_progress({
        "can_continue": ready,
        "current_step_label": "全链路试运行",
        "current_step": "scheduled_job_dry_run",
        "draft_payload_ready": ready,
        "handoff_summary": [
            _handoff_item(
                key="data_connection_sample",
                label="数据连接样例",
                source=data_connection_sample_source if response_available else "not_available",
                status="ready" if response_available else "missing",
                description="已确认数据连接可返回本次试运行样例。",
            ),
            _handoff_item(
                key="ai_output_preview",
                label="AI 输出预览",
                source="skill_output_schema" if output_preview_ready else "not_available",
                status="ready" if output_preview_ready else "missing",
                description="已按 Skill 输出 Schema 生成可映射的结构化结果样例。",
            ),
            _handoff_item(
                key="action_write_preview",
                label="动作写入预览",
                source=result_action_preview_source,
                status="ready" if action_preview_ready else "missing",
                description="已确认动作写入目标、数量和样例记录。",
            ),
            _handoff_item(
                key="job_config",
                label="作业配置",
                source="current_dry_run_payload",
                status="ready" if ready else "pending",
                description="可保存当前连接、AI 执行和动作配置为定时作业。",
            ),
        ],
        "missing_requirements": missing_requirements,
        "next_action": "save_scheduled_job" if ready else "review_dry_run_issues",
        "next_action_description": (
            "保存当前配置为定时作业，后续运行记录将继续展示三段核心节点。"
            if ready
            else "先处理缺失的样例、AI 输出或动作写入预览，再保存作业。"
        ),
        "primary_action_label": "保存为定时作业" if ready else "检查试运行问题",
        "sample_source": data_connection_sample_source if response_available else "not_available",
        "status": "ready" if ready else "partial",
        "steps": [
            _step(
                key="connection_test",
                label="数据连接样例",
                source=data_connection_sample_source if response_available else "not_available",
                status="succeeded" if response_available else "blocked",
            ),
            _step(
                key="ai_processing_preview",
                label="AI 处理预览",
                source="skill_output_schema" if output_preview_ready else "not_available",
                status="succeeded" if output_preview_ready else "blocked",
            ),
            _step(
                key="action_trial",
                label="动作写入预览",
                source=result_action_preview_source,
                status="succeeded" if action_preview_ready else "blocked",
            ),
            _step(
                key="scheduled_job_config",
                label="生成作业配置",
                source="current_dry_run_payload",
                status="ready" if ready else "pending",
            ),
        ],
    })
