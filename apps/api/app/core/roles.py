from __future__ import annotations

from copy import deepcopy
from typing import Any

ROLE_DEFINITIONS: list[dict[str, Any]] = [
    {
        "business_roles": ["平台管理员"],
        "category": "system",
        "code": "admin",
        "description": "负责用户、角色、模型网关、审计与系统级配置管理。",
        "data_scope": "全平台系统配置、审计事件和授权业务数据。",
        "decision_scope": "账号、角色、模型网关和系统配置治理；不替代业务负责人做产品取舍。",
        "is_assignable": True,
        "limitations": [
            "不代替产品负责人、研发负责人或评审负责人做业务最终决策。",
            "所有系统配置、用户和模型网关变更必须写入审计。",
        ],
        "menu_scope": ["系统管理", "审计与运行", "产品资产", "需求交付", "任务中心"],
        "name": "系统管理员",
        "permissions": [
            "system.users.manage",
            "system.model_gateway.manage",
            "audit.read",
            "workspace.read",
            "workspace.write",
        ],
        "responsibilities": [
            "管理本地用户账号、状态和角色分配。",
            "维护 OpenAI-compatible 模型网关配置。",
            "查看审计与运行状态，处理系统级异常。",
        ],
        "sort_order": 10,
        "status": "active",
    },
    {
        "business_roles": ["产品负责人"],
        "category": "delivery",
        "code": "product_owner",
        "description": "负责产品配置、版本模块、需求审批、任务生成和产品侧交付闭环。",
        "data_scope": "所负责产品、版本和模块下的需求、AI 任务、Bug、知识引用和看板摘要。",
        "decision_scope": "需求审批、产品详细设计确认、迭代规划采纳和产品侧优先级决策。",
        "is_assignable": True,
        "limitations": [
            "不能确认技术方案或代码 Review 报告。",
            "不能维护系统用户、角色或模型网关密钥。",
        ],
        "menu_scope": ["需求管理", "产品管理", "任务管理", "Bug 管理", "首页 IT 团队看板"],
        "name": "产品负责人",
        "permissions": [
            "product.manage",
            "requirement.create",
            "requirement.approve",
            "requirement.task_generate",
            "planning.decide",
            "bug.manage",
            "workspace.read",
            "workspace.write",
        ],
        "responsibilities": [
            "维护产品、版本、模块和相关系统上下文。",
            "审批需求并从已批准需求生成 AI 任务。",
            "确认产品详细设计、采纳或驳回迭代建议。",
        ],
        "sort_order": 20,
        "status": "active",
    },
    {
        "business_roles": ["研发负责人"],
        "category": "delivery",
        "code": "rd_owner",
        "description": "负责研发任务执行、技术方案确认、Bug 处理和研发知识沉淀。",
        "data_scope": "授权产品下的 AI 任务、技术方案、GitLab 只读快照、Bug 和研发知识。",
        "decision_scope": "技术方案确认、研发任务推进、Bug 处理和研发知识沉淀决策。",
        "is_assignable": True,
        "limitations": [
            "不能维护系统用户、角色或模型网关密钥。",
            "产品优先级和迭代采纳仍由产品负责人确认。",
        ],
        "menu_scope": ["任务管理", "Bug 管理", "知识中心", "研发运营看板", "首页 IT 团队看板"],
        "name": "研发负责人",
        "permissions": [
            "task.create",
            "task.execute",
            "review.decide",
            "gitlab.read",
            "knowledge.manage",
            "bug.manage",
            "workspace.read",
            "workspace.write",
        ],
        "responsibilities": [
            "创建并启动研发 AI 任务，推进技术方案闭环。",
            "确认技术方案和研发侧人工 Review。",
            "处理 Bug、沉淀研发知识并维护研发执行上下文。",
        ],
        "sort_order": 30,
        "status": "active",
    },
    {
        "business_roles": ["指定评审人", "研发负责人"],
        "category": "review",
        "code": "reviewer",
        "description": "负责高影响 AI 输出、需求分析、设计方案和代码评审的人工确认。",
        "data_scope": "分配给评审人的 AI 任务、Review 检查点、MR 只读快照和评审报告。",
        "decision_scope": "对高影响 AI 输出执行批准、修改后批准、拒绝或要求补充信息。",
        "is_assignable": True,
        "limitations": [
            "不能维护产品主数据或审批需求。",
            "不能启动非评审范围内的 AI 任务。",
        ],
        "menu_scope": ["任务管理", "审计与运行"],
        "name": "评审负责人",
        "permissions": ["review.decide", "task.read", "gitlab.review", "workspace.read"],
        "responsibilities": [
            "确认产品详细设计、技术方案或代码 Review 报告。",
            "在信息不足时要求补充，并保留评审原因。",
            "守住高影响 AI 动作的人审门禁。",
        ],
        "sort_order": 40,
        "status": "active",
    },
    {
        "business_roles": ["文档/知识维护者"],
        "category": "knowledge",
        "code": "knowledge_owner",
        "description": "负责知识文档导入、权限角色维护、检索治理和沉淀审核。",
        "data_scope": "知识文档、chunk、检索结果、权限角色和知识沉淀候选。",
        "decision_scope": "知识导入、权限配置、索引治理和沉淀候选审核。",
        "is_assignable": True,
        "limitations": [
            "不能审批需求、确认技术方案或创建代码 Review 任务。",
            "知识权限只能从已定义角色目录中选择。",
        ],
        "menu_scope": ["知识中心", "审计与运行"],
        "name": "知识负责人",
        "permissions": [
            "knowledge.manage",
            "knowledge.search",
            "knowledge.deposit.decide",
            "workspace.read",
        ],
        "responsibilities": [
            "导入和维护知识文档及索引状态。",
            "维护知识访问角色，确保检索前完成权限过滤。",
            "审核任务产出的知识沉淀候选。",
        ],
        "sort_order": 50,
        "status": "active",
    },
    {
        "business_roles": ["IT 管理者", "测试负责人", "测试人员", "只读参与者"],
        "category": "readonly",
        "code": "viewer",
        "description": "只能查看有权限访问的工作台数据、任务结果、知识和看板摘要。",
        "data_scope": "授权范围内的列表、详情、任务结果、知识检索结果和看板摘要。",
        "decision_scope": "无写入或审批决策权限。",
        "is_assignable": True,
        "limitations": [
            "不能执行写操作、审批或配置变更。",
            "只能读取已授权产品、任务或知识范围内的数据。",
        ],
        "menu_scope": ["首页 IT 团队看板", "授权业务列表", "知识检索"],
        "name": "查看者",
        "permissions": ["workspace.read"],
        "responsibilities": [
            "查看授权范围内的业务数据和任务结果。",
            "查看知识、审计摘要和后续阶段真实空状态。",
        ],
        "sort_order": 60,
        "status": "active",
    },
]

ROLE_CODES = {role["code"] for role in ROLE_DEFINITIONS}
ASSIGNABLE_ROLE_CODES = {
    role["code"]
    for role in ROLE_DEFINITIONS
    if role.get("is_assignable") is True and role.get("status") == "active"
}


def list_role_definitions() -> list[dict[str, Any]]:
    return deepcopy(ROLE_DEFINITIONS)
