from urllib.error import HTTPError

from fastapi.testclient import TestClient
from gitlab_fakes import install_real_gitlab_api_stub

from app.main import app

client = TestClient(app)


def auth_headers() -> dict[str, str]:
    response = client.post(
        "/api/auth/login",
        json={"username": "admin@example.com", "password": "admin123"},
    )
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_gitlab_mr_preview_reads_real_gitlab_api_when_remote_url_is_configured(monkeypatch):
    calls = install_real_gitlab_api_stub(monkeypatch)
    headers = auth_headers()
    app.state.store.reset()
    product = client.post(
        "/api/products",
        json={"code": "real-gitlab-product", "name": "真实 GitLab 产品"},
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

    preview = client.get(
        f"/api/devops/gitlab/merge-requests/{repository['id']}/7/preview",
        headers=headers,
    ).json()["data"]

    assert preview["title"] == "真实 GitLab MR"
    assert preview["author"] == {"username": "alice", "name": "Alice"}
    assert preview["source_branch"] == "feature/real-gitlab"
    assert preview["target_branch"] == "main"
    assert preview["base_sha"] == "real-base-sha"
    assert preview["head_sha"] == "real-head-sha"
    assert preview["changed_file_count"] == 2
    assert preview["changed_files_summary"] == [
        {"path": "apps/api/app/main.py", "additions": 1, "deletions": 1},
        {"path": "apps/web/src/App.tsx", "additions": 2, "deletions": 0},
    ]
    assert preview["writeback_allowed"] is False
    assert calls == [
        {
            "base_url": "https://gitlab.example.com",
            "path": "/api/v4/projects/platform%2Fai-brain/merge_requests/7",
            "token": "readonly-token",
        },
        {
            "base_url": "https://gitlab.example.com",
            "path": "/api/v4/projects/platform%2Fai-brain/merge_requests/7/changes",
            "token": "readonly-token",
        },
    ]


def test_gitlab_mr_preview_requires_configured_gitlab_base_url(monkeypatch):
    monkeypatch.delenv("GITLAB_BASE_URL", raising=False)
    monkeypatch.delenv("GITLAB_READONLY_TOKEN", raising=False)
    headers = auth_headers()
    app.state.store.reset()
    product = client.post(
        "/api/products",
        json={"code": "missing-gitlab-base", "name": "缺失 GitLab 地址产品"},
        headers=headers,
    ).json()["data"]
    repository = client.post(
        f"/api/products/{product['id']}/git-repositories",
        json={
            "name": "AI Brain API",
            "git_provider": "gitlab",
            "project_path": "platform/ai-brain",
            "credential_ref": "env:GITLAB_READONLY_TOKEN",
        },
        headers=headers,
    ).json()["data"]

    response = client.get(
        f"/api/devops/gitlab/merge-requests/{repository['id']}/7/preview",
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "GITLAB_CONFIG_INVALID"


def test_gitlab_mr_preview_maps_gitlab_404_to_documented_error(monkeypatch):
    monkeypatch.setenv("GITLAB_READONLY_TOKEN", "readonly-token")
    headers = auth_headers()
    app.state.store.reset()
    product = client.post(
        "/api/products",
        json={"code": "missing-mr-product", "name": "缺失 MR 产品"},
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

    def missing_gitlab_mr(_request, timeout=10):
        raise HTTPError(
            "https://gitlab.example.com/api/v4/projects/platform%2Fai-brain/merge_requests/404",
            404,
            "Not Found",
            {},
            None,
        )

    monkeypatch.setattr("app.main.urlopen", missing_gitlab_mr)

    response = client.get(
        f"/api/devops/gitlab/merge-requests/{repository['id']}/404/preview",
        headers=headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "GITLAB_MR_NOT_FOUND"


def build_confirmed_solution_context(headers: dict[str, str]) -> dict[str, str]:
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
            "title": "Review MR 输入快照",
            "product_id": product["id"],
            "version_id": version["id"],
            "content": "需要在代码 Review 前保存 GitLab MR diff 快照。",
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
            "title": "技术方案：Review MR 输入快照",
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
    return {
        "product_detail_design_task_id": design_task["task_id"],
        "product_id": product["id"],
        "repository_id": repository["id"],
        "requirement_id": requirement["id"],
        "technical_solution_task_id": solution_task["id"],
        "version_id": version["id"],
    }


def test_gitlab_mr_preview_and_snapshot_are_read_only_and_immutable(monkeypatch):
    install_real_gitlab_api_stub(monkeypatch)
    headers = auth_headers()
    context = build_confirmed_solution_context(headers)

    preview = client.get(
        f"/api/devops/gitlab/merge-requests/{context['repository_id']}/42/preview",
        headers=headers,
    ).json()["data"]
    assert preview["mr_iid"] == 42
    assert preview["project_path"] == "platform/ai-brain"
    assert preview["writeback_allowed"] is False
    assert preview["changed_file_count"] == 2

    snapshot = client.post(
        f"/api/devops/gitlab/merge-requests/{context['repository_id']}/42/snapshot",
        json={
            "requirement_id": context["requirement_id"],
            "technical_solution_task_id": context["technical_solution_task_id"],
        },
        headers=headers,
    ).json()["data"]
    assert snapshot["id"].startswith("snapshot_")
    assert snapshot["mr_iid"] == 42
    assert snapshot["diff_size_bytes"] > 0
    assert snapshot["diff_limit_bytes"] >= snapshot["diff_size_bytes"]
    assert snapshot["snapshot_hash"]
    assert snapshot["writeback_allowed"] is False

    audit_events = client.get(
        f"/api/audit/events?subject_type=gitlab_mr_snapshot&subject_id={snapshot['id']}",
        headers=headers,
    ).json()["data"]["items"]
    assert [event["event_type"] for event in audit_events] == ["gitlab_mr.snapshotted"]


def test_gitlab_mr_snapshot_reuses_existing_snapshot_for_same_diff(monkeypatch):
    install_real_gitlab_api_stub(monkeypatch)
    headers = auth_headers()
    context = build_confirmed_solution_context(headers)

    first = client.post(
        f"/api/devops/gitlab/merge-requests/{context['repository_id']}/42/snapshot",
        json={
            "requirement_id": context["requirement_id"],
            "technical_solution_task_id": context["technical_solution_task_id"],
        },
        headers=headers,
    ).json()["data"]
    second = client.post(
        f"/api/devops/gitlab/merge-requests/{context['repository_id']}/42/snapshot",
        json={
            "requirement_id": context["requirement_id"],
            "technical_solution_task_id": context["technical_solution_task_id"],
        },
        headers=headers,
    ).json()["data"]

    assert second["id"] == first["id"]
    assert second["snapshot_hash"] == first["snapshot_hash"]
    assert list(app.state.store.gitlab_mr_snapshots) == [first["id"]]

    audit_events = client.get(
        f"/api/audit/events?subject_type=gitlab_mr_snapshot&subject_id={first['id']}",
        headers=headers,
    ).json()["data"]["items"]
    assert [event["event_type"] for event in audit_events] == [
        "gitlab_mr.snapshot_reused",
        "gitlab_mr.snapshotted",
    ]


def test_gitlab_snapshot_records_audit_when_diff_exceeds_limit(monkeypatch):
    headers = auth_headers()
    context = build_confirmed_solution_context(headers)

    def oversized_preview(repository: dict, mr_iid: int) -> dict:
        return {
            "author": {"username": "alice", "name": "Alice"},
            "base_sha": "base-large",
            "changed_file_count": 1,
            "changed_files_summary": [
                {
                    "additions": 1,
                    "deletions": 0,
                    "path": f"apps/api/{'large-path-' * 25_000}.py",
                }
            ],
            "diff_refs": {"base_sha": "base-large", "head_sha": "head-large"},
            "head_sha": "head-large",
            "mr_iid": mr_iid,
            "project_id": repository.get("project_id"),
            "project_path": repository["project_path"],
            "repository_id": repository["id"],
            "source_branch": "feature/large-diff",
            "target_branch": "main",
            "title": "超大 MR",
            "web_url": "https://gitlab.example.com/platform/ai-brain/-/merge_requests/99",
            "writeback_allowed": False,
        }

    monkeypatch.setattr("app.main._gitlab_preview", oversized_preview)

    response = client.post(
        f"/api/devops/gitlab/merge-requests/{context['repository_id']}/99/snapshot",
        json={
            "requirement_id": context["requirement_id"],
            "technical_solution_task_id": context["technical_solution_task_id"],
        },
        headers=headers,
    )

    assert response.status_code == 413
    assert response.json()["detail"]["code"] == "GITLAB_MR_DIFF_TOO_LARGE"
    assert app.state.store.gitlab_mr_snapshots == {}

    audit_events = client.get(
        "/api/audit/events?event_type=gitlab_mr.snapshot_failed",
        headers=headers,
    ).json()["data"]["items"]
    assert len(audit_events) == 1
    failure_event = audit_events[0]
    assert failure_event["subject_type"] == "product_git_repository"
    assert failure_event["subject_id"] == context["repository_id"]
    assert failure_event["payload"]["reason"] == "diff_too_large"
    assert failure_event["payload"]["mr_iid"] == 99
    assert failure_event["payload"]["diff_limit_bytes"] == 204_800
    assert failure_event["payload"]["diff_size_bytes"] > 204_800


def test_gitlab_snapshot_rejects_changed_file_count_over_limit(monkeypatch):
    headers = auth_headers()
    context = build_confirmed_solution_context(headers)

    def too_many_files_preview(repository: dict, mr_iid: int) -> dict:
        return {
            "author": {"username": "alice", "name": "Alice"},
            "base_sha": "base-many-files",
            "changed_file_count": 51,
            "changed_files_summary": [
                {"additions": 1, "deletions": 0, "path": f"apps/api/file_{index}.py"}
                for index in range(51)
            ],
            "diff_refs": {"base_sha": "base-many-files", "head_sha": "head-many-files"},
            "head_sha": "head-many-files",
            "mr_iid": mr_iid,
            "project_id": repository.get("project_id"),
            "project_path": repository["project_path"],
            "repository_id": repository["id"],
            "source_branch": "feature/many-files",
            "target_branch": "main",
            "title": "过多文件 MR",
            "web_url": "https://gitlab.example.com/platform/ai-brain/-/merge_requests/100",
            "writeback_allowed": False,
        }

    monkeypatch.setattr("app.main._gitlab_preview", too_many_files_preview)

    response = client.post(
        f"/api/devops/gitlab/merge-requests/{context['repository_id']}/100/snapshot",
        json={
            "requirement_id": context["requirement_id"],
            "technical_solution_task_id": context["technical_solution_task_id"],
        },
        headers=headers,
    )

    assert response.status_code == 413
    assert response.json()["detail"]["code"] == "GITLAB_MR_DIFF_TOO_LARGE"
    assert app.state.store.gitlab_mr_snapshots == {}

    audit_events = client.get(
        "/api/audit/events?event_type=gitlab_mr.snapshot_failed",
        headers=headers,
    ).json()["data"]["items"]
    assert len(audit_events) == 1
    failure_event = audit_events[0]
    assert failure_event["payload"]["reason"] == "changed_file_count_too_large"
    assert failure_event["payload"]["changed_file_count"] == 51
    assert failure_event["payload"]["changed_file_limit"] == 50
    assert failure_event["payload"]["diff_size_bytes"] <= 204_800


def test_gitlab_snapshot_rejects_single_file_diff_over_limit(monkeypatch):
    headers = auth_headers()
    context = build_confirmed_solution_context(headers)

    def oversized_file_preview(repository: dict, mr_iid: int) -> dict:
        return {
            "author": {"username": "alice", "name": "Alice"},
            "base_sha": "base-large-file",
            "changed_file_count": 1,
            "changed_files_summary": [
                {
                    "additions": 1_501,
                    "deletions": 500,
                    "path": "apps/api/app/main.py",
                }
            ],
            "diff_refs": {"base_sha": "base-large-file", "head_sha": "head-large-file"},
            "head_sha": "head-large-file",
            "mr_iid": mr_iid,
            "project_id": repository.get("project_id"),
            "project_path": repository["project_path"],
            "repository_id": repository["id"],
            "source_branch": "feature/large-file",
            "target_branch": "main",
            "title": "单文件过大 MR",
            "web_url": "https://gitlab.example.com/platform/ai-brain/-/merge_requests/101",
            "writeback_allowed": False,
        }

    monkeypatch.setattr("app.main._gitlab_preview", oversized_file_preview)

    response = client.post(
        f"/api/devops/gitlab/merge-requests/{context['repository_id']}/101/snapshot",
        json={
            "requirement_id": context["requirement_id"],
            "technical_solution_task_id": context["technical_solution_task_id"],
        },
        headers=headers,
    )

    assert response.status_code == 413
    assert response.json()["detail"]["code"] == "GITLAB_MR_DIFF_TOO_LARGE"
    assert app.state.store.gitlab_mr_snapshots == {}

    audit_events = client.get(
        "/api/audit/events?event_type=gitlab_mr.snapshot_failed",
        headers=headers,
    ).json()["data"]["items"]
    assert len(audit_events) == 1
    failure_event = audit_events[0]
    assert failure_event["payload"]["reason"] == "single_file_diff_too_large"
    assert failure_event["payload"]["file_path"] == "apps/api/app/main.py"
    assert failure_event["payload"]["file_diff_line_count"] == 2_001
    assert failure_event["payload"]["file_diff_line_limit"] == 2_000
    assert failure_event["payload"]["diff_size_bytes"] <= 204_800


def test_gitlab_snapshot_rejects_cross_product_requirement_context():
    headers = auth_headers()
    context = build_confirmed_solution_context(headers)
    other_product = client.post(
        "/api/products",
        json={"code": "other-product", "name": "其他产品"},
        headers=headers,
    ).json()["data"]
    other_version = client.post(
        f"/api/products/{other_product['id']}/versions",
        json={"code": "v1", "name": "v1"},
        headers=headers,
    ).json()["data"]
    other_requirement = client.post(
        "/api/requirements",
        json={
            "title": "不应复用其他产品 MR 快照",
            "product_id": other_product["id"],
            "version_id": other_version["id"],
            "content": "跨产品上下文不能进入同一份 GitLab MR 快照。",
        },
        headers=headers,
    ).json()["data"]

    response = client.post(
        f"/api/devops/gitlab/merge-requests/{context['repository_id']}/42/snapshot",
        json={
            "requirement_id": other_requirement["id"],
            "technical_solution_task_id": context["technical_solution_task_id"],
        },
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "GITLAB_CONTEXT_MISMATCH"


def test_technical_solution_task_rejects_design_from_another_requirement():
    headers = auth_headers()
    context = build_confirmed_solution_context(headers)
    unrelated_requirement = client.post(
        "/api/requirements",
        json={
            "title": "同产品内另一条需求",
            "product_id": context["product_id"],
            "version_id": context["version_id"],
            "content": "技术方案不能复用另一条需求的产品详细设计。",
        },
        headers=headers,
    ).json()["data"]

    response = client.post(
        "/api/ai-tasks",
        json={
            "task_type": "technical_solution",
            "title": "错配上下文技术方案",
            "requirement_id": unrelated_requirement["id"],
            "input": {
                "product_detail_design_task_id": context["product_detail_design_task_id"],
            },
        },
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "TASK_CONTEXT_MISMATCH"


def test_code_review_task_rejects_requirement_that_does_not_match_snapshot(monkeypatch):
    install_real_gitlab_api_stub(monkeypatch)
    headers = auth_headers()
    context = build_confirmed_solution_context(headers)
    snapshot = client.post(
        f"/api/devops/gitlab/merge-requests/{context['repository_id']}/42/snapshot",
        json={
            "requirement_id": context["requirement_id"],
            "technical_solution_task_id": context["technical_solution_task_id"],
        },
        headers=headers,
    ).json()["data"]
    unrelated_requirement = client.post(
        "/api/requirements",
        json={
            "title": "同产品的另一条需求",
            "product_id": context["product_id"],
            "version_id": context["version_id"],
            "content": "同一产品内也不能错配快照来源需求。",
        },
        headers=headers,
    ).json()["data"]

    response = client.post(
        "/api/ai-tasks",
        json={
            "task_type": "code_review",
            "title": "Review MR !42",
            "requirement_id": unrelated_requirement["id"],
            "input": {"gitlab_mr_snapshot_id": snapshot["id"]},
        },
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "GITLAB_CONTEXT_MISMATCH"
