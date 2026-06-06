from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.core.store import DEFAULT_BRAIN_APP_ID


def _drop_requirements_without_product_context(payload: dict[str, Any]) -> None:
    products = payload.get("products", {})
    versions = payload.get("product_versions", {})
    requirements = payload.get("requirements", {})
    payload["requirements"] = {
        requirement_id: requirement
        for requirement_id, requirement in requirements.items()
        if requirement.get("product_id") in products
        and (
            requirement.get("version_id") is None
            or (
                requirement.get("version_id") in versions
                and versions[requirement["version_id"]].get("product_id")
                == requirement.get("product_id")
            )
        )
    }


def _drop_ai_tasks_without_context(payload: dict[str, Any]) -> None:
    products = payload.get("products", {})
    versions = payload.get("product_versions", {})
    requirements = payload.get("requirements", {})
    ai_tasks = payload.get("ai_tasks", {})
    payload["ai_tasks"] = {
        task_id: task
        for task_id, task in ai_tasks.items()
        if task.get("product_id") in products
        and task.get("requirement_id") in requirements
        and requirements[task["requirement_id"]].get("product_id") == task.get("product_id")
        and requirements[task["requirement_id"]].get("version_id") == task.get("version_id")
        and (
            task.get("version_id") is None
            or (
                task.get("version_id") in versions
                and versions[task["version_id"]].get("product_id") == task.get("product_id")
            )
        )
    }


def _ensure_ai_task_defaults(payload: dict[str, Any]) -> None:
    for requirement in payload.get("requirements", {}).values():
        requirement.setdefault("brain_app_id", DEFAULT_BRAIN_APP_ID)
    for task in payload.get("ai_tasks", {}).values():
        task.setdefault("brain_app_id", DEFAULT_BRAIN_APP_ID)
        task.setdefault("graph_run_ids", [])
        task.setdefault("input_json", {})
        task.setdefault("product_context", {})
        task.setdefault("review_ids", [])


def _drop_workflow_runtime_without_tasks(payload: dict[str, Any]) -> None:
    ai_tasks = payload.get("ai_tasks", {})
    graph_runs = payload.get("graph_runs", {})
    payload["graph_runs"] = {
        run_id: run
        for run_id, run in graph_runs.items()
        if run.get("ai_task_id") in ai_tasks
    }
    graph_runs = payload["graph_runs"]
    graph_checkpoints = payload.get("graph_checkpoints", {})
    payload["graph_checkpoints"] = {
        checkpoint_id: checkpoint
        for checkpoint_id, checkpoint in graph_checkpoints.items()
        if checkpoint.get("ai_task_id") in ai_tasks
        and checkpoint.get("graph_run_id") in graph_runs
    }
    human_reviews = payload.get("human_reviews", {})
    payload["human_reviews"] = {
        review_id: review
        for review_id, review in human_reviews.items()
        if review.get("ai_task_id") in ai_tasks
    }


def _sync_task_runtime_links(payload: dict[str, Any]) -> None:
    ai_tasks = payload.get("ai_tasks", {})
    for review_id, review in payload.get("human_reviews", {}).items():
        task = ai_tasks.get(review.get("ai_task_id"))
        if task is None:
            continue
        review_ids = task.setdefault("review_ids", [])
        if review_id not in review_ids:
            review_ids.append(review_id)
    for run_id, graph_run in payload.get("graph_runs", {}).items():
        task = ai_tasks.get(graph_run.get("ai_task_id"))
        if task is None:
            continue
        graph_run_ids = task.setdefault("graph_run_ids", [])
        if run_id not in graph_run_ids:
            graph_run_ids.append(run_id)
        if graph_run.get("checkpoint_id"):
            task["checkpoint_id"] = graph_run["checkpoint_id"]


def _sync_code_review_report_links(payload: dict[str, Any]) -> None:
    ai_tasks = payload.get("ai_tasks", {})
    for report_id, report in payload.get("code_review_reports", {}).items():
        task = ai_tasks.get(report.get("task_id"))
        if task is None:
            continue
        task["code_review_report_id"] = report_id


def _drop_knowledge_without_context(payload: dict[str, Any]) -> None:
    ai_tasks = payload.get("ai_tasks", {})
    knowledge_documents = payload.get("knowledge_documents", {})
    knowledge_chunks = payload.get("knowledge_chunks", {})
    knowledge_deposits = payload.get("knowledge_deposits", {})
    payload["knowledge_chunks"] = {
        chunk_id: chunk
        for chunk_id, chunk in knowledge_chunks.items()
        if chunk.get("document_id") in knowledge_documents
    }
    cleaned_deposits = {}
    for deposit_id, deposit in knowledge_deposits.items():
        if ai_tasks and deposit.get("ai_task_id") not in ai_tasks:
            continue
        if deposit.get("knowledge_document_id") not in knowledge_documents:
            deposit = deepcopy(deposit)
            deposit["knowledge_document_id"] = None
        cleaned_deposits[deposit_id] = deposit
    payload["knowledge_deposits"] = cleaned_deposits


def _drop_bugs_without_context(payload: dict[str, Any]) -> None:
    products = payload.get("products", {})
    versions = payload.get("product_versions", {})
    requirements = payload.get("requirements", {})
    ai_tasks = payload.get("ai_tasks", {})
    bugs = payload.get("bugs", {})
    cleaned_bugs = {}
    for bug_id, bug in bugs.items():
        product_id = bug.get("product_id")
        version_id = bug.get("version_id")
        requirement_id = bug.get("requirement_id")
        related_task_id = bug.get("related_task_id")
        if products and product_id not in products:
            continue
        if version_id and versions and (
            version_id not in versions or versions[version_id].get("product_id") != product_id
        ):
            continue
        if requirement_id and requirements and requirement_id not in requirements:
            continue
        if related_task_id and ai_tasks and related_task_id not in ai_tasks:
            continue
        cleaned_bugs[bug_id] = deepcopy(bug)
    for bug_id, bug in cleaned_bugs.items():
        duplicate_of_bug_id = bug.get("duplicate_of_bug_id")
        if duplicate_of_bug_id and duplicate_of_bug_id not in cleaned_bugs:
            bug["duplicate_of_bug_id"] = None
        if duplicate_of_bug_id == bug_id:
            bug["duplicate_of_bug_id"] = None
    payload["bugs"] = cleaned_bugs


def _drop_user_feedback_without_context(payload: dict[str, Any]) -> None:
    products = payload.get("products", {})
    requirements = payload.get("requirements", {})
    feedback_items = payload.get("user_feedback", {})
    cleaned_feedback = {}
    for feedback_id, feedback in feedback_items.items():
        product_id = feedback.get("product_id")
        requirement_id = feedback.get("related_requirement_id")
        if products and product_id not in products:
            continue
        if requirement_id and requirements and requirement_id not in requirements:
            continue
        cleaned_feedback[feedback_id] = deepcopy(feedback)
    payload["user_feedback"] = cleaned_feedback


def _drop_user_usage_metrics_without_context(payload: dict[str, Any]) -> None:
    products = payload.get("products", {})
    metrics = payload.get("user_usage_metrics", {})
    cleaned_metrics = {}
    for metric_id, metric in metrics.items():
        product_id = metric.get("product_id")
        if products and product_id not in products:
            continue
        cleaned_metrics[metric_id] = deepcopy(metric)
    payload["user_usage_metrics"] = cleaned_metrics


def _drop_gitlab_daily_code_metrics_without_context(payload: dict[str, Any]) -> None:
    products = payload.get("products", {})
    repositories = payload.get("product_git_repositories", {})
    metrics = payload.get("gitlab_daily_code_metrics", {})
    cleaned_metrics = {}
    for metric_id, metric in metrics.items():
        product_id = metric.get("product_id")
        repository_id = metric.get("repository_id")
        if products and product_id not in products:
            continue
        if repositories and repository_id not in repositories:
            continue
        if repositories and repositories[repository_id].get("product_id") != product_id:
            continue
        cleaned_metrics[metric_id] = deepcopy(metric)
    payload["gitlab_daily_code_metrics"] = cleaned_metrics


def _drop_jenkins_release_records_without_context(payload: dict[str, Any]) -> None:
    products = payload.get("products", {})
    versions = payload.get("product_versions", {})
    releases = payload.get("jenkins_release_records", {})
    cleaned_releases = {}
    for release_id, release in releases.items():
        product_id = release.get("product_id")
        version_id = release.get("version_id")
        if products and product_id not in products:
            continue
        if versions and version_id not in versions:
            continue
        if versions and versions[version_id].get("product_id") != product_id:
            continue
        cleaned_releases[release_id] = deepcopy(release)
    payload["jenkins_release_records"] = cleaned_releases


def _drop_online_log_metrics_without_context(payload: dict[str, Any]) -> None:
    products = payload.get("products", {})
    metrics = payload.get("online_log_metrics", {})
    cleaned_metrics = {}
    for metric_id, metric in metrics.items():
        product_id = metric.get("product_id")
        if products and product_id not in products:
            continue
        cleaned_metrics[metric_id] = deepcopy(metric)
    payload["online_log_metrics"] = cleaned_metrics


def _drop_iteration_planning_without_context(payload: dict[str, Any]) -> None:
    products = payload.get("products", {})
    versions = payload.get("product_versions", {})
    requirements = payload.get("requirements", {})
    suggestions = payload.get("iteration_plan_suggestions", {})
    decisions = payload.get("iteration_plan_decisions", {})
    cleaned_suggestions = {}
    for suggestion_id, suggestion in suggestions.items():
        product_id = suggestion.get("product_id")
        version_id = suggestion.get("version_id")
        if products and product_id not in products:
            continue
        if version_id and versions and (
            version_id not in versions or versions[version_id].get("product_id") != product_id
        ):
            continue
        cleaned = deepcopy(suggestion)
        converted_requirement_id = cleaned.get("converted_requirement_id")
        if (
            converted_requirement_id
            and requirements
            and converted_requirement_id not in requirements
        ):
            cleaned["converted_requirement_id"] = None
        cleaned_suggestions[suggestion_id] = cleaned
    cleaned_decisions = {}
    for decision_id, decision in decisions.items():
        suggestion_id = decision.get("suggestion_id")
        if suggestion_id not in cleaned_suggestions:
            continue
        cleaned = deepcopy(decision)
        requirement_id = cleaned.get("created_requirement_id")
        if requirement_id and requirements and requirement_id not in requirements:
            cleaned["created_requirement_id"] = None
        cleaned_decisions[decision_id] = cleaned
    payload["iteration_plan_suggestions"] = cleaned_suggestions
    payload["iteration_plan_decisions"] = cleaned_decisions


def _known_lifecycle_subject(
    payload: dict[str, Any],
    subject_type: str | None,
    subject_id: str | None,
) -> bool:
    if not subject_type or not subject_id:
        return False
    subject_collections = {
        "ai_task": "ai_tasks",
        "bug": "bugs",
        "code_review_report": "code_review_reports",
        "gitlab_daily_code_metric": "gitlab_daily_code_metrics",
        "gitlab_mr_snapshot": "gitlab_mr_snapshots",
        "graph_checkpoint": "graph_checkpoints",
        "graph_run": "graph_runs",
        "human_review": "human_reviews",
        "iteration_plan_suggestion": "iteration_plan_suggestions",
        "jenkins_release": "jenkins_release_records",
        "knowledge_deposit": "knowledge_deposits",
        "knowledge_document": "knowledge_documents",
        "mock_issue": "mock_writebacks",
        "online_log_metric": "online_log_metrics",
        "product": "products",
        "requirement": "requirements",
        "user_feedback": "user_feedback",
        "user_usage_metric": "user_usage_metrics",
    }
    if subject_type == "audit_event":
        return any(event.get("id") == subject_id for event in payload.get("audit_events", []))
    if subject_type == "mock_issue":
        return any(
            issue.get("id") == subject_id
            for writeback in payload.get("mock_writebacks", {}).values()
            for issue in writeback.get("issues", [])
        )
    collection_name = subject_collections.get(subject_type)
    if collection_name is None:
        return True
    collection = payload.get(collection_name, {})
    return not collection or subject_id in collection


def _drop_lifecycle_context_without_context(payload: dict[str, Any]) -> None:
    products = payload.get("products", {})
    requirements = payload.get("requirements", {})
    ai_tasks = payload.get("ai_tasks", {})
    edges = payload.get("lifecycle_context_edges", {})
    payload["lifecycle_context_edges"] = {
        edge_id: deepcopy(edge)
        for edge_id, edge in edges.items()
        if (not products or not edge.get("product_id") or edge.get("product_id") in products)
        and _known_lifecycle_subject(
            payload,
            edge.get("source_subject_type"),
            edge.get("source_subject_id"),
        )
        and _known_lifecycle_subject(
            payload,
            edge.get("target_subject_type"),
            edge.get("target_subject_id"),
        )
    }
    risks = payload.get("lifecycle_risk_signals", {})
    payload["lifecycle_risk_signals"] = {
        risk_id: deepcopy(risk)
        for risk_id, risk in risks.items()
        if (not products or not risk.get("product_id") or risk.get("product_id") in products)
        and (
            not risk.get("requirement_id")
            or not requirements
            or risk.get("requirement_id") in requirements
        )
        and (
            not risk.get("task_id")
            or not ai_tasks
            or risk.get("task_id") in ai_tasks
        )
        and _known_lifecycle_subject(
            payload,
            risk.get("source_subject_type"),
            risk.get("source_subject_id"),
        )
    }


def _drop_dashboard_snapshots_without_context(payload: dict[str, Any]) -> None:
    products = payload.get("products", {})
    snapshots = payload.get("dashboard_metric_snapshots", {})
    payload["dashboard_metric_snapshots"] = {
        snapshot_id: deepcopy(snapshot)
        for snapshot_id, snapshot in snapshots.items()
        if not products or not snapshot.get("product_id") or snapshot.get("product_id") in products
    }


def _drop_collector_runs_without_context(payload: dict[str, Any]) -> None:
    products = payload.get("products", {})
    runs = payload.get("collector_runs", {})
    cleaned_runs = {}
    for run_id, run in runs.items():
        product_id = run.get("product_id")
        if product_id and products and product_id not in products:
            continue
        cleaned_runs[run_id] = deepcopy(run)
    payload["collector_runs"] = cleaned_runs


def _clean_pending_attribution_references(payload: dict[str, Any]) -> None:
    products = payload.get("products", {})
    modules = payload.get("product_modules", {})
    requirements = payload.get("requirements", {})
    collector_runs = payload.get("collector_runs", {})
    cleaned_items = {}
    for item_id, item in payload.get("pending_attribution_items", {}).items():
        cleaned = deepcopy(item)
        collector_run_id = cleaned.get("collector_run_id")
        if collector_run_id and collector_run_id not in collector_runs:
            cleaned["collector_run_id"] = None
        suggested_product_id = cleaned.get("suggested_product_id")
        if suggested_product_id and suggested_product_id not in products:
            cleaned["suggested_product_id"] = None
            cleaned["suggested_module_code"] = None
        resolved_product_id = cleaned.get("resolved_product_id")
        if resolved_product_id and resolved_product_id not in products:
            cleaned["resolved_product_id"] = None
            cleaned["resolved_module_code"] = None
        resolved_requirement_id = cleaned.get("resolved_requirement_id")
        if resolved_requirement_id and resolved_requirement_id not in requirements:
            cleaned["resolved_requirement_id"] = None
        if cleaned.get("resolved_requirement_id") and requirements:
            requirement = requirements[cleaned["resolved_requirement_id"]]
            if cleaned.get("resolved_product_id") and requirement.get("product_id") != cleaned.get(
                "resolved_product_id"
            ):
                cleaned["resolved_requirement_id"] = None
        resolved_module_code = cleaned.get("resolved_module_code")
        if resolved_module_code and cleaned.get("resolved_product_id"):
            module_matches = any(
                module.get("product_id") == cleaned["resolved_product_id"]
                and module.get("code") == resolved_module_code
                for module in modules.values()
            )
            if not module_matches:
                cleaned["resolved_module_code"] = None
        cleaned_items[item_id] = cleaned
    payload["pending_attribution_items"] = cleaned_items


def _drop_gitlab_review_without_context(payload: dict[str, Any]) -> None:
    products = payload.get("products", {})
    repositories = payload.get("product_git_repositories", {})
    versions = payload.get("product_versions", {})
    requirements = payload.get("requirements", {})
    ai_tasks = payload.get("ai_tasks", {})
    human_reviews = payload.get("human_reviews", {})
    snapshots = payload.get("gitlab_mr_snapshots", {})

    cleaned_snapshots = {}
    for snapshot_id, snapshot in snapshots.items():
        repository = repositories.get(snapshot.get("repository_id"))
        product_id = snapshot.get("product_id")
        version_id = snapshot.get("version_id")
        requirement = requirements.get(snapshot.get("requirement_id"))
        solution_task = ai_tasks.get(snapshot.get("technical_solution_task_id"))
        if repository is None or repository.get("product_id") != product_id:
            continue
        if product_id not in products:
            continue
        if version_id and (
            version_id not in versions or versions[version_id].get("product_id") != product_id
        ):
            continue
        if requirement is None or requirement.get("product_id") != product_id:
            continue
        if version_id and requirement.get("version_id") != version_id:
            continue
        if solution_task is None or solution_task.get("product_id") != product_id:
            continue
        if solution_task.get("requirement_id") != snapshot.get("requirement_id"):
            continue
        if version_id and solution_task.get("version_id") != version_id:
            continue
        cleaned_snapshots[snapshot_id] = deepcopy(snapshot)

    cleaned_reports = {}
    for report_id, report in payload.get("code_review_reports", {}).items():
        if report.get("gitlab_mr_snapshot_id") not in cleaned_snapshots:
            continue
        task = ai_tasks.get(report.get("task_id"))
        if task is None:
            continue
        cleaned_report = deepcopy(report)
        review_id = cleaned_report.get("review_id")
        if review_id:
            review = human_reviews.get(review_id)
            if review is None or review.get("ai_task_id") != report.get("task_id"):
                cleaned_report["review_id"] = None
        cleaned_reports[report_id] = cleaned_report

    payload["gitlab_mr_snapshots"] = cleaned_snapshots
    payload["code_review_reports"] = cleaned_reports


def _drop_mock_writebacks_without_tasks(payload: dict[str, Any]) -> None:
    ai_tasks = payload.get("ai_tasks", {})
    cleaned_writebacks = {}
    for idempotency_key, writeback in payload.get("mock_writebacks", {}).items():
        task_id = writeback.get("task_id")
        if task_id not in ai_tasks:
            continue
        cleaned_issues = []
        for issue in writeback.get("issues", []):
            if issue.get("source_task_id") != task_id:
                continue
            cleaned_issues.append(deepcopy(issue))
        if not cleaned_issues:
            continue
        cleaned_writeback = deepcopy(writeback)
        cleaned_writeback["idempotency_key"] = writeback.get("idempotency_key") or idempotency_key
        cleaned_writeback["issues"] = cleaned_issues
        cleaned_writeback["task_id"] = task_id
        cleaned_writebacks[idempotency_key] = cleaned_writeback
    payload["mock_writebacks"] = cleaned_writebacks
