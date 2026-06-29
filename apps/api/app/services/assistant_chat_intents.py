from __future__ import annotations

from time import perf_counter
from typing import Any

from app.core.store import MemoryStore
from app.services.assistant_metrics import assistant_metrics_response
from app.services.assistant_tools import assistant_tool_results

SCHEDULED_JOB_RUN_ONCE_KEYWORDS = (
    "执行一次",
    "执行一下",
    "运行一次",
    "运行一下",
    "跑一次",
    "跑一下",
    "立即执行",
    "立即运行",
    "手动执行",
    "run once",
    "run now",
    "execute once",
)
SCHEDULED_JOB_RUN_NEGATION_KEYWORDS = ("不要执行", "别执行", "不执行", "不要运行", "别运行")
TASK_CREATION_WIZARD_STEPS = ["数据来源", "AI处理", "结果动作", "调度策略", "确认执行"]
TASK_CREATION_GUIDE_ITEMS = [
    {
        "dependencies": [],
        "description": "选择或 @ 一个已规划需求后，生成可确认的产品详细设计研发任务草案。",
        "draft_action": "create_rd_task",
        "prompt": "我要新增研发任务，请先让我 @需求 后生成产品详细设计任务草案",
        "title": "研发任务",
        "type": "rd_task",
        "wizard_steps": TASK_CREATION_WIZARD_STEPS,
    },
    {
        "dependencies": ["数据连接", "AI能力", "结果动作"],
        "description": "按数据来源、AI处理、结果动作和调度策略生成可确认的定时作业草案。",
        "draft_action": "create_scheduled_job",
        "prompt": "帮我新增定时作业，先按数据来源、AI处理、结果动作和调度策略生成草案",
        "title": "定时作业",
        "type": "scheduled_job",
        "wizard_steps": TASK_CREATION_WIZARD_STEPS,
    },
    {
        "dependencies": ["业务场景", "模型网关", "Skill", "AI角色"],
        "description": "选择代码巡检或线上日志等场景后，生成 Skill 和 AI角色配置草案。",
        "draft_action": "create_ai_capability",
        "prompt": "帮我新增代码巡检 AI能力配置草案，生成 Skill 和 AI角色草案",
        "title": "AI能力配置",
        "type": "ai_capability",
        "wizard_steps": TASK_CREATION_WIZARD_STEPS,
    },
    {
        "dependencies": ["插件连接"],
        "description": "为 GitHub、GitLab、邮箱等插件生成结果动作草案，确认前不写入真实动作。",
        "draft_action": "create_plugin_action",
        "prompt": "帮我新增插件动作，先生成可确认的动作草案",
        "title": "插件动作",
        "type": "plugin_action",
        "wizard_steps": TASK_CREATION_WIZARD_STEPS,
    },
    {
        "dependencies": ["GitHub/GitLab 连接", "代码巡检动作"],
        "description": "按仓库、分支、AI处理和结果动作生成代码巡检定时作业草案。",
        "draft_action": "create_scheduled_job",
        "prompt": "帮我配置代码巡检定时作业草案",
        "title": "代码巡检",
        "type": "code_inspection",
        "wizard_steps": TASK_CREATION_WIZARD_STEPS,
    },
    {
        "dependencies": ["用户反馈数据连接", "反馈洞察动作"],
        "description": "抽取每周用户反馈、经过 AI 处理后写入反馈洞察结果。",
        "draft_action": "create_scheduled_job",
        "prompt": "帮我配置每周用户反馈洞察定时作业草案",
        "title": "反馈洞察",
        "type": "feedback_insight",
        "wizard_steps": TASK_CREATION_WIZARD_STEPS,
    },
]


def scheduled_job_run_once_requested(message: str) -> bool:
    normalized = message.lower()
    if any(keyword in normalized for keyword in SCHEDULED_JOB_RUN_NEGATION_KEYWORDS):
        return False
    return any(keyword in normalized for keyword in SCHEDULED_JOB_RUN_ONCE_KEYWORDS)


def scheduled_job_diagnostic_requested(message: str) -> bool:
    normalized = message.lower()
    has_diagnostic_intent = any(
        keyword in normalized
        for keyword in ("为什么", "原因", "失败", "诊断", "排查", "failed", "failure", "diagnose")
    )
    has_scheduled_job_context = any(
        keyword in normalized
        for keyword in ("定时任务", "定时作业", "作业", "运行", "scheduled job", "run")
    )
    has_create_intent = any(
        keyword in normalized
        for keyword in ("创建", "新增", "配置", "生成", "新建", "create", "draft")
    )
    return has_diagnostic_intent and has_scheduled_job_context and not has_create_intent


def assistant_metrics_explanation_requested(message: str) -> bool:
    normalized = message.lower()
    has_metrics_intent = any(
        keyword in normalized
        for keyword in ("指标", "效果", "漏斗", "采纳率", "修复率", "成功率", "metrics", "funnel")
    )
    has_assistant_context = any(
        keyword in normalized
        for keyword in ("助手", "ai assistant", "草案", "引用", "运行", "失败修复")
    )
    return has_metrics_intent and has_assistant_context


def task_creation_guide_requested(message: str) -> bool:
    normalized = message.lower()
    has_create_intent = any(
        keyword in normalized
        for keyword in ("新增", "新建", "创建", "增加", "create", "add")
    )
    has_task_context = any(keyword in normalized for keyword in ("任务", "作业", "task"))
    has_specific_task_type = any(
        keyword in normalized
        for keyword in (
            "定时作业",
            "定时任务",
            "研发任务",
            "ai任务",
            "ai 任务",
            "产品详细设计",
            "插件动作",
            "插件连接",
            "代码巡检",
            "反馈洞察",
            "用户反馈",
            "scheduled job",
            "plugin action",
            "code inspection",
            "feedback",
        )
    )
    has_generic_ai_capability_config = any(
        keyword in normalized
        for keyword in (
            "ai 能力配置",
            "ai能力配置",
            "ai 能力",
            "ai能力",
            "ai 角色",
            "ai角色",
            "skill",
            "agent",
            "智能体",
        )
    )
    has_specific_ai_capability_scenario = _ai_capability_specific_scenario_requested(normalized)
    return (
        has_create_intent
        and (
            (has_task_context and not has_specific_task_type)
            or (
                has_generic_ai_capability_config
                and not has_specific_ai_capability_scenario
            )
        )
    )


def plugin_connection_diagnostic_requested(message: str) -> bool:
    normalized = message.lower()
    has_connection_context = any(
        keyword in normalized
        for keyword in ("插件连接", "连接失败", "连接不可用", "connection", "connector")
    )
    has_failure_intent = any(
        keyword in normalized
        for keyword in (
            "为什么",
            "原因",
            "失败",
            "不可用",
            "诊断",
            "排查",
            "怎么修",
            "修复",
            "failed",
            "failure",
            "diagnose",
            "repair",
            "fix",
        )
    )
    has_create_intent = any(
        keyword in normalized
        for keyword in ("创建", "新增", "配置", "生成", "新建", "接入", "create", "draft")
    )
    return has_connection_context and has_failure_intent and not has_create_intent


def plugin_connection_diagnostic_output(
    current_store: MemoryStore,
    *,
    payload: Any,
    selected_references: list[dict[str, str]],
) -> dict[str, Any]:
    started = perf_counter()
    tool_results = [
        result
        for result in assistant_tool_results(
            current_store,
            message=payload.message,
            product_id=payload.product_id,
            references=selected_references,
        )
        if result.get("tool") == "assistant.plugin_connection_diagnostic"
    ]
    diagnosed_count = sum(len(result.get("items") or []) for result in tool_results)
    failed_count = sum(
        int((result.get("summary") or {}).get("failed_count") or 0)
        for result in tool_results
    )
    if diagnosed_count:
        answer = (
            f"我已读取最近插件连接测试记录，找到 {failed_count} 个失败连接，"
            "并按连接配置、最近测试、修复建议整理如下。"
        )
    else:
        answer = (
            "我没有找到最近失败的插件连接测试记录。"
            "请先在插件管理里执行一次连接测试，或补充具体连接名称后继续排查。"
        )
    diagnostic_references = [
        reference
        for result in tool_results
        for reference in result.get("references", [])
        if isinstance(reference, dict)
    ]
    return {
        "answer": answer,
        "latency_ms": int((perf_counter() - started) * 1000),
        "model": "assistant-deterministic",
        "references": merge_assistant_references(
            selected_references,
            diagnostic_references,
        ),
        "selected_references": selected_references,
        "suggestions": ["生成插件连接修复草案", "打开插件管理"],
        "tool_results": tool_results,
    }


def scheduled_job_diagnostic_output(
    current_store: MemoryStore,
    *,
    payload: Any,
    selected_references: list[dict[str, str]],
) -> dict[str, Any]:
    started = perf_counter()
    tool_results = [
        result
        for result in assistant_tool_results(
            current_store,
            message=payload.message,
            product_id=payload.product_id,
            references=selected_references,
        )
        if result.get("tool") == "assistant.scheduled_job_diagnostic"
    ]
    diagnosed_count = sum(len(result.get("items") or []) for result in tool_results)
    failed_count = sum(
        int((result.get("summary") or {}).get("failed_count") or 0)
        for result in tool_results
    )
    if diagnosed_count:
        answer = (
            f"我已读取最近定时作业运行记录，找到 {failed_count} 个失败运行，"
            "并按数据连接、AI 处理、结果动作三段整理诊断。"
        )
    else:
        answer = (
            "我没有找到可诊断的失败运行。"
            "可以先 @具体定时作业或 @运行记录，或手动执行一次后再继续排查。"
        )
    diagnostic_references = [
        reference
        for result in tool_results
        for reference in result.get("references", [])
        if isinstance(reference, dict)
    ]
    return {
        "answer": answer,
        "latency_ms": int((perf_counter() - started) * 1000),
        "model": "assistant-deterministic",
        "references": merge_assistant_references(
            selected_references,
            diagnostic_references,
        ),
        "selected_references": selected_references,
        "suggestions": [
            "围绕某次运行继续追问",
            "生成失败修复草案",
            "查看定时作业运行记录",
        ],
        "tool_results": tool_results,
    }


def assistant_metrics_explanation_output(
    current_store: MemoryStore,
    *,
    user: dict[str, Any],
) -> dict[str, Any]:
    started = perf_counter()
    metrics = assistant_metrics_response(current_store, user=user)
    summary = metrics.get("summary") or {}
    answer = (
        "当前 AI 助手效果指标："
        f"草案生成 {int(summary.get('draft_total') or 0)} 个，"
        f"草案确认率 {_format_ratio(summary.get('draft_adoption_rate'))}，"
        f"@ 引用使用率 {_format_ratio(summary.get('reference_usage_rate'))}，"
        f"作业运行成功率 {_format_ratio(summary.get('scheduled_job_run_success_rate'))}，"
        f"失败修复率 {_format_ratio(summary.get('failed_run_repair_rate'))}。"
    )
    return {
        "answer": answer,
        "latency_ms": int((perf_counter() - started) * 1000),
        "model": "assistant-deterministic",
        "references": [],
        "selected_references": [],
        "suggestions": [
            "查看草案采纳漏斗",
            "解释作业运行成功率",
            "分析失败修复率",
        ],
        "tool_results": [
            {
                "intent": "assistant_metrics_explanation",
                "items": metrics.get("funnel", {}).get("stages", []),
                "summary": summary,
                "tool": "assistant.metrics_summary",
            }
        ],
    }


def task_creation_guide_output(
    *,
    selected_references: list[dict[str, str]],
) -> dict[str, Any]:
    started = perf_counter()
    return {
        "answer": (
            "你想新增哪类任务？我会先按向导生成可确认的草案，确认前不会写入真实配置。"
        ),
        "latency_ms": int((perf_counter() - started) * 1000),
        "model": "assistant-deterministic",
        "references": selected_references,
        "selected_references": selected_references,
        "suggestions": [
            "新增研发任务",
            "新增定时作业",
            "新增AI能力配置",
            "新增插件动作",
            "配置代码巡检定时作业",
            "配置每周用户反馈洞察定时作业",
        ],
        "tool_results": [
            {
                "intent": "task_creation_guide",
                "items": TASK_CREATION_GUIDE_ITEMS,
                "summary": {
                    "draft_first": True,
                    "option_count": len(TASK_CREATION_GUIDE_ITEMS),
                    "wizard_steps": TASK_CREATION_WIZARD_STEPS,
                },
                "tool": "assistant.task_creation_guide",
            }
        ],
    }


def scheduled_job_reference_needed_output(
    *,
    attempted_queries: list[str],
    selected_references: list[dict[str, str]],
) -> dict[str, Any]:
    query_text = "、".join(attempted_queries) if attempted_queries else "这个 @ 引用"
    return {
        "answer": (
            f"我没有找到唯一匹配的定时作业：{query_text}。"
            "请从 @ 候选中点选一个定时作业后再执行一次。"
        ),
        "latency_ms": 0,
        "model": "assistant-deterministic",
        "references": selected_references,
        "selected_references": selected_references,
        "suggestions": ["输入 @ 后选择定时作业，再发送执行一次"],
        "tool_results": [
            {
                "intent": "scheduled_job_run_once",
                "items": [],
                "summary": {
                    "queries": attempted_queries,
                    "status": "needs_scheduled_job_reference",
                },
                "tool": "assistant.scheduled_job_run",
            }
        ],
    }


def merge_assistant_references(
    *reference_lists: list[dict[str, str]],
) -> list[dict[str, str]]:
    references: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for reference_list in reference_lists:
        for reference in reference_list:
            key = (str(reference.get("type")), str(reference.get("id")))
            if key in seen:
                continue
            if not all(reference.get(field) for field in ("id", "title", "type", "url")):
                continue
            seen.add(key)
            references.append(reference)
            if len(references) >= 6:
                return references
    return references


def _ai_capability_specific_scenario_requested(normalized_message: str) -> bool:
    return any(
        keyword in normalized_message
        for keyword in (
            "代码巡检",
            "code inspection",
            "github",
            "gitlab",
            "线上日志异常",
            "线上日志分析",
            "日志异常",
            "日志分析",
            "online log anomaly",
            "online_log_anomaly",
            "online_log",
            "log anomaly",
        )
    )


def _format_ratio(value: Any) -> str:
    try:
        return f"{float(value) * 100:.1f}%"
    except (TypeError, ValueError):
        return "0.0%"
