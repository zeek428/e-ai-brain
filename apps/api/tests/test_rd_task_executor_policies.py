import base64
import json

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient

from app.main import app
from app.services.rd_policy_resolution import (
    PolicyResolutionError,
    _base_snapshot_for_source,
    _hash,
    derive_assessment_rd_policy_snapshot,
    freeze_base_rd_policy_snapshot,
    is_monotonic_strengthening,
    merge_policy_payloads,
    merge_version_rd_policy_snapshot,
    resolve_final_rd_policy,
    resolve_work_item_binding,
    validate_snapshot_chain,
)
from tests.test_technical_solution_export import auth_headers

client = TestClient(app)


def create_codex_runner(headers: dict[str, str]) -> dict:
    response = client.post(
        "/api/system/ai-executor-runners",
        json={
            "executor_types": ["codex"],
            "name": "本地 Codex 研发执行器",
            "protocol": "runner_polling",
            "runner_token": "runner-secret",
            "trust_boundary_id": "coding-pool-a",
            "trust_domain": "coding",
            "workspace_roots": ["/Users/zeek/source/e-ai-brain"],
        },
        headers=headers,
    )
    assert response.status_code == 200
    return response.json()["data"]


def create_verification_runner(headers: dict[str, str]) -> tuple[dict, Ed25519PrivateKey]:
    signing_key = Ed25519PrivateKey.generate()
    public_key = signing_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    response = client.post(
        "/api/system/ai-executor-runners",
        headers=headers,
        json={
            "attestation_public_key": base64.b64encode(public_key).decode("ascii"),
            "attestation_status": "active",
            "executor_types": ["codex"],
            "name": "独立 Codex 验证执行器",
            "protocol": "runner_polling",
            "runner_token": "verifier-secret",
            "trust_boundary_id": "verification-pool-a",
            "trust_domain": "verification",
            "workspace_roots": ["/Users/zeek/source/e-ai-brain"],
        },
    )
    assert response.status_code == 200
    return response.json()["data"], signing_key


def signed_execution_attestation(signing_key: Ed25519PrivateKey, *, runner_task_id: str) -> dict:
    payload = {"runner_task_id": runner_task_id, "status": "succeeded"}
    serialized = json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return {
        "payload": payload,
        "signature": base64.b64encode(signing_key.sign(serialized)).decode("ascii"),
    }


def create_unified_runner_policy(
    headers: dict[str, str],
    *,
    product_id: str,
    runner: dict,
    task_type: str = "development_planning",
    instruction: str = "处理任务 {{task_id}}",
    autonomy_config: dict | None = None,
    quality_gate_config: dict | None = None,
    git_config: dict | None = None,
) -> dict:
    profile_id = f"policy-profile-{runner['id']}"
    app.state.store.rd_executor_profiles[profile_id] = {
        "id": profile_id,
        "executor_type": "codex",
        "runner_id": runner["id"],
        "status": "active",
    }
    response = client.post(
        "/api/delivery/rd-task-executor-policies",
        headers=headers,
        json={
            "name": f"统一 {task_type} Runner 策略",
            "brain_app_id": "rd_brain",
            "product_id": product_id,
            "status": "active",
            "matching_config": {
                "task_types": [task_type],
                "execution_role_code": "developer",
            },
            "assessment_config": {
                "instruction_template": instruction,
                "output_contract": {"summary": "string"},
            },
            "iteration_config": {},
            "delivery_target": "ready_for_release",
            "team_config": {"required_role_codes": ["developer"]},
            "autonomy_config": autonomy_config or {"timeout_seconds": 600},
            "quality_gate_config": quality_gate_config or {},
            "git_config": git_config or {"workspace_root": "/Users/zeek/source/e-ai-brain"},
            "experience_reuse_config": {},
            "deployment_config": {},
            "role_bindings": [
                {
                    "role_code": "developer",
                    "actor_mode": "ai",
                    "primary_executor_profile_id": profile_id,
                    "status": "active",
                }
            ],
        },
    )
    assert response.status_code == 200
    return response.json()["data"]["policy"]


def create_development_planning_task(headers: dict[str, str]) -> tuple[dict, dict]:
    from tests.test_v1_1_task_types import create_confirmed_technical_solution_task

    requirement, technical_solution_task_id = create_confirmed_technical_solution_task(headers)
    task = client.post(
        "/api/ai-tasks",
        headers=headers,
        json={
            "input": {"technical_solution_task_id": technical_solution_task_id},
            "requirement_id": requirement["id"],
            "task_type": "development_planning",
            "title": "统一策略执行",
        },
    ).json()["data"]
    return requirement, task


def claim_runner_task(runner: dict) -> dict:
    response = client.post(
        "/api/system/ai-executor-tasks/claim",
        json={"executor_type": "codex", "runner_id": runner["id"]},
        headers={"X-Runner-Token": "runner-secret"},
    )
    assert response.status_code == 200
    return response.json()["data"]["task"]


def test_unified_policy_queues_runner_and_creates_review_on_success():
    from tests.test_v1_1_task_types import create_confirmed_technical_solution_task

    headers = auth_headers()
    requirement, technical_solution_task_id = create_confirmed_technical_solution_task(headers)
    runner = create_codex_runner(headers)
    policy = create_unified_runner_policy(
        headers,
        product_id=requirement["product_id"],
        runner=runner,
        instruction="处理任务 {{task_id}} / {{task_title}}，需求 {{requirement_id}}。",
    )
    task = client.post(
        "/api/ai-tasks",
        headers=headers,
        json={
            "input": {"technical_solution_task_id": technical_solution_task_id},
            "requirement_id": requirement["id"],
            "task_type": "development_planning",
            "title": "统一策略执行",
        },
    ).json()["data"]
    started = client.post(f"/api/ai-tasks/{task['id']}/start", headers=headers).json()["data"]
    assert started["executor_policy_id"] == policy["id"]
    claimed = client.post(
        "/api/system/ai-executor-tasks/claim",
        json={"executor_type": "codex", "runner_id": runner["id"]},
        headers={"X-Runner-Token": "runner-secret"},
    ).json()["data"]["task"]
    assert claimed["instruction"].startswith(f"处理任务 {task['id']}")
    completed = client.post(
        f"/api/system/ai-executor-tasks/{claimed['id']}/complete",
        json={
            "runner_id": runner["id"],
            "status": "succeeded",
            "result_json": {"summary": "统一 Runner 完成"},
        },
        headers={"X-Runner-Token": "runner-secret"},
    )
    assert completed.status_code == 200
    detail = client.get(f"/api/ai-tasks/{task['id']}", headers=headers).json()["data"]
    assert detail["status"] == "waiting_review"
    assert detail["output_summary"] == "统一 Runner 完成"


def test_unified_autonomy_config_starts_agent_loop():
    from tests.test_v1_1_task_types import create_confirmed_technical_solution_task

    headers = auth_headers()
    requirement, technical_solution_task_id = create_confirmed_technical_solution_task(headers)
    runner = create_codex_runner(headers)
    create_unified_runner_policy(
        headers,
        product_id=requirement["product_id"],
        runner=runner,
        autonomy_config={
            "mode": "autonomous_loop",
            "max_duration_seconds": 1800,
            "max_iterations": 2,
            "timeout_seconds": 600,
        },
        quality_gate_config={"code_change_review_mode": "auto_commit"},
    )
    task = client.post(
        "/api/ai-tasks",
        headers=headers,
        json={
            "input": {"technical_solution_task_id": technical_solution_task_id},
            "requirement_id": requirement["id"],
            "task_type": "development_planning",
            "title": "统一策略自治循环",
        },
    ).json()["data"]

    started = client.post(f"/api/ai-tasks/{task['id']}/start", headers=headers)

    assert started.status_code == 200
    detail = client.get(f"/api/ai-tasks/{task['id']}", headers=headers).json()["data"]
    assert detail["agent_loop"]["current_iteration"] == 1


def test_unified_policy_scopes_runner_knowledge_to_task_product():
    headers = auth_headers()
    requirement, task = create_development_planning_task(headers)
    runner = create_codex_runner(headers)
    create_unified_runner_policy(headers, product_id=requirement["product_id"], runner=runner)
    app.state.store.knowledge_documents.update(
        {
            "policy_knowledge_in_scope": {
                "id": "policy_knowledge_in_scope",
                "brain_app_id": "rd_brain",
                "product_id": requirement["product_id"],
                "version_id": requirement["version_id"],
                "title": "本产品编码规范",
                "doc_type": "project_doc",
                "permission_roles": ["admin"],
                "index_status": "indexed",
            },
            "policy_knowledge_other_product": {
                "id": "policy_knowledge_other_product",
                "brain_app_id": "rd_brain",
                "product_id": "other_product",
                "version_id": requirement["version_id"],
                "title": "不应泄露的其他产品文档",
                "doc_type": "project_doc",
                "permission_roles": ["admin"],
                "index_status": "indexed",
            },
        }
    )
    app.state.store.knowledge_chunks.update(
        {
            "policy_knowledge_in_scope_chunk": {
                "id": "policy_knowledge_in_scope_chunk",
                "document_id": "policy_knowledge_in_scope",
                "chunk_index": 0,
                "content": "本产品必须补充回归测试。",
                "metadata": {},
                "permission_scope": {},
            },
            "policy_knowledge_other_product_chunk": {
                "id": "policy_knowledge_other_product_chunk",
                "document_id": "policy_knowledge_other_product",
                "chunk_index": 0,
                "content": "其他产品专属上下文不能进入任务。",
                "metadata": {},
                "permission_scope": {},
            },
        }
    )

    started = client.post(f"/api/ai-tasks/{task['id']}/start", headers=headers)
    assert started.status_code == 200
    claimed = claim_runner_task(runner)

    assert "本产品必须补充回归测试" in claimed["instruction"]
    assert "其他产品专属上下文不能进入任务" not in claimed["instruction"]
    assert [item["document_id"] for item in claimed["input_payload"]["knowledge_references"]] == [
        "policy_knowledge_in_scope"
    ]


def test_unified_policy_review_requests_workspace_merge_or_discard():
    headers = auth_headers()
    requirement, task = create_development_planning_task(headers)
    runner = create_codex_runner(headers)
    create_unified_runner_policy(headers, product_id=requirement["product_id"], runner=runner)
    started = client.post(f"/api/ai-tasks/{task['id']}/start", headers=headers).json()["data"]
    claimed = claim_runner_task(runner)
    completed = client.post(
        f"/api/system/ai-executor-tasks/{claimed['id']}/complete",
        json={
            "runner_id": runner["id"],
            "status": "succeeded",
            "result_json": {
                "summary": "隔离工作区完成",
                "workspace_isolation": {
                    "base_workspace_root": "/Users/zeek/source/e-ai-brain",
                    "branch_name": "ai-brain/unified-policy",
                    "mode": "git_worktree",
                    "status": "pending_review",
                    "worktree_path": "/tmp/unified-policy-worktree",
                },
            },
        },
        headers={"X-Runner-Token": "runner-secret"},
    )
    assert completed.status_code == 200
    detail = client.get(f"/api/ai-tasks/{task['id']}", headers=headers).json()["data"]
    approved = client.post(
        f"/api/reviews/{detail['pending_review']['id']}/approve",
        json={"version": detail["pending_review"]["version"]},
        headers=headers,
    )
    assert approved.status_code == 200
    runner_status = client.get(
        f"/api/system/ai-executor-tasks/{started['executor_task_id']}/runner-status?runner_id={runner['id']}",
        headers={"X-Runner-Token": "runner-secret"},
    ).json()["data"]["task"]
    decision = runner_status["workspace_isolation"]["decision"]
    assert decision["action"] == "merge"
    assert decision["decided_by"] == "user_admin"
    assert decision["status"] == "requested"

    rejected_task = client.post(
        "/api/ai-tasks",
        headers=headers,
        json={
            "input": {"technical_solution_task_id": detail["input"]["technical_solution_task_id"]},
            "requirement_id": requirement["id"],
            "task_type": "development_planning",
            "title": "统一策略隔离工作区拒绝",
        },
    ).json()["data"]
    rejected_start = client.post(
        f"/api/ai-tasks/{rejected_task['id']}/start", headers=headers
    ).json()["data"]
    rejected_claim = claim_runner_task(runner)
    rejected_completion = client.post(
        f"/api/system/ai-executor-tasks/{rejected_claim['id']}/complete",
        json={
            "runner_id": runner["id"],
            "status": "succeeded",
            "result_json": {
                "summary": "需要拒绝",
                "workspace_isolation": {
                    "base_workspace_root": "/Users/zeek/source/e-ai-brain",
                    "branch_name": "ai-brain/reject-unified-policy",
                    "mode": "git_worktree",
                    "status": "pending_review",
                    "worktree_path": "/tmp/reject-unified-policy-worktree",
                },
            },
        },
        headers={"X-Runner-Token": "runner-secret"},
    )
    assert rejected_completion.status_code == 200
    rejected_detail = client.get(f"/api/ai-tasks/{rejected_task['id']}", headers=headers).json()[
        "data"
    ]
    rejected = client.post(
        f"/api/reviews/{rejected_detail['pending_review']['id']}/reject",
        json={
            "decision_reason": "隔离结果不符合预期",
            "version": rejected_detail["pending_review"]["version"],
        },
        headers=headers,
    )
    assert rejected.status_code == 200
    rejected_runner_status = client.get(
        f"/api/system/ai-executor-tasks/{rejected_start['executor_task_id']}/runner-status?runner_id={runner['id']}",
        headers={"X-Runner-Token": "runner-secret"},
    ).json()["data"]["task"]
    assert rejected_runner_status["workspace_isolation"]["decision"]["action"] == "discard"


def test_task_detail_extracts_readable_executor_output_summary():
    headers = auth_headers()
    app.state.store.reset()
    task_id = "task_executor_preview_summary"
    output_preview = (
        "@@ -150,7 +202,7 @@\n- secret\n+ environment variable\n\n"
        "tokens used\n169,685\n**整改状态：已修复**\n\n"
        "- Finding：hardcoded credential\n\n**验证方式**\n- npm test：通过\n"
    )
    app.state.store.ai_tasks[task_id] = {
        "id": task_id,
        "brain_app_id": "rd_brain",
        "created_by": "user_admin",
        "created_at": "2026-07-07T02:46:15+00:00",
        "updated_at": "2026-07-07T02:46:15+00:00",
        "status": "waiting_review",
        "current_step": "executor_completed",
        "task_type": "code_inspection_remediation",
        "title": "硬编码凭据整改",
        "product_id": "product_119",
        "version_id": None,
        "requirement_id": None,
        "input_json": {},
        "product_context": {},
        "review_ids": [],
        "graph_run_ids": [],
        "output_json": {"result": {"output_preview": output_preview}},
    }

    detail = client.get(f"/api/ai-tasks/{task_id}", headers=headers).json()["data"]

    assert detail["output_summary"].startswith("**整改状态：已修复**")
    assert "验证方式" in detail["output_summary"]
    assert "@@ -150" not in detail["output_summary"]
    assert "tokens used" not in detail["output_summary"]


def test_unified_policy_instruction_carries_code_inspection_finding_context():
    headers = auth_headers()
    app.state.store.reset()
    runner = create_codex_runner(headers)
    create_unified_runner_policy(
        headers,
        product_id=None,
        runner=runner,
        task_type="code_inspection_remediation",
        instruction="请处理 {{task_id}} / {{task_title}}。",
    )
    task_id = "task_code_inspection_context"
    app.state.store.ai_tasks[task_id] = {
        "id": task_id,
        "brain_app_id": "rd_brain",
        "created_by": "user_admin",
        "created_at": "2026-07-06T10:00:00+00:00",
        "updated_at": "2026-07-06T10:00:00+00:00",
        "status": "draft",
        "current_step": "draft",
        "task_type": "code_inspection_remediation",
        "title": "硬编码敏感凭据",
        "product_id": "product_119",
        "version_id": None,
        "requirement_id": None,
        "input_json": {
            "branch": "master",
            "file_path": "apps/api/tests/test_production_readiness.py",
            "line_number": 147,
            "rule_id": "secrets.hardcoded_credential",
            "recommendation": "使用环境变量替代。",
        },
        "product_context": {},
        "review_ids": [],
        "graph_run_ids": [],
        "output_json": None,
    }

    started = client.post(f"/api/ai-tasks/{task_id}/start", headers=headers)
    assert started.status_code == 200
    claimed = claim_runner_task(runner)

    assert "apps/api/tests/test_production_readiness.py" in claimed["instruction"]
    assert "147" in claimed["instruction"]
    assert "secrets.hardcoded_credential" in claimed["instruction"]
    assert claimed["input_payload"]["code_inspection"]["file_path"] == (
        "apps/api/tests/test_production_readiness.py"
    )


def test_unified_auto_commit_waits_for_independent_quality_gate():
    headers = auth_headers()
    requirement, task = create_development_planning_task(headers)
    runner = create_codex_runner(headers)
    verification_runner, signing_key = create_verification_runner(headers)
    assert verification_runner["attestation_status"] == "active"
    assert verification_runner["trust_domain"] == "verification"
    create_unified_runner_policy(
        headers,
        product_id=requirement["product_id"],
        runner=runner,
        quality_gate_config={"code_change_review_mode": "auto_commit"},
    )
    started = client.post(f"/api/ai-tasks/{task['id']}/start", headers=headers)
    assert started.status_code == 200
    claimed = claim_runner_task(runner)
    completed = client.post(
        f"/api/system/ai-executor-tasks/{claimed['id']}/complete",
        json={
            "runner_id": runner["id"],
            "status": "succeeded",
            "result_json": {
                "summary": "编码完成，等待独立门禁",
                "workspace_isolation": {
                    "base_workspace_root": "/Users/zeek/source/e-ai-brain",
                    "branch_name": "ai-brain/independent-gate",
                    "mode": "git_worktree",
                    "status": "pending_review",
                    "worktree_path": (
                        "/Users/zeek/source/e-ai-brain/.ai-brain-worktrees/independent-gate"
                    ),
                },
            },
        },
        headers={"X-Runner-Token": "runner-secret"},
    )
    assert completed.status_code == 200

    detail = client.get(f"/api/ai-tasks/{task['id']}", headers=headers).json()["data"]

    assert detail["current_step"] == "quality_gate_running"
    assert detail["pending_review"] is None
    gate_claim = client.post(
        "/api/system/ai-executor-tasks/claim",
        json={"executor_type": "codex", "runner_id": verification_runner["id"]},
        headers={"X-Runner-Token": "verifier-secret"},
    )
    assert gate_claim.status_code == 200
    gate_task = gate_claim.json()["data"]["task"]
    assert gate_task is not None
    gate_completed = client.post(
        f"/api/system/ai-executor-tasks/{gate_task['id']}/complete",
        json={
            "runner_id": verification_runner["id"],
            "status": "succeeded",
            "result_json": {
                "summary": "Independent verification passed",
                "changed_files": ["apps/api/app/main.py"],
                "changed_lines": 1,
                "risk_findings": [],
                "checks": [
                    {
                        "type": check_type,
                        "status": "passed",
                        "source": "platform_scan"
                        if check_type == "secret_scan"
                        else "platform_verifier",
                        "independent": True,
                        "summary": "passed",
                        "evidence_ref": f"platform://quality/{check_type}/001",
                    }
                    for check_type in ("unit_test", "type_check", "secret_scan")
                ],
                "execution_attestation": signed_execution_attestation(
                    signing_key, runner_task_id=gate_task["id"]
                ),
            },
        },
        headers={"X-Runner-Token": "verifier-secret"},
    )
    assert gate_completed.status_code == 200
    completed_detail = client.get(f"/api/ai-tasks/{task['id']}", headers=headers).json()["data"]
    assert completed_detail["status"] == "completed"
    assert completed_detail["quality_gate"]["status"] == "passed"
    runner_status = client.get(
        f"/api/system/ai-executor-tasks/{claimed['id']}/runner-status?runner_id={runner['id']}",
        headers={"X-Runner-Token": "runner-secret"},
    ).json()["data"]["task"]
    assert runner_status["workspace_isolation"]["decision"]["action"] == "merge"


def test_unified_autonomous_loop_can_be_stopped_for_human_takeover():
    headers = auth_headers()
    requirement, task = create_development_planning_task(headers)
    runner = create_codex_runner(headers)
    create_unified_runner_policy(
        headers,
        product_id=requirement["product_id"],
        runner=runner,
        autonomy_config={
            "mode": "autonomous_loop",
            "max_duration_seconds": 1800,
            "max_iterations": 3,
            "timeout_seconds": 600,
        },
    )
    started = client.post(f"/api/ai-tasks/{task['id']}/start", headers=headers)
    assert started.status_code == 200

    takeover = client.post(
        f"/api/ai-tasks/{task['id']}/agent-loop/takeover",
        json={"reason": "需要人工核对验收标准"},
        headers=headers,
    )

    assert takeover.status_code == 200
    detail = client.get(f"/api/ai-tasks/{task['id']}", headers=headers).json()["data"]
    assert detail["status"] == "waiting_review"
    assert detail["agent_loop"]["stop_reason"] == "human_takeover_requested"
    assert detail["pending_review"]["content"]["takeover_reason"] == "需要人工核对验收标准"
    runner_task = client.get(
        f"/api/system/ai-executor-tasks?ai_task_id={task['id']}", headers=headers
    ).json()["data"]["items"][0]
    assert runner_task["status"] == "cancelled"
    assert runner_task.get("workspace_isolation", {}).get("decision") is None


def test_unified_autonomous_loop_retries_failed_gate_with_versioned_context():
    headers = auth_headers()
    requirement, task = create_development_planning_task(headers)
    runner = create_codex_runner(headers)
    verification_runner, signing_key = create_verification_runner(headers)
    create_unified_runner_policy(
        headers,
        product_id=requirement["product_id"],
        runner=runner,
        autonomy_config={
            "mode": "autonomous_loop",
            "max_duration_seconds": 1800,
            "max_iterations": 2,
            "timeout_seconds": 600,
        },
        quality_gate_config={"code_change_review_mode": "auto_commit"},
    )
    started = client.post(f"/api/ai-tasks/{task['id']}/start", headers=headers)
    assert started.status_code == 200
    coding_task = claim_runner_task(runner)
    completed = client.post(
        f"/api/system/ai-executor-tasks/{coding_task['id']}/complete",
        json={
            "runner_id": runner["id"],
            "status": "succeeded",
            "result_json": {"summary": "第一轮完成"},
        },
        headers={"X-Runner-Token": "runner-secret"},
    )
    assert completed.status_code == 200
    gate_task = client.post(
        "/api/system/ai-executor-tasks/claim",
        json={"executor_type": "codex", "runner_id": verification_runner["id"]},
        headers={"X-Runner-Token": "verifier-secret"},
    ).json()["data"]["task"]
    assert gate_task["task_kind"] == "quality_gate"
    gate_completed = client.post(
        f"/api/system/ai-executor-tasks/{gate_task['id']}/complete",
        json={
            "runner_id": verification_runner["id"],
            "status": "succeeded",
            "result_json": {
                "summary": "单元测试失败",
                "checks": [
                    {
                        "type": "unit_test",
                        "status": "failed",
                        "source": "platform_verifier",
                        "summary": "first gate",
                        "evidence_ref": "platform://gate/1/unit_test",
                    }
                ],
                "risk_findings": [],
            },
        },
        headers={"X-Runner-Token": "verifier-secret"},
    )
    assert gate_completed.status_code == 200

    detail = client.get(f"/api/ai-tasks/{task['id']}", headers=headers).json()["data"]

    assert detail["current_step"] == "agent_loop_retrying"
    assert detail["agent_loop"]["current_iteration"] == 2
    assert detail["execution_context_manifest"]["version"] == 2
    retry_coding_task = claim_runner_task(runner)
    assert retry_coding_task["request_config"]["reuse_workspace"] is True
    retry_completed = client.post(
        f"/api/system/ai-executor-tasks/{retry_coding_task['id']}/complete",
        json={
            "runner_id": runner["id"],
            "status": "succeeded",
            "result_json": {"summary": "第二轮修复完成"},
        },
        headers={"X-Runner-Token": "runner-secret"},
    )
    assert retry_completed.status_code == 200
    second_gate_task = client.post(
        "/api/system/ai-executor-tasks/claim",
        json={"executor_type": "codex", "runner_id": verification_runner["id"]},
        headers={"X-Runner-Token": "verifier-secret"},
    ).json()["data"]["task"]
    assert second_gate_task["task_kind"] == "quality_gate"
    second_gate_completed = client.post(
        f"/api/system/ai-executor-tasks/{second_gate_task['id']}/complete",
        json={
            "runner_id": verification_runner["id"],
            "status": "succeeded",
            "result_json": {
                "summary": "第二轮独立验证通过",
                "risk_findings": [],
                "checks": [
                    {
                        "type": check_type,
                        "status": "passed",
                        "source": "platform_scan"
                        if check_type == "secret_scan"
                        else "platform_verifier",
                        "independent": True,
                        "summary": "passed",
                        "evidence_ref": f"platform://gate/2/{check_type}",
                    }
                    for check_type in ("unit_test", "type_check", "secret_scan")
                ],
                "execution_attestation": signed_execution_attestation(
                    signing_key, runner_task_id=second_gate_task["id"]
                ),
            },
        },
        headers={"X-Runner-Token": "verifier-secret"},
    )
    assert second_gate_completed.status_code == 200
    completed_detail = client.get(f"/api/ai-tasks/{task['id']}", headers=headers).json()["data"]
    assert completed_detail["status"] == "completed"
    assert completed_detail["agent_loop"]["status"] == "succeeded"


def valid_policy_payload(**overrides: object) -> dict:
    payload = {
        "assessment_config": {},
        "autonomy_config": {"mode": "single_pass"},
        "brain_app_id": "rd_brain",
        "delivery_target": "ready_for_release",
        "deployment_config": {},
        "experience_reuse_config": {},
        "git_config": {},
        "iteration_config": {},
        "matching_config": {"task_types": ["development_planning"]},
        "name": "统一研发执行策略",
        "product_id": None,
        "quality_gate_config": {},
        "role_bindings": [
            {
                "actor_mode": "ai",
                "primary_executor_profile_id": "executor_profile_codex",
                "role_code": "developer",
                "status": "active",
            }
        ],
        "status": "active",
        "team_config": {"required_role_codes": ["developer"]},
    }
    payload.update(overrides)
    return payload


def test_policy_rejects_missing_required_role_binding():
    response = client.post(
        "/api/delivery/rd-task-executor-policies",
        headers=auth_headers(),
        json=valid_policy_payload(role_bindings=[]),
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "RD_POLICY_REQUIRED_ROLE_MISSING"


def test_policy_rejects_legacy_task_executor_fields():
    response = client.post(
        "/api/delivery/rd-task-executor-policies",
        headers=auth_headers(),
        json=valid_policy_payload(
            executor_type="codex",
            runner_id="runner_codex",
            task_type="development_planning",
        ),
    )

    assert response.status_code == 422


def test_policy_rejects_model_gateway_executor_profile():
    app.state.store.reset()
    profile_id = "profile_model_gateway"
    app.state.store.rd_executor_profiles[profile_id] = {
        "id": profile_id,
        "executor_type": "model_gateway",
        "runner_id": "runner_model_gateway",
        "status": "active",
    }
    payload = valid_policy_payload(
        role_bindings=[
            {
                "role_code": "developer",
                "actor_mode": "ai",
                "primary_executor_profile_id": profile_id,
                "status": "active",
            }
        ]
    )

    response = client.post(
        "/api/delivery/rd-task-executor-policies", headers=auth_headers(), json=payload
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "RD_EXECUTION_POLICY_INVALID"


def test_policy_patch_requires_matching_policy_version_and_keeps_unified_contract():
    app.state.store.reset()
    headers = auth_headers()
    created = client.post(
        "/api/delivery/rd-task-executor-policies",
        headers=headers,
        json=valid_policy_payload(),
    )
    assert created.status_code == 200
    policy = created.json()["data"]["policy"]
    assert policy["policy_version"] == 1
    assert policy["role_bindings"][0]["role_code"] == "developer"

    duplicate = client.post(
        "/api/delivery/rd-task-executor-policies",
        headers=headers,
        json=valid_policy_payload(name="同一范围的第二个策略"),
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"]["code"] == "RD_EXECUTION_POLICY_INVALID"

    updated = client.patch(
        f"/api/delivery/rd-task-executor-policies/{policy['id']}",
        headers=headers,
        json={
            "changes": {"name": "策略 v2"},
            "expected_policy_version": 1,
        },
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["policy"]["policy_version"] == 2

    stale = client.patch(
        f"/api/delivery/rd-task-executor-policies/{policy['id']}",
        headers=headers,
        json={
            "changes": {"name": "过期更新"},
            "expected_policy_version": 1,
        },
    )
    assert stale.status_code == 409
    assert stale.json()["detail"]["code"] == "RD_VERSION_CONFLICT"
    assert updated.json()["data"]["policy"]["role_bindings"][0]["role_code"] == "developer"

    deleted = client.delete(
        f"/api/delivery/rd-task-executor-policies/{policy['id']}", headers=headers
    )
    assert deleted.status_code == 200
    assert deleted.json()["data"] == {"deleted": True, "id": policy["id"]}
    assert policy["id"] not in app.state.store.rd_task_executor_policies
    assert {
        event["event_type"]
        for event in app.state.store.audit_events
        if event.get("subject_id") == policy["id"]
    } >= {
        "rd_task_executor_policy.created",
        "rd_task_executor_policy.updated",
        "rd_task_executor_policy.deleted",
    }


def test_policy_list_uses_all_canonical_task_types_without_legacy_scalar_filter():
    app.state.store.reset()
    headers = auth_headers()
    created = client.post(
        "/api/delivery/rd-task-executor-policies",
        headers=headers,
        json=valid_policy_payload(
            matching_config={"task_types": ["development_planning", "automated_testing"]}
        ),
    )
    assert created.status_code == 200

    response = client.get(
        "/api/delivery/rd-task-executor-policies?task_type=automated_testing",
        headers=headers,
    )

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["data"]["items"]] == [
        created.json()["data"]["policy"]["id"]
    ]


def test_work_item_binding_requires_exactly_one_active_role_without_fallback():
    snapshot = {
        "content_hash": "sha256:ignored",
        "payload_json": {
            "matching_config": {"task_types": ["development_planning"]},
            "role_bindings": [
                {"role_code": "developer", "status": "active", "actor_mode": "ai"},
                {"role_code": "developer", "status": "active", "actor_mode": "ai"},
            ],
        },
    }

    try:
        resolve_work_item_binding(
            snapshot,
            role_code="developer",
            task_type="development_planning",
        )
    except PolicyResolutionError as exc:
        assert exc.code == "RD_POLICY_SNAPSHOT_INVALID"
    else:
        raise AssertionError("multiple active bindings must not select a fallback executor")


def test_version_merge_tightens_known_policy_operators_and_rejects_unknown_delta():
    merged = merge_policy_payloads(
        [
            {
                "delivery_target": "deployed",
                "quality_gate_config": {"gates": ["security"], "max_risk": "medium"},
                "experience_reuse_config": {
                    "enabled": True,
                    "min_confidence": 0.6,
                    "max_capacity": 8,
                    "max_age_days": 30,
                    "policy_compatibility": "same_policy_schema",
                    "repository_trust_domains": ["trusted", "internal"],
                    "tool_trust_domains": ["approved", "internal"],
                    "require_independent_reviewer": False,
                },
                "git_config": {
                    "allowlist": ["repo-a", "repo-b"],
                    "denylist": ["repo-danger"],
                    "repository_trust_domains": ["trusted", "internal"],
                    "tool_trust_domains": ["approved", "internal"],
                },
                "iteration_config": {
                    "budget": {
                        "base_run_cap": 100,
                        "per_requirement_allocations": {"req-a": 80},
                    }
                },
            },
            {
                "delivery_target": "ready_for_release",
                "quality_gate_config": {"gates": ["compliance"], "max_risk": "low"},
                "experience_reuse_config": {
                    "enabled": False,
                    "min_confidence": 0.8,
                    "max_capacity": 4,
                    "max_age_days": 7,
                    "policy_compatibility": "same_policy_version",
                    "repository_trust_domains": ["trusted", "partner"],
                    "tool_trust_domains": ["approved", "sandbox"],
                    "require_independent_reviewer": True,
                },
                "git_config": {
                    "allowlist": ["repo-b", "repo-c"],
                    "denylist": ["repo-legacy"],
                    "repository_trust_domains": ["trusted", "partner"],
                    "tool_trust_domains": ["approved", "sandbox"],
                },
                "iteration_config": {
                    "budget": {
                        "base_run_cap": 60,
                        "per_requirement_allocations": {"req-b": 40},
                    }
                },
            },
        ]
    )
    assert merged["delivery_target"] == "ready_for_release"
    assert merged["quality_gate_config"]["gates"] == ["compliance", "security"]
    assert merged["quality_gate_config"]["max_risk"] == "low"
    assert merged["experience_reuse_config"] == {
        "enabled": False,
        "min_confidence": 0.8,
        "max_capacity": 4,
        "max_age_days": 7,
        "policy_compatibility": "same_policy_version",
        "repository_trust_domains": ["trusted"],
        "tool_trust_domains": ["approved"],
        "require_independent_reviewer": True,
    }
    assert merged["git_config"]["allowlist"] == ["repo-b"]
    assert merged["git_config"]["denylist"] == ["repo-danger", "repo-legacy"]
    assert merged["git_config"]["repository_trust_domains"] == ["trusted"]
    assert merged["git_config"]["tool_trust_domains"] == ["approved"]
    assert merged["iteration_config"]["budget"] == {
        "base_run_cap": 60,
        "per_requirement_allocations": {"req-a": 80, "req-b": 40},
    }

    compatibility = merge_policy_payloads(
        [
            {"experience_reuse_config": {"policy_compatibility": "same_policy_version"}},
            {"experience_reuse_config": {"policy_compatibility": "same_policy_schema"}},
        ]
    )
    assert compatibility["experience_reuse_config"]["policy_compatibility"] == (
        "same_policy_version"
    )

    try:
        merge_policy_payloads(
            [
                {"quality_gate_config": {"max_undeclared": 5}},
                {"quality_gate_config": {"max_undeclared": 3}},
            ]
        )
    except PolicyResolutionError as exc:
        assert exc.code == "RD_VERSION_POLICY_MERGE_REQUIRED"
    else:
        raise AssertionError("undeclared numeric paths must require a human decision")

    base = {"quality_gate_config": {}}
    candidate = {"quality_gate_config": {"max_undeclared": 3}}
    try:
        merge_policy_payloads([base, candidate])
    except PolicyResolutionError as exc:
        assert exc.code == "RD_VERSION_POLICY_MERGE_REQUIRED"
    else:
        raise AssertionError("absent unregistered fields must require a human decision")
    assert not is_monotonic_strengthening(base, candidate)

    base = {"experience_reuse_config": {}}
    candidate = {"experience_reuse_config": {"policy_compatibility": "same_policy_schema"}}
    normalized = merge_policy_payloads([base, candidate])
    assert normalized["experience_reuse_config"]["policy_compatibility"] == ("same_policy_version")
    assert not is_monotonic_strengthening(base, candidate)

    try:
        merge_policy_payloads([{"undeclared": "one"}, {"undeclared": "two"}])
    except PolicyResolutionError as exc:
        assert exc.code == "RD_VERSION_POLICY_MERGE_REQUIRED"
    else:
        raise AssertionError("incomparable fields must require a human decision")


def test_policy_snapshot_hash_and_identity_are_checked_and_no_delta_reuses_base():
    class Repository:
        def __init__(self) -> None:
            self.snapshots: dict[str, dict] = {}

        def freeze_base_policy_snapshot(self, snapshot: dict) -> dict:
            self.snapshots[snapshot["id"]] = snapshot
            return snapshot

        def get_rd_policy_snapshot(self, snapshot_id: str) -> dict | None:
            return self.snapshots.get(snapshot_id)

    class Store:
        repository = Repository()

        def __init__(self) -> None:
            self.index = 0

        def new_id(self, prefix: str) -> str:
            self.index += 1
            return f"{prefix}_{self.index}"

    store = Store()
    policy = {"id": "policy_1", "policy_version": 1, "created_by": "user_admin"}
    policy.update(valid_policy_payload())
    base = freeze_base_rd_policy_snapshot(store, policy=policy)
    assert (
        resolve_final_rd_policy(
            store,
            requirement={"id": "requirement_1"},
            assessment={"id": "assessment_1", "initial_strategy_snapshot_id": base["id"]},
        )
        == base
    )

    bad_hash = {**base, "content_hash": "sha256:wrong"}
    store.repository.snapshots[base["id"]] = bad_hash
    try:
        resolve_final_rd_policy(
            store,
            requirement={"id": "requirement_1"},
            assessment={"id": "assessment_1", "initial_strategy_snapshot_id": base["id"]},
        )
    except PolicyResolutionError as exc:
        assert exc.code == "RD_POLICY_SNAPSHOT_INVALID"
    else:
        raise AssertionError("historical reads must reject hash-mismatched snapshots")


def test_assessment_policy_expansion_requires_human_decision():
    class Repository:
        def __init__(self, snapshot: dict) -> None:
            self.snapshot = snapshot

        def get_rd_policy_snapshot(self, _snapshot_id: str) -> dict:
            return self.snapshot

    class Store:
        def __init__(self, snapshot: dict) -> None:
            self.repository = Repository(snapshot)

        def new_id(self, prefix: str) -> str:
            return f"{prefix}_next"

    payload = valid_policy_payload(quality_gate_config={"max_risk": "low"})
    snapshot = {
        "id": "snapshot_base",
        "policy_id": "policy_1",
        "policy_version": 1,
        "parent_snapshot_id": None,
        "snapshot_kind": "base",
        "resolution_context_key": "policy:policy_1:version:1",
        "resolution_revision": 0,
        "schema_version": 1,
        "created_by": "user_admin",
        "content_hash": _hash(payload),
        "payload_json": payload,
    }
    try:
        derive_assessment_rd_policy_snapshot(
            Store(snapshot),
            assessment_id="assessment_1",
            parent_snapshot_id="snapshot_base",
            resolution_revision=1,
            tightened_payload=valid_policy_payload(quality_gate_config={"max_risk": "medium"}),
        )
    except PolicyResolutionError as exc:
        assert exc.code == "RD_POLICY_HUMAN_DECISION_REQUIRED"
    else:
        raise AssertionError("assessment must not expand automation or risk scope")


def test_snapshot_chain_rejects_cross_assessment_revision_two_parent():
    payload = valid_policy_payload()
    base = {
        "id": "base",
        "policy_id": "policy_1",
        "policy_version": 1,
        "parent_snapshot_id": None,
        "snapshot_kind": "base",
        "resolution_context_key": "policy:policy_1:version:1",
        "resolution_revision": 0,
        "schema_version": 1,
        "created_by": "user_admin",
        "content_hash": _hash(payload),
        "payload_json": payload,
    }
    revision_one = {
        **base,
        "id": "revision_one",
        "parent_snapshot_id": "base",
        "snapshot_kind": "assessment_resolved",
        "resolution_context_key": "assessment:other_assessment",
        "resolution_revision": 1,
    }
    revision_two = {
        **base,
        "id": "revision_two",
        "parent_snapshot_id": "revision_one",
        "snapshot_kind": "assessment_resolved",
        "resolution_context_key": "assessment:this_assessment",
        "resolution_revision": 2,
    }

    class Repository:
        snapshots = {"base": base, "revision_one": revision_one}

        def get_rd_policy_snapshot(self, snapshot_id: str) -> dict | None:
            return self.snapshots.get(snapshot_id)

    try:
        validate_snapshot_chain(Repository(), revision_two)
    except PolicyResolutionError as exc:
        assert exc.code == "RD_POLICY_SNAPSHOT_INVALID"
    else:
        raise AssertionError("revision two must use the same assessment revision one parent")


def test_base_snapshot_source_traversal_rejects_parent_cycle():
    payload = valid_policy_payload()
    first = {
        "id": "assessment_a",
        "policy_id": "policy_1",
        "policy_version": 1,
        "parent_snapshot_id": "assessment_b",
        "snapshot_kind": "assessment_resolved",
        "resolution_context_key": "assessment:assessment_1",
        "resolution_revision": 2,
        "schema_version": 1,
        "created_by": "user_admin",
        "content_hash": _hash(payload),
        "payload_json": payload,
    }
    second = {
        **first,
        "id": "assessment_b",
        "parent_snapshot_id": "assessment_a",
        "resolution_revision": 1,
    }
    snapshots = {"assessment_a": first, "assessment_b": second}

    try:
        _base_snapshot_for_source(first, snapshots.get)
    except PolicyResolutionError as exc:
        assert exc.code == "RD_POLICY_SNAPSHOT_INVALID"
    else:
        raise AssertionError("source traversal must reject a parent cycle")


def test_merge_ambiguity_persists_constrained_decision_without_snapshot():
    base_payload = valid_policy_payload(product_id="product_1")

    def snapshot(
        snapshot_id: str,
        *,
        parent_id: str | None,
        kind: str,
        context: str,
        revision: int,
        payload: dict,
    ) -> dict:
        return {
            "id": snapshot_id,
            "policy_id": "policy_1",
            "policy_version": 1,
            "parent_snapshot_id": parent_id,
            "snapshot_kind": kind,
            "resolution_context_key": context,
            "resolution_revision": revision,
            "schema_version": 1,
            "created_by": "user_admin",
            "content_hash": _hash(payload),
            "payload_json": payload,
        }

    base = snapshot(
        "base",
        parent_id=None,
        kind="base",
        context="policy:policy_1:version:1",
        revision=0,
        payload=base_payload,
    )
    first = snapshot(
        "assessment_one",
        parent_id="base",
        kind="assessment_resolved",
        context="assessment:assessment_1",
        revision=1,
        payload=valid_policy_payload(
            product_id="product_1", assessment_config={"unregistered": "first"}
        ),
    )
    second = snapshot(
        "assessment_two",
        parent_id="base",
        kind="assessment_resolved",
        context="assessment:assessment_2",
        revision=1,
        payload=valid_policy_payload(
            product_id="product_1", assessment_config={"unregistered": "second"}
        ),
    )

    class Repository:
        snapshots = {"base": base, "assessment_one": first, "assessment_two": second}
        assessments = {
            "assessment_1": {"id": "assessment_1", "requirement_id": "requirement_1"},
            "assessment_2": {"id": "assessment_2", "requirement_id": "requirement_2"},
        }

        def __init__(self) -> None:
            self.decisions: list[dict] = []

        def get_rd_policy_snapshot(self, snapshot_id: str) -> dict | None:
            return self.snapshots.get(snapshot_id)

        def get_requirement_assessment(self, assessment_id: str) -> dict | None:
            return self.assessments.get(assessment_id)

        def save_decision_request_record(self, record: dict) -> dict:
            self.decisions.append(record)
            return record

    class Store:
        def __init__(self) -> None:
            self.repository = Repository()
            self.index = 0

        def new_id(self, prefix: str) -> str:
            self.index += 1
            return f"{prefix}_{self.index}"

    store = Store()
    try:
        merge_version_rd_policy_snapshot(
            store,
            version_id="version_1",
            scope_version=1,
            source_provenance=[
                {"final_snapshot_id": "assessment_one", "assessment_id": "assessment_1"},
                {"final_snapshot_id": "assessment_two", "assessment_id": "assessment_2"},
            ],
        )
    except PolicyResolutionError as exc:
        assert exc.code == "RD_VERSION_POLICY_MERGE_REQUIRED"
        assert exc.details["decision_request_id"] == store.repository.decisions[0]["id"]
    else:
        raise AssertionError("an unregistered merge path must not create a version snapshot")
    assert [option["code"] for option in store.repository.decisions[0]["options_json"]] == [
        "split_requirements",
        "remove_requirement",
        "reassess_with_updated_policy",
        "cancel_start",
    ]


def test_version_merge_persists_requirement_assessment_source_provenance():
    class Repository:
        def __init__(self) -> None:
            self.snapshots: dict[str, dict] = {}
            self.assessments = {
                "assessment_1": {"id": "assessment_1", "requirement_id": "requirement_1"},
                "assessment_2": {"id": "assessment_2", "requirement_id": "requirement_2"},
            }
            self.merged_sources: list[dict] = []

        def freeze_base_policy_snapshot(self, snapshot: dict) -> dict:
            self.snapshots[snapshot["id"]] = snapshot
            return snapshot

        def derive_assessment_policy_snapshot(
            self, *, base_snapshot_id: str, snapshot: dict
        ) -> dict:
            assert snapshot["parent_snapshot_id"] == base_snapshot_id
            self.snapshots[snapshot["id"]] = snapshot
            return snapshot

        def get_rd_policy_snapshot(self, snapshot_id: str) -> dict | None:
            return self.snapshots.get(snapshot_id)

        def get_requirement_assessment(self, assessment_id: str) -> dict | None:
            return self.assessments.get(assessment_id)

        def merge_version_policy_snapshot_with_sources(
            self, *, snapshot: dict, sources: list[dict]
        ) -> dict:
            self.snapshots[snapshot["id"]] = snapshot
            self.merged_sources = sources
            return snapshot

    class Store:
        def __init__(self) -> None:
            self.repository = Repository()
            self.index = 0

        def new_id(self, prefix: str) -> str:
            self.index += 1
            return f"{prefix}_{self.index}"

    store = Store()
    policy = {"id": "policy_1", "policy_version": 1, "created_by": "user_admin"}
    policy.update(valid_policy_payload(quality_gate_config={"max_risk": "medium"}))
    base = freeze_base_rd_policy_snapshot(store, policy=policy)
    first = derive_assessment_rd_policy_snapshot(
        store,
        assessment_id="assessment_1",
        parent_snapshot_id=base["id"],
        resolution_revision=1,
        tightened_payload=valid_policy_payload(quality_gate_config={"max_risk": "low"}),
    )
    first_revision_two = derive_assessment_rd_policy_snapshot(
        store,
        assessment_id="assessment_1",
        parent_snapshot_id=first["id"],
        resolution_revision=2,
        tightened_payload=valid_policy_payload(
            quality_gate_config={"max_risk": "low", "gates": ["security"]}
        ),
    )
    second = derive_assessment_rd_policy_snapshot(
        store,
        assessment_id="assessment_2",
        parent_snapshot_id=base["id"],
        resolution_revision=1,
        tightened_payload=valid_policy_payload(
            quality_gate_config={"max_risk": "medium", "gates": ["security"]}
        ),
    )

    merged = merge_version_rd_policy_snapshot(
        store,
        version_id="version_1",
        scope_version=3,
        source_provenance=[
            {
                "final_snapshot_id": first_revision_two["id"],
                "assessment_id": "assessment_1",
            },
            {"final_snapshot_id": second["id"], "assessment_id": "assessment_2"},
        ],
    )

    assert merged["resolution_context_key"] == "version:version_1:scope:3"
    assert {
        (source["requirement_id"], source["assessment_id"])
        for source in store.repository.merged_sources
    } == {("requirement_1", "assessment_1"), ("requirement_2", "assessment_2")}
