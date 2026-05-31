from __future__ import annotations

from copy import deepcopy
from typing import Any

ROLE_DEFINITIONS: list[dict[str, Any]] = [
    {
        "code": "admin",
        "name": "系统管理员",
        "description": "负责用户、角色、模型网关、审计与系统级配置管理。",
        "permissions": [
            "system.users.manage",
            "system.model_gateway.manage",
            "audit.read",
            "workspace.read",
            "workspace.write",
        ],
    },
    {
        "code": "product_owner",
        "name": "产品负责人",
        "description": "负责产品配置、版本模块、需求审批、任务生成和产品侧交付闭环。",
        "permissions": [
            "product.manage",
            "requirement.approve",
            "requirement.task_generate",
            "bug.manage",
            "workspace.read",
        ],
    },
    {
        "code": "rd_owner",
        "name": "研发负责人",
        "description": "负责研发任务执行、技术方案确认、Bug 处理和研发知识沉淀。",
        "permissions": [
            "task.execute",
            "review.decide",
            "knowledge.manage",
            "bug.manage",
            "workspace.read",
        ],
    },
    {
        "code": "reviewer",
        "name": "评审负责人",
        "description": "负责高影响 AI 输出、需求分析、设计方案和代码评审的人工确认。",
        "permissions": ["review.decide", "task.read", "workspace.read"],
    },
    {
        "code": "knowledge_owner",
        "name": "知识负责人",
        "description": "负责知识文档导入、权限角色维护、检索治理和沉淀审核。",
        "permissions": ["knowledge.manage", "knowledge.search", "workspace.read"],
    },
    {
        "code": "viewer",
        "name": "查看者",
        "description": "只能查看有权限访问的工作台数据、任务结果、知识和看板摘要。",
        "permissions": ["workspace.read"],
    },
]

ROLE_CODES = {role["code"] for role in ROLE_DEFINITIONS}


def list_role_definitions() -> list[dict[str, Any]]:
    return deepcopy(ROLE_DEFINITIONS)
