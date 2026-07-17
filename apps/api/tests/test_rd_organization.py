from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.repositories.rd_collaboration_work_writes import RdCollaborationWorkWriteMixin
from app.main import app
from app.services.rd_ai_employees import qualify_ai_actor, validate_ai_actor_selector
from app.services.rd_role_definitions import qualify_human_actor, validate_human_actor_selector

client = TestClient(app)


def auth_headers(username: str = "admin@example.com", password: str = "admin123") -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def role_payload(**overrides: object) -> dict[str, object]:
    suffix = uuid4().hex[:8]
    return {
        "code": f"developer-{suffix}",
        "name": "开发工程师",
        "capabilities": ["implementation", "review"],
        "responsibilities": ["implement"],
        "maximum_risk_level": "high",
        "assignable_subject_types": ["human_user", "ai_employee"],
        **overrides,
    }


def ai_employee_payload(**overrides: object) -> dict[str, object]:
    suffix = uuid4().hex[:8]
    return {
        "code": f"developer-ai-{suffix}",
        "name": "开发数字员工",
        "capability_tags": ["python", "review"],
        "persona_version": 2,
        "persona_json": {"tone": "precise"},
        "work_style_version": 3,
        "work_style_json": {"collaboration": "async"},
        **overrides,
    }


def executor_profile_payload(**overrides: object) -> dict[str, object]:
    suffix = uuid4().hex[:8]
    return {
        "code": f"codex-profile-{suffix}",
        "name": "Codex 执行档案",
        "executor_type": "codex",
        "workspace_capabilities": {"filesystem": "workspace"},
        "max_concurrency": 2,
        "supported_role_codes": ["developer"],
        "health_status": "healthy",
        **overrides,
    }


def test_creating_rd_role_does_not_grant_system_permission():
    app.state.store.reset()
    admin_headers = auth_headers()

    response = client.post(
        "/api/delivery/rd-roles",
        headers=admin_headers,
        json=role_payload(),
    )

    assert response.status_code == 200
    role = response.json()["data"]
    assert role["system_role_id"] is None
    assert "granted_permissions" not in role
    assert "permissions" not in role


def test_rd_organization_catalog_requires_its_own_manage_permission():
    app.state.store.reset()
    admin_headers = auth_headers()
    username = f"rd-org-viewer-{uuid4().hex[:8]}@example.com"
    user = client.post(
        "/api/users",
        headers=admin_headers,
        json={
            "display_name": "R&D Organization Viewer",
            "password": "viewer123",
            "roles": ["viewer"],
            "username": username,
        },
    ).json()["data"]
    try:
        response = client.post(
            "/api/delivery/rd-ai-employees",
            headers=auth_headers(username, "viewer123"),
            json=ai_employee_payload(),
        )
        assert response.status_code == 403
        assert response.json()["detail"]["code"] == "FORBIDDEN"
    finally:
        client.delete(f"/api/users/{user['id']}", headers=admin_headers)


def test_rd_organization_catalog_rejects_an_unknown_brain_scope():
    app.state.store.reset()
    response = client.post(
        "/api/delivery/rd-roles",
        headers=auth_headers(),
        json=role_payload(brain_app_id="unknown-brain"),
    )

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "RD_BRAIN_APP_NOT_FOUND"


def test_ai_employee_is_a_stable_identity_without_secret_or_permission_fields():
    app.state.store.reset()
    response = client.post(
        "/api/delivery/rd-ai-employees",
        headers=auth_headers(),
        json=ai_employee_payload(),
    )

    assert response.status_code == 200
    employee = response.json()["data"]
    assert employee["persona_version"] == 2
    assert employee["work_style_version"] == 3
    assert "credential_ref" not in employee
    assert "permissions" not in employee
    assert "granted_permissions" not in employee


def test_executor_profile_rejects_credential_references_and_does_not_return_them():
    app.state.store.reset()
    response = client.post(
        "/api/delivery/rd-executor-profiles",
        headers=auth_headers(),
        json=executor_profile_payload(credential_ref="secret://rd-codex-token"),
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "RD_EXECUTOR_PROFILE_SECRET_FORBIDDEN"


def test_role_and_executor_profile_crud_keep_catalogs_separate_from_credentials():
    app.state.store.reset()
    headers = auth_headers()
    role = client.post(
        "/api/delivery/rd-roles",
        headers=headers,
        json=role_payload(),
    )
    assert role.status_code == 200
    role_id = role.json()["data"]["id"]
    disabled_role = client.patch(
        f"/api/delivery/rd-roles/{role_id}",
        headers=headers,
        json={"status": "disabled"},
    )
    assert disabled_role.status_code == 200
    assert disabled_role.json()["data"]["status"] == "disabled"
    assert (
        client.get("/api/delivery/rd-roles?status=disabled", headers=headers).json()["data"][
            "items"
        ][0]["id"]
        == role_id
    )

    profile = client.post(
        "/api/delivery/rd-executor-profiles",
        headers=headers,
        json=executor_profile_payload(),
    )
    assert profile.status_code == 200
    profile_id = profile.json()["data"]["id"]
    assert "credential_ref" not in profile.json()["data"]
    disabled_profile = client.patch(
        f"/api/delivery/rd-executor-profiles/{profile_id}",
        headers=headers,
        json={"status": "disabled"},
    )
    assert disabled_profile.status_code == 200
    assert disabled_profile.json()["data"]["status"] == "disabled"
    assert (
        client.get("/api/delivery/rd-executor-profiles?status=disabled", headers=headers).json()[
            "data"
        ]["items"][0]["id"]
        == profile_id
    )


def test_rd_organization_catalogs_support_list_and_patch_without_cross_identity_fields():
    app.state.store.reset()
    headers = auth_headers()
    employee = client.post(
        "/api/delivery/rd-ai-employees",
        headers=headers,
        json=ai_employee_payload(),
    )
    assert employee.status_code == 200
    employee_id = employee.json()["data"]["id"]

    patched = client.patch(
        f"/api/delivery/rd-ai-employees/{employee_id}",
        headers=headers,
        json={"status": "disabled", "persona_version": 4},
    )
    assert patched.status_code == 200
    assert patched.json()["data"]["status"] == "disabled"
    assert patched.json()["data"]["persona_version"] == 4

    listed = client.get("/api/delivery/rd-ai-employees?status=disabled", headers=headers)
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()["data"]["items"]] == [employee_id]


def test_human_qualification_requires_collaboration_permission_and_product_scope():
    role = {
        "brain_app_id": "rd_brain",
        "code": "developer",
        "assignable_subject_types": ["human_user"],
        "status": "active",
    }
    user = {
        "id": "user-developer",
        "permissions": ["delivery.rd_collaboration.work"],
        "scope_summary": [
            {"access_level": "write", "scope_id": "product-a", "scope_type": "product"}
        ],
    }

    assert qualify_human_actor(user, role_definition=role, product_id="product-a")
    assert not qualify_human_actor(user, role_definition=role, product_id="product-b")
    assert not qualify_human_actor(
        {**user, "permissions": []}, role_definition=role, product_id="product-a"
    )


def test_system_administrator_qualifies_for_a_scoped_human_collaboration_role():
    role = {
        "brain_app_id": "rd_brain",
        "code": "developer",
        "assignable_subject_types": ["human_user"],
        "status": "active",
    }
    administrator = {"id": "admin", "permissions": ["system.admin"], "scope_summary": []}

    assert qualify_human_actor(
        administrator,
        role_definition=role,
        product_id="product-a",
    )


def test_p0_actor_selectors_reject_implicit_team_and_role_membership():
    from fastapi import HTTPException

    for selector, validator, code in (
        ({"team_id": "implicit-team"}, validate_human_actor_selector, "RD_HUMAN_SELECTOR_INVALID"),
        ({"role_codes": ["developer"]}, validate_ai_actor_selector, "RD_AI_SELECTOR_INVALID"),
    ):
        try:
            validator(selector)
        except HTTPException as exc:
            assert exc.status_code == 400
            assert exc.detail["code"] == code
        else:
            raise AssertionError("implicit actor selector was accepted")


def test_ai_employee_identity_and_executor_profile_are_qualified_separately():
    role = {
        "brain_app_id": "rd_brain",
        "code": "developer",
        "assignable_subject_types": ["ai_employee"],
        "status": "active",
    }
    profile = {
        "id": "executor-shared",
        "brain_app_id": "rd_brain",
        "status": "active",
        "health_status": "healthy",
        "supported_role_codes": ["developer"],
    }
    employee_a = {"id": "dev-a", "brain_app_id": "rd_brain", "status": "active"}
    employee_b = {"id": "dev-b", "brain_app_id": "rd_brain", "status": "active"}

    for employee in (employee_a, employee_b):
        assert qualify_ai_actor(
            employee,
            profile,
            role_definition=role,
            policy_binding={
                "status": "active",
                "actor_mode": "ai",
                "candidate_ai_employee_ids": [employee["id"]],
                "primary_executor_profile_id": "executor-shared",
            },
        )
    assert employee_a["id"] != employee_b["id"]
    assert profile["id"] == "executor-shared"
    assert not qualify_ai_actor(
        employee_a,
        profile,
        role_definition=role,
        policy_binding={
            "status": "active",
            "actor_mode": "ai",
            "candidate_ai_employee_ids": [employee_a["id"]],
            "primary_executor_profile_id": "different-executor",
        },
    )


def test_frozen_decision_answer_selector_and_human_scope_cannot_be_bypassed():
    assert not RdCollaborationWorkWriteMixin._selector_matches(
        {"user_ids": ["selected-user"]},
        actor_id="other-user",
        actor_role_codes=["rd_owner"],
        actor_seat_ids=["seat-other"],
    )
    assert RdCollaborationWorkWriteMixin._selector_matches(
        {"user_ids": ["selected-user"]},
        actor_id="selected-user",
        actor_role_codes=[],
        actor_seat_ids=[],
    )
    role = {
        "brain_app_id": "rd_brain",
        "code": "developer",
        "assignable_subject_types": ["human_user"],
        "status": "active",
    }
    answerer = {
        "id": "selected-user",
        "permissions": ["delivery.rd_collaboration.work", "delivery.decision_requests.answer"],
        "scope_summary": [
            {"access_level": "write", "scope_id": "product-a", "scope_type": "product"}
        ],
    }
    assert qualify_human_actor(answerer, role_definition=role, product_id="product-a")
    assert not qualify_human_actor(answerer, role_definition=role, product_id="product-b")


def test_migration_seeds_the_complete_rd_permission_matrix():
    migration = (
        __import__("pathlib").Path(__file__).parents[1]
        / "app/db/migrations/109_requirement_driven_rd_collaboration.sql"
    ).read_text(encoding="utf-8")
    expected_permissions = {
        "delivery.rd_roles.manage",
        "delivery.rd_ai_employees.manage",
        "delivery.rd_executor_profiles.manage",
        "delivery.requirement_assessments.read",
        "delivery.requirement_assessments.decide",
        "delivery.rd_collaboration.read",
        "delivery.rd_collaboration.plan",
        "delivery.rd_collaboration.work",
        "delivery.decision_requests.decide",
        "delivery.decision_requests.answer",
        "delivery.rd_role_experiences.read",
        "delivery.rd_role_experiences.decide",
    }
    assert all(f"'{permission}'" in migration for permission in expected_permissions)


def test_role_patch_rejects_explicit_null_and_omission_preserves_disabled_status():
    app.state.store.reset()
    headers = auth_headers()
    created = client.post(
        "/api/delivery/rd-roles",
        headers=headers,
        json=role_payload(status="disabled", maximum_risk_level="high"),
    ).json()["data"]

    omitted = client.patch(f"/api/delivery/rd-roles/{created['id']}", headers=headers, json={})
    assert omitted.status_code == 200
    assert omitted.json()["data"]["status"] == "disabled"
    assert omitted.json()["data"]["maximum_risk_level"] == "high"

    for field in ("status", "maximum_risk_level", "capabilities"):
        response = client.patch(
            f"/api/delivery/rd-roles/{created['id']}", headers=headers, json={field: None}
        )
        assert response.status_code == 400
        assert response.json()["detail"]["code"] == "VALIDATION_ERROR"

    persisted = client.get("/api/delivery/rd-roles?status=disabled", headers=headers)
    assert [item["id"] for item in persisted.json()["data"]["items"]] == [created["id"]]


def test_employee_patch_rejects_explicit_null_and_omission_preserves_identity_metadata():
    app.state.store.reset()
    headers = auth_headers()
    created = client.post(
        "/api/delivery/rd-ai-employees",
        headers=headers,
        json=ai_employee_payload(status="disabled"),
    ).json()["data"]

    omitted = client.patch(
        f"/api/delivery/rd-ai-employees/{created['id']}", headers=headers, json={}
    )
    assert omitted.status_code == 200
    assert omitted.json()["data"]["status"] == "disabled"
    assert omitted.json()["data"]["persona_version"] == 2

    for field in ("status", "persona_version", "persona_json", "work_style_json"):
        response = client.patch(
            f"/api/delivery/rd-ai-employees/{created['id']}", headers=headers, json={field: None}
        )
        assert response.status_code == 400
        assert response.json()["detail"]["code"] == "VALIDATION_ERROR"


def test_executor_profile_patch_rejects_security_nulls_and_allows_nullable_reference_clear():
    app.state.store.reset()
    headers = auth_headers()
    created = client.post(
        "/api/delivery/rd-executor-profiles",
        headers=headers,
        json=executor_profile_payload(status="disabled", runner_id="runner-clearable"),
    ).json()["data"]

    omitted = client.patch(
        f"/api/delivery/rd-executor-profiles/{created['id']}", headers=headers, json={}
    )
    assert omitted.status_code == 200
    assert omitted.json()["data"]["status"] == "disabled"
    assert omitted.json()["data"]["health_status"] == "healthy"

    for field in ("status", "health_status", "executor_type", "max_concurrency", "credential_ref"):
        response = client.patch(
            f"/api/delivery/rd-executor-profiles/{created['id']}",
            headers=headers,
            json={field: None},
        )
        assert response.status_code == 400
        assert response.json()["detail"]["code"] == "VALIDATION_ERROR"

    cleared = client.patch(
        f"/api/delivery/rd-executor-profiles/{created['id']}",
        headers=headers,
        json={"runner_id": None},
    )
    assert cleared.status_code == 200
    assert cleared.json()["data"]["runner_id"] is None


def test_catalog_metadata_rejects_secret_like_keys_and_values_on_create_and_patch():
    app.state.store.reset()
    headers = auth_headers()
    create_cases = (
        (
            "/api/delivery/rd-ai-employees",
            ai_employee_payload(persona_json={"api_key": "placeholder"}),
        ),
        (
            "/api/delivery/rd-ai-employees",
            ai_employee_payload(work_style_json={"nested": {"password": "placeholder"}}),
        ),
        (
            "/api/delivery/rd-executor-profiles",
            executor_profile_payload(workspace_capabilities={"access_token": "placeholder"}),
        ),
        (
            "/api/delivery/rd-executor-profiles",
            executor_profile_payload(workspace_capabilities={"reference": "secret://placeholder"}),
        ),
    )
    for path, payload in create_cases:
        response = client.post(path, headers=headers, json=payload)
        assert response.status_code == 400
        assert response.json()["detail"]["code"] == "RD_CATALOG_SECRET_FORBIDDEN"

    employee = client.post(
        "/api/delivery/rd-ai-employees", headers=headers, json=ai_employee_payload()
    ).json()["data"]
    profile = client.post(
        "/api/delivery/rd-executor-profiles", headers=headers, json=executor_profile_payload()
    ).json()["data"]
    patch_cases = (
        (f"/api/delivery/rd-ai-employees/{employee['id']}", {"persona_json": {"token": "x"}}),
        (
            f"/api/delivery/rd-ai-employees/{employee['id']}",
            {"work_style_json": {"reference": "env:PLACEHOLDER"}},
        ),
        (
            f"/api/delivery/rd-executor-profiles/{profile['id']}",
            {"workspace_capabilities": {"credential": "placeholder"}},
        ),
    )
    for path, payload in patch_cases:
        response = client.patch(path, headers=headers, json=payload)
        assert response.status_code == 400
        assert response.json()["detail"]["code"] == "RD_CATALOG_SECRET_FORBIDDEN"


def test_catalog_response_redacts_legacy_secret_like_metadata():
    app.state.store.reset()
    headers = auth_headers()
    app.state.store.rd_ai_employees["legacy-employee"] = {
        "id": "legacy-employee",
        "code": "legacy-employee",
        "persona_json": {"api_key": "placeholder", "safe": "visible"},
        "work_style_json": {"reference": "secret://placeholder"},
        "status": "active",
    }
    app.state.store.rd_executor_profiles["legacy-profile"] = {
        "id": "legacy-profile",
        "code": "legacy-profile",
        "workspace_capabilities": {
            "password": "placeholder",
            "reference": "secret://placeholder",
            "safe": "visible",
        },
        "credential_ref": "secret://placeholder",
        "status": "active",
    }

    employee_response = client.get("/api/delivery/rd-ai-employees", headers=headers)
    profile_response = client.get("/api/delivery/rd-executor-profiles", headers=headers)
    employee_text = employee_response.text
    profile_text = profile_response.text
    assert employee_response.status_code == 200
    assert profile_response.status_code == 200
    assert "api_key" not in employee_text
    assert "secret://placeholder" not in employee_text
    assert "password" not in profile_text
    assert "secret://placeholder" not in profile_text
    assert "visible" in employee_text
    assert "visible" in profile_text


def test_catalog_metadata_allows_non_secret_business_terms():
    app.state.store.reset()
    response = client.post(
        "/api/delivery/rd-ai-employees",
        headers=auth_headers(),
        json=ai_employee_payload(
            persona_json={"tokenizer": "visible", "description": "secret review process"}
        ),
    )

    assert response.status_code == 200
    assert response.json()["data"]["persona_json"]["tokenizer"] == "visible"
