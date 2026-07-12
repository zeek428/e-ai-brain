from app.core.store import MemoryStore
from app.services.production_change_controls import (
    approve_production_change,
    create_production_change_control,
    deployment_can_start,
    production_deployment_can_start,
    set_release_freeze,
)


def test_creator_cannot_approve_own_production_change_and_two_roles_are_required() -> None:
    store = MemoryStore()
    control = create_production_change_control(
        store,
        created_by="user_maker",
        deployment_id="deployment_001",
        product_id="product_001",
        required_roles=["ops", "release_manager"],
    )

    own = approve_production_change(
        store,
        control_id=control["id"],
        decision="approved",
        role_code="ops",
        user_id="user_maker",
    )
    first = approve_production_change(
        store,
        control_id=control["id"],
        decision="approved",
        role_code="ops",
        user_id="user_ops",
    )
    second = approve_production_change(
        store,
        control_id=control["id"],
        decision="approved",
        role_code="release_manager",
        user_id="user_release",
    )

    assert own["status"] == "rejected"
    assert not deployment_can_start(control, [own, first])
    assert deployment_can_start(control, [own, first, second])


def test_active_release_freeze_blocks_production_start() -> None:
    store = MemoryStore()
    control = create_production_change_control(
        store,
        created_by="user_maker",
        deployment_id="deployment_001",
        product_id="product_001",
        required_roles=[],
    )
    set_release_freeze(store, created_by="user_admin", product_id="product_001", status="active")

    assert not production_deployment_can_start(
        store,
        deployment_id=control["deployment_id"],
        product_id="product_001",
    )
