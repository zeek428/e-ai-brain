from test_database_persistence import FakeSnapshotRepository, app, auth_headers, client

from app.core.persistence import PersistentMemoryStore, PostgresRuntimeStore
from app.core.users import MemoryUserRepository


def test_insight_planning_routes_write_repository_without_request_persist():
    original_store = app.state.store
    original_users = app.state.user_repository
    repository = FakeSnapshotRepository()

    def use_empty_postgres_runtime_store() -> PostgresRuntimeStore:
        runtime_store = PostgresRuntimeStore(repository)
        app.state.store = runtime_store
        return runtime_store

    use_empty_postgres_runtime_store()
    app.state.user_repository = MemoryUserRepository.seeded()

    try:
        admin_headers = auth_headers()
        reviewer_headers = auth_headers("reviewer@example.com", "reviewer123")
        product = client.post(
            "/api/products",
            json={"code": "INSIGHT-DBFIRST", "name": "洞察 DB-first 产品"},
            headers=admin_headers,
        ).json()["data"]
        version = client.post(
            f"/api/products/{product['id']}/versions",
            json={"code": "2026Q3", "name": "2026 Q3", "status": "planning"},
            headers=admin_headers,
        ).json()["data"]
        module = client.post(
            f"/api/products/{product['id']}/modules",
            json={"code": "knowledge", "name": "知识中心"},
            headers=admin_headers,
        ).json()["data"]

        use_empty_postgres_runtime_store()
        usage = client.post(
            "/api/insights/usage-metrics",
            json={
                "active_users": 12,
                "event_count": 36,
                "feature_code": "semantic-search",
                "module_code": module["code"],
                "product_id": product["id"],
                "user_segment": "rd",
                "window_end": "2026-06-03T11:00:00Z",
                "window_start": "2026-06-03T10:00:00Z",
            },
            headers=admin_headers,
        ).json()["data"]

        use_empty_postgres_runtime_store()
        usage_items = client.get(
            f"/api/insights/usage-metrics?product_id={product['id']}&module_code={module['code']}",
            headers=admin_headers,
        ).json()["data"]["items"]
        assert usage_items[0]["id"] == usage["id"]

        feedback = client.post(
            "/api/insights/user-feedback",
            json={
                "content": "知识检索最近方案命中率偏低。",
                "feedback_type": "improvement",
                "module_code": module["code"],
                "product_id": product["id"],
                "satisfaction_score": 2,
                "sentiment": "negative",
            },
            headers=reviewer_headers,
        ).json()["data"]

        use_empty_postgres_runtime_store()
        patched_feedback = client.patch(
            f"/api/insights/user-feedback/{feedback['id']}",
            json={"status": "triaged", "triage_note": "进入迭代建议证据池。"},
            headers=admin_headers,
        ).json()["data"]
        assert patched_feedback["status"] == "triaged"

        use_empty_postgres_runtime_store()
        feedback_items = client.get(
            f"/api/insights/user-feedback?product_id={product['id']}&status=triaged",
            headers=admin_headers,
        ).json()["data"]["items"]
        assert feedback_items[0]["id"] == feedback["id"]

        bug = client.post(
            "/api/bugs",
            json={
                "description": "搜索排序偶发返回过期方案。",
                "module_code": module["code"],
                "product_id": product["id"],
                "severity": "major",
                "source": "manual_test",
                "title": "搜索排序返回过期方案",
                "version_id": version["id"],
            },
            headers=admin_headers,
        ).json()["data"]

        use_empty_postgres_runtime_store()
        generated = client.post(
            "/api/planning/iteration-suggestions",
            json={
                "module_codes": [module["code"]],
                "planning_cycle": "2026Q3",
                "product_id": product["id"],
                "version_id": version["id"],
            },
            headers=admin_headers,
        ).json()["data"]
        suggestion = generated["items"][0]
        assert [
            (evidence["subject_type"], evidence["subject_id"])
            for evidence in suggestion["evidence"]
        ] == [("user_feedback", feedback["id"]), ("bug", bug["id"])]

        use_empty_postgres_runtime_store()
        listed_suggestions = client.get(
            f"/api/planning/iteration-suggestions?product_id={product['id']}&status=suggested",
            headers=admin_headers,
        ).json()["data"]["items"]
        assert listed_suggestions[0]["id"] == suggestion["id"]

        decided = client.post(
            f"/api/planning/iteration-suggestions/{suggestion['id']}/decide",
            json={
                "comment": "采纳为真实需求。",
                "convert_to_requirement": True,
                "decision": "edited_accepted",
                "edited_scope": "先优化知识检索召回与排序。",
                "edited_title": "优化知识检索召回与排序",
            },
            headers=admin_headers,
        ).json()["data"]
        assert decided["status"] == "converted_to_requirement"

        use_empty_postgres_runtime_store()
        requirements = client.get(
            f"/api/requirements?product_id={product['id']}",
            headers=admin_headers,
        ).json()["data"]["items"]
        assert requirements[0]["id"] == decided["converted_requirement_id"]
        assert requirements[0]["title"] == "优化知识检索召回与排序"
        converted_suggestions = client.get(
            f"/api/planning/iteration-suggestions?product_id={product['id']}",
            headers=admin_headers,
        ).json()["data"]["items"]
        assert converted_suggestions[0]["converted_requirement_id"] == requirements[0]["id"]

        event_types = [
            event["event_type"] for event in repository.audit_events_payload["audit_events"]
        ]
        for event_type in [
            "usage_metric.created",
            "user_feedback.created",
            "user_feedback.updated",
            "iteration_suggestion.generated",
            "requirement.created",
            "iteration_suggestion.decided",
        ]:
            assert event_type in event_types
    finally:
        app.state.store = original_store
        app.state.user_repository = original_users


def test_user_feedback_update_and_conversion_read_repository_when_runtime_store_is_stale():
    original_store = app.state.store
    original_users = app.state.user_repository
    repository = FakeSnapshotRepository()
    repository.product_config_payload = {
        "product_git_repositories": {},
        "product_modules": {
            "module_repo_001": {
                "code": "assistant",
                "created_at": "2026-06-03T08:00:00+00:00",
                "description": "",
                "display_order": 1,
                "id": "module_repo_001",
                "name": "AI 助手",
                "owner_id": "user_admin",
                "product_id": "product_repo_001",
                "status": "active",
                "updated_at": "2026-06-03T08:00:00+00:00",
            }
        },
        "product_versions": {},
        "products": {
            "product_repo_001": {
                "code": "AIBRAIN-REPO",
                "created_at": "2026-06-03T08:00:00+00:00",
                "description": "",
                "display_order": 1,
                "id": "product_repo_001",
                "name": "AI Brain Repository Product",
                "owner_id": "user_admin",
                "status": "active",
                "updated_at": "2026-06-03T08:00:00+00:00",
            }
        },
        "related_systems": {},
    }
    repository.user_feedback_payload = {
        "user_feedback": {
            "feedback_repo_001": {
                "content": "希望 AI 助手草案能直接转需求。",
                "created_at": "2026-06-03T08:10:00+00:00",
                "created_by": "user_admin",
                "feedback_type": "improvement",
                "id": "feedback_repo_001",
                "module_code": "assistant",
                "product_id": "product_repo_001",
                "satisfaction_score": 3,
                "sentiment": "neutral",
                "source_channel": "manual",
                "status": "open",
                "tags": ["assistant"],
                "updated_at": "2026-06-03T08:10:00+00:00",
            }
        }
    }
    app.state.store = PostgresRuntimeStore(repository)
    app.state.user_repository = MemoryUserRepository.seeded()

    try:
        headers = auth_headers()
        patched = client.patch(
            "/api/insights/user-feedback/feedback_repo_001",
            json={"status": "triaged", "triage_note": "纳入需求池。"},
            headers=headers,
        ).json()["data"]
        assert patched["status"] == "triaged"
        assert patched["triage_note"] == "纳入需求池。"
        assert repository.user_feedback_payload["user_feedback"]["feedback_repo_001"][
            "status"
        ] == "triaged"

        app.state.store = PostgresRuntimeStore(repository)
        converted = client.post(
            "/api/insights/user-feedback/feedback_repo_001/convert-requirement",
            json={
                "priority": "P1",
                "title": "AI 助手草案转需求",
                "triage_note": "已经转入需求管理。",
            },
            headers=headers,
        ).json()["data"]
        requirement = converted["requirement"]
        feedback = converted["feedback"]
        assert requirement["source"] == "user_feedback"
        assert requirement["product_id"] == "product_repo_001"
        assert requirement["module_code"] == "assistant"
        assert feedback["status"] == "linked"
        assert feedback["related_requirement_id"] == requirement["id"]
        assert repository.requirements_payload["requirements"][requirement["id"]][
            "title"
        ] == "AI 助手草案转需求"
        assert repository.user_feedback_payload["user_feedback"]["feedback_repo_001"][
            "related_requirement_id"
        ] == requirement["id"]
    finally:
        app.state.store = original_store
        app.state.user_repository = original_users


def test_insight_planning_lists_use_repository_when_runtime_store_is_stale():
    original_store = app.state.store
    original_users = app.state.user_repository
    repository = FakeSnapshotRepository()
    repository.user_usage_metrics_payload = {
        "user_usage_metrics": {
            "usage_repo_001": {
                "active_users": 21,
                "created_at": "2026-06-03T08:00:00+00:00",
                "created_by": "user_admin",
                "error_count": 1,
                "event_count": 88,
                "feature_code": "chat",
                "id": "usage_repo_001",
                "module_code": "assistant",
                "product_id": "product_insight_repo",
                "updated_at": "2026-06-03T08:30:00+00:00",
                "user_segment": "rd",
                "window_end": "2026-06-03T08:30:00+00:00",
                "window_start": "2026-06-03T08:00:00+00:00",
            },
            "usage_repo_002": {
                "active_users": 9,
                "created_at": "2026-06-03T09:00:00+00:00",
                "created_by": "user_admin",
                "error_count": 0,
                "event_count": 22,
                "feature_code": "chat",
                "id": "usage_repo_002",
                "module_code": "assistant",
                "product_id": "product_other",
                "updated_at": "2026-06-03T09:30:00+00:00",
                "user_segment": "rd",
                "window_end": "2026-06-03T09:30:00+00:00",
                "window_start": "2026-06-03T09:00:00+00:00",
            },
        }
    }
    repository.user_feedback_payload = {
        "user_feedback": {
            "feedback_repo_001": {
                "content": "AI 助手需要保留上下文。",
                "created_at": "2026-06-03T08:10:00+00:00",
                "created_by": "user_admin",
                "feature_code": "chat",
                "feedback_type": "improvement",
                "id": "feedback_repo_001",
                "module_code": "assistant",
                "product_id": "product_insight_repo",
                "source_channel": "manual",
                "status": "triaged",
                "tags": ["assistant"],
                "updated_at": "2026-06-03T08:20:00+00:00",
            },
            "feedback_repo_002": {
                "content": "其他产品反馈。",
                "created_at": "2026-06-03T08:15:00+00:00",
                "created_by": "user_admin",
                "feedback_type": "bug",
                "id": "feedback_repo_002",
                "product_id": "product_other",
                "source_channel": "manual",
                "status": "open",
                "tags": [],
                "updated_at": "2026-06-03T08:15:00+00:00",
            },
        }
    }
    repository.iteration_planning_payload = {
        "iteration_plan_decisions": {},
        "iteration_plan_suggestions": {
            "suggestion_repo_001": {
                "business_value": "提升助手可用性。",
                "confidence_level": "medium",
                "created_at": "2026-06-03T08:40:00+00:00",
                "created_by": "user_admin",
                "dependencies": [],
                "estimated_effort": "medium",
                "evidence": [
                    {"subject_id": "feedback_repo_001", "subject_type": "user_feedback"}
                ],
                "evidence_insufficient": False,
                "id": "suggestion_repo_001",
                "module_codes": ["assistant"],
                "planning_cycle": "2026Q3",
                "priority": "P1",
                "priority_score": 81,
                "product_id": "product_insight_repo",
                "recommendation_reason": "真实反馈集中。",
                "risk_signals": ["user_feedback_signal"],
                "status": "suggested",
                "title": "优化 AI 助手上下文",
                "updated_at": "2026-06-03T08:45:00+00:00",
            },
            "suggestion_repo_002": {
                "business_value": "其他产品优化。",
                "confidence_level": "low",
                "created_at": "2026-06-03T08:35:00+00:00",
                "created_by": "user_admin",
                "dependencies": [],
                "estimated_effort": "small",
                "evidence": [],
                "evidence_insufficient": True,
                "id": "suggestion_repo_002",
                "module_codes": [],
                "planning_cycle": "2026Q3",
                "priority": "P2",
                "priority_score": 40,
                "product_id": "product_other",
                "recommendation_reason": "其他证据。",
                "risk_signals": [],
                "status": "suggested",
                "title": "其他迭代建议",
                "updated_at": "2026-06-03T08:35:00+00:00",
            },
        },
    }
    stale_store = PersistentMemoryStore.from_repository(repository)
    stale_store.user_usage_metrics = {}
    stale_store.user_feedback = {}
    stale_store.iteration_plan_suggestions = {}
    app.state.store = stale_store
    app.state.user_repository = MemoryUserRepository.seeded()

    try:
        headers = auth_headers()
        usage = client.get(
            "/api/insights/usage-metrics?product_id=product_insight_repo"
            "&module_code=assistant&feature_code=chat&user_segment=rd"
            "&from=2026-06-03T08:00:00Z&to=2026-06-03T08:30:00Z",
            headers=headers,
        ).json()["data"]["items"]
        assert [item["id"] for item in usage] == ["usage_repo_001"]

        feedback = client.get(
            "/api/insights/user-feedback?product_id=product_insight_repo"
            "&module_code=assistant&feature_code=chat&status=triaged"
            "&created_by=user_admin",
            headers=headers,
        ).json()["data"]["items"]
        assert [item["id"] for item in feedback] == ["feedback_repo_001"]

        suggestions = client.get(
            "/api/planning/iteration-suggestions?product_id=product_insight_repo"
            "&planning_cycle=2026Q3&status=suggested",
            headers=headers,
        ).json()["data"]["items"]
        assert [item["id"] for item in suggestions] == ["suggestion_repo_001"]
        assert suggestions[0]["evidence"][0]["subject_id"] == "feedback_repo_001"
    finally:
        app.state.store = original_store
        app.state.user_repository = original_users
