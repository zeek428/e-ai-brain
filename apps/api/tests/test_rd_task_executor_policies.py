from fastapi.testclient import TestClient

from app.main import app
from tests.test_technical_solution_export import auth_headers
from tests.test_v1_1_task_types import create_confirmed_technical_solution_task

client = TestClient(app)


def create_codex_runner(headers: dict[str, str]) -> dict:
    response = client.post(
        "/api/system/ai-executor-runners",
        json={
            "executor_types": ["codex"],
            "name": "本地 Codex 研发执行器",
            "protocol": "runner_polling",
            "runner_token": "runner-secret",
            "workspace_roots": ["/Users/zeek/source/e-ai-brain"],
        },
        headers=headers,
    )
    assert response.status_code == 200
    return response.json()["data"]


def test_rd_task_executor_policy_queues_runner_and_creates_review_on_success():
    headers = auth_headers()
    requirement, technical_solution_task_id = create_confirmed_technical_solution_task(headers)
    runner = create_codex_runner(headers)

    policy_response = client.post(
        "/api/delivery/rd-task-executor-policies",
        json={
            "executor_type": "codex",
            "instruction_template": (
                "处理任务 {{task_id}} / {{task_title}}，需求 {{requirement_id}}。"
            ),
            "name": "开发计划走 Codex",
            "output_contract": {"summary": "string"},
            "priority": 10,
            "product_id": requirement["product_id"],
            "runner_id": runner["id"],
            "status": "active",
            "task_type": "development_planning",
            "timeout_seconds": 600,
            "workspace_root": "/Users/zeek/source/e-ai-brain",
        },
        headers=headers,
    )
    assert policy_response.status_code == 200
    policy = policy_response.json()["data"]
    assert policy["executor_type"] == "codex"
    assert policy["runner_id"] == runner["id"]
    assert "agent" not in policy
    assert "skill" not in policy

    created = client.post(
        "/api/ai-tasks",
        json={
            "input": {"technical_solution_task_id": technical_solution_task_id},
            "requirement_id": requirement["id"],
            "task_type": "development_planning",
            "title": "开发计划：走本地执行器",
        },
        headers=headers,
    ).json()["data"]

    started = client.post(f"/api/ai-tasks/{created['id']}/start", headers=headers)
    assert started.status_code == 200
    start_payload = started.json()["data"]
    assert start_payload["status"] == "running"
    assert start_payload["current_step"] == "waiting_ai_executor"
    assert start_payload["executor_policy_id"] == policy["id"]
    assert start_payload["runner_id"] == runner["id"]

    runner_task_id = start_payload["executor_task_id"]
    claimed = client.post(
        "/api/system/ai-executor-tasks/claim",
        json={"executor_type": "codex", "runner_id": runner["id"]},
        headers={"X-Runner-Token": "runner-secret"},
    )
    assert claimed.status_code == 200
    claimed_task = claimed.json()["data"]["task"]
    assert claimed_task["id"] == runner_task_id
    assert claimed_task["ai_task_id"] == created["id"]
    assert claimed_task["instruction"].startswith(f"处理任务 {created['id']}")

    completed = client.post(
        f"/api/system/ai-executor-tasks/{runner_task_id}/complete",
        json={
            "logs": [{"level": "info", "message": "codex finished"}],
            "result_json": {"summary": "开发计划已生成", "tasks": ["补充接口", "联调页面"]},
            "runner_id": runner["id"],
            "status": "succeeded",
        },
        headers={"X-Runner-Token": "runner-secret"},
    )
    assert completed.status_code == 200

    detail = client.get(f"/api/ai-tasks/{created['id']}", headers=headers).json()["data"]
    assert detail["status"] == "waiting_review"
    assert detail["current_step"] == "executor_completed"
    assert detail["input"]["executor"]["runner_task_id"] == runner_task_id
    assert detail["output"]["executor"]["runner_id"] == runner["id"]
    assert detail["output"]["result"]["summary"] == "开发计划已生成"
    assert detail["output"]["summary"] == "开发计划已生成"
    assert detail["output_summary"] == "开发计划已生成"
    assert detail["pending_review"]["status"] == "pending"
    assert detail["pending_review"]["stage"] == "development_planning"
    assert detail["pending_review"]["content"]["summary"] == "开发计划已生成"

    runner_tasks = client.get(
        f"/api/system/ai-executor-tasks?ai_task_id={created['id']}",
        headers=headers,
    ).json()["data"]
    assert runner_tasks["total"] == 1
    assert runner_tasks["items"][0]["id"] == runner_task_id


def test_rd_task_executor_policy_includes_product_knowledge_references_for_runner():
    headers = auth_headers()
    requirement, technical_solution_task_id = create_confirmed_technical_solution_task(headers)
    runner = create_codex_runner(headers)
    product_id = requirement["product_id"]
    version_id = requirement["version_id"]

    app.state.store.knowledge_documents["knowledge_project_doc"] = {
        "active_chunk_set_id": None,
        "brain_app_id": "rd_brain",
        "content": "项目约定正文",
        "created_at": "2026-07-08T09:00:00+00:00",
        "created_by": "user_admin",
        "doc_type": "project_doc",
        "folder_id": None,
        "id": "knowledge_project_doc",
        "index_status": "indexed",
        "knowledge_space_id": None,
        "permission_roles": ["admin"],
        "product_id": product_id,
        "tags": ["研发规范"],
        "title": "研发大脑项目编码规范",
        "updated_at": "2026-07-08T09:00:00+00:00",
        "version_id": version_id,
    }
    app.state.store.knowledge_chunks["knowledge_project_doc_chunk_001"] = {
        "chunk_index": 0,
        "content": "项目文档要求：登录页不得硬编码账号密码，任务实现必须补充回归测试。",
        "document_id": "knowledge_project_doc",
        "id": "knowledge_project_doc_chunk_001",
        "metadata": {},
        "permission_scope": {},
    }
    app.state.store.knowledge_documents["knowledge_other_product_doc"] = {
        "active_chunk_set_id": None,
        "brain_app_id": "rd_brain",
        "content": "其他产品正文",
        "created_at": "2026-07-08T09:00:00+00:00",
        "created_by": "user_admin",
        "doc_type": "project_doc",
        "folder_id": None,
        "id": "knowledge_other_product_doc",
        "index_status": "indexed",
        "knowledge_space_id": None,
        "permission_roles": ["admin"],
        "product_id": "product_other",
        "tags": ["隔离验证"],
        "title": "其他产品项目文档",
        "updated_at": "2026-07-08T09:00:00+00:00",
        "version_id": version_id,
    }
    app.state.store.knowledge_chunks["knowledge_other_product_doc_chunk_001"] = {
        "chunk_index": 0,
        "content": "其他产品专属上下文不能进入当前研发任务。",
        "document_id": "knowledge_other_product_doc",
        "id": "knowledge_other_product_doc_chunk_001",
        "metadata": {},
        "permission_scope": {},
    }

    policy_response = client.post(
        "/api/delivery/rd-task-executor-policies",
        json={
            "executor_type": "codex",
            "instruction_template": "处理任务 {{task_id}} / {{task_title}}。",
            "name": "开发计划带知识上下文",
            "output_contract": {"summary": "string"},
            "priority": 10,
            "product_id": product_id,
            "runner_id": runner["id"],
            "status": "active",
            "task_type": "development_planning",
            "timeout_seconds": 600,
            "workspace_root": "/Users/zeek/source/e-ai-brain",
        },
        headers=headers,
    )
    assert policy_response.status_code == 200

    created = client.post(
        "/api/ai-tasks",
        json={
            "input": {"technical_solution_task_id": technical_solution_task_id},
            "requirement_id": requirement["id"],
            "task_type": "development_planning",
            "title": "开发计划：携带项目文档",
        },
        headers=headers,
    ).json()["data"]

    started = client.post(f"/api/ai-tasks/{created['id']}/start", headers=headers)
    assert started.status_code == 200
    runner_task_id = started.json()["data"]["executor_task_id"]

    claimed = client.post(
        "/api/system/ai-executor-tasks/claim",
        json={"executor_type": "codex", "runner_id": runner["id"]},
        headers={"X-Runner-Token": "runner-secret"},
    )
    assert claimed.status_code == 200
    claimed_task = claimed.json()["data"]["task"]
    assert claimed_task["id"] == runner_task_id

    instruction = claimed_task["instruction"]
    assert "产品知识中心上下文" in instruction
    assert "研发大脑项目编码规范" in instruction
    assert "登录页不得硬编码账号密码" in instruction
    assert "其他产品专属上下文" not in instruction
    references = claimed_task["input_payload"]["knowledge_references"]
    assert references == [
        {
            "chunk_id": "knowledge_project_doc_chunk_001",
            "chunk_index": 0,
            "content": "项目文档要求：登录页不得硬编码账号密码，任务实现必须补充回归测试。",
            "document_id": "knowledge_project_doc",
            "doc_type": "project_doc",
            "folder_id": None,
            "knowledge_space_id": None,
            "title": "研发大脑项目编码规范",
        }
    ]


def test_executor_review_decision_exposes_workspace_isolation_action_to_runner():
    headers = auth_headers()
    requirement, technical_solution_task_id = create_confirmed_technical_solution_task(headers)
    runner = create_codex_runner(headers)

    policy_response = client.post(
        "/api/delivery/rd-task-executor-policies",
        json={
            "executor_type": "codex",
            "instruction_template": "处理任务 {{task_id}}。",
            "name": "Codex 隔离工作区",
            "output_contract": {"summary": "string"},
            "priority": 10,
            "product_id": requirement["product_id"],
            "runner_id": runner["id"],
            "status": "active",
            "task_type": "development_planning",
            "timeout_seconds": 600,
            "workspace_root": "/Users/zeek/source/e-ai-brain",
        },
        headers=headers,
    )
    assert policy_response.status_code == 200

    created = client.post(
        "/api/ai-tasks",
        json={
            "input": {"technical_solution_task_id": technical_solution_task_id},
            "requirement_id": requirement["id"],
            "task_type": "development_planning",
            "title": "开发计划：隔离工作区",
        },
        headers=headers,
    ).json()["data"]
    started = client.post(f"/api/ai-tasks/{created['id']}/start", headers=headers).json()["data"]
    assert started["executor_policy_id"] == policy_response.json()["data"]["id"]
    runner_task_id = started["executor_task_id"]
    client.post(
        "/api/system/ai-executor-tasks/claim",
        json={"executor_type": "codex", "runner_id": runner["id"]},
        headers={"X-Runner-Token": "runner-secret"},
    )
    completed = client.post(
        f"/api/system/ai-executor-tasks/{runner_task_id}/complete",
        json={
            "result_json": {
                "summary": "开发计划已生成",
                "workspace_isolation": {
                    "base_workspace_root": "/Users/zeek/source/e-ai-brain",
                    "branch_name": "ai-brain/ai_executor_task_001",
                    "mode": "git_worktree",
                    "status": "pending_review",
                    "worktree_path": (
                        "/Users/zeek/source/e-ai-brain/.ai-brain-worktrees/"
                        "ai_executor_task_001"
                    ),
                },
            },
            "runner_id": runner["id"],
            "status": "succeeded",
        },
        headers={"X-Runner-Token": "runner-secret"},
    )
    assert completed.status_code == 200

    detail = client.get(f"/api/ai-tasks/{created['id']}", headers=headers).json()["data"]
    review_id = detail["pending_review"]["id"]
    approved = client.post(
        f"/api/reviews/{review_id}/approve",
        json={"version": detail["pending_review"]["version"]},
        headers=headers,
    )
    assert approved.status_code == 200
    runner_status = client.get(
        f"/api/system/ai-executor-tasks/{runner_task_id}/runner-status?runner_id={runner['id']}",
        headers={"X-Runner-Token": "runner-secret"},
    ).json()["data"]["task"]
    assert runner_status["workspace_isolation"]["decision"]["action"] == "merge"
    assert runner_status["workspace_isolation"]["decision"]["status"] == "requested"
    merge_completed = client.post(
        f"/api/system/ai-executor-tasks/{runner_task_id}/workspace-decision",
        json={
            "action": "merge",
            "message": "merged into base workspace",
            "runner_id": runner["id"],
            "status": "completed",
        },
        headers={"X-Runner-Token": "runner-secret"},
    )
    assert merge_completed.status_code == 200
    assert (
        merge_completed.json()["data"]["workspace_isolation"]["decision"]["status"]
        == "completed"
    )

    created_for_reject = client.post(
        "/api/ai-tasks",
        json={
            "input": {"technical_solution_task_id": technical_solution_task_id},
            "requirement_id": requirement["id"],
            "task_type": "development_planning",
            "title": "开发计划：隔离工作区拒绝",
        },
        headers=headers,
    ).json()["data"]
    started_for_reject = client.post(
        f"/api/ai-tasks/{created_for_reject['id']}/start",
        headers=headers,
    ).json()["data"]
    reject_runner_task_id = started_for_reject["executor_task_id"]
    client.post(
        "/api/system/ai-executor-tasks/claim",
        json={"executor_type": "codex", "runner_id": runner["id"]},
        headers={"X-Runner-Token": "runner-secret"},
    )
    client.post(
        f"/api/system/ai-executor-tasks/{reject_runner_task_id}/complete",
        json={
            "result_json": {
                "summary": "需要拒绝",
                "workspace_isolation": {
                    "base_workspace_root": "/Users/zeek/source/e-ai-brain",
                    "branch_name": "ai-brain/ai_executor_task_002",
                    "mode": "git_worktree",
                    "status": "pending_review",
                    "worktree_path": (
                        "/Users/zeek/source/e-ai-brain/.ai-brain-worktrees/"
                        "ai_executor_task_002"
                    ),
                },
            },
            "runner_id": runner["id"],
            "status": "succeeded",
        },
        headers={"X-Runner-Token": "runner-secret"},
    )
    reject_detail = client.get(
        f"/api/ai-tasks/{created_for_reject['id']}",
        headers=headers,
    ).json()["data"]
    rejected = client.post(
        f"/api/reviews/{reject_detail['pending_review']['id']}/reject",
        json={
            "decision_reason": "隔离结果不符合预期",
            "version": reject_detail["pending_review"]["version"],
        },
        headers=headers,
    )
    assert rejected.status_code == 200
    reject_runner_status = client.get(
        f"/api/system/ai-executor-tasks/{reject_runner_task_id}/runner-status?runner_id={runner['id']}",
        headers={"X-Runner-Token": "runner-secret"},
    ).json()["data"]["task"]
    assert reject_runner_status["workspace_isolation"]["decision"]["action"] == "discard"
    assert reject_runner_status["workspace_isolation"]["decision"]["status"] == "requested"
    discard_completed = client.post(
        f"/api/system/ai-executor-tasks/{reject_runner_task_id}/workspace-decision",
        json={
            "action": "discard",
            "message": "discarded isolated worktree",
            "runner_id": runner["id"],
            "status": "completed",
        },
        headers={"X-Runner-Token": "runner-secret"},
    )
    assert discard_completed.status_code == 200
    assert (
        discard_completed.json()["data"]["workspace_isolation"]["decision"]["status"]
        == "completed"
    )


def test_executor_policy_auto_commit_requests_workspace_merge_without_pending_review():
    headers = auth_headers()
    requirement, technical_solution_task_id = create_confirmed_technical_solution_task(headers)
    runner = create_codex_runner(headers)

    policy_response = client.post(
        "/api/delivery/rd-task-executor-policies",
        json={
            "code_change_review_mode": "auto_commit",
            "executor_type": "codex",
            "instruction_template": "处理任务 {{task_id}}。",
            "name": "Codex 自动提交隔离工作区",
            "output_contract": {"summary": "string"},
            "priority": 10,
            "product_id": requirement["product_id"],
            "runner_id": runner["id"],
            "status": "active",
            "task_type": "development_planning",
            "timeout_seconds": 600,
            "workspace_root": "/Users/zeek/source/e-ai-brain",
        },
        headers=headers,
    )
    assert policy_response.status_code == 200
    assert policy_response.json()["data"]["code_change_review_mode"] == "auto_commit"

    created = client.post(
        "/api/ai-tasks",
        json={
            "input": {"technical_solution_task_id": technical_solution_task_id},
            "requirement_id": requirement["id"],
            "task_type": "development_planning",
            "title": "开发计划：自动提交隔离工作区",
        },
        headers=headers,
    ).json()["data"]
    started = client.post(f"/api/ai-tasks/{created['id']}/start", headers=headers).json()["data"]
    assert started["executor_policy_id"] == policy_response.json()["data"]["id"]
    runner_task_id = started["executor_task_id"]
    client.post(
        "/api/system/ai-executor-tasks/claim",
        json={"executor_type": "codex", "runner_id": runner["id"]},
        headers={"X-Runner-Token": "runner-secret"},
    )
    completed = client.post(
        f"/api/system/ai-executor-tasks/{runner_task_id}/complete",
        json={
            "result_json": {
                "summary": "开发计划已生成并通过自动提交策略",
                "workspace_isolation": {
                    "base_workspace_root": "/Users/zeek/source/e-ai-brain",
                    "branch_name": "ai-brain/ai_executor_task_auto_commit",
                    "mode": "git_worktree",
                    "status": "pending_review",
                    "worktree_path": (
                        "/Users/zeek/source/e-ai-brain/.ai-brain-worktrees/"
                        "ai_executor_task_auto_commit"
                    ),
                },
            },
            "runner_id": runner["id"],
            "status": "succeeded",
        },
        headers={"X-Runner-Token": "runner-secret"},
    )
    assert completed.status_code == 200

    detail = client.get(f"/api/ai-tasks/{created['id']}", headers=headers).json()["data"]
    assert detail["input"]["executor"]["executor_policy_id"] == policy_response.json()["data"]["id"]
    assert detail["status"] == "completed"
    assert detail["current_step"] == "complete_archive"
    assert detail["pending_review"] is None
    assert detail["reviews"]["items"][0]["status"] == "approved"
    assert detail["reviews"]["items"][0]["decision_reason"] == "auto_commit_by_executor_policy"
    assert detail["knowledge_deposits"]["items"][0]["content"] == (
        "开发计划已生成并通过自动提交策略"
    )

    runner_status = client.get(
        f"/api/system/ai-executor-tasks/{runner_task_id}/runner-status?runner_id={runner['id']}",
        headers={"X-Runner-Token": "runner-secret"},
    ).json()["data"]["task"]
    assert runner_status["workspace_isolation"]["decision"]["action"] == "merge"
    assert runner_status["workspace_isolation"]["decision"]["decided_by"] == "system"
    assert runner_status["workspace_isolation"]["decision"]["status"] == "requested"


def test_task_detail_extracts_readable_executor_output_summary():
    headers = auth_headers()
    app.state.store.reset()
    task_id = "task_executor_preview_summary"
    output_preview = (
        "@@ -150,7 +202,7 @@\n"
        "- username: 'admin@example.com',\n"
        "+ username: TEST_LOGIN_USERNAME,\n"
        "\n"
        "tokens used\n"
        "169,685\n"
        "**整改状态：已修复**\n\n"
        "- Finding：`code_inspection_finding_176`\n"
        "- 修改文件：`apps/web/src/pages/Login/index.tsx`\n\n"
        "**验证方式**\n\n"
        "- `npm test -- AuthFlow.test.tsx`：通过\n"
    )
    app.state.store.ai_tasks[task_id] = {
        "brain_app_id": "rd_brain",
        "created_at": "2026-07-07T02:46:15+00:00",
        "created_by": "user_admin",
        "current_step": "executor_completed",
        "error_code": None,
        "error_message": None,
        "graph_run_ids": [],
        "id": task_id,
        "input_json": {},
        "module_code": None,
        "output_json": {
            "executor": {
                "executor_type": "codex",
                "runner_id": "ai_executor_runner_003",
                "runner_task_id": "ai_executor_task_057",
                "status": "succeeded",
                "workspace_root": "/Users/zeek/source/e-ai-brain",
            },
            "result": {
                "duration_ms": 516619,
                "exit_code": 0,
                "executor_type": "codex",
                "output_preview": output_preview,
                "workspace_root": "/Users/zeek/source/e-ai-brain",
            },
        },
        "product_context": {},
        "product_id": "product_119",
        "requirement_id": None,
        "requirement_snapshot": None,
        "review_ids": [],
        "status": "waiting_review",
        "task_type": "code_inspection_remediation",
        "title": "[Code Inspection Remediation] 硬编码敏感凭据",
        "updated_at": "2026-07-07T02:46:15+00:00",
        "version_id": None,
    }

    detail = client.get(f"/api/ai-tasks/{task_id}", headers=headers).json()["data"]

    assert detail["output_summary"].startswith("**整改状态：已修复**")
    assert "Finding" in detail["output_summary"]
    assert "验证方式" in detail["output_summary"]
    assert "@@ -150" not in detail["output_summary"]
    assert "tokens used" not in detail["output_summary"]
    assert detail["output"]["result"]["output_preview"].startswith("@@ -150")


def test_code_inspection_remediation_policy_instruction_carries_finding_context():
    headers = auth_headers()
    app.state.store.reset()
    runner = create_codex_runner(headers)

    policy_response = client.post(
        "/api/delivery/rd-task-executor-policies",
        json={
            "executor_type": "codex",
            "instruction_template": (
                "请基于研发任务 {{task_id}} / {{task_title}} 在当前仓库完成分析，并输出结构化结果。"
            ),
            "name": "代码整改走 Codex",
            "output_contract": {"details": "object", "summary": "string"},
            "priority": 10,
            "runner_id": runner["id"],
            "status": "active",
            "task_type": "code_inspection_remediation",
            "timeout_seconds": 600,
            "workspace_root": "/Users/zeek/source/e-ai-brain",
        },
        headers=headers,
    )
    assert policy_response.status_code == 200

    task_id = "task_code_inspection_context"
    app.state.store.ai_tasks[task_id] = {
        "brain_app_id": "rd_brain",
        "created_at": "2026-07-06T10:00:00+00:00",
        "created_by": "user_admin",
        "current_step": "draft",
        "error_code": None,
        "error_message": None,
        "graph_run_ids": [],
        "id": task_id,
        "input_json": {
            "branch": "master",
            "code_inspection_finding_id": "code_inspection_finding_173",
            "code_inspection_report_id": "code_inspection_report_063",
            "commit_sha": "60c192860f4bb77fe8cd5438b53d46707755e1de",
            "description": "生产就绪性测试文件中存在疑似硬编码敏感凭据。",
            "file_path": "apps/api/tests/test_production_readiness.py",
            "line_number": 147,
            "recommendation": "使用环境变量、密钥管理或测试专用假数据替代。",
            "repository": {
                "default_branch": "master",
                "id": "repo_102",
                "project_path": "zeek428/e-ai-brain",
                "remote_url": "https://github.com/zeek428/e-ai-brain.git",
            },
            "repository_id": "repo_102",
            "risk_level": "critical",
            "rule_id": "secrets.hardcoded_credential",
            "severity": "critical",
            "title": "硬编码敏感凭据",
        },
        "module_code": None,
        "output_json": None,
        "product_context": {
            "repository": {
                "default_branch": "master",
                "id": "repo_102",
                "project_path": "zeek428/e-ai-brain",
                "remote_url": "https://github.com/zeek428/e-ai-brain.git",
            },
            "source": "code_inspection",
        },
        "product_id": "product_119",
        "requirement_id": None,
        "requirement_snapshot": None,
        "review_ids": [],
        "status": "draft",
        "task_type": "code_inspection_remediation",
        "title": "[Code Inspection Remediation] 硬编码敏感凭据",
        "updated_at": "2026-07-06T10:00:00+00:00",
        "version_id": None,
    }

    started = client.post(f"/api/ai-tasks/{task_id}/start", headers=headers)
    assert started.status_code == 200
    runner_task_id = started.json()["data"]["executor_task_id"]

    claimed = client.post(
        "/api/system/ai-executor-tasks/claim",
        json={"executor_type": "codex", "runner_id": runner["id"]},
        headers={"X-Runner-Token": "runner-secret"},
    )
    assert claimed.status_code == 200
    claimed_task = claimed.json()["data"]["task"]
    assert claimed_task["id"] == runner_task_id

    instruction = claimed_task["instruction"]
    assert "apps/api/tests/test_production_readiness.py" in instruction
    assert "147" in instruction
    assert "secrets.hardcoded_credential" in instruction
    assert "使用环境变量、密钥管理或测试专用假数据替代" in instruction
    assert "不要进行仓库级安全扫描" in instruction
    assert "优先只处理本条 finding" in instruction
    assert claimed_task["input_payload"]["branch"] == "master"
    assert claimed_task["input_payload"]["code_inspection"]["file_path"] == (
        "apps/api/tests/test_production_readiness.py"
    )


def test_rd_task_executor_policy_rejects_agent_and_skill_fields():
    headers = auth_headers()
    app.state.store.reset()
    runner = create_codex_runner(headers)

    rejected = client.post(
        "/api/delivery/rd-task-executor-policies",
        json={
            "agent_id": "agent_001",
            "executor_type": "codex",
            "instruction_template": "不应允许 Agent 或 Skill 字段",
            "name": "错误策略",
            "runner_id": runner["id"],
            "skill_ids": ["skill_001"],
            "task_type": "development_planning",
            "workspace_root": "/Users/zeek/source/e-ai-brain",
        },
        headers=headers,
    )
    assert rejected.status_code == 422


def test_rd_task_executor_policy_create_update_delete_memory_fallback():
    headers = auth_headers()
    app.state.store.reset()
    runner = create_codex_runner(headers)

    created = client.post(
        "/api/delivery/rd-task-executor-policies",
        json={
            "executor_type": "codex",
            "instruction_template": "处理任务 {{task_id}}。",
            "name": "策略 fallback 验证",
            "output_contract": {"summary": "string"},
            "priority": 20,
            "runner_id": runner["id"],
            "status": "active",
            "task_type": "development_planning",
            "timeout_seconds": 600,
            "workspace_root": "/Users/zeek/source/e-ai-brain",
        },
        headers=headers,
    )
    assert created.status_code == 200
    policy = created.json()["data"]
    assert app.state.store.rd_task_executor_policies[policy["id"]]["name"] == (
        "策略 fallback 验证"
    )

    updated = client.patch(
        f"/api/delivery/rd-task-executor-policies/{policy['id']}",
        json={"name": "策略 fallback 已更新", "priority": 30, "status": "disabled"},
        headers=headers,
    )
    assert updated.status_code == 200
    assert app.state.store.rd_task_executor_policies[policy["id"]]["name"] == (
        "策略 fallback 已更新"
    )
    assert app.state.store.rd_task_executor_policies[policy["id"]]["priority"] == 30
    assert app.state.store.rd_task_executor_policies[policy["id"]]["status"] == "disabled"

    deleted = client.delete(
        f"/api/delivery/rd-task-executor-policies/{policy['id']}",
        headers=headers,
    )
    assert deleted.status_code == 200
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


def test_rd_task_executor_policy_rejects_model_gateway_executor():
    headers = auth_headers()
    app.state.store.reset()
    runner = create_codex_runner(headers)

    rejected = client.post(
        "/api/delivery/rd-task-executor-policies",
        json={
            "executor_type": "model_gateway",
            "instruction_template": "不应允许模型网关作为研发工程执行器",
            "name": "错误策略",
            "runner_id": runner["id"],
            "task_type": "development_planning",
            "workspace_root": "/Users/zeek/source/e-ai-brain",
        },
        headers=headers,
    )
    assert rejected.status_code == 400
    assert rejected.json()["detail"]["code"] == "VALIDATION_ERROR"
