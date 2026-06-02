from gitlab_fakes import install_real_github_api_stub
from test_gitlab_snapshot import auth_headers, build_confirmed_solution_context, client


def test_github_repository_preview_reads_real_github_api(monkeypatch):
    calls = install_real_github_api_stub(monkeypatch)
    headers = auth_headers()
    app = client.app
    app.state.store.reset()
    product = client.post(
        "/api/products",
        json={"code": "real-github-product", "name": "真实 GitHub 产品"},
        headers=headers,
    ).json()["data"]
    repository = client.post(
        f"/api/products/{product['id']}/git-repositories",
        json={
            "name": "AI Brain GitHub",
            "remote_url": "git@github.com:zeek428/e-ai-brain.git",
            "git_provider": "github",
            "project_path": "zeek428/e-ai-brain",
            "credential_ref": "ghp_direct_local_token",
        },
        headers=headers,
    ).json()["data"]

    preview = client.get(
        f"/api/devops/github/pull-requests/{repository['id']}/3/preview",
        headers=headers,
    ).json()["data"]

    assert preview["title"] == "真实 GitHub PR"
    assert preview["author"] == {"username": "zeek428", "name": "zeek428"}
    assert preview["source_branch"] == "feature/github-pr"
    assert preview["target_branch"] == "main"
    assert preview["base_sha"] == "github-base-sha"
    assert preview["head_sha"] == "github-head-sha"
    assert preview["changed_file_count"] == 2
    assert preview["changed_files_summary"] == [
        {"path": "apps/api/app/main.py", "additions": 4, "deletions": 1},
        {"path": "apps/web/src/pages/TaskCenter/index.tsx", "additions": 2, "deletions": 0},
    ]
    assert preview["writeback_allowed"] is False
    assert calls == [
        {
            "base_url": "https://api.github.com",
            "path": "/repos/zeek428/e-ai-brain/pulls/3",
            "token": "ghp_direct_local_token",
        },
        {
            "base_url": "https://api.github.com",
            "path": "/repos/zeek428/e-ai-brain/pulls/3/files?per_page=100",
            "token": "ghp_direct_local_token",
        },
    ]


def test_github_pull_request_list_reads_real_github_api(monkeypatch):
    calls = install_real_github_api_stub(monkeypatch)
    headers = auth_headers()
    app = client.app
    app.state.store.reset()
    product = client.post(
        "/api/products",
        json={"code": "real-github-pr-list-product", "name": "真实 GitHub PR 列表产品"},
        headers=headers,
    ).json()["data"]
    repository = client.post(
        f"/api/products/{product['id']}/git-repositories",
        json={
            "name": "AI Brain GitHub",
            "remote_url": "git@github.com:zeek428/e-ai-brain.git",
            "git_provider": "github",
            "project_path": "zeek428/e-ai-brain",
            "credential_ref": "ghp_direct_local_token",
        },
        headers=headers,
    ).json()["data"]

    response = client.get(
        f"/api/devops/github/pull-requests/{repository['id']}?state=all&limit=2",
        headers=headers,
    )

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["total"] == 1
    assert body["items"] == [
        {
            "author": {"name": "zeek428", "username": "zeek428"},
            "base_sha": "github-base-sha",
            "created_at": "2026-06-02T08:00:00Z",
            "head_sha": "github-head-sha",
            "number": 3,
            "project_path": "zeek428/e-ai-brain",
            "repository_id": repository["id"],
            "source_branch": "feature/github-pr",
            "state": "open",
            "target_branch": "main",
            "title": "真实 GitHub PR",
            "updated_at": "2026-06-02T09:00:00Z",
            "web_url": "https://github.com/zeek428/e-ai-brain/pull/3",
            "writeback_allowed": False,
        }
    ]
    assert calls == [
        {
            "base_url": "https://api.github.com",
            "path": "/repos/zeek428/e-ai-brain/pulls?state=all&per_page=2",
            "token": "ghp_direct_local_token",
        }
    ]


def test_github_pull_request_snapshot_can_create_code_review_task(monkeypatch):
    install_real_github_api_stub(monkeypatch)
    headers = auth_headers()
    context = build_confirmed_solution_context(
        headers,
        repository_payload={
            "name": "AI Brain GitHub",
            "remote_url": "git@github.com:zeek428/e-ai-brain.git",
            "git_provider": "github",
            "project_path": "zeek428/e-ai-brain",
            "credential_ref": "ghp_direct_local_token",
        },
    )

    snapshot = client.post(
        f"/api/devops/github/pull-requests/{context['repository_id']}/3/snapshot",
        json={
            "requirement_id": context["requirement_id"],
            "technical_solution_task_id": context["technical_solution_task_id"],
        },
        headers=headers,
    ).json()["data"]

    assert snapshot["id"].startswith("snapshot_")
    assert snapshot["mr_iid"] == 3
    assert snapshot["project_path"] == "zeek428/e-ai-brain"
    assert snapshot["writeback_allowed"] is False

    task_response = client.post(
        "/api/ai-tasks",
        json={
            "task_type": "code_review",
            "title": "Review GitHub PR #3",
            "requirement_id": context["requirement_id"],
            "input": {"gitlab_mr_snapshot_id": snapshot["id"]},
        },
        headers=headers,
    )

    assert task_response.status_code == 200
    assert task_response.json()["data"]["task_type"] == "code_review"
