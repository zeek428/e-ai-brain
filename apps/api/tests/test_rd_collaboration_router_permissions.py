from __future__ import annotations

from app.api.routers import rd_collaboration


def test_work_item_review_allows_reviewer_role_without_broadening_plan_access(
    monkeypatch,
) -> None:
    calls: list[tuple[set[str], set[str]]] = []

    def capture(user, permissions, roles) -> None:
        _ = user
        calls.append((set(permissions), set(roles)))

    monkeypatch.setattr(rd_collaboration, "require_any_permission_or_roles", capture)

    rd_collaboration._require_work_item_review({"roles": ["reviewer"]})
    rd_collaboration._require({"roles": ["reviewer"]}, "delivery.rd_collaboration.plan")

    assert calls == [
        (
            {"delivery.rd_collaboration.work"},
            {"admin", "developer", "product_owner", "rd_owner", "reviewer", "tester"},
        ),
        (
            {"delivery.rd_collaboration.plan"},
            {"admin", "developer", "product_owner", "rd_owner", "tester"},
        ),
    ]
