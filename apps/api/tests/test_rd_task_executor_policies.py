from fastapi.testclient import TestClient

from app.main import app
from app.services.rd_policy_resolution import (
    PolicyResolutionError,
    _hash,
    derive_assessment_rd_policy_snapshot,
    freeze_base_rd_policy_snapshot,
    merge_policy_payloads,
    resolve_final_rd_policy,
    resolve_work_item_binding,
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


def test_policy_patch_requires_matching_policy_version_and_keeps_unified_contract():
    app.state.store.reset()
    headers = auth_headers()
    created = client.post(
        "/api/delivery/rd-task-executor-policies",
        headers=headers,
        json=valid_policy_payload(),
    )
    assert created.status_code == 200
    policy = created.json()["data"]
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
    assert updated.json()["data"]["policy_version"] == 2

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
    assert updated.json()["data"]["role_bindings"][0]["role_code"] == "developer"


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
                    "require_independent_reviewer": False,
                },
                "git_config": {"allowlist": ["repo-a", "repo-b"]},
            },
            {
                "delivery_target": "ready_for_release",
                "quality_gate_config": {"gates": ["compliance"], "max_risk": "low"},
                "experience_reuse_config": {
                    "enabled": False,
                    "min_confidence": 0.8,
                    "require_independent_reviewer": True,
                },
                "git_config": {"allowlist": ["repo-b", "repo-c"]},
            },
        ]
    )
    assert merged["delivery_target"] == "ready_for_release"
    assert merged["quality_gate_config"]["gates"] == ["compliance", "security"]
    assert merged["quality_gate_config"]["max_risk"] == "low"
    assert merged["experience_reuse_config"] == {
        "enabled": False,
        "min_confidence": 0.8,
        "require_independent_reviewer": True,
    }
    assert merged["git_config"]["allowlist"] == ["repo-b"]

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
