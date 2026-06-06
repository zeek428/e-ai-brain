from __future__ import annotations

from typing import Any


def assistant_reference_candidates(
    current_store: Any,
    *,
    message: str,
    product_id: str | None,
    limit: int = 6,
) -> list[dict[str, str]]:
    products = list(current_store.products.values())
    if product_id:
        products = [product for product in products if product.get("id") == product_id]
    product_ids = {str(product["id"]) for product in products if product.get("id") is not None}
    requirements = [
        requirement
        for requirement in current_store.requirements.values()
        if not product_ids or requirement.get("product_id") in product_ids
    ]
    tasks = [
        task
        for task in current_store.ai_tasks.values()
        if not product_ids or task.get("product_id") in product_ids
    ]
    task_ids = {str(task["id"]) for task in tasks if task.get("id") is not None}
    versions = [
        version
        for version in current_store.product_versions.values()
        if not product_ids or version.get("product_id") in product_ids
    ]
    reviews = [
        review
        for review in current_store.human_reviews.values()
        if str(review.get("ai_task_id")) in task_ids
    ]
    bugs = [
        bug
        for bug in current_store.bugs.values()
        if not product_ids or bug.get("product_id") in product_ids
    ]
    code_reviews = [
        report
        for report in current_store.code_review_reports.values()
        if str(report.get("task_id")) in task_ids
    ]
    deposits = [
        deposit
        for deposit in current_store.knowledge_deposits.values()
        if str(deposit.get("ai_task_id")) in task_ids
    ]
    pools: list[tuple[str, list[dict[str, Any]]]] = [
        ("product", products),
        ("iteration_version", versions),
        ("requirement", requirements),
        ("ai_task", tasks),
        ("human_review", reviews),
        ("bug", bugs),
        ("code_review_report", code_reviews),
        ("knowledge_deposit", deposits),
    ]
    references: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    preferred_types = _assistant_reference_type_preferences(message)
    ordered_pools = sorted(
        pools,
        key=lambda item: preferred_types.get(item[0], len(preferred_types) + 10),
    )
    for entity_type, items in ordered_pools:
        for item in sorted(items, key=_assistant_reference_sort_key, reverse=True)[:3]:
            reference = _assistant_reference_for_entity(entity_type, item)
            if reference is None:
                continue
            key = (reference["type"], reference["id"])
            if key in seen:
                continue
            seen.add(key)
            references.append(reference)
            if len(references) >= limit:
                return references
    return references


def normalize_assistant_references(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    references: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for item in value:
        if not isinstance(item, dict):
            continue
        item_id = str(item.get("id") or "").strip()
        item_type = str(item.get("type") or "").strip()
        title = str(item.get("title") or item_id).strip()
        url = str(item.get("url") or "").strip()
        if not item_id or not item_type or not title or not url:
            continue
        key = (item_type, item_id)
        if key in seen:
            continue
        seen.add(key)
        references.append(
            {
                "id": item_id,
                "title": title,
                "type": item_type,
                "url": url,
            }
        )
        if len(references) >= 6:
            break
    return references


def _assistant_reference_type_preferences(message: str) -> dict[str, int]:
    normalized = message.lower()
    ordered: list[str] = []
    keyword_map = [
        (("需求", "requirement"), ["requirement"]),
        (("bug", "缺陷", "阻塞"), ["bug", "requirement"]),
        (("任务", "task"), ["ai_task", "human_review"]),
        (("review", "确认", "评审"), ["human_review", "code_review_report", "ai_task"]),
        (("迭代", "版本", "version"), ["iteration_version", "requirement"]),
        (("产品", "product"), ["product"]),
        (("代码", "pr", "github"), ["code_review_report", "ai_task"]),
        (("知识", "沉淀"), ["knowledge_deposit"]),
    ]
    for keywords, entity_types in keyword_map:
        if any(keyword in normalized for keyword in keywords):
            ordered.extend(entity_types)
    ordered.extend(
        [
            "requirement",
            "ai_task",
            "human_review",
            "bug",
            "iteration_version",
            "code_review_report",
            "knowledge_deposit",
            "product",
        ]
    )
    preferences: dict[str, int] = {}
    for entity_type in ordered:
        preferences.setdefault(entity_type, len(preferences))
    return preferences


def _assistant_reference_sort_key(item: dict[str, Any]) -> str:
    return str(
        item.get("updated_at")
        or item.get("created_at")
        or item.get("last_message_at")
        or item.get("id")
        or ""
    )


def _assistant_reference_for_entity(
    entity_type: str,
    item: dict[str, Any],
) -> dict[str, str] | None:
    item_id = item.get("id")
    if item_id is None:
        return None
    title = (
        item.get("title")
        or item.get("name")
        or item.get("summary")
        or item.get("code")
        or str(item_id)
    )
    route_map = {
        "ai_task": f"/tasks/management?task_id={item_id}",
        "bug": f"/delivery/bugs?bug_id={item_id}",
        "code_review_report": f"/tasks/management?code_review_report_id={item_id}",
        "human_review": f"/tasks/management?review_id={item_id}",
        "iteration_version": f"/delivery/versions?version_id={item_id}",
        "knowledge_deposit": f"/knowledge/documents?deposit_id={item_id}",
        "product": f"/assets/products?product_id={item_id}",
        "requirement": f"/delivery/requirements?requirement_id={item_id}",
    }
    return {
        "id": str(item_id),
        "title": str(title),
        "type": entity_type,
        "url": route_map[entity_type],
    }
