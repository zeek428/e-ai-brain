from __future__ import annotations

# Aggregate modules intentionally share one serialization/transaction vocabulary.
# ruff: noqa: F401
from collections.abc import Callable, Iterable, Sequence
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from psycopg import sql
from psycopg.types.json import Jsonb

from app.core.repositories.rd_collaboration_shared import (
    POLICY_COLUMNS,
    TABLE_COLUMNS,
    RdCollaborationRepositoryError,
    RdCollaborationTransaction,
    RdCollaborationVersionConflictError,
    _adapt,
    _canonical_hash,
    _canonical_scope_operations,
    _response_hash,
    _row_dict,
)


class RdCollaborationScopeWriteMixin:
    def _insert_run(self, cursor: Any, run: dict[str, Any]) -> dict[str, Any]:
        columns = (
            "id",
            "brain_app_id",
            "product_id",
            "product_version_id",
            "strategy_snapshot_id",
            "run_generation",
            "supersedes_run_id",
            "scope_version",
            "plan_version",
            "status",
            "delivery_target",
            "budget_json",
            "graph_definition",
            "graph_version",
            "resume_state",
            "suspended_decision_request_id",
            "suspended_at",
            "completion_reason",
            "started_at",
            "completed_at",
            "version",
            "created_by",
            "created_at",
            "updated_at",
        )
        included = [column for column in columns if column in run]
        cursor.execute(
            sql.SQL(
                "INSERT INTO rd_collaboration_runs ({columns}) VALUES ({values}) "
                "ON CONFLICT (id) DO NOTHING RETURNING *"
            ).format(
                columns=sql.SQL(", ").join(map(sql.Identifier, included)),
                values=sql.SQL(", ").join(sql.Placeholder() for _ in included),
            ),
            tuple(_adapt(run[column], column) for column in included),
        )
        persisted = _row_dict(cursor, cursor.fetchone())
        if persisted is not None:
            return persisted
        cursor.execute("SELECT * FROM rd_collaboration_runs WHERE id = %s", (run["id"],))
        existing = _row_dict(cursor, cursor.fetchone())
        if existing is None:
            raise RuntimeError("collaboration run replay lookup failed")
        for field in (
            "brain_app_id",
            "product_id",
            "product_version_id",
            "strategy_snapshot_id",
            "run_generation",
            "supersedes_run_id",
            "scope_version",
        ):
            if field in run and existing[field] != run[field]:
                raise RdCollaborationRepositoryError(
                    "RD_IDEMPOTENCY_CONFLICT",
                    "run id is already bound to different immutable scope",
                )
        return existing

    def _insert_run_scope(self, cursor: Any, record: dict[str, Any]) -> dict[str, Any]:
        cursor.execute(
            """
            INSERT INTO rd_collaboration_run_requirements (
              id, collaboration_run_id, requirement_id, requirement_revision,
              assessment_id, final_strategy_snapshot_id,
              acceptance_criteria_hash, repository_scope_hash, created_at
            )
            VALUES (
              %s, %s, %s, %s, %s, %s, %s, %s,
              COALESCE(%s::timestamptz, now())
            )
            ON CONFLICT (collaboration_run_id, requirement_id) DO NOTHING
            RETURNING *
            """,
            (
                record["id"],
                record["collaboration_run_id"],
                record["requirement_id"],
                record["requirement_revision"],
                record["assessment_id"],
                record["final_strategy_snapshot_id"],
                record["acceptance_criteria_hash"],
                record["repository_scope_hash"],
                record.get("created_at"),
            ),
        )
        persisted = _row_dict(cursor, cursor.fetchone())
        if persisted is not None:
            return persisted
        cursor.execute(
            """
            SELECT * FROM rd_collaboration_run_requirements
            WHERE collaboration_run_id = %s AND requirement_id = %s
            """,
            (record["collaboration_run_id"], record["requirement_id"]),
        )
        existing = _row_dict(cursor, cursor.fetchone())
        if existing is None:
            raise RuntimeError("run scope replay lookup failed")
        self._assert_immutable_replay(
            existing=existing,
            incoming=record,
            fields=(
                "id",
                "collaboration_run_id",
                "requirement_id",
                "requirement_revision",
                "assessment_id",
                "final_strategy_snapshot_id",
                "acceptance_criteria_hash",
                "repository_scope_hash",
            ),
            message="run scope identity is bound to different immutable provenance",
            collaboration_run_id=record["collaboration_run_id"],
            requirement_id=record["requirement_id"],
        )
        return existing

    def create_collaboration_run_with_exact_scope(
        self,
        *,
        run: dict[str, Any],
        scope_rows: list[dict[str, Any]],
        snapshot: dict[str, Any] | None = None,
        sources: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM product_versions WHERE id = %s FOR UPDATE",
                    (run["product_version_id"],),
                )
                version = _row_dict(cursor, cursor.fetchone())
                if version is None:
                    raise RdCollaborationRepositoryError(
                        "RD_SCOPE_VERSION_CONFLICT",
                        "product version does not exist",
                    )
                if int(version["scope_version"]) != int(run["scope_version"]):
                    raise RdCollaborationRepositoryError(
                        "RD_SCOPE_VERSION_CONFLICT",
                        "scope version is stale",
                        details={"current_scope_version": version["scope_version"]},
                    )
                if snapshot is not None:
                    persisted_snapshot = self._insert_snapshot(cursor, snapshot)
                    for source in sorted(
                        sources or [], key=lambda item: str(item["requirement_id"])
                    ):
                        self._insert_snapshot_source(
                            cursor,
                            {**source, "snapshot_id": persisted_snapshot["id"]},
                        )
                persisted_run = self._insert_run(cursor, run)
                persisted_scope = [
                    self._insert_run_scope(
                        cursor,
                        {**scope, "collaboration_run_id": persisted_run["id"]},
                    )
                    for scope in sorted(
                        scope_rows,
                        key=lambda item: str(item["requirement_id"]),
                    )
                ]
                return {**persisted_run, "run": persisted_run, "scope_rows": persisted_scope}

    def restart_terminal_collaboration_run(
        self,
        *,
        terminal_run_id: str,
        run: dict[str, Any],
        scope_rows: list[dict[str, Any]],
    ) -> dict[str, Any]:
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM product_versions WHERE id = %s FOR UPDATE",
                    (run["product_version_id"],),
                )
                version = _row_dict(cursor, cursor.fetchone())
                cursor.execute(
                    "SELECT * FROM rd_collaboration_runs WHERE id = %s FOR UPDATE",
                    (terminal_run_id,),
                )
                terminal = _row_dict(cursor, cursor.fetchone())
                if (
                    version is None
                    or terminal is None
                    or terminal["product_version_id"] != run["product_version_id"]
                    or terminal["status"] not in {"failed", "cancelled"}
                    or version["status"] not in {"active", "testing"}
                    or int(terminal["run_generation"]) + 1 != int(run["run_generation"])
                    or run.get("supersedes_run_id") != terminal_run_id
                ):
                    raise RdCollaborationRepositoryError(
                        "RD_RUN_RESTART_NOT_ALLOWED",
                        "terminal collaboration run cannot be restarted",
                    )
                cursor.execute(
                    """
                    SELECT max(run_generation),
                           count(*) FILTER (
                             WHERE status NOT IN ('completed', 'failed', 'cancelled')
                           )
                    FROM rd_collaboration_runs
                    WHERE product_version_id = %s
                    """,
                    (run["product_version_id"],),
                )
                generation_state = cursor.fetchone()
                if (
                    generation_state is None
                    or int(generation_state[0] or 0) != int(terminal["run_generation"])
                    or int(generation_state[1]) != 0
                ):
                    raise RdCollaborationRepositoryError(
                        "RD_RUN_RESTART_NOT_ALLOWED",
                        "terminal run is not the latest generation or an active run exists",
                    )
                persisted = self._insert_run(cursor, run)
                for scope in sorted(scope_rows, key=lambda item: str(item["requirement_id"])):
                    self._insert_run_scope(
                        cursor,
                        {**scope, "collaboration_run_id": persisted["id"]},
                    )
                return persisted

    def assign_requirement_to_version_and_increment_scope(
        self,
        *,
        requirement_id: str,
        product_version_id: str,
        expected_scope_version: int,
    ) -> dict[str, Any]:
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM product_versions WHERE id = %s FOR UPDATE",
                    (product_version_id,),
                )
                version = _row_dict(cursor, cursor.fetchone())
                if version is None:
                    raise RdCollaborationRepositoryError(
                        "RD_SCOPE_VERSION_CONFLICT",
                        "product version does not exist",
                    )
                cursor.execute(
                    "SELECT * FROM requirements WHERE id = %s FOR UPDATE",
                    (requirement_id,),
                )
                requirement = _row_dict(cursor, cursor.fetchone())
                if requirement is None or requirement["product_id"] != version["product_id"]:
                    raise RdCollaborationRepositoryError(
                        "RD_SCOPE_CHANGE_INVALID",
                        "requirement does not belong to the product version",
                    )
                current_scope = int(version["scope_version"])
                if requirement.get("version_id") == product_version_id:
                    return {**version, "requirement": requirement, "idempotent_replay": True}
                if current_scope != int(expected_scope_version):
                    raise RdCollaborationRepositoryError(
                        "RD_SCOPE_VERSION_CONFLICT",
                        "scope version is stale",
                        details={
                            "current_scope_version": current_scope,
                            "retryable": False,
                            "next_action": "reload_version_scope",
                        },
                    )
                if version["status"] in {"ready_for_release", "deploying", "released"}:
                    raise self._ready_scope_frozen()
                cursor.execute(
                    """
                    SELECT id, status, suspended_decision_request_id
                    FROM rd_collaboration_runs
                    WHERE product_version_id = %s
                      AND status NOT IN ('completed', 'failed', 'cancelled')
                    ORDER BY run_generation DESC
                    LIMIT 1
                    FOR UPDATE
                    """,
                    (product_version_id,),
                )
                active_run = cursor.fetchone()
                if active_run is not None:
                    details: dict[str, Any] = {
                        "retryable": False,
                        "next_action": "create_scope_change_request",
                    }
                    if active_run[1] == "waiting_human":
                        details.update(
                            {
                                "decision_request_id": active_run[2],
                                "next_action": "resolve_existing_decision",
                            }
                        )
                    raise RdCollaborationRepositoryError(
                        "RD_SCOPE_FROZEN",
                        "product version scope is frozen by an active collaboration run",
                        details=details,
                    )
                if version["status"] != "planning":
                    raise RdCollaborationRepositoryError(
                        "RD_SCOPE_FROZEN",
                        "only a planning product version accepts ordinary scope assignment",
                        details={
                            "retryable": False,
                            "next_action": "create_scope_change_request",
                        },
                    )
                cursor.execute(
                    """
                    UPDATE requirements
                    SET version_id = %s, status = 'planned', updated_at = now()
                    WHERE id = %s
                    RETURNING *
                    """,
                    (product_version_id, requirement_id),
                )
                assigned = _row_dict(cursor, cursor.fetchone())
                cursor.execute(
                    """
                    UPDATE product_versions
                    SET scope_version = scope_version + 1, updated_at = now()
                    WHERE id = %s
                    RETURNING *
                    """,
                    (product_version_id,),
                )
                updated_version = _row_dict(cursor, cursor.fetchone())
                if assigned is None or updated_version is None:
                    raise RuntimeError("scope assignment did not return updated rows")
                return {**updated_version, "requirement": assigned, "idempotent_replay": False}

    @staticmethod
    def _ready_scope_frozen() -> RdCollaborationRepositoryError:
        return RdCollaborationRepositoryError(
            "RD_SCOPE_FROZEN",
            "delivered product version scope must move to a new planning version",
            details={
                "retryable": False,
                "resolution": "new_planning_version",
                "next_action": "create_followup_requirement",
            },
        )

    @staticmethod
    def _validate_scope_operations(operations: list[dict[str, Any]]) -> None:
        _canonical_scope_operations(operations)

    @staticmethod
    def _scope_decision(
        cursor: Any,
        *,
        decision: dict[str, Any],
        request: dict[str, Any],
        require_active: bool,
    ) -> tuple[dict[str, Any], dict[str, str]]:
        invalid = (
            decision.get("brain_app_id", "rd_brain") != "rd_brain"
            or decision.get("product_id") != request.get("product_id")
            or decision.get("subject_type") != "rd_scope_change_request"
            or decision.get("subject_id") != request.get("id")
            or decision.get("decision_type") != "scope_change"
        )
        if require_active:
            invalid = invalid or decision.get("status") != "pending"
            cursor.execute("SELECT now() < %s", (decision.get("expires_at"),))
            invalid = invalid or not bool(cursor.fetchone()[0])
        options = decision.get("options_json") or []
        mapping: dict[str, str] = {}
        for option in options:
            code = str(option.get("code") or "")
            outcome = str(option.get("outcome") or "")
            if code and outcome in {"approve", "reject"} and code not in mapping:
                mapping[code] = outcome
            else:
                invalid = True
        if set(mapping.values()) != {"approve", "reject"} or len(mapping) != 2:
            invalid = True
        if invalid:
            raise RdCollaborationRepositoryError(
                "RD_DECISION_REQUIRED",
                "scope change requires its active unexpired frozen decision",
            )
        return decision, mapping

    def _insert_scope_change_request(
        self,
        cursor: Any,
        request: dict[str, Any],
    ) -> dict[str, Any]:
        columns = (
            "id",
            "product_version_id",
            "request_id",
            "source_run_id",
            "source_run_state",
            "expected_scope_version",
            "expected_run_generation",
            "operations_json",
            "operations_hash",
            "reason",
            "status",
            "decision_request_id",
            "applied_scope_version",
            "requested_by",
            "applied_at",
            "created_at",
            "updated_at",
        )
        included = [column for column in columns if column in request]
        cursor.execute(
            sql.SQL(
                "INSERT INTO rd_scope_change_requests ({columns}) VALUES ({values}) RETURNING *"
            ).format(
                columns=sql.SQL(", ").join(map(sql.Identifier, included)),
                values=sql.SQL(", ").join(sql.Placeholder() for _ in included),
            ),
            tuple(_adapt(request[column], column) for column in included),
        )
        persisted = _row_dict(cursor, cursor.fetchone())
        if persisted is None:
            raise RuntimeError("scope change request persistence did not return a row")
        return persisted

    def _insert_scope_change_operation(
        self,
        cursor: Any,
        record: dict[str, Any],
    ) -> dict[str, Any]:
        columns = (
            "id",
            "scope_change_request_id",
            "position",
            "op",
            "requirement_id",
            "requirement_revision",
            "assessment_id",
            "final_strategy_snapshot_id",
            "repository_id",
            "branch_config_version",
            "base_commit_sha",
            "destination",
            "created_at",
        )
        included = [column for column in columns if column in record]
        cursor.execute(
            sql.SQL(
                "INSERT INTO rd_scope_change_request_operations ({columns}) "
                "VALUES ({values}) RETURNING *"
            ).format(
                columns=sql.SQL(", ").join(map(sql.Identifier, included)),
                values=sql.SQL(", ").join(sql.Placeholder() for _ in included),
            ),
            tuple(_adapt(record[column], column) for column in included),
        )
        persisted = _row_dict(cursor, cursor.fetchone())
        if persisted is None:
            raise RuntimeError("scope change operation persistence did not return a row")
        return persisted

    def create_scope_change_request(
        self,
        *,
        request: dict[str, Any],
        operations: list[dict[str, Any]],
        decision_request: dict[str, Any],
    ) -> dict[str, Any]:
        canonical_operations = _canonical_scope_operations(operations)
        operations_hash = _canonical_hash(canonical_operations)
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM product_versions WHERE id = %s FOR UPDATE",
                    (request["product_version_id"],),
                )
                version = _row_dict(cursor, cursor.fetchone())
                if version is None:
                    raise RdCollaborationRepositoryError(
                        "RD_SCOPE_VERSION_CONFLICT",
                        "product version does not exist",
                    )
                cursor.execute(
                    "SELECT * FROM rd_collaboration_runs WHERE id = %s FOR UPDATE",
                    (request["source_run_id"],),
                )
                run = _row_dict(cursor, cursor.fetchone())
                if run is None or run["product_version_id"] != request["product_version_id"]:
                    raise RdCollaborationRepositoryError(
                        "RD_RUN_GENERATION_CONFLICT",
                        "source collaboration run does not belong to the product version",
                    )
                frozen_request = {
                    **request,
                    "product_id": run["product_id"],
                    "operations_json": canonical_operations,
                    "operations_hash": operations_hash,
                }
                cursor.execute(
                    """
                    SELECT * FROM rd_scope_change_requests
                    WHERE product_version_id = %s AND request_id = %s
                    FOR UPDATE
                    """,
                    (request["product_version_id"], request["request_id"]),
                )
                replay = _row_dict(cursor, cursor.fetchone())
                if replay is not None:
                    if replay["operations_hash"] != operations_hash:
                        raise RdCollaborationRepositoryError(
                            "RD_IDEMPOTENCY_CONFLICT",
                            "scope request id is already bound to different operations",
                        )
                    return replay
                if version["status"] in {"ready_for_release", "deploying", "released"}:
                    raise self._ready_scope_frozen()
                if (
                    run["status"] == "completed"
                    and run.get("delivery_target") == "ready_for_release"
                ):
                    raise self._ready_scope_frozen()
                if int(version["scope_version"]) != int(request["expected_scope_version"]):
                    raise RdCollaborationRepositoryError(
                        "RD_SCOPE_VERSION_CONFLICT",
                        "scope version is stale",
                        details={"current_scope_version": version["scope_version"]},
                    )
                cursor.execute(
                    """
                    SELECT COALESCE(max(run_generation), 0)
                    FROM rd_collaboration_runs
                    WHERE product_version_id = %s
                    """,
                    (request["product_version_id"],),
                )
                current_generation = int(cursor.fetchone()[0])
                if int(run["run_generation"]) != int(
                    request["expected_run_generation"]
                ) or current_generation != int(request["expected_run_generation"]):
                    raise RdCollaborationRepositoryError(
                        "RD_RUN_GENERATION_CONFLICT",
                        "collaboration run generation is stale",
                        details={"current_run_generation": current_generation},
                    )
                if run["status"] == "waiting_human":
                    raise RdCollaborationRepositoryError(
                        "RD_SCOPE_FROZEN",
                        "collaboration run is already paused by another decision",
                        details={
                            "retryable": False,
                            "decision_request_id": run["suspended_decision_request_id"],
                            "next_action": "resolve_existing_decision",
                        },
                    )
                cursor.execute(
                    """
                    SELECT id, decision_request_id
                    FROM rd_scope_change_requests
                    WHERE product_version_id = %s AND status = 'pending_decision'
                    LIMIT 1
                    FOR UPDATE
                    """,
                    (request["product_version_id"],),
                )
                pending = cursor.fetchone()
                if pending is not None:
                    raise RdCollaborationRepositoryError(
                        "RD_SCOPE_FROZEN",
                        "another scope change decision is already pending",
                        details={
                            "retryable": False,
                            "scope_change_request_id": pending[0],
                            "decision_request_id": pending[1],
                            "next_action": "resolve_existing_decision",
                        },
                    )
                frozen_decision = {
                    **decision_request,
                    "options_hash": _canonical_hash(decision_request.get("options_json") or []),
                }
                self._scope_decision(
                    cursor,
                    decision=frozen_decision,
                    request=frozen_request,
                    require_active=True,
                )
                if frozen_request.get("decision_request_id") != frozen_decision.get("id"):
                    raise RdCollaborationRepositoryError(
                        "RD_DECISION_REQUIRED",
                        "scope request decision id does not match the frozen decision",
                    )
                persisted_decision = self._insert_decision_request(cursor, frozen_decision)
                persisted_request = self._insert_scope_change_request(
                    cursor,
                    {
                        **frozen_request,
                        "source_run_state": run["status"],
                        "status": "pending_decision",
                        "decision_request_id": persisted_decision["id"],
                    },
                )
                for index, operation in enumerate(operations):
                    canonical = canonical_operations[index]
                    self._insert_scope_change_operation(
                        cursor,
                        {
                            "id": operation.get("id") or f"rd-scope-operation-{uuid4().hex}",
                            **canonical,
                            "scope_change_request_id": persisted_request["id"],
                        },
                    )
                if run["status"] in {"running", "integrating", "verifying"}:
                    cursor.execute(
                        """
                        UPDATE rd_collaboration_runs
                        SET status = 'waiting_human', resume_state = status,
                            suspended_decision_request_id = %s,
                            suspended_at = now(), version = version + 1,
                            updated_at = now()
                        WHERE id = %s
                        """,
                        (persisted_decision["id"], run["id"]),
                    )
                return persisted_request

    def _scope_change_result(
        self,
        cursor: Any,
        request: dict[str, Any],
    ) -> dict[str, Any]:
        cursor.execute(
            "SELECT * FROM product_versions WHERE id = %s",
            (request["product_version_id"],),
        )
        version = _row_dict(cursor, cursor.fetchone())
        cursor.execute(
            "SELECT * FROM rd_collaboration_runs WHERE id = %s",
            (request["source_run_id"],),
        )
        run = _row_dict(cursor, cursor.fetchone())
        cursor.execute(
            "SELECT * FROM decision_requests WHERE id = %s",
            (request["decision_request_id"],),
        )
        decision = _row_dict(cursor, cursor.fetchone())
        return {
            "scope_change_request": request,
            "product_version": version,
            "run": run,
            "decision_request": decision,
            "terminal_run_id": run["id"] if request["status"] == "applied" else None,
            "restart_required": request["status"] == "applied",
        }

    def _apply_scope_operations(
        self,
        cursor: Any,
        *,
        product_id: str,
        product_version_id: str,
        operations: Iterable[dict[str, Any]],
    ) -> None:
        for operation in operations:
            kind = operation["op"]
            if kind in {"add_requirement", "replace_requirement_snapshot"}:
                cursor.execute(
                    """
                    SELECT assessment.id
                    FROM requirement_assessments assessment
                    JOIN requirements requirement
                      ON requirement.id = assessment.requirement_id
                    WHERE assessment.id = %s
                      AND assessment.requirement_id = %s
                      AND assessment.requirement_revision = %s
                      AND assessment.final_strategy_snapshot_id = %s
                      AND assessment.status = 'accepted'
                      AND requirement.product_id = %s
                    FOR KEY SHARE
                    """,
                    (
                        operation["assessment_id"],
                        operation["requirement_id"],
                        operation["requirement_revision"],
                        operation["final_strategy_snapshot_id"],
                        product_id,
                    ),
                )
                if cursor.fetchone() is None:
                    raise RdCollaborationRepositoryError(
                        "RD_SCOPE_CHANGE_INVALID",
                        "scope operation does not reference the accepted assessment provenance",
                        details={"operation_index": operation["position"]},
                    )
                if kind == "add_requirement":
                    cursor.execute(
                        """
                        UPDATE requirements
                        SET version_id = %s, status = 'planned', updated_at = now()
                        WHERE id = %s
                          AND product_id = %s
                          AND (version_id IS NULL OR version_id = %s)
                        RETURNING id
                        """,
                        (
                            product_version_id,
                            operation["requirement_id"],
                            product_id,
                            product_version_id,
                        ),
                    )
                    if cursor.fetchone() is None:
                        raise RdCollaborationRepositoryError(
                            "RD_SCOPE_CHANGE_INVALID",
                            "requirement cannot be added to this product version",
                            details={"operation_index": operation["position"]},
                        )
            elif kind == "remove_requirement":
                cursor.execute(
                    """
                    UPDATE requirements
                    SET version_id = NULL, status = 'approved', updated_at = now()
                    WHERE id = %s AND product_id = %s AND version_id = %s
                    RETURNING id
                    """,
                    (operation["requirement_id"], product_id, product_version_id),
                )
                if cursor.fetchone() is None:
                    raise RdCollaborationRepositoryError(
                        "RD_SCOPE_CHANGE_INVALID",
                        "requirement is not in the current product version",
                        details={"operation_index": operation["position"]},
                    )
            elif kind == "update_repository_baseline":
                cursor.execute(
                    """
                    SELECT branch.id, branch.branch_config_version
                    FROM product_version_branch_configs branch
                    JOIN product_git_repositories repository
                      ON repository.id = branch.repository_id
                    WHERE branch.version_id = %s
                      AND branch.repository_id = %s
                      AND branch.product_id = %s
                      AND repository.product_id = %s
                    FOR UPDATE
                    """,
                    (
                        product_version_id,
                        operation["repository_id"],
                        product_id,
                        product_id,
                    ),
                )
                branch = cursor.fetchone()
                if branch is None or int(branch[1]) != int(operation["branch_config_version"]):
                    raise RdCollaborationRepositoryError(
                        "RD_SCOPE_CHANGE_INVALID",
                        "repository baseline branch configuration version is stale",
                        details={"operation_index": operation["position"]},
                    )
                cursor.execute(
                    """
                    UPDATE product_version_branch_configs
                    SET base_commit_sha = %s,
                        branch_config_version = branch_config_version + 1,
                        updated_at = now()
                    WHERE id = %s AND branch_config_version = %s
                    """,
                    (operation["base_commit_sha"], branch[0], operation["branch_config_version"]),
                )

    def apply_scope_change_bundle(
        self,
        *,
        scope_change_request_id: str,
        decision: str,
        decided_by: str,
        expected_decision_version: int,
        cancellation_outbox_events: list[dict[str, Any]] | None = None,
        failure_injection: Callable[[str], None] | None = None,
    ) -> dict[str, Any]:
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM rd_scope_change_requests WHERE id = %s",
                    (scope_change_request_id,),
                )
                identity = _row_dict(cursor, cursor.fetchone())
                if identity is None:
                    raise RdCollaborationRepositoryError(
                        "RD_SCOPE_CHANGE_INVALID",
                        "scope change request does not exist",
                    )
                # Global lock order for scope transactions: version -> run -> request -> decision.
                cursor.execute(
                    "SELECT * FROM product_versions WHERE id = %s FOR UPDATE",
                    (identity["product_version_id"],),
                )
                version = _row_dict(cursor, cursor.fetchone())
                cursor.execute(
                    "SELECT * FROM rd_collaboration_runs WHERE id = %s FOR UPDATE",
                    (identity["source_run_id"],),
                )
                run = _row_dict(cursor, cursor.fetchone())
                cursor.execute(
                    "SELECT * FROM rd_scope_change_requests WHERE id = %s FOR UPDATE",
                    (scope_change_request_id,),
                )
                request = _row_dict(cursor, cursor.fetchone())
                if request is None or version is None or run is None:
                    raise RdCollaborationRepositoryError(
                        "RD_SCOPE_CHANGE_INVALID",
                        "scope change aggregate is incomplete",
                    )
                if request["status"] in {"applied", "rejected"}:
                    return self._scope_change_result(cursor, request)
                cursor.execute(
                    "SELECT * FROM decision_requests WHERE id = %s FOR UPDATE",
                    (request["decision_request_id"],),
                )
                decision_row = _row_dict(cursor, cursor.fetchone())
                if decision_row is None:
                    raise RdCollaborationRepositoryError(
                        "RD_DECISION_REQUIRED",
                        "scope change decision request is missing",
                    )
                _, option_mapping = self._scope_decision(
                    cursor,
                    decision=decision_row,
                    request={**request, "product_id": run["product_id"]},
                    require_active=True,
                )
                if _canonical_hash(decision_row.get("options_json") or []) != decision_row.get(
                    "options_hash"
                ):
                    raise self._idempotency_conflict(
                        "scope decision options no longer match their frozen hash",
                        decision_request_id=decision_row["id"],
                    )
                outcome = option_mapping.get(decision)
                if outcome is None:
                    raise RdCollaborationRepositoryError(
                        "RD_DECISION_INPUT_INVALID",
                        "selected option is not in the frozen scope decision mapping",
                        details={"field": "selected_option"},
                    )
                if int(decision_row["version"]) != int(expected_decision_version):
                    raise RdCollaborationVersionConflictError(int(decision_row["version"]))
                if int(version["scope_version"]) != int(request["expected_scope_version"]) or int(
                    run["run_generation"]
                ) != int(request["expected_run_generation"]):
                    raise RdCollaborationRepositoryError(
                        "RD_SCOPE_VERSION_CONFLICT",
                        "scope or generation changed before the decision was applied",
                        details={
                            "current_scope_version": version["scope_version"],
                            "current_run_generation": run["run_generation"],
                        },
                    )
                now = datetime.now(UTC)
                if outcome == "reject":
                    cursor.execute(
                        """
                        UPDATE decision_requests
                        SET status = 'rejected', selected_option_code = %s,
                            decided_by = %s, decided_at = now(),
                            version = version + 1, updated_at = now()
                        WHERE id = %s
                        """,
                        (decision, decided_by, decision_row["id"]),
                    )
                    cursor.execute(
                        """
                        UPDATE rd_scope_change_requests
                        SET status = 'rejected', updated_at = now()
                        WHERE id = %s
                        RETURNING *
                        """,
                        (request["id"],),
                    )
                    rejected = _row_dict(cursor, cursor.fetchone())
                    if (
                        run["status"] == "waiting_human"
                        and run["suspended_decision_request_id"] == decision_row["id"]
                    ):
                        cursor.execute(
                            """
                            UPDATE rd_collaboration_runs
                            SET status = resume_state, resume_state = NULL,
                                suspended_decision_request_id = NULL,
                                suspended_at = NULL, version = version + 1,
                                updated_at = now()
                            WHERE id = %s
                            """,
                            (run["id"],),
                        )
                    if rejected is None:
                        raise RuntimeError("scope rejection did not return a row")
                    transaction = RdCollaborationTransaction(self, cursor)
                    transaction.save_collaboration_event(
                        {
                            "id": f"event:scope-change:{request['id']}:rejected",
                            "collaboration_run_id": run["id"],
                            "event_type": "scope_change.rejected",
                            "event_key": f"scope-change:{request['id']}:rejected",
                            "subject_type": "rd_scope_change_request",
                            "subject_id": request["id"],
                            "payload_json": {
                                "scope_version": version["scope_version"],
                                "run_generation": run["run_generation"],
                            },
                        }
                    )
                    transaction.save_audit_event(
                        {
                            "id": f"audit:scope-change:{request['id']}:rejected",
                            "event_type": "rd_scope_change.rejected",
                            "actor_id": decided_by,
                            "subject_type": "rd_scope_change_request",
                            "subject_id": request["id"],
                            "payload": {
                                "product_version_id": request["product_version_id"],
                                "source_run_id": run["id"],
                            },
                        }
                    )
                    if failure_injection is not None:
                        failure_injection("after_mandatory_effects")
                    return self._scope_change_result(cursor, rejected)

                cursor.execute(
                    """
                    SELECT * FROM rd_scope_change_request_operations
                    WHERE scope_change_request_id = %s
                    ORDER BY position
                    FOR KEY SHARE
                    """,
                    (request["id"],),
                )
                operations = [
                    operation
                    for row in cursor.fetchall()
                    if (operation := _row_dict(cursor, row)) is not None
                ]
                canonical_operations = _canonical_scope_operations(operations)
                if canonical_operations != request.get("operations_json") or _canonical_hash(
                    canonical_operations
                ) != request.get("operations_hash"):
                    raise self._idempotency_conflict(
                        "scope operations no longer match their frozen representation",
                        scope_change_request_id=request["id"],
                    )
                cursor.execute(
                    """
                    SELECT id FROM rd_work_items
                    WHERE collaboration_run_id = %s
                    ORDER BY id
                    FOR UPDATE
                    """,
                    (run["id"],),
                )
                work_item_ids = [str(row[0]) for row in cursor.fetchall()]
                cursor.execute(
                    """
                    SELECT attempt.id
                    FROM rd_work_item_attempts attempt
                    JOIN rd_work_items item ON item.id = attempt.work_item_id
                    WHERE item.collaboration_run_id = %s
                    ORDER BY attempt.id
                    FOR UPDATE OF attempt
                    """,
                    (run["id"],),
                )
                attempt_ids = [str(row[0]) for row in cursor.fetchall()]
                cursor.execute(
                    """
                    SELECT id FROM ai_tasks
                    WHERE collaboration_run_id = %s
                    ORDER BY id
                    FOR UPDATE
                    """,
                    (run["id"],),
                )
                task_ids = [str(row[0]) for row in cursor.fetchall()]
                aggregate_ids = [str(run["id"]), *work_item_ids, *attempt_ids, *task_ids]
                cursor.execute(
                    """
                    UPDATE rd_command_replay_secrets secret
                    SET secret_ciphertext = NULL, scrubbed_at = COALESCE(scrubbed_at, now()),
                        updated_at = now()
                    FROM rd_command_idempotency_records command
                    WHERE secret.command_record_id = command.id
                      AND secret.secret_ciphertext IS NOT NULL
                      AND (command.aggregate_id = ANY(%s) OR command.result_id = ANY(%s))
                    """,
                    (aggregate_ids, aggregate_ids),
                )
                cursor.execute(
                    """
                    UPDATE rd_work_item_attempts attempt
                    SET status = 'cancelled', completed_at = COALESCE(completed_at, now()),
                        updated_at = now()
                    FROM rd_work_items item
                    WHERE attempt.work_item_id = item.id
                      AND item.collaboration_run_id = %s
                      AND attempt.status NOT IN ('completed', 'failed', 'cancelled', 'expired')
                    """,
                    (run["id"],),
                )
                cursor.execute(
                    """
                    UPDATE rd_work_items
                    SET status = 'cancelled', lease_owner = NULL, lease_expires_at = NULL,
                        resume_state = NULL, suspended_attempt_id = NULL,
                        suspended_decision_request_id = NULL, suspended_at = NULL,
                        version = version + 1, updated_at = now()
                    WHERE collaboration_run_id = %s
                      AND status NOT IN ('completed', 'failed', 'cancelled')
                    """,
                    (run["id"],),
                )
                cursor.execute(
                    """
                    UPDATE human_reviews review
                    SET status = 'cancelled', decision_reason = 'scope_change',
                        decided_by = %s, decided_at = now(), updated_at = now()
                    FROM ai_tasks task
                    WHERE review.ai_task_id = task.id
                      AND task.collaboration_run_id = %s
                      AND review.status = 'pending'
                    """,
                    (decided_by, run["id"]),
                )
                cursor.execute(
                    """
                    UPDATE ai_tasks
                    SET status = 'cancelled', error_code = 'RD_SCOPE_FROZEN',
                        error_message = 'cancelled by approved scope change',
                        updated_at = now()
                    WHERE collaboration_run_id = %s
                      AND status NOT IN ('completed', 'failed', 'cancelled')
                    """,
                    (run["id"],),
                )
                cursor.execute(
                    """
                    UPDATE execution_outbox_events
                    SET status = 'cancelled', lease_owner = NULL, lease_until = NULL,
                        updated_at = now()
                    WHERE aggregate_id = ANY(%s)
                      AND status IN ('pending', 'failed')
                    """,
                    (aggregate_ids,),
                )
                transaction = RdCollaborationTransaction(self, cursor)
                cursor.execute(
                    """
                    SELECT * FROM execution_outbox_events
                    WHERE aggregate_id = ANY(%s)
                      AND status IN ('processing', 'completed', 'dead_letter')
                    ORDER BY id
                    FOR UPDATE
                    """,
                    (aggregate_ids,),
                )
                for row in cursor.fetchall():
                    source_outbox = _row_dict(cursor, row)
                    if source_outbox is None:
                        continue
                    reconciliation_id = (
                        f"outbox:scope-change:{request['id']}:reconcile:{source_outbox['id']}"
                    )
                    transaction.save_outbox_event(
                        {
                            "id": reconciliation_id,
                            "aggregate_type": source_outbox["aggregate_type"],
                            "aggregate_id": source_outbox["aggregate_id"],
                            "event_type": "rd.scope_change.reconcile_cancellation",
                            "idempotency_key": (
                                f"scope-change:{request['id']}:reconcile:{source_outbox['id']}"
                            ),
                            "payload_json": {
                                "scope_change_request_id": request["id"],
                                "source_outbox_id": source_outbox["id"],
                                "source_status": source_outbox["status"],
                            },
                        }
                    )
                transaction.save_outbox_event(
                    {
                        "id": f"outbox:scope-change:{request['id']}:cancel-generation",
                        "aggregate_type": "rd_collaboration_run",
                        "aggregate_id": run["id"],
                        "event_type": "rd.scope_change.cancel_generation",
                        "idempotency_key": f"scope-change:{request['id']}:cancel-generation",
                        "payload_json": {
                            "scope_change_request_id": request["id"],
                            "run_generation": run["run_generation"],
                            "aggregate_ids": aggregate_ids,
                        },
                    }
                )
                for outbox in cancellation_outbox_events or []:
                    transaction.save_outbox_event(outbox)
                cursor.execute(
                    """
                    UPDATE rd_collaboration_runs
                    SET status = 'cancelled', completion_reason = 'scope_change',
                        completed_at = COALESCE(completed_at, now()),
                        resume_state = NULL, suspended_decision_request_id = NULL,
                        suspended_at = NULL, version = version + 1, updated_at = now()
                    WHERE id = %s
                      AND status NOT IN ('completed', 'failed', 'cancelled')
                    """,
                    (run["id"],),
                )
                self._apply_scope_operations(
                    cursor,
                    product_id=run["product_id"],
                    product_version_id=run["product_version_id"],
                    operations=canonical_operations,
                )
                cursor.execute(
                    """
                    UPDATE product_versions
                    SET scope_version = scope_version + 1, updated_at = now()
                    WHERE id = %s
                    RETURNING scope_version
                    """,
                    (version["id"],),
                )
                applied_scope_version = int(cursor.fetchone()[0])
                cursor.execute(
                    """
                    UPDATE decision_requests
                    SET status = 'approved', selected_option_code = %s,
                        decided_by = %s, decided_at = now(),
                        version = version + 1, updated_at = now()
                    WHERE id = %s
                    """,
                    (decision, decided_by, decision_row["id"]),
                )
                cursor.execute(
                    """
                    UPDATE rd_scope_change_requests
                    SET status = 'applied', applied_scope_version = %s,
                        applied_at = %s, updated_at = now()
                    WHERE id = %s
                    RETURNING *
                    """,
                    (applied_scope_version, now, request["id"]),
                )
                applied = _row_dict(cursor, cursor.fetchone())
                if applied is None:
                    raise RuntimeError("scope approval did not return a row")
                transaction.save_collaboration_event(
                    {
                        "id": f"event:scope-change:{request['id']}:applied",
                        "collaboration_run_id": run["id"],
                        "event_type": "scope_change.applied",
                        "event_key": f"scope-change:{request['id']}:applied",
                        "subject_type": "rd_scope_change_request",
                        "subject_id": request["id"],
                        "payload_json": {
                            "applied_scope_version": applied_scope_version,
                            "run_generation": run["run_generation"],
                        },
                    }
                )
                transaction.save_audit_event(
                    {
                        "id": f"audit:scope-change:{request['id']}:applied",
                        "event_type": "rd_scope_change.applied",
                        "actor_id": decided_by,
                        "subject_type": "rd_scope_change_request",
                        "subject_id": request["id"],
                        "payload": {
                            "product_version_id": request["product_version_id"],
                            "source_run_id": run["id"],
                            "applied_scope_version": applied_scope_version,
                        },
                    }
                )
                if failure_injection is not None:
                    failure_injection("after_mandatory_effects")
                return self._scope_change_result(cursor, applied)

    def execute_idempotent_rd_command(
        self,
        *,
        command_type: str,
        aggregate_type: str,
        aggregate_id: str,
        idempotency_key: str,
        request_hash: str,
        operation: Callable[[Any], dict[str, Any]],
        command_record_id: str | None = None,
        failure_injection: Callable[[str], None] | None = None,
    ) -> dict[str, Any]:
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT pg_advisory_xact_lock(hashtext(%s), hashtext(%s))",
                    (
                        f"{command_type}:{aggregate_type}:{aggregate_id}",
                        idempotency_key,
                    ),
                )
                cursor.execute(
                    """
                    SELECT * FROM rd_command_idempotency_records
                    WHERE command_type = %s AND aggregate_type = %s
                      AND aggregate_id = %s AND idempotency_key = %s
                    """,
                    (command_type, aggregate_type, aggregate_id, idempotency_key),
                )
                existing = _row_dict(cursor, cursor.fetchone())
                if existing is not None:
                    if existing["request_hash"] != request_hash:
                        raise RdCollaborationRepositoryError(
                            "RD_IDEMPOTENCY_CONFLICT",
                            "idempotency key is already bound to a different request hash",
                        )
                    if (
                        _response_hash(deepcopy(existing["response_json"]))
                        != existing["response_hash"]
                    ):
                        raise self._idempotency_conflict(
                            "stored command response does not match its server hash",
                            command_record_id=existing["id"],
                        )
                    return {
                        "command_record": existing,
                        "http_status": existing["http_status"],
                        "response_json": deepcopy(existing["response_json"]),
                        "idempotent_replay": True,
                    }
                transaction = RdCollaborationTransaction(self, cursor)
                result = operation(transaction)
                if failure_injection is not None:
                    failure_injection("after_domain")
                response = deepcopy(result["response_json"])
                response_hash = _response_hash(response)
                record_id = command_record_id or f"rd-command-{uuid4().hex}"
                cursor.execute(
                    """
                    INSERT INTO rd_command_idempotency_records (
                      id, command_type, aggregate_type, aggregate_id,
                      idempotency_key, request_hash, result_type, result_id,
                      http_status, response_hash, response_json, created_at
                    )
                    VALUES (
                      %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                      COALESCE(%s::timestamptz, now())
                    )
                    RETURNING *
                    """,
                    (
                        record_id,
                        command_type,
                        aggregate_type,
                        aggregate_id,
                        idempotency_key,
                        request_hash,
                        result["result_type"],
                        result["result_id"],
                        int(result["http_status"]),
                        response_hash,
                        Jsonb(response),
                        result.get("created_at"),
                    ),
                )
                persisted = _row_dict(cursor, cursor.fetchone())
                if persisted is None:
                    raise RuntimeError("command idempotency record was not persisted")
                if failure_injection is not None:
                    failure_injection("after_response")
                replay_secret = result.get("claim_replay_secret")
                if replay_secret is not None:
                    self._insert_claim_replay_secret(
                        cursor,
                        {**replay_secret, "command_record_id": record_id},
                    )
                if failure_injection is not None:
                    failure_injection("after_secret")
                return {
                    "command_record": persisted,
                    "http_status": persisted["http_status"],
                    "response_json": response,
                    "idempotent_replay": False,
                }

    def _insert_claim_replay_secret(
        self,
        cursor: Any,
        secret: dict[str, Any],
    ) -> dict[str, Any]:
        cursor.execute(
            """
            INSERT INTO rd_command_replay_secrets (
              id, command_record_id, secret_ciphertext, key_id,
              expires_at, scrubbed_at, created_at, updated_at
            )
            VALUES (
              %s, %s, %s, %s, %s, %s,
              COALESCE(%s::timestamptz, now()),
              COALESCE(%s::timestamptz, now())
            )
            ON CONFLICT (command_record_id) DO NOTHING
            RETURNING *
            """,
            (
                secret["id"],
                secret["command_record_id"],
                secret.get("secret_ciphertext"),
                secret["key_id"],
                secret["expires_at"],
                secret.get("scrubbed_at"),
                secret.get("created_at"),
                secret.get("updated_at") or secret.get("created_at"),
            ),
        )
        persisted = _row_dict(cursor, cursor.fetchone())
        if persisted is not None:
            return persisted
        cursor.execute(
            "SELECT * FROM rd_command_replay_secrets WHERE command_record_id = %s",
            (secret["command_record_id"],),
        )
        existing = _row_dict(cursor, cursor.fetchone())
        if existing is None:
            raise RuntimeError("claim replay secret lookup failed")
        for field in ("id", "secret_ciphertext", "key_id", "expires_at"):
            if existing[field] != secret.get(field):
                raise self._idempotency_conflict(
                    "claim replay secret is bound to different provenance",
                    command_record_id=secret["command_record_id"],
                    field=field,
                )
        return existing

    def save_and_scrub_claim_replay_secret(
        self,
        *,
        secret: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                persisted: dict[str, Any] | None = None
                if secret is not None:
                    persisted = self._insert_claim_replay_secret(cursor, secret)
                cursor.execute("SELECT scrub_expired_rd_command_replay_secrets()")
                scrubbed_count = int(cursor.fetchone()[0])
                return {"secret": persisted, "scrubbed_count": scrubbed_count}
