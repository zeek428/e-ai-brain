from __future__ import annotations

from app.services.product_scope import (
    product_scope_filter,
    user_can_read_product,
    user_product_access,
)
from app.services.scheduled_job_access import (
    scheduled_job_product_scope_filter,
    user_can_access_scheduled_job_product,
)


def test_non_admin_without_product_scope_gets_empty_product_range():
    user = {
        "id": "user_viewer",
        "permissions": ["product.read"],
        "roles": ["viewer"],
        "scope_summary": [],
    }

    assert user_product_access(user) == (False, set())
    assert product_scope_filter(user) == []
    assert user_can_read_product(user, "product_alpha") is False


def test_explicit_global_scope_keeps_global_product_access():
    user = {
        "id": "user_global",
        "permissions": ["product.read"],
        "roles": ["viewer"],
        "scope_summary": [
            {"access_level": "read", "scope_id": "*", "scope_type": "global"}
        ],
    }

    assert user_product_access(user) == (True, set())
    assert product_scope_filter(user) is None
    assert user_can_read_product(user, "product_alpha") is True


def test_scheduled_jobs_use_same_empty_scope_default():
    user = {
        "id": "user_runner",
        "permissions": ["system.scheduled_jobs.run"],
        "roles": ["developer"],
        "scope_summary": [{"access_level": "read", "scope_id": "*", "scope_type": "self"}],
    }

    assert scheduled_job_product_scope_filter(user) == []
    assert user_can_access_scheduled_job_product(user, None) is True
    assert user_can_access_scheduled_job_product(user, "product_alpha") is False
