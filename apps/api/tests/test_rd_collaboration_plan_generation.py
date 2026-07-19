from __future__ import annotations

import pytest

from app.api.deps import api_error
from app.core.store import MemoryStore
from app.services.rd_collaboration_plan_generation import generate_and_persist_work_item_plan
from app.workers.execution_worker import run_execution_worker_iteration


def _planning_store() -> MemoryStore:
    store = MemoryStore()
    store.products["product-1"] = {"id": "product-1", "name": "研发协同产品"}
    store.requirements["requirement-1"] = {
        "id": "requirement-1",
        "product_id": "product-1",
        "version_id": "version-1",
        "title": "支持版本总览快速启动研发协同",
        "description": "用户可从迭代版本总览启动并查看完整研发链路。",
        "acceptance_criteria": ["总览可启动", "协同工作项可追踪"],
        "repository_scope": {"repository_ids": ["repository-1"]},
    }
    store.rd_task_executor_policy_snapshots["snapshot-1"] = {
        "id": "snapshot-1",
        "policy_id": "policy-1",
        "policy_version": 1,
        "content_hash": "sha256:policy-1",
        "payload_json": {
            "delivery_target": "ready_for_release",
            "git_config": {"workspace_root": "/tmp/rd-collaboration"},
        },
    }
    store.rd_collaboration_runs["run-1"] = {
        "id": "run-1",
        "brain_app_id": "rd_brain",
        "product_id": "product-1",
        "product_version_id": "version-1",
        "strategy_snapshot_id": "snapshot-1",
        "scope_version": 1,
        "plan_version": 0,
        "status": "planning",
        "version": 1,
        "created_by": "user-owner",
    }
    store.rd_collaboration_run_requirements["run-1:requirement-1"] = {
        "id": "run-1:requirement-1",
        "collaboration_run_id": "run-1",
        "requirement_id": "requirement-1",
        "requirement_revision": 1,
        "assessment_id": "assessment-1",
        "final_strategy_snapshot_id": "snapshot-1",
        "acceptance_criteria_hash": "sha256:acceptance",
        "repository_scope_hash": "sha256:repository",
    }
    store.rd_run_seats.update(
        {
            "seat-product": {
                "id": "seat-product",
                "collaboration_run_id": "run-1",
                "role_code": "product_manager",
                "subject_type": "human_user",
                "human_user_id": "user-owner",
                "capacity": 1,
                "status": "active",
            },
            "seat-developer": {
                "id": "seat-developer",
                "collaboration_run_id": "run-1",
                "role_code": "developer",
                "subject_type": "ai_employee",
                "ai_employee_id": "employee-developer",
                "executor_profile_id": "executor-codex",
                "capacity": 1,
                "status": "active",
            },
            "seat-tester": {
                "id": "seat-tester",
                "collaboration_run_id": "run-1",
                "role_code": "tester",
                "subject_type": "human_user",
                "human_user_id": "user-tester",
                "capacity": 1,
                "status": "active",
            },
        }
    )
    return store


def _valid_plan() -> dict:
    return {
        "work_items": [
            {
                "id": "design-dashboard-entry",
                "requirement_id": "requirement-1",
                "work_item_type": "product_detail_design",
                "title": "设计迭代版本总览入口",
                "objective": "明确总览信息与阶段快捷操作",
                "owner_role_code": "product_manager",
                "reviewer_role_code": "tester",
                "input_contract": {"source": "frozen_requirement_scope"},
                "output_contract": {"artifact": "interaction_design"},
                "acceptance_criteria": ["覆盖全部研发阶段"],
                "risk_level": "low",
                "priority": 10,
            },
            {
                "id": "implement-dashboard-entry",
                "requirement_id": "requirement-1",
                "work_item_type": "implementation",
                "title": "实现迭代版本总览入口",
                "objective": "实现总览和快捷操作",
                "owner_role_code": "developer",
                "reviewer_role_code": "tester",
                "resource_claims": [
                    {
                        "repository_id": "repository-1",
                        "path": "apps/web/src/pages/IterationVersions/index.tsx",
                        "mode": "write",
                    }
                ],
                "input_contract": {"source": "design-dashboard-entry"},
                "output_contract": {"artifact": "source_code"},
                "acceptance_criteria": ["入口可用"],
                "risk_level": "medium",
                "priority": 20,
            },
        ],
        "dependencies": [
            {
                "predecessor_work_item_id": "design-dashboard-entry",
                "successor_work_item_id": "implement-dashboard-entry",
            }
        ],
    }


def test_planner_receives_frozen_scope_and_activates_only_the_validated_dag() -> None:
    store = _planning_store()
    observed_request: dict = {}

    def planner(request: dict) -> dict:
        observed_request.update(request)
        return _valid_plan()

    result = generate_and_persist_work_item_plan(
        store,
        collaboration_run_id="run-1",
        planner=planner,
    )

    assert observed_request["collaboration_run_id"] == "run-1"
    assert observed_request["strategy_snapshot"]["content_hash"] == "sha256:policy-1"
    assert observed_request["requirements"] == [
        {
            "acceptance_criteria": ["总览可启动", "协同工作项可追踪"],
            "description": "用户可从迭代版本总览启动并查看完整研发链路。",
            "id": "requirement-1",
            "repository_scope": {"repository_ids": ["repository-1"]},
            "revision": 1,
            "title": "支持版本总览快速启动研发协同",
        }
    ]
    assert {seat["role_code"] for seat in observed_request["seats"]} == {
        "developer",
        "product_manager",
        "tester",
    }
    assert result["status"] == "planned"
    assert result["plan_version"] == 1
    assert store.rd_collaboration_runs["run-1"]["status"] == "running"
    assert store.rd_work_items["run-1:plan:1:item:design-dashboard-entry"]["status"] == "ready"
    assert store.rd_work_items["run-1:plan:1:item:implement-dashboard-entry"]["status"] == "blocked"


def test_invalid_llm_plan_is_rejected_without_activating_the_collaboration_run() -> None:
    store = _planning_store()
    invalid = _valid_plan()
    invalid["dependencies"].append(
        {
            "predecessor_work_item_id": "implement-dashboard-entry",
            "successor_work_item_id": "design-dashboard-entry",
        }
    )

    with pytest.raises(type(api_error(422, "RD_PLAN_INVALID", "invalid"))) as exc_info:
        generate_and_persist_work_item_plan(
            store,
            collaboration_run_id="run-1",
            planner=lambda _: invalid,
        )

    assert exc_info.value.detail["code"] == "RD_PLAN_INVALID"
    assert store.rd_collaboration_runs["run-1"]["status"] == "planning"
    assert store.rd_work_items == {}


def test_planner_cannot_attach_a_work_item_to_a_requirement_outside_the_frozen_scope() -> None:
    store = _planning_store()
    escaped_scope = _valid_plan()
    escaped_scope["work_items"][0]["requirement_id"] = "requirement-not-in-run"

    with pytest.raises(type(api_error(422, "RD_PLAN_INVALID", "invalid"))) as exc_info:
        generate_and_persist_work_item_plan(
            store,
            collaboration_run_id="run-1",
            planner=lambda _: escaped_scope,
        )

    assert exc_info.value.detail["reason"] == "requirement_outside_frozen_scope"
    assert store.rd_collaboration_runs["run-1"]["status"] == "planning"
    assert store.rd_work_items == {}


def test_planner_serializes_unordered_conflicting_implementation_items() -> None:
    store = _planning_store()
    plan = _valid_plan()
    plan["work_items"].append(
        {
            "id": "implement-dashboard-api",
            "requirement_id": "requirement-1",
            "work_item_type": "implementation",
            "title": "实现总览协同接口",
            "objective": "在同一页面目录实现接口接入",
            "owner_role_code": "developer",
            "reviewer_role_code": "tester",
            "resource_claims": [
                {
                    "repository_id": "repository-1",
                    "path": "apps/web/src/pages/IterationVersions",
                    "mode": "write",
                }
            ],
            "input_contract": {},
            "output_contract": {"artifact": "source_code"},
            "acceptance_criteria": ["接口可用"],
            "risk_level": "medium",
            "priority": 30,
        }
    )

    result = generate_and_persist_work_item_plan(
        store,
        collaboration_run_id="run-1",
        planner=lambda _: plan,
    )

    conflict_dependency = next(
        dependency
        for dependency in result["dependencies"]
        if dependency["predecessor_work_item_id"].endswith("implement-dashboard-entry")
        and dependency["successor_work_item_id"].endswith("implement-dashboard-api")
    )
    assert conflict_dependency["dependency_type"] == "finish_to_start"
    api_item = store.rd_work_items["run-1:plan:1:item:implement-dashboard-api"]
    assert api_item["input_contract"]["resource_claims"] == [
        {
            "repository_id": "repository-1",
            "path": "apps/web/src/pages/IterationVersions",
            "mode": "write",
        }
    ]
    assert api_item["release_conditions"] == [
        {
            "kind": "parallel_resource_conflict",
            "other_path": "apps/web/src/pages/IterationVersions",
            "path": "apps/web/src/pages/IterationVersions/index.tsx",
            "predecessor_work_item_id": "implement-dashboard-entry",
            "repository_id": "repository-1",
            "successor_work_item_id": "implement-dashboard-api",
        }
    ]


def test_planner_rejects_implementation_without_a_repository_write_claim() -> None:
    store = _planning_store()
    plan = _valid_plan()
    plan["work_items"][1].pop("resource_claims")

    with pytest.raises(type(api_error(422, "RD_PLAN_INVALID", "invalid"))) as exc_info:
        generate_and_persist_work_item_plan(
            store,
            collaboration_run_id="run-1",
            planner=lambda _: plan,
        )

    assert exc_info.value.detail["reason"] == "implementation_resource_claim_missing"
    assert store.rd_collaboration_runs["run-1"]["status"] == "planning"
    assert store.rd_work_items == {}


def test_execution_worker_generates_a_frozen_plan_before_auto_dispatch() -> None:
    store = _planning_store()

    counts = run_execution_worker_iteration(
        store,
        worker_id="planner-worker",
        collaboration_planner=lambda _: _valid_plan(),
    )

    assert counts["rd_collaboration_plan_count"] == 1
    assert store.rd_collaboration_runs["run-1"]["status"] == "running"
    assert store.rd_work_items["run-1:plan:1:item:design-dashboard-entry"]["status"] == "ready"
