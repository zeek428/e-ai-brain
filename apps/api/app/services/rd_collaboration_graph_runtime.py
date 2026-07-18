"""Bridge committed collaboration events to the durable LangGraph cursor.

The repository command is the atomic boundary for Inbox/event, audit, Outbox
and feedback.  The graph checkpoint is intentionally written afterwards.  A
checkpoint failure therefore leaves one committed event that can be observed
idempotently on the next resume rather than repeating an external side effect.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from threading import Lock
from typing import Any

from app.core.rd_collaboration_graph import (
    RD_COLLABORATION_GRAPH_DEFINITION,
    RD_COLLABORATION_GRAPH_VERSION,
    build_rd_collaboration_graph,
    rd_collaboration_thread_id,
)


class CheckpointIncompatibleError(RuntimeError):
    """Raised when a stored graph cursor cannot safely run this graph version."""


def _records(store: Any, name: str) -> dict[str, dict[str, Any]]:
    records = getattr(store, name, None)
    if not isinstance(records, dict):
        records = {}
        setattr(store, name, records)
    return records


def _canonical_hash(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return f"sha256:{hashlib.sha256(raw.encode()).hexdigest()}"


def _now() -> str:
    return datetime.now(UTC).isoformat()


class RdCollaborationGraphRuntime:
    """Persist events first, then advance an idempotent collaboration cursor."""

    def __init__(self, store: Any, *, checkpointer: Any) -> None:
        self.store = store
        self.checkpointer = checkpointer
        self.graph = build_rd_collaboration_graph(checkpointer)
        self._fail_checkpoint_once = False
        self._memory_lock = Lock()

    def fail_next_checkpoint_write(self) -> None:
        """Test-only fault injection at the domain/cursor commit boundary."""
        self._fail_checkpoint_once = True

    def write_incompatible_checkpoint_for_test(self, collaboration_run_id: str) -> None:
        """Seed an incompatible persisted cursor for fail-closed regression tests."""
        config = self._config(collaboration_run_id)
        self.graph.invoke(
            {
                "collaboration_run_id": collaboration_run_id,
                "current_step": "start",
                "processed_event_ids": [],
            },
            config=config,
        )
        self.graph.update_state(
            config,
            {
                "graph_definition": RD_COLLABORATION_GRAPH_DEFINITION,
                "graph_version": "unsupported",
            },
        )

    def handle_event(
        self,
        *,
        collaboration_run_id: str,
        event_id: str,
        event_type: str,
        payload: dict[str, Any] | None = None,
        subject_type: str = "rd_collaboration_run",
        subject_id: str | None = None,
    ) -> dict[str, Any]:
        """Commit an event once and advance its cursor separately.

        Replaying the same event after a cursor failure is expected: the domain
        command returns its original snapshot while the graph re-reads current
        domain state and records the already-committed event exactly once.
        """
        run = self._load_run(collaboration_run_id)
        if run is None:
            raise ValueError("Collaboration run does not exist")
        if not self._checkpoint_is_compatible(collaboration_run_id):
            self._request_human_takeover(run)
            return {
                "checkpoint_status": "incompatible",
                "human_takeover_required": True,
                "collaboration_run_id": collaboration_run_id,
            }

        event = self._commit_domain_event(
            run=run,
            event_id=event_id,
            event_type=event_type,
            payload=payload or {},
            subject_type=subject_type,
            subject_id=subject_id or collaboration_run_id,
        )
        current_run = self._load_run(collaboration_run_id) or run
        try:
            if self._fail_checkpoint_once:
                self._fail_checkpoint_once = False
                raise RuntimeError("injected LangGraph checkpoint failure")
            state = self.graph.invoke(
                {
                    "collaboration_run_id": collaboration_run_id,
                    "domain_status": current_run.get("status"),
                    "domain_version": int(current_run.get("version") or 1),
                    "event_id": event["id"],
                },
                config=self._config(collaboration_run_id),
            )
        except Exception as exc:  # checkpoint is deliberately a separate retryable commit.
            return {
                "checkpoint_status": "failed",
                "checkpoint_error": type(exc).__name__,
                "collaboration_run_id": collaboration_run_id,
                "event": deepcopy(event),
                "human_takeover_required": False,
            }
        return {
            "checkpoint_status": "persisted",
            "collaboration_run_id": collaboration_run_id,
            "event": deepcopy(event),
            "state": dict(state),
            "human_takeover_required": False,
        }

    def domain_transition_count(self, event_id: str) -> int:
        return sum(
            1
            for event in _records(self.store, "rd_collaboration_events").values()
            if event.get("event_key") == f"graph-event:{event_id}"
        )

    def outbox_count(self, event_id: str) -> int:
        return sum(
            1
            for event in _records(self.store, "execution_outbox_events").values()
            if event.get("idempotency_key", "").endswith(f":{event_id}")
        )

    def role_feedback_count(self, *, source_event_id: str) -> int:
        return sum(
            1
            for feedback in _records(self.store, "role_feedback_records").values()
            if feedback.get("source_event_id") == source_event_id
        )

    @staticmethod
    def _config(collaboration_run_id: str) -> dict[str, dict[str, str]]:
        return {"configurable": {"thread_id": rd_collaboration_thread_id(collaboration_run_id)}}

    def _load_run(self, collaboration_run_id: str) -> dict[str, Any] | None:
        repository = getattr(self.store, "repository", None)
        get_run = getattr(repository, "get_rd_collaboration_run", None)
        if callable(get_run):
            return get_run(collaboration_run_id)
        run = _records(self.store, "rd_collaboration_runs").get(collaboration_run_id)
        return deepcopy(run) if run is not None else None

    def _checkpoint_is_compatible(self, collaboration_run_id: str) -> bool:
        snapshot = self.graph.get_state(self._config(collaboration_run_id))
        values = getattr(snapshot, "values", None) or {}
        definition = values.get("graph_definition")
        version = values.get("graph_version")
        return definition in {None, RD_COLLABORATION_GRAPH_DEFINITION} and version in {
            None,
            RD_COLLABORATION_GRAPH_VERSION,
        }

    def _commit_domain_event(
        self,
        *,
        run: dict[str, Any],
        event_id: str,
        event_type: str,
        payload: dict[str, Any],
        subject_type: str,
        subject_id: str,
    ) -> dict[str, Any]:
        repository = getattr(self.store, "repository", None)
        execute = getattr(repository, "execute_idempotent_rd_command", None)
        if callable(execute):
            return self._commit_domain_event_repository(
                execute=execute,
                run=run,
                event_id=event_id,
                event_type=event_type,
                payload=payload,
                subject_type=subject_type,
                subject_id=subject_id,
            )
        return self._commit_domain_event_memory(
            run=run,
            event_id=event_id,
            event_type=event_type,
            payload=payload,
            subject_type=subject_type,
            subject_id=subject_id,
        )

    def _event_record(
        self,
        *,
        run: dict[str, Any],
        event_id: str,
        event_type: str,
        payload: dict[str, Any],
        subject_type: str,
        subject_id: str,
    ) -> dict[str, Any]:
        return {
            "id": event_id,
            "collaboration_run_id": run["id"],
            "event_type": event_type,
            "event_key": f"graph-event:{event_id}",
            "subject_type": subject_type,
            "subject_id": subject_id,
            "payload_json": deepcopy(payload),
            "occurred_at": _now(),
        }

    def _feedback_record(self, *, run: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
        event_id = str(event["id"])
        return {
            "id": f"graph-feedback:{run['id']}:{event_id}",
            "brain_app_id": run.get("brain_app_id", "rd_brain"),
            "product_id": run["product_id"],
            "collaboration_run_id": run["id"],
            "feedback_kind": "graph_event_processed",
            "source_event_id": event_id,
            "feedback_fingerprint": _canonical_hash(
                {
                    "source_event_id": event_id,
                    "outcome": "graph_event_processed",
                    "producer_subject_type": "service",
                    "producer_subject_id": "collaboration_orchestrator",
                }
            ),
            "role_code": "system",
            "seat_id": None,
            # A service-produced fact is still attributed to the accountable
            # run initiator.  The feedback table intentionally requires a
            # durable human/AI subject even when the producer is a service.
            "human_user_id": run.get("created_by"),
            "ai_employee_id": None,
            "executor_profile_id": None,
            "work_item_id": None,
            "attempt_id": None,
            "strategy_snapshot_id": run["strategy_snapshot_id"],
            "evidence_refs": [{"kind": "collaboration_event", "id": event_id}],
            "producer_subject_type": "service",
            "producer_subject_id": "collaboration_orchestrator",
            "producer_role_code": None,
            "producer_seat_id": None,
            "recorded_by": "collaboration_orchestrator",
        }

    def _outbox_record(self, *, run: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
        event_id = str(event["id"])
        return {
            "id": f"graph-outbox:{run['id']}:{event_id}",
            "aggregate_type": "rd_collaboration_run",
            "aggregate_id": run["id"],
            "event_type": "rd_collaboration.graph_event_committed",
            "idempotency_key": f"rd-collaboration-graph:{run['id']}:{event_id}",
            "payload_json": {"event_id": event_id, "event_type": event["event_type"]},
            "status": "pending",
        }

    def _audit_record(self, *, run: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": f"graph-audit:{run['id']}:{event['id']}",
            "event_type": "rd_collaboration.graph_event_committed",
            "actor_id": "collaboration_orchestrator",
            "subject_type": "rd_collaboration_run",
            "subject_id": run["id"],
            "payload": {"event_id": event["id"], "event_type": event["event_type"]},
        }

    def _commit_domain_event_memory(
        self,
        *,
        run: dict[str, Any],
        event_id: str,
        event_type: str,
        payload: dict[str, Any],
        subject_type: str,
        subject_id: str,
    ) -> dict[str, Any]:
        with self._memory_lock:
            existing = next(
                (
                    item
                    for item in _records(self.store, "rd_collaboration_events").values()
                    if item.get("collaboration_run_id") == run["id"]
                    and item.get("event_key") == f"graph-event:{event_id}"
                ),
                None,
            )
            if existing is not None:
                return deepcopy(existing)
            event = self._event_record(
                run=run,
                event_id=event_id,
                event_type=event_type,
                payload=payload,
                subject_type=subject_type,
                subject_id=subject_id,
            )
            feedback = self._feedback_record(run=run, event=event)
            outbox = self._outbox_record(run=run, event=event)
            audit = self._audit_record(run=run, event=event)
            # Validate all facts before mutating the in-memory test double, then
            # publish them together to mirror the repository transaction.
            if not run.get("product_id") or not run.get("strategy_snapshot_id"):
                raise ValueError("Collaboration run provenance is unavailable")
            _records(self.store, "rd_collaboration_events")[event["id"]] = event
            _records(self.store, "execution_outbox_events")[outbox["id"]] = outbox
            _records(self.store, "audit_events")[audit["id"]] = audit
            _records(self.store, "role_feedback_records")[feedback["id"]] = feedback
            return deepcopy(event)

    def _commit_domain_event_repository(
        self,
        *,
        execute: Any,
        run: dict[str, Any],
        event_id: str,
        event_type: str,
        payload: dict[str, Any],
        subject_type: str,
        subject_id: str,
    ) -> dict[str, Any]:
        event = self._event_record(
            run=run,
            event_id=event_id,
            event_type=event_type,
            payload=payload,
            subject_type=subject_type,
            subject_id=subject_id,
        )
        feedback = self._feedback_record(run=run, event=event)
        outbox = self._outbox_record(run=run, event=event)
        audit = self._audit_record(run=run, event=event)

        def operation(transaction: Any) -> dict[str, Any]:
            persisted_event = transaction.save_collaboration_event(event)
            transaction.save_audit_event(audit)
            transaction.save_outbox_event(outbox)
            transaction.save_role_feedback_once(feedback)
            return {
                "result_type": "rd_collaboration_event",
                "result_id": persisted_event["id"],
                "http_status": 200,
                "response_json": {"event": persisted_event},
            }

        result = execute(
            command_type="rd_collaboration_graph_event",
            aggregate_type="rd_collaboration_run",
            aggregate_id=run["id"],
            idempotency_key=event_id,
            request_hash=_canonical_hash(
                {
                    "event_type": event_type,
                    "payload": payload,
                    "subject_type": subject_type,
                    "subject_id": subject_id,
                }
            ),
            command_record_id=f"graph-command:{run['id']}:{event_id}",
            operation=operation,
        )
        response = result.get("response_json") or {}
        persisted = response.get("event")
        if not isinstance(persisted, dict):
            raise RuntimeError("Collaboration graph command did not return its event")
        return persisted

    def _request_human_takeover(self, run: dict[str, Any]) -> None:
        repository = getattr(self.store, "repository", None)
        if repository is None:
            persisted = _records(self.store, "rd_collaboration_runs").get(str(run["id"]))
            if persisted is not None and persisted.get("status") != "waiting_human":
                decision_id = f"graph-takeover:{run['id']}"
                _records(self.store, "decision_requests")[decision_id] = {
                    "id": decision_id,
                    "brain_app_id": persisted.get("brain_app_id", "rd_brain"),
                    "product_id": persisted.get("product_id"),
                    "subject_type": "rd_collaboration_run",
                    "subject_id": run["id"],
                    "decision_type": "graph_checkpoint_incompatible",
                    "plan_version": int(persisted.get("plan_version") or 0),
                    "options_json": [
                        {
                            "code": "take_over",
                            "outcome": "approve",
                            "subject_transition": "keep_paused",
                            "input_schema": {},
                        }
                    ],
                    "status": "pending",
                    "version": 1,
                    "created_by": persisted.get("created_by", "system"),
                }
                persisted.update(
                    {
                        "status": "waiting_human",
                        "resume_state": persisted.get("status"),
                        "suspended_at": _now(),
                        "suspended_decision_request_id": decision_id,
                        "version": int(persisted.get("version") or 1) + 1,
                    }
                )
            return
        if run.get("status") == "waiting_human":
            return
        if run.get("status") not in {"running", "integrating", "verifying"}:
            raise CheckpointIncompatibleError(
                f"Checkpoint for collaboration run {run['id']} is incompatible and cannot resume"
            )
        execute = getattr(repository, "execute_idempotent_rd_command", None)
        if not callable(execute):
            raise CheckpointIncompatibleError(
                "Checkpoint for collaboration run "
                f"{run['id']} is incompatible; human takeover required"
            )

        decision_id = f"graph-checkpoint-takeover:{run['id']}"
        options = [
            {
                "code": "take_over",
                "outcome": "approve",
                "subject_transition": "keep_paused",
                "input_schema": {},
            }
        ]
        decision = {
            "id": decision_id,
            "brain_app_id": run["brain_app_id"],
            "product_id": run["product_id"],
            "subject_type": "rd_collaboration_run",
            "subject_id": run["id"],
            "decision_type": "graph_checkpoint_incompatible",
            "plan_version": int(run.get("plan_version") or 0),
            "options_json": options,
            "options_hash": _canonical_hash(options),
            "evidence_json": [
                {
                    "kind": "graph_checkpoint",
                    "thread_id": rd_collaboration_thread_id(str(run["id"])),
                    "graph_definition": RD_COLLABORATION_GRAPH_DEFINITION,
                    "required_graph_version": RD_COLLABORATION_GRAPH_VERSION,
                }
            ],
            "recommendation_json": {"action": "human_takeover"},
            "decision_actor_selector": {"roles": ["rd_owner"]},
            "answer_actor_selector": {},
            "answer_schema": {"type": "object", "additionalProperties": False},
            "status": "pending",
            "expires_at": (datetime.now(UTC) + timedelta(days=7)).isoformat(),
            "timeout_policy": "escalate_keep_paused",
            "escalation_target_selector": {"roles": ["rd_owner"]},
            "escalation_level": 0,
            "version": 1,
            "created_by": run["created_by"],
        }

        def operation(transaction: Any) -> dict[str, Any]:
            persisted_decision = transaction.save_decision_request_record(decision)
            paused_run = transaction.suspend_collaboration_run(
                collaboration_run_id=run["id"],
                decision_request_id=persisted_decision["id"],
                expected_version=int(run.get("version") or 1),
            )
            transaction.save_audit_event(
                {
                    "id": f"graph-checkpoint-takeover-audit:{run['id']}",
                    "event_type": "rd_collaboration.graph_checkpoint_incompatible",
                    "actor_id": run["created_by"],
                    "subject_type": "rd_collaboration_run",
                    "subject_id": run["id"],
                    "payload": {"decision_request_id": persisted_decision["id"]},
                }
            )
            return {
                "result_type": "decision_request",
                "result_id": persisted_decision["id"],
                "http_status": 202,
                "response_json": {"decision_request": persisted_decision, "run": paused_run},
            }

        execute(
            command_type="rd_collaboration_graph_checkpoint_incompatible",
            aggregate_type="rd_collaboration_run",
            aggregate_id=run["id"],
            idempotency_key="checkpoint-incompatible",
            request_hash=_canonical_hash(
                {
                    "graph_definition": RD_COLLABORATION_GRAPH_DEFINITION,
                    "graph_version": RD_COLLABORATION_GRAPH_VERSION,
                }
            ),
            command_record_id=f"graph-checkpoint-takeover-command:{run['id']}",
            operation=operation,
        )
