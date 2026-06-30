from __future__ import annotations

from typing import Any


REGRESSION_OBJECTIVE_DOMAINS: tuple[tuple[str, str], ...] = (
    ("user_feedback_to_requirement", "用户反馈转需求"),
    ("requirement_version_scheduling", "需求归入迭代版本"),
    ("ai_task_review", "AI 任务与 Review"),
    ("knowledge_deposit", "知识沉淀"),
    ("knowledge_index_health", "知识索引健康"),
    ("version_branch", "迭代版本代码分支"),
    ("code_inspection_governance", "代码巡检治理闭环"),
    ("bug_remediation", "Bug 和整改任务写回"),
    ("runner_reliability", "Runner 运行可靠性"),
    ("assistant_draft_governance", "AI 动作确认中心"),
    ("version_dashboard", "版本总览"),
    ("release_blockers", "发布阻塞项"),
    ("full_chain_trace", "需求全链路聚合"),
    ("team_dashboard", "IT 团队看板"),
    ("assistant_qa", "AI 助手问答"),
    ("permission_visibility", "权限可视化"),
)
REGRESSION_OBJECTIVE_DOMAIN_KEYS = tuple(key for key, _label in REGRESSION_OBJECTIVE_DOMAINS)
REGRESSION_OBJECTIVE_DOMAIN_LABELS = {
    key: label for key, label in REGRESSION_OBJECTIVE_DOMAINS
}
REGRESSION_TARGETED_SUITE_NAMES = (
    "runner-reliability",
    "version-dashboard",
    "assistant-qa",
    "assistant-draft-governance",
    "code-inspection-governance",
    "knowledge-index-health",
    "permission-visibility",
)
REGRESSION_TARGETED_DOMAIN_KEYS = tuple(
    key
    for key in REGRESSION_OBJECTIVE_DOMAIN_KEYS
    if key
    in {
        "ai_task_review",
        "assistant_qa",
        "assistant_draft_governance",
        "bug_remediation",
        "code_inspection_governance",
        "knowledge_index_health",
        "permission_visibility",
        "release_blockers",
        "requirement_version_scheduling",
        "runner_reliability",
        "version_branch",
        "version_dashboard",
    }
)
REGRESSION_SUITE_DOMAINS: dict[str, tuple[str, ...]] = {
    "full": REGRESSION_OBJECTIVE_DOMAIN_KEYS,
    "all-targeted": REGRESSION_TARGETED_DOMAIN_KEYS,
    "runner-reliability": ("runner_reliability",),
    "version-dashboard": (
        "requirement_version_scheduling",
        "ai_task_review",
        "version_branch",
        "version_dashboard",
        "release_blockers",
    ),
    "assistant-draft-governance": ("assistant_draft_governance",),
    "assistant-qa": (
        "requirement_version_scheduling",
        "ai_task_review",
        "version_dashboard",
        "release_blockers",
        "assistant_qa",
    ),
    "code-inspection-governance": (
        "version_branch",
        "code_inspection_governance",
        "bug_remediation",
        "version_dashboard",
    ),
    "knowledge-index-health": ("knowledge_index_health",),
    "permission-visibility": ("permission_visibility",),
}


def regression_suite_coverage(suite: str) -> dict[str, Any]:
    covered_keys = list(REGRESSION_SUITE_DOMAINS.get(suite, ()))
    covered_key_set = set(covered_keys)
    skipped_keys = [
        key for key in REGRESSION_OBJECTIVE_DOMAIN_KEYS if key not in covered_key_set
    ]
    return {
        "covered": [
            {"key": key, "label": REGRESSION_OBJECTIVE_DOMAIN_LABELS[key]}
            for key in covered_keys
        ],
        "covered_domain_count": len(covered_keys),
        "covered_keys": covered_keys,
        "is_complete_chain": not skipped_keys,
        "objective_domain_count": len(REGRESSION_OBJECTIVE_DOMAIN_KEYS),
        "skipped": [
            {"key": key, "label": REGRESSION_OBJECTIVE_DOMAIN_LABELS[key]}
            for key in skipped_keys
        ],
        "skipped_keys": skipped_keys,
        "suite": suite,
    }
