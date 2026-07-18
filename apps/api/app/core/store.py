from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

DEFAULT_BRAIN_APP_ID = "rd_brain"


def default_brain_apps() -> dict[str, dict[str, Any]]:
    return {
        DEFAULT_BRAIN_APP_ID: {
            "id": DEFAULT_BRAIN_APP_ID,
            "code": DEFAULT_BRAIN_APP_ID,
            "name": "研发大脑",
            "status": "active",
            "description": "把研发需求转成可确认、可回写、可沉淀的任务方案。",
            "config": {
                "default_task_types": [
                    "product_detail_design",
                    "technical_solution",
                    "development_planning",
                    "automated_testing",
                    "release_readiness",
                    "post_release_analysis",
                    "code_review",
                    "bug_fix",
                ],
            },
        }
    }


def _next_id(prefix: str, current: int) -> str:
    return f"{prefix}_{current:03d}"


@dataclass
class MemoryStore:
    brain_apps: dict[str, dict[str, Any]] = field(default_factory=default_brain_apps)
    products: dict[str, dict[str, Any]] = field(default_factory=dict)
    product_versions: dict[str, dict[str, Any]] = field(default_factory=dict)
    product_version_branch_configs: dict[str, dict[str, Any]] = field(default_factory=dict)
    product_modules: dict[str, dict[str, Any]] = field(default_factory=dict)
    product_git_repositories: dict[str, dict[str, Any]] = field(default_factory=dict)
    related_systems: dict[str, dict[str, Any]] = field(default_factory=dict)
    model_gateway_configs: dict[str, dict[str, Any]] = field(default_factory=dict)
    model_gateway_logs: list[dict[str, Any]] = field(default_factory=list)
    ai_skills: dict[str, dict[str, Any]] = field(default_factory=dict)
    ai_agents: dict[str, dict[str, Any]] = field(default_factory=dict)
    integration_plugins: dict[str, dict[str, Any]] = field(default_factory=dict)
    plugin_connections: dict[str, dict[str, Any]] = field(default_factory=dict)
    plugin_actions: dict[str, dict[str, Any]] = field(default_factory=dict)
    plugin_invocation_logs: dict[str, dict[str, Any]] = field(default_factory=dict)
    ai_executor_runners: dict[str, dict[str, Any]] = field(default_factory=dict)
    ai_executor_tasks: dict[str, dict[str, Any]] = field(default_factory=dict)
    ai_executor_approval_requests: dict[str, dict[str, Any]] = field(default_factory=dict)
    execution_attestations: dict[str, dict[str, Any]] = field(default_factory=dict)
    acceptance_test_plans: dict[str, dict[str, Any]] = field(default_factory=dict)
    acceptance_test_cases: dict[str, dict[str, Any]] = field(default_factory=dict)
    acceptance_test_runs: dict[str, dict[str, Any]] = field(default_factory=dict)
    production_change_controls: dict[str, dict[str, Any]] = field(default_factory=dict)
    production_change_approvals: dict[str, dict[str, Any]] = field(default_factory=dict)
    release_freezes: dict[str, dict[str, Any]] = field(default_factory=dict)
    external_operations: dict[str, dict[str, Any]] = field(default_factory=dict)
    execution_worker_heartbeats: dict[str, dict[str, Any]] = field(default_factory=dict)
    agent_budget_ledgers: dict[str, dict[str, Any]] = field(default_factory=dict)
    agent_circuit_records: dict[str, dict[str, Any]] = field(default_factory=dict)
    knowledge_visual_embeddings: dict[str, dict[str, Any]] = field(default_factory=dict)
    execution_context_manifests: dict[str, dict[str, Any]] = field(default_factory=dict)
    quality_gate_policies: dict[str, dict[str, Any]] = field(default_factory=dict)
    quality_gate_runs: dict[str, dict[str, Any]] = field(default_factory=dict)
    quality_gate_checks: dict[str, dict[str, Any]] = field(default_factory=dict)
    agent_loop_runs: dict[str, dict[str, Any]] = field(default_factory=dict)
    agent_loop_iterations: dict[str, dict[str, Any]] = field(default_factory=dict)
    execution_outbox_events: dict[str, dict[str, Any]] = field(default_factory=dict)
    execution_resource_grants: dict[str, dict[str, Any]] = field(default_factory=dict)
    deployment_run_steps: dict[str, dict[str, Any]] = field(default_factory=dict)
    external_event_inbox: dict[str, dict[str, Any]] = field(default_factory=dict)
    rd_task_executor_policies: dict[str, dict[str, Any]] = field(default_factory=dict)
    rd_role_definitions: dict[str, dict[str, Any]] = field(default_factory=dict)
    rd_ai_employees: dict[str, dict[str, Any]] = field(default_factory=dict)
    rd_executor_profiles: dict[str, dict[str, Any]] = field(default_factory=dict)
    rd_task_executor_policy_role_bindings: dict[str, dict[str, Any]] = field(
        default_factory=dict,
    )
    rd_task_executor_policy_snapshots: dict[str, dict[str, Any]] = field(default_factory=dict)
    rd_task_executor_policy_snapshot_sources: dict[str, dict[str, Any]] = field(
        default_factory=dict,
    )
    requirement_assessments: dict[str, dict[str, Any]] = field(default_factory=dict)
    requirement_assessment_opinions: dict[str, dict[str, Any]] = field(default_factory=dict)
    rd_collaboration_runs: dict[str, dict[str, Any]] = field(default_factory=dict)
    rd_collaboration_run_requirements: dict[str, dict[str, Any]] = field(default_factory=dict)
    rd_product_version_requirement_provenance: dict[str, dict[str, Any]] = field(
        default_factory=dict,
    )
    rd_scope_change_requests: dict[str, dict[str, Any]] = field(default_factory=dict)
    rd_scope_change_request_operations: dict[str, dict[str, Any]] = field(
        default_factory=dict,
    )
    rd_run_seats: dict[str, dict[str, Any]] = field(default_factory=dict)
    rd_role_sessions: dict[str, dict[str, Any]] = field(default_factory=dict)
    rd_work_items: dict[str, dict[str, Any]] = field(default_factory=dict)
    rd_work_item_dependencies: dict[str, dict[str, Any]] = field(default_factory=dict)
    rd_work_item_attempts: dict[str, dict[str, Any]] = field(default_factory=dict)
    rd_collaboration_events: dict[str, dict[str, Any]] = field(default_factory=dict)
    decision_requests: dict[str, dict[str, Any]] = field(default_factory=dict)
    rd_command_idempotency_records: dict[str, dict[str, Any]] = field(default_factory=dict)
    rd_command_replay_secrets: dict[str, dict[str, Any]] = field(default_factory=dict)
    role_feedback_records: dict[str, dict[str, Any]] = field(default_factory=dict)
    rd_role_experience_records: dict[str, dict[str, Any]] = field(default_factory=dict)
    rd_role_experience_sources: dict[str, dict[str, Any]] = field(default_factory=dict)
    rd_role_experience_decisions: dict[str, dict[str, Any]] = field(default_factory=dict)
    rd_collaboration_upgrade_state: dict[str, dict[str, Any]] = field(default_factory=dict)
    scheduled_jobs: dict[str, dict[str, Any]] = field(default_factory=dict)
    scheduled_job_runs: dict[str, dict[str, Any]] = field(default_factory=dict)
    assistant_chat_runs: dict[str, dict[str, Any]] = field(default_factory=dict)
    assistant_conversations: dict[str, dict[str, Any]] = field(default_factory=dict)
    assistant_messages: dict[str, dict[str, Any]] = field(default_factory=dict)
    assistant_action_drafts: dict[str, dict[str, Any]] = field(default_factory=dict)
    assistant_action_runs: dict[str, dict[str, Any]] = field(default_factory=dict)
    assistant_action_reference_configs: dict[str, dict[str, Any]] = field(default_factory=dict)
    assistant_role_quick_tasks: dict[str, dict[str, Any]] = field(default_factory=dict)
    gitlab_mr_snapshots: dict[str, dict[str, Any]] = field(default_factory=dict)
    code_review_reports: dict[str, dict[str, Any]] = field(default_factory=dict)
    code_inspection_reports: dict[str, dict[str, Any]] = field(default_factory=dict)
    code_inspection_findings: dict[str, dict[str, Any]] = field(default_factory=dict)
    code_inspection_notifications: dict[str, dict[str, Any]] = field(default_factory=dict)
    knowledge_spaces: dict[str, dict[str, Any]] = field(default_factory=dict)
    knowledge_space_members: dict[str, dict[str, Any]] = field(default_factory=dict)
    knowledge_folders: dict[str, dict[str, Any]] = field(default_factory=dict)
    knowledge_assets: dict[str, dict[str, Any]] = field(default_factory=dict)
    knowledge_import_jobs: dict[str, dict[str, Any]] = field(default_factory=dict)
    knowledge_chunk_sets: dict[str, dict[str, Any]] = field(default_factory=dict)
    knowledge_processing_profiles: dict[str, dict[str, Any]] = field(default_factory=dict)
    knowledge_document_versions: dict[str, dict[str, Any]] = field(default_factory=dict)
    knowledge_citation_feedback: dict[str, dict[str, Any]] = field(default_factory=dict)
    knowledge_documents: dict[str, dict[str, Any]] = field(default_factory=dict)
    knowledge_chunks: dict[str, dict[str, Any]] = field(default_factory=dict)
    knowledge_deposits: dict[str, dict[str, Any]] = field(default_factory=dict)
    mock_writebacks: dict[str, dict[str, Any]] = field(default_factory=dict)
    bugs: dict[str, dict[str, Any]] = field(default_factory=dict)
    gitlab_daily_code_metrics: dict[str, dict[str, Any]] = field(default_factory=dict)
    jenkins_release_records: dict[str, dict[str, Any]] = field(default_factory=dict)
    deployment_schemes: dict[str, dict[str, Any]] = field(default_factory=dict)
    deployment_requests: dict[str, dict[str, Any]] = field(default_factory=dict)
    deployment_runs: dict[str, dict[str, Any]] = field(default_factory=dict)
    online_log_metrics: dict[str, dict[str, Any]] = field(default_factory=dict)
    user_usage_metrics: dict[str, dict[str, Any]] = field(default_factory=dict)
    user_feedback: dict[str, dict[str, Any]] = field(default_factory=dict)
    iteration_plan_suggestions: dict[str, dict[str, Any]] = field(default_factory=dict)
    iteration_plan_decisions: dict[str, dict[str, Any]] = field(default_factory=dict)
    lifecycle_context_edges: dict[str, dict[str, Any]] = field(default_factory=dict)
    lifecycle_risk_signals: dict[str, dict[str, Any]] = field(default_factory=dict)
    dashboard_metric_snapshots: dict[str, dict[str, Any]] = field(default_factory=dict)
    system_settings: dict[str, Any] = field(default_factory=dict)
    system_alert_incidents: dict[str, dict[str, Any]] = field(default_factory=dict)
    system_alert_notifications: dict[str, dict[str, Any]] = field(default_factory=dict)
    system_alert_rules: dict[str, dict[str, Any]] = field(default_factory=dict)
    system_alert_subscriptions: dict[str, dict[str, Any]] = field(default_factory=dict)
    knowledge_quality_events: dict[str, dict[str, Any]] = field(default_factory=dict)
    collector_runs: dict[str, dict[str, Any]] = field(default_factory=dict)
    pending_attribution_items: dict[str, dict[str, Any]] = field(default_factory=dict)
    requirements: dict[str, dict[str, Any]] = field(default_factory=dict)
    ai_tasks: dict[str, dict[str, Any]] = field(default_factory=dict)
    graph_runs: dict[str, dict[str, Any]] = field(default_factory=dict)
    graph_checkpoints: dict[str, dict[str, Any]] = field(default_factory=dict)
    human_reviews: dict[str, dict[str, Any]] = field(default_factory=dict)
    audit_events: list[dict[str, Any]] = field(default_factory=list)
    counters: dict[str, int] = field(default_factory=dict)

    def reset(self) -> None:
        self.brain_apps = default_brain_apps()
        self.products.clear()
        self.product_versions.clear()
        self.product_version_branch_configs.clear()
        self.product_modules.clear()
        self.product_git_repositories.clear()
        self.related_systems.clear()
        self.model_gateway_configs.clear()
        self.model_gateway_logs.clear()
        self.ai_skills.clear()
        self.ai_agents.clear()
        self.integration_plugins.clear()
        self.plugin_connections.clear()
        self.plugin_actions.clear()
        self.plugin_invocation_logs.clear()
        self.ai_executor_runners.clear()
        self.ai_executor_tasks.clear()
        self.ai_executor_approval_requests.clear()
        self.execution_attestations.clear()
        self.execution_context_manifests.clear()
        self.quality_gate_policies.clear()
        self.quality_gate_runs.clear()
        self.quality_gate_checks.clear()
        self.agent_loop_runs.clear()
        self.agent_loop_iterations.clear()
        self.execution_outbox_events.clear()
        self.execution_resource_grants.clear()
        self.deployment_run_steps.clear()
        self.external_event_inbox.clear()
        self.rd_task_executor_policies.clear()
        self.rd_role_definitions.clear()
        self.rd_ai_employees.clear()
        self.rd_executor_profiles.clear()
        self.rd_task_executor_policy_role_bindings.clear()
        self.rd_task_executor_policy_snapshots.clear()
        self.rd_task_executor_policy_snapshot_sources.clear()
        self.requirement_assessments.clear()
        self.requirement_assessment_opinions.clear()
        self.rd_collaboration_runs.clear()
        self.rd_collaboration_run_requirements.clear()
        self.rd_scope_change_requests.clear()
        self.rd_scope_change_request_operations.clear()
        self.rd_run_seats.clear()
        self.rd_role_sessions.clear()
        self.rd_work_items.clear()
        self.rd_work_item_dependencies.clear()
        self.rd_work_item_attempts.clear()
        self.rd_collaboration_events.clear()
        self.decision_requests.clear()
        self.rd_command_idempotency_records.clear()
        self.rd_command_replay_secrets.clear()
        self.role_feedback_records.clear()
        self.rd_role_experience_records.clear()
        self.rd_role_experience_sources.clear()
        self.rd_role_experience_decisions.clear()
        self.rd_collaboration_upgrade_state.clear()
        self.scheduled_jobs.clear()
        self.scheduled_job_runs.clear()
        self.assistant_chat_runs.clear()
        self.assistant_conversations.clear()
        self.assistant_messages.clear()
        self.assistant_action_drafts.clear()
        self.assistant_action_runs.clear()
        self.assistant_action_reference_configs.clear()
        self.assistant_role_quick_tasks.clear()
        self.gitlab_mr_snapshots.clear()
        self.code_review_reports.clear()
        self.code_inspection_reports.clear()
        self.code_inspection_findings.clear()
        self.code_inspection_notifications.clear()
        self.knowledge_spaces.clear()
        self.knowledge_space_members.clear()
        self.knowledge_folders.clear()
        self.knowledge_assets.clear()
        self.knowledge_import_jobs.clear()
        self.knowledge_chunk_sets.clear()
        self.knowledge_processing_profiles.clear()
        self.knowledge_document_versions.clear()
        self.knowledge_citation_feedback.clear()
        self.knowledge_documents.clear()
        self.knowledge_chunks.clear()
        self.knowledge_deposits.clear()
        self.mock_writebacks.clear()
        self.bugs.clear()
        self.gitlab_daily_code_metrics.clear()
        self.jenkins_release_records.clear()
        self.deployment_schemes.clear()
        self.deployment_requests.clear()
        self.deployment_runs.clear()
        self.online_log_metrics.clear()
        self.user_usage_metrics.clear()
        self.user_feedback.clear()
        self.iteration_plan_suggestions.clear()
        self.iteration_plan_decisions.clear()
        self.lifecycle_context_edges.clear()
        self.lifecycle_risk_signals.clear()
        self.dashboard_metric_snapshots.clear()
        self.system_settings.clear()
        self.system_alert_incidents.clear()
        self.system_alert_notifications.clear()
        self.system_alert_rules.clear()
        self.system_alert_subscriptions.clear()
        self.knowledge_quality_events.clear()
        self.collector_runs.clear()
        self.pending_attribution_items.clear()
        self.requirements.clear()
        self.ai_tasks.clear()
        self.graph_runs.clear()
        self.graph_checkpoints.clear()
        self.human_reviews.clear()
        self.audit_events.clear()
        self.counters.clear()

    def new_id(self, prefix: str) -> str:
        next_value = self.counters.get(prefix, 0) + 1
        self.counters[prefix] = next_value
        return _next_id(prefix, next_value)

    def snapshot(self, value: dict[str, Any]) -> dict[str, Any]:
        return deepcopy(value)

    def audit(
        self,
        *,
        event_type: str,
        actor_id: str,
        ai_task_id: str | None = None,
        subject_type: str | None = None,
        subject_id: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        event = {
            "id": self.new_id("audit"),
            "event_type": event_type,
            "actor_id": actor_id,
            "ai_task_id": ai_task_id,
            "subject_type": subject_type,
            "subject_id": subject_id,
            "payload": payload or {},
            "sequence": len(self.audit_events) + 1,
            "created_at": datetime.now(UTC).isoformat(),
        }
        self.audit_events.append(event)
        return event
