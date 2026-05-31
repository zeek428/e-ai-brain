from app import main as main_module


def install_real_gitlab_api_stub(monkeypatch):
    monkeypatch.setenv("GITLAB_READONLY_TOKEN", "readonly-token")
    calls: list[dict[str, str]] = []
    mr_path_prefix = "/api/v4/projects/platform%2Fai-brain/merge_requests/"

    def fake_gitlab_request_json(base_url: str, token: str, path: str) -> dict:
        calls.append({"base_url": base_url, "path": path, "token": token})
        if path.startswith(mr_path_prefix) and not path.endswith("/changes"):
            mr_iid = int(path.rsplit("/", 1)[1])
            return {
                "iid": mr_iid,
                "title": "真实 GitLab MR",
                "author": {"username": "alice", "name": "Alice"},
                "source_branch": "feature/real-gitlab",
                "target_branch": "main",
                "web_url": f"https://gitlab.example.com/platform/ai-brain/-/merge_requests/{mr_iid}",
                "diff_refs": {
                    "base_sha": "real-base-sha",
                    "head_sha": "real-head-sha",
                    "start_sha": "real-start-sha",
                },
            }
        if path.startswith(mr_path_prefix) and path.endswith("/changes"):
            return {
                "changes": [
                    {
                        "old_path": "apps/api/app/main.py",
                        "new_path": "apps/api/app/main.py",
                        "diff": "@@ -1,2 +1,2 @@\n-old line\n+new line\n context\n",
                    },
                    {
                        "old_path": "apps/web/src/App.tsx",
                        "new_path": "apps/web/src/App.tsx",
                        "diff": "@@ -1,0 +1,2 @@\n+first\n+second\n",
                    },
                ],
            }
        raise AssertionError(f"Unexpected GitLab API path: {path}")

    monkeypatch.setattr(main_module, "_gitlab_request_json", fake_gitlab_request_json)
    return calls
