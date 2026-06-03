import json

from fastapi.testclient import TestClient
from gitlab_fakes import install_real_gitlab_api_stub

from app.main import app, settings

client = TestClient(app)


def auth_headers() -> dict[str, str]:
    response = client.post(
        "/api/auth/login",
        json={"username": "admin@example.com", "password": "admin123"},
    )
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def build_mr_snapshot(headers: dict[str, str]) -> tuple[str, str]:
    app.state.store.reset()
    product = client.post(
        "/api/products",
        json={"code": "rd-platform", "name": "研发大脑平台"},
        headers=headers,
    ).json()["data"]
    version = client.post(
        f"/api/products/{product['id']}/versions",
        json={"code": "v1", "name": "v1 MVP"},
        headers=headers,
    ).json()["data"]
    repository = client.post(
        f"/api/products/{product['id']}/git-repositories",
        json={
            "name": "AI Brain API",
            "remote_url": "https://gitlab.example.com/platform/ai-brain.git",
            "git_provider": "gitlab",
            "project_path": "platform/ai-brain",
            "credential_ref": "env:GITLAB_READONLY_TOKEN",
        },
        headers=headers,
    ).json()["data"]
    requirement = client.post(
        "/api/requirements",
        json={
            "title": "内部 MR Code Review",
            "product_id": product["id"],
            "version_id": version["id"],
            "content": "需要基于 MR diff 生成内部代码 Review 报告。",
        },
        headers=headers,
    ).json()["data"]
    client.post(f"/api/requirements/{requirement['id']}/approve", json={}, headers=headers)
    design_task = client.post(
        f"/api/requirements/{requirement['id']}/generate-task",
        headers=headers,
    ).json()["data"]
    design_started = client.post(
        f"/api/ai-tasks/{design_task['task_id']}/start",
        headers=headers,
    ).json()["data"]
    client.post(
        f"/api/reviews/{design_started['review_id']}/approve",
        json={"version": 1},
        headers=headers,
    )
    solution_task = client.post(
        "/api/ai-tasks",
        json={
            "task_type": "technical_solution",
            "title": "技术方案：内部 MR Code Review",
            "requirement_id": requirement["id"],
            "input": {"product_detail_design_task_id": design_task["task_id"]},
        },
        headers=headers,
    ).json()["data"]
    solution_started = client.post(
        f"/api/ai-tasks/{solution_task['id']}/start",
        headers=headers,
    ).json()["data"]
    client.post(
        f"/api/reviews/{solution_started['review_id']}/approve",
        json={"version": 1},
        headers=headers,
    )
    snapshot = client.post(
        f"/api/devops/gitlab/merge-requests/{repository['id']}/42/snapshot",
        json={
            "requirement_id": requirement["id"],
            "technical_solution_task_id": solution_task["id"],
        },
        headers=headers,
    ).json()["data"]
    return requirement["id"], snapshot["id"]


def test_code_review_report_is_confirmed_and_archived_without_gitlab_writeback(monkeypatch):
    install_real_gitlab_api_stub(monkeypatch)
    headers = auth_headers()
    requirement_id, snapshot_id = build_mr_snapshot(headers)

    task = client.post(
        "/api/ai-tasks",
        json={
            "task_type": "code_review",
            "title": "Review MR !42",
            "requirement_id": requirement_id,
            "input": {"gitlab_mr_snapshot_id": snapshot_id},
        },
        headers=headers,
    ).json()["data"]
    assert task["status"] == "draft"

    started = client.post(f"/api/ai-tasks/{task['id']}/start", headers=headers).json()["data"]
    assert started["status"] == "waiting_review"

    pending_report = client.get(
        f"/api/ai-tasks/{task['id']}/code-review-report",
        headers=headers,
    ).json()["data"]
    assert pending_report["status"] == "pending_review"
    assert pending_report["risk_level"] == "medium"
    assert pending_report["findings"][0]["severity"] == "high"
    assert pending_report["gitlab_writeback_performed"] is False

    confirmed = client.post(
        f"/api/reviews/{started['review_id']}/approve",
        json={"version": 1},
        headers=headers,
    ).json()["data"]
    assert confirmed["task_status"] == "completed"

    archived = client.get(
        f"/api/ai-tasks/{task['id']}/code-review-report",
        headers=headers,
    ).json()["data"]
    assert archived["status"] == "confirmed"
    assert archived["archived_at"].startswith("20")
    assert archived["gitlab_writeback_performed"] is False

    audit_response = client.get(
        f"/api/audit/events?ai_task_id={task['id']}",
        headers=headers,
    )
    event_types = [event["event_type"] for event in audit_response.json()["data"]["items"]]
    assert event_types == [
        "review.submitted",
        "human_review.created",
        "code_review.generated",
        "ai_task.started",
        "code_review.executor_called",
        "model_gateway.called",
        "ai_task.created",
    ]


def test_code_review_task_uses_configured_executor_boundary(monkeypatch):
    install_real_gitlab_api_stub(monkeypatch)
    headers = auth_headers()
    requirement_id, snapshot_id = build_mr_snapshot(headers)

    task = client.post(
        "/api/ai-tasks",
        json={
            "task_type": "code_review",
            "title": "Review MR !42 via executor",
            "requirement_id": requirement_id,
            "input": {"gitlab_mr_snapshot_id": snapshot_id},
        },
        headers=headers,
    ).json()["data"]
    calls = []

    class FakeCodeReviewExecutor:
        executor_name = "code-review"
        executor_type = "claude_code_skill"

        def execute(self, *, current_store, task, payload):
            calls.append(
                {
                    "task_id": task["id"],
                    "snapshot_id": payload["gitlab_mr_snapshot"]["id"],
                }
            )
            return {
                "summary": "执行器边界生成的 Review 报告。",
                "risk_level": "low",
                "findings": [],
            }

    def fail_if_model_gateway_is_called(*_args, **_kwargs):
        raise AssertionError("code_review must use code_review_executor")

    monkeypatch.setattr(app.state, "code_review_executor", FakeCodeReviewExecutor(), raising=False)
    monkeypatch.setattr("app.main.urlopen", fail_if_model_gateway_is_called)

    started = client.post(f"/api/ai-tasks/{task['id']}/start", headers=headers).json()["data"]

    assert started["status"] == "waiting_review"
    assert calls == [{"task_id": task["id"], "snapshot_id": snapshot_id}]
    report = client.get(
        f"/api/ai-tasks/{task['id']}/code-review-report",
        headers=headers,
    ).json()["data"]
    assert report["summary"] == "执行器边界生成的 Review 报告。"
    assert report["executor"] == {
        "executor_name": "code-review",
        "executor_type": "claude_code_skill",
        "retryable": False,
    }

    audit_events = client.get(
        f"/api/audit/events?ai_task_id={task['id']}",
        headers=headers,
    ).json()["data"]["items"]
    assert "model_gateway.called" not in [event["event_type"] for event in audit_events]
    executor_event = next(
        event for event in audit_events if event["event_type"] == "code_review.executor_called"
    )
    assert executor_event["payload"] == {
        "executor_name": "code-review",
        "executor_type": "claude_code_skill",
        "retryable": False,
        "stage": "execute",
    }


def test_code_review_uses_model_gateway_when_external_executor_command_missing(monkeypatch):
    install_real_gitlab_api_stub(monkeypatch)
    headers = auth_headers()
    requirement_id, snapshot_id = build_mr_snapshot(headers)
    settings.code_review_executor_type = "claude_code_skill"
    settings.code_review_executor_name = "code-review"
    settings.code_review_executor_command = ""

    task = client.post(
        "/api/ai-tasks",
        json={
            "task_type": "code_review",
            "title": "Review MR !42 without external command",
            "requirement_id": requirement_id,
            "input": {"gitlab_mr_snapshot_id": snapshot_id},
        },
        headers=headers,
    ).json()["data"]

    started = client.post(f"/api/ai-tasks/{task['id']}/start", headers=headers).json()["data"]

    assert started["status"] == "waiting_review"
    report = client.get(
        f"/api/ai-tasks/{task['id']}/code-review-report",
        headers=headers,
    ).json()["data"]
    assert report["executor"] == {
        "executor_name": "code-review",
        "executor_type": "model_gateway",
        "retryable": False,
    }


def test_model_gateway_code_review_normalizes_common_review_shape(monkeypatch):
    install_real_gitlab_api_stub(monkeypatch)
    headers = auth_headers()
    requirement_id, snapshot_id = build_mr_snapshot(headers)
    settings.code_review_executor_type = "claude_code_skill"
    settings.code_review_executor_name = "code-review"
    settings.code_review_executor_command = ""
    captured_payload = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self) -> bytes:
            return json.dumps(
                {
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {
                                        "findings": [],
                                        "overall": "request_changes",
                                        "score": 64,
                                        "summary": "模型返回了常见 Review 结构。",
                                    },
                                    ensure_ascii=False,
                                )
                            }
                        }
                    ],
                    "usage": {"completion_tokens": 9, "prompt_tokens": 20, "total_tokens": 29},
                },
                ensure_ascii=False,
            ).encode("utf-8")

    def fake_urlopen(request, timeout):
        del timeout
        request_body = json.loads(request.data.decode("utf-8"))
        captured_payload.update(json.loads(request_body["messages"][1]["content"]))
        return FakeResponse()

    monkeypatch.setattr("app.main.urlopen", fake_urlopen)
    task = client.post(
        "/api/ai-tasks",
        json={
            "task_type": "code_review",
            "title": "Review MR !42 common model shape",
            "requirement_id": requirement_id,
            "input": {"gitlab_mr_snapshot_id": snapshot_id},
        },
        headers=headers,
    ).json()["data"]

    client.post(f"/api/ai-tasks/{task['id']}/start", headers=headers)

    report = client.get(
        f"/api/ai-tasks/{task['id']}/code-review-report",
        headers=headers,
    ).json()["data"]
    assert report["risk_level"] == "high"
    assert report["executor"] == {
        "executor_name": "code-review",
        "executor_type": "model_gateway",
        "retryable": False,
    }
    assert captured_payload["gitlab_mr_snapshot"]["id"] == snapshot_id
    assert captured_payload["technical_solution_task"]["task_type"] == "technical_solution"


def test_code_review_report_edit_approve_also_confirms_and_archives_report(monkeypatch):
    install_real_gitlab_api_stub(monkeypatch)
    headers = auth_headers()
    requirement_id, snapshot_id = build_mr_snapshot(headers)

    task = client.post(
        "/api/ai-tasks",
        json={
            "task_type": "code_review",
            "title": "Review MR !42 with edits",
            "requirement_id": requirement_id,
            "input": {"gitlab_mr_snapshot_id": snapshot_id},
        },
        headers=headers,
    ).json()["data"]
    started = client.post(f"/api/ai-tasks/{task['id']}/start", headers=headers).json()["data"]

    result = client.post(
        f"/api/reviews/{started['review_id']}/edit-approve",
        json={
            "version": 1,
            "edited_content": {
                "summary": "人工确认后保留一处高风险问题并补充边界测试建议。"
            },
        },
        headers=headers,
    ).json()["data"]

    assert result["task_status"] == "completed"
    archived = client.get(
        f"/api/ai-tasks/{task['id']}/code-review-report",
        headers=headers,
    ).json()["data"]
    assert archived["status"] == "confirmed"
    assert archived["archived_at"].startswith("20")
    assert archived["summary"] == "人工确认后保留一处高风险问题并补充边界测试建议。"
    assert archived["gitlab_writeback_performed"] is False


def test_code_review_executor_failure_uses_executor_error_code(monkeypatch):
    install_real_gitlab_api_stub(monkeypatch)
    headers = auth_headers()
    requirement_id, snapshot_id = build_mr_snapshot(headers)

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self) -> bytes:
            return json.dumps(
                {
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {"kind": "code_review", "summary": "缺少 executor 字段"},
                                    ensure_ascii=False,
                                )
                            }
                        }
                    ],
                    "usage": {"completion_tokens": 8, "prompt_tokens": 12, "total_tokens": 20},
                },
                ensure_ascii=False,
            ).encode("utf-8")

    def fake_urlopen(_request, timeout):
        return FakeResponse()

    monkeypatch.setattr("app.main.urlopen", fake_urlopen)
    client.post(
        "/api/system/model-gateway-configs",
        json={
            "api_key": "sk-code-review",
            "base_url": "https://llm.example.com/v1",
            "default_chat_model": "gpt-review",
            "default_embedding_model": "text-embedding-review",
            "is_default": True,
            "name": "Code Review 执行器",
            "provider": "openai_compatible",
            "status": "active",
        },
        headers=headers,
    )
    task = client.post(
        "/api/ai-tasks",
        json={
            "task_type": "code_review",
            "title": "Review MR !42 executor failure",
            "requirement_id": requirement_id,
            "input": {"gitlab_mr_snapshot_id": snapshot_id},
        },
        headers=headers,
    ).json()["data"]

    response = client.post(f"/api/ai-tasks/{task['id']}/start", headers=headers)

    assert response.status_code == 502
    assert response.json()["detail"]["code"] == "CODE_REVIEW_EXECUTOR_FAILED"
    detail = client.get(f"/api/ai-tasks/{task['id']}", headers=headers).json()["data"]
    assert detail["status"] == "failed"
    assert detail["current_step"] == "code_review_executor_failed"

    audit_events = client.get(
        f"/api/audit/events?ai_task_id={task['id']}",
        headers=headers,
    ).json()["data"]["items"]
    event_types = [event["event_type"] for event in audit_events]
    assert "code_review.executor_failed" in event_types
    assert "ai_task.failed" in event_types
