import json

from fastapi.testclient import TestClient

import app.api.routers.assistant as assistant_router
import app.main as main
import app.services.git_review as git_review_service
import app.services.model_gateway as model_gateway_service
from app.core.persistence import PersistentMemoryStore, PostgresRuntimeStore
from app.core.store import MemoryStore
from app.core.users import MemoryUserRepository
from app.main import app

client = TestClient(app)


class FakeSnapshotRepository:
    def __init__(self) -> None:
        self.payload: dict | None = None
        self.product_config_payload: dict | None = None
        self.requirements_payload: dict | None = None
        self.ai_tasks_payload: dict | None = None
        self.workflow_runtime_payload: dict | None = None
        self.knowledge_payload: dict | None = None
        self.audit_events_payload: dict | None = None
        self.bugs_payload: dict | None = None
        self.model_gateway_payload: dict | None = None
        self.assistant_chat_payload: dict | None = None
        self.gitlab_review_payload: dict | None = None
        self.mock_writebacks_payload: dict | None = None
        self.gitlab_daily_code_metrics_payload: dict | None = None
        self.jenkins_release_records_payload: dict | None = None
        self.online_log_metrics_payload: dict | None = None
        self.user_usage_metrics_payload: dict | None = None
        self.user_feedback_payload: dict | None = None
        self.iteration_planning_payload: dict | None = None
        self.collector_runs_payload: dict | None = None
        self.pending_attribution_payload: dict | None = None
        self.lifecycle_context_payload: dict | None = None
        self.dashboard_payload: dict | None = None
        self.id_counters: dict[str, int] = {}
        self.product_config_direct_writes: list[str] = []
        self.requirement_direct_writes: list[str] = []
        self.ai_task_direct_writes: list[str] = []
        self.workflow_direct_writes: list[str] = []
        self.task_state_direct_writes: list[str] = []
        self.task_workflow_source_row_reads = 0
        self.dashboard_source_row_reads = 0
        self.dashboard_snapshot_direct_writes: list[str] = []
        self.lifecycle_source_row_reads = 0

    def load(self) -> dict | None:
        return self.payload

    def _max_existing_id(self, prefix: str) -> int:
        max_value = self.id_counters.get(prefix, 0)
        expected_prefix = f"{prefix}_"

        def visit(value: object) -> None:
            nonlocal max_value
            if isinstance(value, dict):
                for key, item in value.items():
                    if isinstance(key, str) and key.startswith(expected_prefix):
                        suffix = key.removeprefix(expected_prefix)
                        if suffix.isdigit():
                            max_value = max(max_value, int(suffix))
                    if key == "id" and isinstance(item, str) and item.startswith(expected_prefix):
                        suffix = item.removeprefix(expected_prefix)
                        if suffix.isdigit():
                            max_value = max(max_value, int(suffix))
                    visit(item)
            elif isinstance(value, list):
                for item in value:
                    visit(item)

        for name, payload in self.__dict__.items():
            if name in {"id_counters", "payload"}:
                continue
            visit(payload)
        return max_value

    def next_id(self, prefix: str) -> str:
        self.id_counters[prefix] = self._max_existing_id(prefix) + 1
        return f"{prefix}_{self.id_counters[prefix]:03d}"

    def save(self, payload: dict) -> None:
        self.payload = payload

    def load_product_config(self) -> dict | None:
        return self.product_config_payload

    def save_product_config(self, payload: dict) -> None:
        self.product_config_payload = payload

    def _product_config_collection(self, collection_name: str) -> dict:
        payload = self.product_config_payload or {}
        return payload.get(collection_name, {})

    def list_products(self, *, active_only: bool = False) -> list[dict]:
        products = sorted(
            (dict(item) for item in self._product_config_collection("products").values()),
            key=lambda item: (item.get("display_order", 0), item["code"]),
        )
        return [item for item in products if not active_only or item.get("status") == "active"]

    def get_product(self, product_id: str) -> dict | None:
        product = self._product_config_collection("products").get(product_id)
        return dict(product) if product is not None else None

    def list_product_versions(
        self,
        product_id: str,
        *,
        active_only: bool = False,
    ) -> list[dict]:
        versions = sorted(
            (
                dict(item)
                for item in self._product_config_collection("product_versions").values()
                if item.get("product_id") == product_id
            ),
            key=lambda item: item["code"],
        )
        return [item for item in versions if not active_only or item.get("status") == "active"]

    def list_product_modules(
        self,
        product_id: str,
        *,
        active_only: bool = False,
    ) -> list[dict]:
        modules = sorted(
            (
                dict(item)
                for item in self._product_config_collection("product_modules").values()
                if item.get("product_id") == product_id
            ),
            key=lambda item: (item.get("display_order", 0), item["code"]),
        )
        return [item for item in modules if not active_only or item.get("status") == "active"]

    def list_product_git_repositories(
        self,
        product_id: str,
        *,
        active_only: bool = False,
    ) -> list[dict]:
        repositories = sorted(
            (
                dict(item)
                for item in self._product_config_collection("product_git_repositories").values()
                if item.get("product_id") == product_id
            ),
            key=lambda item: item["name"],
        )
        return [
            item
            for item in repositories
            if not active_only or item.get("status") == "active"
        ]

    def list_related_systems(
        self,
        *,
        active_only: bool = False,
        product_id: str | None = None,
    ) -> list[dict]:
        systems = sorted(
            (
                dict(item)
                for item in self._product_config_collection("related_systems").values()
                if product_id is None or item.get("product_id") == product_id
            ),
            key=lambda item: (item.get("display_order", 0), item["code"]),
        )
        return [item for item in systems if not active_only or item.get("status") == "active"]

    def save_product_config_record(
        self,
        collection_name: str,
        record: dict,
        *,
        audit_event: dict | None = None,
    ) -> None:
        payload = self.product_config_payload or {
            "product_git_repositories": {},
            "product_modules": {},
            "product_versions": {},
            "products": {},
            "related_systems": {},
        }
        payload.setdefault(collection_name, {})[record["id"]] = dict(record)
        self.product_config_payload = payload
        self.product_config_direct_writes.append(f"save:{collection_name}:{record['id']}")
        if audit_event is not None:
            self._append_direct_audit_event(audit_event)

    def delete_product_config_record(
        self,
        collection_name: str,
        record_id: str,
        *,
        audit_event: dict | None = None,
    ) -> None:
        payload = self.product_config_payload or {
            "product_git_repositories": {},
            "product_modules": {},
            "product_versions": {},
            "products": {},
            "related_systems": {},
        }
        payload.setdefault(collection_name, {}).pop(record_id, None)
        self.product_config_payload = payload
        self.product_config_direct_writes.append(f"delete:{collection_name}:{record_id}")
        if audit_event is not None:
            self._append_direct_audit_event(audit_event)

    def _append_direct_audit_event(self, audit_event: dict) -> None:
        payload = self.audit_events_payload or {"audit_events": []}
        payload.setdefault("audit_events", []).append(dict(audit_event))
        self.audit_events_payload = payload

    def load_requirements(self) -> dict | None:
        return self.requirements_payload

    def save_requirements(self, payload: dict) -> None:
        self.requirements_payload = payload

    def save_requirement_record(
        self,
        record: dict,
        *,
        audit_event: dict | None = None,
    ) -> None:
        payload = self.requirements_payload or {"requirements": {}}
        payload.setdefault("requirements", {})[record["id"]] = dict(record)
        self.requirements_payload = payload
        self.requirement_direct_writes.append(f"save:{record['id']}:{record.get('status')}")
        if audit_event is not None:
            self._append_direct_audit_event(audit_event)

    def delete_requirement_record(
        self,
        record_id: str,
        *,
        audit_event: dict | None = None,
    ) -> None:
        payload = self.requirements_payload or {"requirements": {}}
        payload.setdefault("requirements", {}).pop(record_id, None)
        self.requirements_payload = payload
        self.requirement_direct_writes.append(f"delete:{record_id}")
        if audit_event is not None:
            self._append_direct_audit_event(audit_event)

    def load_ai_tasks(self) -> dict | None:
        return self.ai_tasks_payload

    def save_ai_tasks(self, payload: dict) -> None:
        self.ai_tasks_payload = payload

    def save_requirement_and_ai_task_records(
        self,
        *,
        requirement: dict,
        task: dict,
        audit_event: dict | None = None,
    ) -> None:
        requirements_payload = self.requirements_payload or {"requirements": {}}
        requirements_payload.setdefault("requirements", {})[requirement["id"]] = dict(requirement)
        self.requirements_payload = requirements_payload
        ai_tasks_payload = self.ai_tasks_payload or {"ai_tasks": {}}
        ai_tasks_payload.setdefault("ai_tasks", {})[task["id"]] = dict(task)
        self.ai_tasks_payload = ai_tasks_payload
        self.ai_task_direct_writes.append(
            f"save:{requirement['id']}:{task['id']}:{task.get('status')}"
        )
        if audit_event is not None:
            self._append_direct_audit_event(audit_event)

    def save_task_start_records(
        self,
        *,
        task: dict,
        review: dict,
        graph_run: dict,
        checkpoint: dict,
        audit_events: list[dict],
        model_log: dict | None = None,
        code_review_report: dict | None = None,
    ) -> None:
        ai_tasks_payload = self.ai_tasks_payload or {"ai_tasks": {}}
        ai_tasks_payload.setdefault("ai_tasks", {})[task["id"]] = dict(task)
        self.ai_tasks_payload = ai_tasks_payload

        workflow_payload = self.workflow_runtime_payload or {
            "graph_checkpoints": {},
            "graph_runs": {},
            "human_reviews": {},
        }
        workflow_payload.setdefault("human_reviews", {})[review["id"]] = dict(review)
        workflow_payload.setdefault("graph_runs", {})[graph_run["id"]] = dict(graph_run)
        workflow_payload.setdefault("graph_checkpoints", {})[checkpoint["id"]] = dict(checkpoint)
        self.workflow_runtime_payload = workflow_payload

        if model_log is not None:
            model_gateway_payload = self.model_gateway_payload or {
                "model_gateway_configs": {},
                "model_gateway_logs": [],
            }
            model_gateway_payload.setdefault("model_gateway_logs", []).append(dict(model_log))
            self.model_gateway_payload = model_gateway_payload

        if code_review_report is not None:
            gitlab_review_payload = self.gitlab_review_payload or {
                "code_review_reports": {},
                "gitlab_mr_snapshots": {},
            }
            gitlab_review_payload.setdefault("code_review_reports", {})[
                code_review_report["id"]
            ] = dict(code_review_report)
            self.gitlab_review_payload = gitlab_review_payload

        for audit_event in audit_events:
            self._append_direct_audit_event(audit_event)
        self.workflow_direct_writes.append(
            f"start:{task['id']}:{review['id']}:{graph_run['id']}:{checkpoint['id']}"
        )

    def save_review_decision_records(
        self,
        *,
        task: dict,
        review: dict,
        graph_run: dict | None,
        checkpoint: dict | None,
        audit_events: list[dict],
        requirement: dict | None = None,
        knowledge_deposits: list[dict] | None = None,
        bugs: list[dict] | None = None,
        code_review_report: dict | None = None,
    ) -> None:
        ai_tasks_payload = self.ai_tasks_payload or {"ai_tasks": {}}
        ai_tasks_payload.setdefault("ai_tasks", {})[task["id"]] = dict(task)
        self.ai_tasks_payload = ai_tasks_payload

        if requirement is not None:
            requirements_payload = self.requirements_payload or {"requirements": {}}
            requirements_payload.setdefault("requirements", {})[requirement["id"]] = dict(
                requirement
            )
            self.requirements_payload = requirements_payload

        workflow_payload = self.workflow_runtime_payload or {
            "graph_checkpoints": {},
            "graph_runs": {},
            "human_reviews": {},
        }
        workflow_payload.setdefault("human_reviews", {})[review["id"]] = dict(review)
        if graph_run is not None:
            workflow_payload.setdefault("graph_runs", {})[graph_run["id"]] = dict(graph_run)
        if checkpoint is not None:
            workflow_payload.setdefault("graph_checkpoints", {})[checkpoint["id"]] = dict(
                checkpoint
            )
        self.workflow_runtime_payload = workflow_payload

        if knowledge_deposits:
            knowledge_payload = self.knowledge_payload or {
                "knowledge_chunks": {},
                "knowledge_deposits": {},
                "knowledge_documents": {},
            }
            for deposit in knowledge_deposits:
                knowledge_payload.setdefault("knowledge_deposits", {})[deposit["id"]] = dict(
                    deposit
                )
            self.knowledge_payload = knowledge_payload

        if bugs:
            bugs_payload = self.bugs_payload or {"bugs": {}}
            for bug in bugs:
                bugs_payload.setdefault("bugs", {})[bug["id"]] = dict(bug)
            self.bugs_payload = bugs_payload

        if code_review_report is not None:
            gitlab_review_payload = self.gitlab_review_payload or {
                "code_review_reports": {},
                "gitlab_mr_snapshots": {},
            }
            gitlab_review_payload.setdefault("code_review_reports", {})[
                code_review_report["id"]
            ] = dict(code_review_report)
            self.gitlab_review_payload = gitlab_review_payload

        for audit_event in audit_events:
            self._append_direct_audit_event(audit_event)
        self.workflow_direct_writes.append(f"review:{task['id']}:{review['id']}:{task['status']}")

    def save_task_state_records(
        self,
        *,
        task: dict,
        audit_events: list[dict],
        reviews: list[dict] | None = None,
        graph_run: dict | None = None,
        checkpoint: dict | None = None,
        model_log: dict | None = None,
    ) -> None:
        ai_tasks_payload = self.ai_tasks_payload or {"ai_tasks": {}}
        ai_tasks_payload.setdefault("ai_tasks", {})[task["id"]] = dict(task)
        self.ai_tasks_payload = ai_tasks_payload

        if model_log is not None:
            model_gateway_payload = self.model_gateway_payload or {
                "model_gateway_configs": {},
                "model_gateway_logs": [],
            }
            model_gateway_payload.setdefault("model_gateway_logs", []).append(dict(model_log))
            self.model_gateway_payload = model_gateway_payload

        if reviews or graph_run is not None or checkpoint is not None:
            workflow_payload = self.workflow_runtime_payload or {
                "graph_checkpoints": {},
                "graph_runs": {},
                "human_reviews": {},
            }
            for review in reviews or []:
                workflow_payload.setdefault("human_reviews", {})[review["id"]] = dict(review)
            if graph_run is not None:
                workflow_payload.setdefault("graph_runs", {})[graph_run["id"]] = dict(graph_run)
            if checkpoint is not None:
                workflow_payload.setdefault("graph_checkpoints", {})[checkpoint["id"]] = dict(
                    checkpoint
                )
            self.workflow_runtime_payload = workflow_payload

        for audit_event in audit_events:
            self._append_direct_audit_event(audit_event)
        self.task_state_direct_writes.append(f"task:{task['id']}:{task['status']}")

    def load_workflow_runtime(self) -> dict | None:
        return self.workflow_runtime_payload

    def get_task_workflow_source_rows(self) -> dict:
        self.task_workflow_source_row_reads += 1
        audit_payload = self.audit_events_payload or {}
        bugs_payload = self.bugs_payload or {}
        gitlab_metrics_payload = self.gitlab_daily_code_metrics_payload or {}
        jenkins_releases_payload = self.jenkins_release_records_payload or {}
        model_gateway_payload = self.model_gateway_payload or {}
        online_metrics_payload = self.online_log_metrics_payload or {}
        product_config = self.product_config_payload or {}
        requirements_payload = self.requirements_payload or {}
        tasks_payload = self.ai_tasks_payload or {}
        workflow_payload = self.workflow_runtime_payload or {}
        knowledge_payload = self.knowledge_payload or {}
        review_payload = self.gitlab_review_payload or {}
        mock_payload = self.mock_writebacks_payload or {}
        return {
            "audit_events": [dict(item) for item in audit_payload.get("audit_events", [])],
            "bugs": [dict(item) for item in bugs_payload.get("bugs", {}).values()],
            "code_review_reports": [
                dict(item)
                for item in review_payload.get("code_review_reports", {}).values()
            ],
            "gitlab_daily_code_metrics": [
                dict(item)
                for item in gitlab_metrics_payload.get("gitlab_daily_code_metrics", {}).values()
            ],
            "gitlab_mr_snapshots": [
                dict(item)
                for item in review_payload.get("gitlab_mr_snapshots", {}).values()
            ],
            "graph_checkpoints": [
                dict(item)
                for item in workflow_payload.get("graph_checkpoints", {}).values()
            ],
            "graph_runs": [
                dict(item)
                for item in workflow_payload.get("graph_runs", {}).values()
            ],
            "human_reviews": [
                dict(item)
                for item in workflow_payload.get("human_reviews", {}).values()
            ],
            "jenkins_release_records": [
                dict(item)
                for item in jenkins_releases_payload.get("jenkins_release_records", {}).values()
            ],
            "knowledge_deposits": [
                dict(item)
                for item in knowledge_payload.get("knowledge_deposits", {}).values()
            ],
            "model_gateway_configs": [
                dict(item)
                for item in model_gateway_payload.get("model_gateway_configs", {}).values()
            ],
            "model_gateway_logs": [
                dict(item)
                for item in model_gateway_payload.get("model_gateway_logs", [])
            ],
            "mock_writebacks": [
                dict(item)
                for item in mock_payload.get("mock_writebacks", {}).values()
            ],
            "online_log_metrics": [
                dict(item)
                for item in online_metrics_payload.get("online_log_metrics", {}).values()
            ],
            "product_git_repositories": [
                dict(item)
                for item in product_config.get("product_git_repositories", {}).values()
            ],
            "product_modules": [
                dict(item)
                for item in product_config.get("product_modules", {}).values()
            ],
            "product_versions": [
                dict(item)
                for item in product_config.get("product_versions", {}).values()
            ],
            "products": [dict(item) for item in product_config.get("products", {}).values()],
            "related_systems": [
                dict(item)
                for item in product_config.get("related_systems", {}).values()
            ],
            "requirements": [
                dict(item)
                for item in requirements_payload.get("requirements", {}).values()
            ],
            "tasks": [dict(item) for item in tasks_payload.get("ai_tasks", {}).values()],
        }

    def list_pending_review_summaries(self, *, read_scope: str | None = None) -> list[dict]:
        tasks_payload = self.ai_tasks_payload or {}
        workflow_payload = self.workflow_runtime_payload or {}
        tasks = tasks_payload.get("ai_tasks", {})

        def can_read_task(task: dict) -> bool:
            if read_scope in {None, "all"}:
                return True
            if read_scope == "code_review":
                return task.get("task_type") == "code_review"
            if read_scope == "non_code_review":
                return task.get("task_type") != "code_review"
            return False

        return [
            dict(review)
            for review in workflow_payload.get("human_reviews", {}).values()
            if review.get("status") == "pending"
            and (task := tasks.get(review.get("ai_task_id"))) is not None
            and can_read_task(task)
        ]

    def save_workflow_runtime(self, payload: dict) -> None:
        self.workflow_runtime_payload = payload

    def load_knowledge(self) -> dict | None:
        return self.knowledge_payload

    def list_knowledge_documents(
        self,
        *,
        user_roles: list[str],
        keyword: str | None = None,
        doc_type: str | None = None,
        index_status: str | None = None,
    ) -> list[dict]:
        payload = self.knowledge_payload or {}
        chunks = payload.get("knowledge_chunks", {})
        documents = []
        for document in payload.get("knowledge_documents", {}).values():
            if not set(user_roles).intersection(document.get("permission_roles", [])):
                continue
            if keyword and keyword.lower() not in (
                f"{document.get('title', '')} {document.get('content', '')}".lower()
            ):
                continue
            if doc_type and document.get("doc_type") != doc_type:
                continue
            if index_status and document.get("index_status") != index_status:
                continue
            item = dict(document)
            item["chunk_count"] = sum(
                1 for chunk in chunks.values() if chunk.get("document_id") == document["id"]
            )
            item["index_error"] = document.get("index_error")
            item["vector_index_error"] = document.get("vector_index_error")
            documents.append(item)
        documents.sort(key=lambda item: item["id"])
        return documents

    def list_knowledge_deposits(self, *, status: str | None = None) -> list[dict]:
        payload = self.knowledge_payload or {}
        deposits = [
            dict(deposit)
            for deposit in payload.get("knowledge_deposits", {}).values()
            if status is None or deposit.get("status") == status
        ]
        deposits.sort(key=lambda item: (item.get("created_at", ""), item["id"]))
        return deposits

    def get_knowledge_deposit(self, deposit_id: str) -> dict | None:
        payload = self.knowledge_payload or {}
        deposit = payload.get("knowledge_deposits", {}).get(deposit_id)
        return dict(deposit) if deposit is not None else None

    def has_readable_vector_chunks(self, *, user_roles: list[str]) -> bool:
        payload = self.knowledge_payload or {}
        documents = payload.get("knowledge_documents", {})
        for chunk in payload.get("knowledge_chunks", {}).values():
            if not isinstance(chunk.get("embedding"), list):
                continue
            document = documents.get(chunk.get("document_id"))
            if document is None:
                continue
            if document.get("index_status") not in {"indexed", "text_indexed", "vector_indexed"}:
                continue
            if not set(user_roles).intersection(document.get("permission_roles", [])):
                continue
            chunk_roles = chunk.get("permission_roles", document.get("permission_roles", []))
            if set(user_roles).intersection(chunk_roles):
                return True
        return False

    def search_knowledge_chunks(
        self,
        *,
        user_roles: list[str],
        query: str | None = None,
    ) -> list[dict]:
        payload = self.knowledge_payload or {}
        documents = payload.get("knowledge_documents", {})
        candidates = []
        for chunk in payload.get("knowledge_chunks", {}).values():
            document = documents.get(chunk.get("document_id"))
            if document is None:
                continue
            if document.get("index_status") not in {"indexed", "text_indexed", "vector_indexed"}:
                continue
            if not set(user_roles).intersection(document.get("permission_roles", [])):
                continue
            chunk_roles = chunk.get("permission_roles", document.get("permission_roles", []))
            if not set(user_roles).intersection(chunk_roles):
                continue
            haystack = f"{document.get('title', '')} {chunk.get('content', '')}".lower()
            if query is not None and query.lower() not in haystack:
                continue
            candidates.append(
                {
                    "chunk": dict(chunk),
                    "document": {
                        "doc_type": document.get("doc_type", "manual"),
                        "id": document["id"],
                        "index_status": document.get("index_status"),
                        "permission_roles": list(document.get("permission_roles", [])),
                        "title": document["title"],
                    },
                }
            )
        candidates.sort(
            key=lambda item: (
                item["document"]["id"],
                item["chunk"].get("chunk_index", 0),
                item["chunk"]["id"],
            )
        )
        return candidates

    def save_knowledge(self, payload: dict) -> None:
        self.knowledge_payload = payload

    def save_knowledge_document_records(
        self,
        *,
        document: dict,
        chunks: list[dict],
        audit_event: dict | None = None,
        model_logs: list[dict] | None = None,
    ) -> None:
        payload = self.knowledge_payload or {
            "knowledge_chunks": {},
            "knowledge_deposits": {},
            "knowledge_documents": {},
        }
        payload.setdefault("knowledge_documents", {})[document["id"]] = dict(document)
        payload["knowledge_chunks"] = {
            chunk_id: chunk
            for chunk_id, chunk in payload.setdefault("knowledge_chunks", {}).items()
            if chunk.get("document_id") != document["id"]
        }
        for chunk in chunks:
            payload.setdefault("knowledge_chunks", {})[chunk["id"]] = dict(chunk)
        self.knowledge_payload = payload
        self._append_direct_model_logs(model_logs or [])
        if audit_event is not None:
            self._append_direct_audit_event(audit_event)

    def delete_knowledge_document_records(
        self,
        *,
        document_id: str,
        deposits: list[dict],
        audit_event: dict | None = None,
    ) -> None:
        payload = self.knowledge_payload or {
            "knowledge_chunks": {},
            "knowledge_deposits": {},
            "knowledge_documents": {},
        }
        payload.setdefault("knowledge_documents", {}).pop(document_id, None)
        payload["knowledge_chunks"] = {
            chunk_id: chunk
            for chunk_id, chunk in payload.setdefault("knowledge_chunks", {}).items()
            if chunk.get("document_id") != document_id
        }
        for deposit in deposits:
            payload.setdefault("knowledge_deposits", {})[deposit["id"]] = dict(deposit)
        self.knowledge_payload = payload
        if audit_event is not None:
            self._append_direct_audit_event(audit_event)

    def save_knowledge_deposit_records(
        self,
        *,
        deposit: dict,
        audit_event: dict | None = None,
        document: dict | None = None,
        chunks: list[dict] | None = None,
        model_logs: list[dict] | None = None,
    ) -> None:
        payload = self.knowledge_payload or {
            "knowledge_chunks": {},
            "knowledge_deposits": {},
            "knowledge_documents": {},
        }
        if document is not None:
            payload.setdefault("knowledge_documents", {})[document["id"]] = dict(document)
            payload["knowledge_chunks"] = {
                chunk_id: chunk
                for chunk_id, chunk in payload.setdefault("knowledge_chunks", {}).items()
                if chunk.get("document_id") != document["id"]
            }
            for chunk in chunks or []:
                payload.setdefault("knowledge_chunks", {})[chunk["id"]] = dict(chunk)
        payload.setdefault("knowledge_deposits", {})[deposit["id"]] = dict(deposit)
        self.knowledge_payload = payload
        self._append_direct_model_logs(model_logs or [])
        if audit_event is not None:
            self._append_direct_audit_event(audit_event)

    def _append_direct_model_logs(self, model_logs: list[dict]) -> None:
        if not model_logs:
            return
        payload = self.model_gateway_payload or {
            "model_gateway_configs": {},
            "model_gateway_logs": [],
        }
        for model_log in model_logs:
            payload.setdefault("model_gateway_logs", []).append(dict(model_log))
        self.model_gateway_payload = payload

    def load_audit_events(self) -> dict | None:
        return self.audit_events_payload

    def list_audit_events(
        self,
        *,
        ai_task_id: str | None = None,
        actor_id: str | None = None,
        subject_type: str | None = None,
        subject_id: str | None = None,
        event_type: str | None = None,
        created_from=None,
        created_to=None,
    ) -> list[dict]:
        payload = self.audit_events_payload or {"audit_events": []}
        events = [dict(event) for event in payload.get("audit_events", [])]
        if actor_id:
            events = [event for event in events if event.get("actor_id") == actor_id]
        if event_type:
            events = [event for event in events if event.get("event_type") == event_type]
        if ai_task_id:
            events = [event for event in events if event.get("ai_task_id") == ai_task_id]
        if subject_type:
            events = [event for event in events if event.get("subject_type") == subject_type]
        if subject_id:
            events = [event for event in events if event.get("subject_id") == subject_id]
        if created_from is not None:
            created_from_text = created_from.isoformat()
            events = [
                event for event in events if event.get("created_at") >= created_from_text
            ]
        if created_to is not None:
            created_to_text = created_to.isoformat()
            events = [event for event in events if event.get("created_at") <= created_to_text]
        events.sort(key=lambda item: item["sequence"], reverse=True)
        return events

    def save_audit_events(self, payload: dict) -> None:
        self.audit_events_payload = payload

    def load_bugs(self) -> dict | None:
        return self.bugs_payload

    def list_bugs(
        self,
        *,
        product_id: str | None = None,
        version_id: str | None = None,
        status: str | None = None,
        severity: str | None = None,
        source: str | None = None,
    ) -> list[dict]:
        payload = self.bugs_payload or {}
        bugs = [dict(bug) for bug in payload.get("bugs", {}).values()]
        if product_id:
            bugs = [bug for bug in bugs if bug.get("product_id") == product_id]
        if version_id:
            bugs = [bug for bug in bugs if bug.get("version_id") == version_id]
        if status:
            bugs = [bug for bug in bugs if bug.get("status") == status]
        if severity:
            bugs = [bug for bug in bugs if bug.get("severity") == severity]
        if source:
            bugs = [bug for bug in bugs if bug.get("source") == source]
        bugs.sort(key=lambda item: (item.get("created_at", ""), item["id"]), reverse=True)
        return bugs

    def save_bugs(self, payload: dict) -> None:
        self.bugs_payload = payload

    def save_bug_record(
        self,
        record: dict,
        *,
        audit_event: dict | None = None,
    ) -> None:
        payload = self.bugs_payload or {"bugs": {}}
        payload.setdefault("bugs", {})[record["id"]] = dict(record)
        self.bugs_payload = payload
        if audit_event is not None:
            self._append_direct_audit_event(audit_event)

    def delete_bug_record(
        self,
        record_id: str,
        *,
        audit_event: dict | None = None,
    ) -> None:
        payload = self.bugs_payload or {"bugs": {}}
        for bug in payload.setdefault("bugs", {}).values():
            if bug.get("duplicate_of_bug_id") == record_id:
                bug["duplicate_of_bug_id"] = None
        payload["bugs"].pop(record_id, None)
        self.bugs_payload = payload
        if audit_event is not None:
            self._append_direct_audit_event(audit_event)

    def load_model_gateway(self) -> dict | None:
        return self.model_gateway_payload

    def list_model_gateway_configs(self) -> list[dict]:
        payload = self.model_gateway_payload or {}
        configs = payload.get("model_gateway_configs", {})
        return [dict(configs[config_id]) for config_id in sorted(configs)]

    def list_model_gateway_logs(
        self,
        *,
        ai_task_id: str | None = None,
        purpose: str | None = None,
        status: str | None = None,
    ) -> list[dict]:
        payload = self.model_gateway_payload or {}
        logs = [dict(log) for log in payload.get("model_gateway_logs", [])]
        if ai_task_id:
            logs = [log for log in logs if log.get("ai_task_id") == ai_task_id]
        if purpose:
            logs = [log for log in logs if log.get("purpose") == purpose]
        if status:
            logs = [log for log in logs if log.get("status") == status]
        logs.sort(key=lambda item: (item.get("created_at", ""), item["id"]), reverse=True)
        return logs

    def save_model_gateway(self, payload: dict) -> None:
        self.model_gateway_payload = payload

    def save_model_gateway_records(
        self,
        payload: dict,
        *,
        audit_event: dict | None = None,
    ) -> None:
        self.model_gateway_payload = payload
        if audit_event is not None:
            self._append_direct_audit_event(audit_event)

    def load_assistant_chat(self) -> dict | None:
        return self.assistant_chat_payload

    def list_assistant_conversations(self, *, user_id: str) -> list[dict]:
        payload = self.assistant_chat_payload or {}
        conversations = [
            dict(conversation)
            for conversation in payload.get("assistant_conversations", {}).values()
            if conversation.get("user_id") == user_id
        ]
        conversations.sort(
            key=lambda item: item.get("last_message_at") or item.get("updated_at", ""),
            reverse=True,
        )
        return conversations

    def list_assistant_conversation_messages(
        self,
        *,
        conversation_id: str,
        user_id: str,
    ) -> list[dict] | None:
        payload = self.assistant_chat_payload or {}
        conversation = payload.get("assistant_conversations", {}).get(conversation_id)
        if conversation is None or conversation.get("user_id") != user_id:
            return None
        messages = [
            dict(message)
            for message in payload.get("assistant_messages", {}).values()
            if message.get("conversation_id") == conversation_id
            and message.get("user_id") == user_id
        ]
        messages.sort(key=lambda item: (item.get("created_at", ""), item["id"]))
        return messages

    def save_assistant_chat(self, payload: dict) -> None:
        self.assistant_chat_payload = payload

    def save_assistant_chat_records(
        self,
        *,
        conversation: dict | None,
        messages: list[dict],
        audit_events: list[dict],
        model_log: dict | None = None,
    ) -> None:
        payload = self.assistant_chat_payload or {
            "assistant_conversations": {},
            "assistant_messages": {},
        }
        if conversation is not None:
            payload.setdefault("assistant_conversations", {})[conversation["id"]] = dict(
                conversation
            )
        for message in messages:
            payload.setdefault("assistant_messages", {})[message["id"]] = dict(message)
        self.assistant_chat_payload = payload
        self._append_direct_model_logs([model_log] if model_log is not None else [])
        for audit_event in audit_events:
            self._append_direct_audit_event(audit_event)

    def load_gitlab_review(self) -> dict | None:
        return self.gitlab_review_payload

    def save_gitlab_review(self, payload: dict) -> None:
        self.gitlab_review_payload = payload

    def save_gitlab_review_snapshot_record(
        self,
        *,
        snapshot: dict | None,
        audit_event: dict | None = None,
    ) -> None:
        payload = self.gitlab_review_payload or {
            "code_review_reports": {},
            "gitlab_mr_snapshots": {},
        }
        if snapshot is not None:
            payload.setdefault("gitlab_mr_snapshots", {})[snapshot["id"]] = dict(snapshot)
        self.gitlab_review_payload = payload
        if audit_event is not None:
            self._append_direct_audit_event(audit_event)

    def load_mock_writebacks(self) -> dict | None:
        return self.mock_writebacks_payload

    def save_mock_writebacks(self, payload: dict) -> None:
        self.mock_writebacks_payload = payload

    def save_mock_writeback_record(
        self,
        record: dict,
        *,
        audit_event: dict | None = None,
    ) -> None:
        payload = self.mock_writebacks_payload or {"mock_writebacks": {}}
        payload.setdefault("mock_writebacks", {})[record["idempotency_key"]] = dict(record)
        self.mock_writebacks_payload = payload
        if audit_event is not None:
            self._append_direct_audit_event(audit_event)

    def load_gitlab_daily_code_metrics(self) -> dict | None:
        return self.gitlab_daily_code_metrics_payload

    def list_gitlab_daily_code_metrics(
        self,
        *,
        product_id: str | None = None,
        repository_id: str | None = None,
        metric_date: str | None = None,
    ) -> list[dict]:
        payload = self.gitlab_daily_code_metrics_payload or {
            "gitlab_daily_code_metrics": {}
        }
        items = []
        for metric in payload.get("gitlab_daily_code_metrics", {}).values():
            if product_id is not None and metric.get("product_id") != product_id:
                continue
            if repository_id is not None and metric.get("repository_id") != repository_id:
                continue
            if metric_date is not None and metric.get("metric_date") != metric_date:
                continue
            items.append(dict(metric))
        return sorted(
            items,
            key=lambda item: (
                item.get("metric_date") or "",
                item.get("updated_at") or item.get("created_at") or "",
            ),
            reverse=True,
        )

    def save_gitlab_daily_code_metrics(self, payload: dict) -> None:
        self.gitlab_daily_code_metrics_payload = payload

    def save_gitlab_daily_code_metric_record(
        self,
        record: dict,
        *,
        audit_event: dict | None = None,
    ) -> None:
        payload = self.gitlab_daily_code_metrics_payload or {"gitlab_daily_code_metrics": {}}
        payload.setdefault("gitlab_daily_code_metrics", {})[record["id"]] = dict(record)
        self.gitlab_daily_code_metrics_payload = payload
        if audit_event is not None:
            self._append_direct_audit_event(audit_event)

    def load_jenkins_release_records(self) -> dict | None:
        return self.jenkins_release_records_payload

    def list_jenkins_release_records(
        self,
        *,
        product_id: str | None = None,
        version_id: str | None = None,
        status: str | None = None,
        environment: str | None = None,
    ) -> list[dict]:
        payload = self.jenkins_release_records_payload or {"jenkins_release_records": {}}
        items = []
        for release in payload.get("jenkins_release_records", {}).values():
            if product_id is not None and release.get("product_id") != product_id:
                continue
            if version_id is not None and release.get("version_id") != version_id:
                continue
            if status is not None and release.get("status") != status:
                continue
            if environment is not None and release.get("environment") != environment:
                continue
            items.append(dict(release))
        return sorted(
            items,
            key=lambda item: (
                item.get("deployed_at") or item.get("created_at") or "",
                item.get("updated_at") or "",
            ),
            reverse=True,
        )

    def save_jenkins_release_records(self, payload: dict) -> None:
        self.jenkins_release_records_payload = payload

    def save_jenkins_release_record(
        self,
        record: dict,
        *,
        audit_event: dict | None = None,
    ) -> None:
        payload = self.jenkins_release_records_payload or {"jenkins_release_records": {}}
        payload.setdefault("jenkins_release_records", {})[record["id"]] = dict(record)
        self.jenkins_release_records_payload = payload
        if audit_event is not None:
            self._append_direct_audit_event(audit_event)

    def load_online_log_metrics(self) -> dict | None:
        return self.online_log_metrics_payload

    def list_online_log_metrics(
        self,
        *,
        product_id: str | None = None,
        module_code: str | None = None,
        environment: str | None = None,
        from_value: str | None = None,
        to_value: str | None = None,
    ) -> list[dict]:
        payload = self.online_log_metrics_payload or {"online_log_metrics": {}}
        items = []
        for metric in payload.get("online_log_metrics", {}).values():
            if product_id is not None and metric.get("product_id") != product_id:
                continue
            if module_code is not None and metric.get("module_code") != module_code:
                continue
            if environment is not None and metric.get("environment") != environment:
                continue
            if from_value is not None and metric.get("window_end") < from_value:
                continue
            if to_value is not None and metric.get("window_start") > to_value:
                continue
            items.append(dict(metric))
        return sorted(
            items,
            key=lambda item: (
                item.get("window_start") or "",
                item.get("updated_at") or item.get("created_at") or "",
            ),
            reverse=True,
        )

    def save_online_log_metrics(self, payload: dict) -> None:
        self.online_log_metrics_payload = payload

    def save_online_log_metric_record(
        self,
        record: dict,
        *,
        audit_event: dict | None = None,
    ) -> None:
        payload = self.online_log_metrics_payload or {"online_log_metrics": {}}
        payload.setdefault("online_log_metrics", {})[record["id"]] = dict(record)
        self.online_log_metrics_payload = payload
        if audit_event is not None:
            self._append_direct_audit_event(audit_event)

    def load_user_feedback(self) -> dict | None:
        return self.user_feedback_payload

    def list_user_feedback(
        self,
        *,
        product_id: str | None = None,
        module_code: str | None = None,
        feature_code: str | None = None,
        status: str | None = None,
        created_by: str | None = None,
    ) -> list[dict]:
        payload = self.user_feedback_payload or {"user_feedback": {}}
        items = []
        for feedback in payload.get("user_feedback", {}).values():
            if product_id is not None and feedback.get("product_id") != product_id:
                continue
            if module_code is not None and feedback.get("module_code") != module_code:
                continue
            if feature_code is not None and feedback.get("feature_code") != feature_code:
                continue
            if status is not None and feedback.get("status") != status:
                continue
            if created_by is not None and feedback.get("created_by") != created_by:
                continue
            items.append(dict(feedback))
        return sorted(
            items,
            key=lambda item: item.get("updated_at") or item.get("created_at") or "",
            reverse=True,
        )

    def save_user_feedback(self, payload: dict) -> None:
        self.user_feedback_payload = payload

    def save_user_feedback_record(
        self,
        record: dict,
        *,
        audit_event: dict | None = None,
    ) -> None:
        payload = self.user_feedback_payload or {"user_feedback": {}}
        payload.setdefault("user_feedback", {})[record["id"]] = dict(record)
        self.user_feedback_payload = payload
        if audit_event is not None:
            self._append_direct_audit_event(audit_event)

    def load_user_usage_metrics(self) -> dict | None:
        return self.user_usage_metrics_payload

    def list_user_usage_metrics(
        self,
        *,
        product_id: str | None = None,
        module_code: str | None = None,
        feature_code: str | None = None,
        user_segment: str | None = None,
        from_value: str | None = None,
        to_value: str | None = None,
    ) -> list[dict]:
        payload = self.user_usage_metrics_payload or {"user_usage_metrics": {}}
        items = []
        for metric in payload.get("user_usage_metrics", {}).values():
            if product_id is not None and metric.get("product_id") != product_id:
                continue
            if module_code is not None and metric.get("module_code") != module_code:
                continue
            if feature_code is not None and metric.get("feature_code") != feature_code:
                continue
            if user_segment is not None and metric.get("user_segment") != user_segment:
                continue
            if from_value is not None and metric.get("window_end") < from_value:
                continue
            if to_value is not None and metric.get("window_start") > to_value:
                continue
            items.append(dict(metric))
        return sorted(
            items,
            key=lambda item: (
                item.get("window_start") or "",
                item.get("updated_at") or item.get("created_at") or "",
            ),
            reverse=True,
        )

    def save_user_usage_metrics(self, payload: dict) -> None:
        self.user_usage_metrics_payload = payload

    def save_user_usage_metric_record(
        self,
        record: dict,
        *,
        audit_event: dict | None = None,
    ) -> None:
        payload = self.user_usage_metrics_payload or {"user_usage_metrics": {}}
        payload.setdefault("user_usage_metrics", {})[record["id"]] = dict(record)
        self.user_usage_metrics_payload = payload
        if audit_event is not None:
            self._append_direct_audit_event(audit_event)

    def load_iteration_planning(self) -> dict | None:
        return self.iteration_planning_payload

    def list_iteration_plan_suggestions(
        self,
        *,
        product_id: str | None = None,
        planning_cycle: str | None = None,
        status: str | None = None,
    ) -> list[dict]:
        payload = self.iteration_planning_payload or {
            "iteration_plan_decisions": {},
            "iteration_plan_suggestions": {},
        }
        items = []
        for suggestion in payload.get("iteration_plan_suggestions", {}).values():
            if product_id is not None and suggestion.get("product_id") != product_id:
                continue
            if planning_cycle is not None and suggestion.get("planning_cycle") != planning_cycle:
                continue
            if status is not None and suggestion.get("status") != status:
                continue
            items.append(dict(suggestion))
        return sorted(
            items,
            key=lambda item: (
                item.get("priority_score", 0),
                item.get("updated_at") or item.get("created_at") or "",
            ),
            reverse=True,
        )

    def save_iteration_planning(self, payload: dict) -> None:
        self.iteration_planning_payload = payload

    def save_iteration_suggestion_record(
        self,
        record: dict,
        *,
        audit_event: dict | None = None,
    ) -> None:
        payload = self.iteration_planning_payload or {
            "iteration_plan_decisions": {},
            "iteration_plan_suggestions": {},
        }
        payload.setdefault("iteration_plan_suggestions", {})[record["id"]] = dict(record)
        self.iteration_planning_payload = payload
        if audit_event is not None:
            self._append_direct_audit_event(audit_event)

    def save_iteration_decision_records(
        self,
        *,
        suggestion: dict,
        decision: dict,
        audit_events: list[dict],
        requirement: dict | None = None,
    ) -> None:
        if requirement is not None:
            requirements_payload = self.requirements_payload or {"requirements": {}}
            requirements_payload.setdefault("requirements", {})[requirement["id"]] = dict(
                requirement
            )
            self.requirements_payload = requirements_payload
        payload = self.iteration_planning_payload or {
            "iteration_plan_decisions": {},
            "iteration_plan_suggestions": {},
        }
        payload.setdefault("iteration_plan_suggestions", {})[suggestion["id"]] = dict(suggestion)
        payload.setdefault("iteration_plan_decisions", {})[decision["id"]] = dict(decision)
        self.iteration_planning_payload = payload
        for audit_event in audit_events:
            self._append_direct_audit_event(audit_event)

    def load_collector_runs(self) -> dict | None:
        return self.collector_runs_payload

    def list_collector_runs(
        self,
        *,
        collector_type: str | None = None,
        product_id: str | None = None,
        status: str | None = None,
        source_system: str | None = None,
    ) -> list[dict]:
        payload = self.collector_runs_payload or {"collector_runs": {}}
        items = []
        for run in payload.get("collector_runs", {}).values():
            if collector_type is not None and run.get("collector_type") != collector_type:
                continue
            if product_id is not None and run.get("product_id") != product_id:
                continue
            if status is not None and run.get("status") != status:
                continue
            if source_system is not None and run.get("source_system") != source_system:
                continue
            items.append(dict(run))
        return sorted(
            items,
            key=lambda item: (
                item.get("started_at") or "",
                item.get("updated_at") or item.get("created_at") or "",
                item["id"],
            ),
            reverse=True,
        )

    def save_collector_runs(self, payload: dict) -> None:
        self.collector_runs_payload = payload

    def save_collector_run_record(
        self,
        record: dict,
        *,
        audit_event: dict | None = None,
    ) -> None:
        payload = self.collector_runs_payload or {"collector_runs": {}}
        payload.setdefault("collector_runs", {})[record["id"]] = dict(record)
        self.collector_runs_payload = payload
        if audit_event is not None:
            self._append_direct_audit_event(audit_event)

    def load_pending_attribution(self) -> dict | None:
        return self.pending_attribution_payload

    def list_pending_attribution_items(
        self,
        *,
        source_type: str | None = None,
        status: str | None = None,
        resolved_product_id: str | None = None,
        collector_run_id: str | None = None,
    ) -> list[dict]:
        payload = self.pending_attribution_payload or {"pending_attribution_items": {}}
        items = []
        for item in payload.get("pending_attribution_items", {}).values():
            if source_type is not None and item.get("source_type") != source_type:
                continue
            if status is not None and item.get("status") != status:
                continue
            if (
                resolved_product_id is not None
                and item.get("resolved_product_id") != resolved_product_id
            ):
                continue
            if collector_run_id is not None and item.get("collector_run_id") != collector_run_id:
                continue
            items.append(dict(item))
        return sorted(
            items,
            key=lambda item: (
                item.get("created_at") or "",
                item.get("updated_at") or "",
                item["id"],
            ),
            reverse=True,
        )

    def save_pending_attribution(self, payload: dict) -> None:
        self.pending_attribution_payload = payload

    def save_pending_attribution_item_record(
        self,
        record: dict,
        *,
        audit_event: dict | None = None,
    ) -> None:
        payload = self.pending_attribution_payload or {"pending_attribution_items": {}}
        payload.setdefault("pending_attribution_items", {})[record["id"]] = dict(record)
        self.pending_attribution_payload = payload
        if audit_event is not None:
            self._append_direct_audit_event(audit_event)

    def load_lifecycle_context(self) -> dict | None:
        return self.lifecycle_context_payload

    def save_lifecycle_context(self, payload: dict) -> None:
        self.lifecycle_context_payload = payload

    def get_lifecycle_context_source_rows(
        self,
        *,
        product_id: str | None = None,
    ) -> dict:
        self.lifecycle_source_row_reads += 1
        rows = self.get_dashboard_it_team_source_rows(
            user_roles=["admin"],
            product_id=product_id,
        )
        lifecycle_payload = self.lifecycle_context_payload or {}
        rows["lifecycle_context_edges"] = [
            dict(item)
            for item in lifecycle_payload.get("lifecycle_context_edges", {}).values()
        ]
        rows["lifecycle_risk_signals"] = [
            dict(item)
            for item in lifecycle_payload.get("lifecycle_risk_signals", {}).values()
        ]
        return rows

    def load_dashboard_snapshots(self) -> dict | None:
        return self.dashboard_payload

    def save_dashboard_snapshots(self, payload: dict) -> None:
        self.dashboard_payload = payload

    def get_dashboard_it_team_source_rows(
        self,
        *,
        user_roles: list[str],
        product_id: str | None = None,
    ) -> dict:
        self.dashboard_source_row_reads += 1
        product_config = self.product_config_payload or {}
        knowledge_payload = self.knowledge_payload or {}
        workflow_payload = self.workflow_runtime_payload or {}
        review_payload = self.gitlab_review_payload or {}
        mock_payload = self.mock_writebacks_payload or {}

        def product_filtered(payload: dict | None, key: str) -> list[dict]:
            items = []
            for item in (payload or {}).get(key, {}).values():
                if product_id is None or item.get("product_id") == product_id:
                    items.append(dict(item))
            return items

        user_role_set = set(user_roles)
        documents = []
        for document in knowledge_payload.get("knowledge_documents", {}).values():
            permission_roles = set(document.get("permission_roles", []))
            if "admin" not in user_role_set and not user_role_set.intersection(permission_roles):
                continue
            documents.append(dict(document))

        return {
            "audit_events": [
                dict(event)
                for event in (self.audit_events_payload or {}).get("audit_events", [])
            ],
            "bugs": product_filtered(self.bugs_payload, "bugs"),
            "code_review_reports": [
                dict(item)
                for item in review_payload.get("code_review_reports", {}).values()
            ],
            "gitlab_daily_code_metrics": product_filtered(
                self.gitlab_daily_code_metrics_payload,
                "gitlab_daily_code_metrics",
            ),
            "gitlab_mr_snapshots": [
                dict(item)
                for item in review_payload.get("gitlab_mr_snapshots", {}).values()
            ],
            "human_reviews": [
                dict(item) for item in workflow_payload.get("human_reviews", {}).values()
            ],
            "iteration_plan_suggestions": product_filtered(
                self.iteration_planning_payload,
                "iteration_plan_suggestions",
            ),
            "jenkins_release_records": product_filtered(
                self.jenkins_release_records_payload,
                "jenkins_release_records",
            ),
            "knowledge_deposits": [
                dict(item) for item in knowledge_payload.get("knowledge_deposits", {}).values()
            ],
            "knowledge_documents": documents,
            "mock_writebacks": [
                dict(item) for item in mock_payload.get("mock_writebacks", {}).values()
            ],
            "online_log_metrics": product_filtered(
                self.online_log_metrics_payload,
                "online_log_metrics",
            ),
            "product_git_repositories": [
                dict(item)
                for item in product_config.get("product_git_repositories", {}).values()
            ],
            "product_modules": [
                dict(item) for item in product_config.get("product_modules", {}).values()
            ],
            "product_versions": [
                dict(item) for item in product_config.get("product_versions", {}).values()
            ],
            "products": [
                dict(item)
                for item in product_config.get("products", {}).values()
                if item.get("status") == "active"
            ],
            "requirements": product_filtered(self.requirements_payload, "requirements"),
            "tasks": product_filtered(self.ai_tasks_payload, "ai_tasks"),
            "user_feedback": product_filtered(self.user_feedback_payload, "user_feedback"),
            "user_usage_metrics": product_filtered(
                self.user_usage_metrics_payload,
                "user_usage_metrics",
            ),
        }

    def save_dashboard_metric_snapshot_record(self, snapshot: dict) -> None:
        payload = self.dashboard_payload or {"dashboard_metric_snapshots": {}}
        payload.setdefault("dashboard_metric_snapshots", {})[snapshot["id"]] = dict(snapshot)
        self.dashboard_payload = payload
        self.dashboard_snapshot_direct_writes.append(snapshot["id"])


class FakeDbFirstIdRepository(FakeSnapshotRepository):
    def __init__(self) -> None:
        super().__init__()
        self.allocated_prefixes: list[str] = []

    def next_id(self, prefix: str) -> str:
        self.allocated_prefixes.append(prefix)
        return f"{prefix}_101"


def auth_headers(username: str = "admin@example.com", password: str = "admin123") -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_persistent_store_delegates_new_ids_to_repository_when_available():
    repository = FakeDbFirstIdRepository()
    store = PersistentMemoryStore.from_repository(repository)

    assert store.new_id("requirement") == "requirement_101"
    assert repository.allocated_prefixes == ["requirement"]
    assert store.counters["requirement"] == 101


def test_persistent_store_does_not_restore_business_state_from_app_snapshot_payload():
    repository = FakeSnapshotRepository()
    repository.payload = {
        "ai_tasks": {
            "task_snapshot_only": {
                "id": "task_snapshot_only",
                "product_id": "product_snapshot_only",
                "requirement_id": "requirement_snapshot_only",
                "status": "completed",
                "task_type": "product_detail_design",
                "title": "旧快照任务",
            }
        },
        "products": {
            "product_snapshot_only": {
                "code": "SNAPSHOT-ONLY",
                "id": "product_snapshot_only",
                "name": "旧快照产品",
                "status": "active",
            }
        },
        "requirements": {
            "requirement_snapshot_only": {
                "content": "旧 app_state_snapshots 中的需求不能作为生产恢复源。",
                "created_by": "user_admin",
                "id": "requirement_snapshot_only",
                "priority": "P1",
                "product_id": "product_snapshot_only",
                "status": "ready_for_dev",
                "task_ids": ["task_snapshot_only"],
                "title": "旧快照需求",
            }
        },
    }

    store = PersistentMemoryStore.from_repository(repository)

    assert "product_snapshot_only" not in store.products
    assert "requirement_snapshot_only" not in store.requirements
    assert "task_snapshot_only" not in store.ai_tasks


def test_persistent_store_persist_does_not_write_app_snapshot_payload():
    repository = FakeSnapshotRepository()
    store = PersistentMemoryStore.from_repository(repository)
    store.products["product_no_snapshot"] = {
        "code": "NO-SNAPSHOT",
        "id": "product_no_snapshot",
        "name": "不写 app_state 快照",
        "status": "active",
    }

    store.persist()

    assert repository.payload is None
    assert repository.product_config_payload["products"]["product_no_snapshot"]["code"] == (
        "NO-SNAPSHOT"
    )


def gitlab_review_context_payload() -> dict:
    return {
        "ai_tasks": {
            "task_002": {
                "created_by": "user_admin",
                "id": "task_002",
                "product_id": "product_001",
                "requirement_id": "requirement_001",
                "status": "completed",
                "task_type": "technical_solution",
                "title": "Technical solution",
                "version_id": "version_001",
            },
            "task_003": {
                "created_by": "user_admin",
                "id": "task_003",
                "product_id": "product_001",
                "requirement_id": "requirement_001",
                "status": "waiting_review",
                "task_type": "code_review",
                "title": "Code Review",
                "version_id": "version_001",
            },
        },
        "human_reviews": {
            "review_003": {
                "ai_task_id": "task_003",
                "content": {},
                "id": "review_003",
                "stage": "code_review",
                "status": "pending",
                "version": 1,
            }
        },
        "product_git_repositories": {
            "repo_001": {
                "default_branch": "main",
                "git_provider": "gitlab",
                "id": "repo_001",
                "name": "Main repository",
                "product_id": "product_001",
                "repo_type": "code",
                "root_path": "/",
                "status": "active",
            }
        },
        "product_versions": {
            "version_001": {
                "code": "v1",
                "id": "version_001",
                "name": "Version 1",
                "product_id": "product_001",
                "status": "planning",
            }
        },
        "products": {
            "product_001": {
                "code": "P1",
                "id": "product_001",
                "name": "Product 1",
                "status": "active",
            }
        },
        "requirements": {
            "requirement_001": {
                "created_by": "user_admin",
                "description": "Review requirement",
                "id": "requirement_001",
                "priority": "P1",
                "product_id": "product_001",
                "status": "task_created",
                "task_ids": ["task_002", "task_003"],
                "title": "Review requirement",
                "version_id": "version_001",
            }
        },
    }


def apply_payload_to_store(store: MemoryStore, payload: dict) -> None:
    for field, value in payload.items():
        getattr(store, field).update(value)


def mock_writeback_context_payload() -> dict:
    return {
        "ai_tasks": {
            "task_010": {
                "created_by": "user_admin",
                "id": "task_010",
                "product_id": "product_010",
                "requirement_id": "requirement_010",
                "status": "completed",
                "task_type": "technical_solution",
                "title": "Persist mock writeback",
                "version_id": "version_010",
            }
        },
        "product_versions": {
            "version_010": {
                "code": "v1",
                "id": "version_010",
                "name": "Version 1",
                "product_id": "product_010",
                "status": "planning",
            }
        },
        "products": {
            "product_010": {
                "code": "MOCK",
                "id": "product_010",
                "name": "Mock Product",
                "status": "active",
            }
        },
        "requirements": {
            "requirement_010": {
                "created_by": "user_admin",
                "description": "Persist mock writeback",
                "id": "requirement_010",
                "priority": "P1",
                "product_id": "product_010",
                "status": "task_created",
                "task_ids": ["task_010"],
                "title": "Persist mock writeback",
                "version_id": "version_010",
            }
        },
    }


def test_business_state_survives_store_rebuild_from_database_snapshot():
    original_store = app.state.store
    original_users = app.state.user_repository
    repository = FakeSnapshotRepository()
    app.state.store = PersistentMemoryStore.from_repository(repository)
    app.state.user_repository = MemoryUserRepository.seeded()

    try:
        headers = auth_headers()
        product = client.post(
            "/api/products",
            json={"code": "REAL-DB", "name": "真实数据库产品"},
            headers=headers,
        ).json()["data"]

        app.state.store = PersistentMemoryStore.from_repository(repository)

        products = client.get("/api/products", headers=headers).json()["data"]["items"]
        assert [item["id"] for item in products] == [product["id"]]
        assert products[0]["code"] == "REAL-DB"
    finally:
        app.state.store = original_store
        app.state.user_repository = original_users


def test_product_config_routes_write_repository_without_request_persist():
    original_store = app.state.store
    original_users = app.state.user_repository
    repository = FakeSnapshotRepository()

    def use_rebuilt_store_without_request_persist() -> None:
        rebuilt_store = PersistentMemoryStore.from_repository(repository)
        rebuilt_store.persist = lambda: None
        app.state.store = rebuilt_store

    use_rebuilt_store_without_request_persist()
    app.state.user_repository = MemoryUserRepository.seeded()

    try:
        headers = auth_headers()
        product = client.post(
            "/api/products",
            json={"code": "DBFIRST-PRODUCT", "name": "DB-first 产品"},
            headers=headers,
        ).json()["data"]
        version = client.post(
            f"/api/products/{product['id']}/versions",
            json={"code": "v1", "name": "v1", "status": "active"},
            headers=headers,
        ).json()["data"]
        module = client.post(
            f"/api/products/{product['id']}/modules",
            json={"code": "core", "name": "核心模块"},
            headers=headers,
        ).json()["data"]
        repository_record = client.post(
            f"/api/products/{product['id']}/git-repositories",
            json={
                "credential_ref": "secret://github/readonly",
                "git_provider": "github",
                "name": "主仓库",
                "project_path": "org/repo",
                "remote_url": "git@github.com:org/repo.git",
            },
            headers=headers,
        ).json()["data"]
        related_system = client.post(
            "/api/system/related-systems",
            json={
                "code": "DBFIRST-SYSTEM",
                "name": "DB-first 相关系统",
                "product_id": product["id"],
            },
            headers=headers,
        ).json()["data"]

        use_rebuilt_store_without_request_persist()
        products = client.get("/api/products", headers=headers).json()["data"]["items"]
        assert [item["id"] for item in products] == [product["id"]]
        versions = client.get(
            f"/api/products/{product['id']}/versions",
            headers=headers,
        ).json()["data"]["items"]
        modules = client.get(
            f"/api/products/{product['id']}/modules",
            headers=headers,
        ).json()["data"]["items"]
        repositories = client.get(
            f"/api/products/{product['id']}/git-repositories",
            headers=headers,
        ).json()["data"]["items"]
        related_systems = client.get(
            f"/api/system/related-systems?product_id={product['id']}",
            headers=headers,
        ).json()["data"]["items"]
        assert [item["id"] for item in versions] == [version["id"]]
        assert [item["id"] for item in modules] == [module["id"]]
        assert [item["id"] for item in repositories] == [repository_record["id"]]
        assert [item["id"] for item in related_systems] == [related_system["id"]]

        patched_product = client.patch(
            f"/api/products/{product['id']}",
            json={"name": "DB-first 产品已修改"},
            headers=headers,
        ).json()["data"]
        patched_version = client.patch(
            f"/api/product-versions/{version['id']}",
            json={"release_date": "2026-06-30"},
            headers=headers,
        ).json()["data"]
        patched_module = client.patch(
            f"/api/product-modules/{module['id']}",
            json={"owner_team": "platform"},
            headers=headers,
        ).json()["data"]
        patched_repository = client.patch(
            f"/api/product-git-repositories/{repository_record['id']}",
            json={"status": "inactive"},
            headers=headers,
        ).json()["data"]
        patched_related_system = client.patch(
            f"/api/system/related-systems/{related_system['id']}",
            json={"status": "inactive"},
            headers=headers,
        ).json()["data"]

        use_rebuilt_store_without_request_persist()
        assert client.get(
            f"/api/products/{product['id']}",
            headers=headers,
        ).json()["data"]["name"] == patched_product["name"]
        assert client.get(
            f"/api/products/{product['id']}/versions",
            headers=headers,
        ).json()["data"]["items"][0]["release_date"] == patched_version["release_date"]
        assert client.get(
            f"/api/products/{product['id']}/modules",
            headers=headers,
        ).json()["data"]["items"][0]["owner_team"] == patched_module["owner_team"]
        assert client.get(
            f"/api/products/{product['id']}/git-repositories",
            headers=headers,
        ).json()["data"]["items"][0]["status"] == patched_repository["status"]
        assert client.get(
            f"/api/system/related-systems?product_id={product['id']}",
            headers=headers,
        ).json()["data"]["items"][0]["status"] == patched_related_system["status"]

        client.delete(
            f"/api/product-git-repositories/{repository_record['id']}",
            headers=headers,
        )
        client.delete(f"/api/product-modules/{module['id']}", headers=headers)
        client.delete(f"/api/product-versions/{version['id']}", headers=headers)
        client.delete(f"/api/products/{product['id']}", headers=headers)

        use_rebuilt_store_without_request_persist()
        assert client.get("/api/products", headers=headers).json()["data"]["items"] == []
        assert client.get(
            f"/api/system/related-systems?product_id={product['id']}",
            headers=headers,
        ).json()["data"]["items"] == []
        assert any(
            write.startswith(f"save:products:{product['id']}")
            for write in repository.product_config_direct_writes
        )
        assert any(
            write.startswith(f"delete:products:{product['id']}")
            for write in repository.product_config_direct_writes
        )
        assert (
            f"delete:related_systems:{related_system['id']}"
            in repository.product_config_direct_writes
        )
    finally:
        app.state.store = original_store
        app.state.user_repository = original_users


def test_product_config_get_routes_use_repository_when_runtime_store_is_stale():
    original_store = app.state.store
    original_users = app.state.user_repository
    repository = FakeSnapshotRepository()
    repository.product_config_payload = {
        "products": {
            "product_read_sql": {
                "code": "READ-SQL",
                "description": "repository product",
                "display_order": 3,
                "id": "product_read_sql",
                "name": "Repository 产品",
                "owner_team": "platform",
                "status": "active",
            },
            "product_inactive_sql": {
                "code": "READ-INACTIVE",
                "description": None,
                "display_order": 9,
                "id": "product_inactive_sql",
                "name": "Inactive 产品",
                "owner_team": None,
                "status": "inactive",
            },
        },
        "product_versions": {
            "version_read_sql": {
                "code": "v1",
                "description": "repository version",
                "id": "version_read_sql",
                "name": "v1",
                "product_id": "product_read_sql",
                "release_date": "2026-06-30",
                "start_date": "2026-06-01",
                "status": "active",
            },
        },
        "product_modules": {
            "module_read_sql": {
                "code": "core",
                "description": "repository module",
                "display_order": 1,
                "id": "module_read_sql",
                "name": "核心模块",
                "owner_team": "rd",
                "product_id": "product_read_sql",
                "status": "active",
            },
        },
        "product_git_repositories": {
            "repo_read_sql": {
                "credential_ref": "secret://github/read",
                "default_branch": "main",
                "git_provider": "github",
                "id": "repo_read_sql",
                "name": "主仓库",
                "product_id": "product_read_sql",
                "project_id": None,
                "project_path": "org/read-sql",
                "remote_url": "git@github.com:org/read-sql.git",
                "repo_type": "code",
                "root_path": "/",
                "status": "active",
            },
        },
        "related_systems": {
            "related_read_sql": {
                "code": "REL-SQL",
                "description": "repository system",
                "display_order": 2,
                "id": "related_read_sql",
                "name": "相关系统",
                "owner_team": "ops",
                "product_id": "product_read_sql",
                "status": "active",
            },
        },
    }
    stale_store = PersistentMemoryStore.from_repository(repository)
    stale_store.products = {}
    stale_store.product_versions = {}
    stale_store.product_modules = {}
    stale_store.product_git_repositories = {}
    stale_store.related_systems = {}
    app.state.store = stale_store
    app.state.user_repository = MemoryUserRepository.seeded()

    try:
        headers = auth_headers()
        products = client.get("/api/products?active_only=true", headers=headers).json()["data"]
        assert [item["id"] for item in products["items"]] == ["product_read_sql"]

        product = client.get("/api/products/product_read_sql", headers=headers).json()["data"]
        assert product["name"] == "Repository 产品"

        versions = client.get(
            "/api/products/product_read_sql/versions",
            headers=headers,
        ).json()["data"]
        modules = client.get(
            "/api/products/product_read_sql/modules",
            headers=headers,
        ).json()["data"]
        repositories = client.get(
            "/api/products/product_read_sql/git-repositories",
            headers=headers,
        ).json()["data"]
        related_systems = client.get(
            "/api/system/related-systems?product_id=product_read_sql",
            headers=headers,
        ).json()["data"]

        assert [item["id"] for item in versions["items"]] == ["version_read_sql"]
        assert [item["id"] for item in modules["items"]] == ["module_read_sql"]
        assert [item["id"] for item in repositories["items"]] == ["repo_read_sql"]
        assert "credential_ref" not in repositories["items"][0]
        assert [item["id"] for item in related_systems["items"]] == ["related_read_sql"]

        missing = client.get("/api/products/missing_product/versions", headers=headers)
        assert missing.status_code == 404
    finally:
        app.state.store = original_store
        app.state.user_repository = original_users


def test_product_config_writes_use_postgres_runtime_source_rows():
    original_store = app.state.store
    original_users = app.state.user_repository
    repository = FakeSnapshotRepository()
    app.state.store = PostgresRuntimeStore(repository)
    app.state.user_repository = MemoryUserRepository.seeded()

    try:
        headers = auth_headers()
        product = client.post(
            "/api/products",
            json={"code": "PG-RUNTIME", "name": "Postgres Runtime 产品"},
            headers=headers,
        ).json()["data"]
        version = client.post(
            f"/api/products/{product['id']}/versions",
            json={"code": "v1", "name": "v1", "status": "active"},
            headers=headers,
        ).json()["data"]
        module = client.post(
            f"/api/products/{product['id']}/modules",
            json={"code": "core", "name": "核心模块", "status": "active"},
            headers=headers,
        ).json()["data"]
        git_repository = client.post(
            f"/api/products/{product['id']}/git-repositories",
            json={
                "git_provider": "github",
                "name": "Frontend",
                "project_path": "acme/frontend",
                "repo_type": "frontend",
                "status": "active",
            },
            headers=headers,
        ).json()["data"]
        related_system = client.post(
            "/api/system/related-systems",
            json={
                "code": "crm",
                "name": "CRM",
                "product_id": product["id"],
                "status": "active",
            },
            headers=headers,
        ).json()["data"]

        assert version["product_id"] == product["id"]
        assert module["product_id"] == product["id"]
        assert git_repository["product_id"] == product["id"]
        assert related_system["product_id"] == product["id"]
        assert f"save:products:{product['id']}" in repository.product_config_direct_writes
        assert (
            f"save:product_versions:{version['id']}"
            in repository.product_config_direct_writes
        )
        assert (
            f"save:product_modules:{module['id']}"
            in repository.product_config_direct_writes
        )
        assert (
            f"save:product_git_repositories:{git_repository['id']}"
            in repository.product_config_direct_writes
        )
        assert (
            f"save:related_systems:{related_system['id']}"
            in repository.product_config_direct_writes
        )
    finally:
        app.state.store = original_store
        app.state.user_repository = original_users


def test_requirement_routes_write_repository_without_request_persist():
    original_store = app.state.store
    original_users = app.state.user_repository
    repository = FakeSnapshotRepository()

    def use_rebuilt_store_without_request_persist() -> None:
        rebuilt_store = PersistentMemoryStore.from_repository(repository)
        rebuilt_store.persist = lambda: None
        app.state.store = rebuilt_store

    use_rebuilt_store_without_request_persist()
    app.state.user_repository = MemoryUserRepository.seeded()

    try:
        headers = auth_headers()
        product = client.post(
            "/api/products",
            json={"code": "REQ-DBFIRST", "name": "需求 DB-first 产品"},
            headers=headers,
        ).json()["data"]
        version = client.post(
            f"/api/products/{product['id']}/versions",
            json={"code": "v1", "name": "v1", "status": "active"},
            headers=headers,
        ).json()["data"]
        requirement = client.post(
            "/api/requirements",
            json={
                "content": "需求台账写接口不能依赖请求结束 persist。",
                "product_id": product["id"],
                "title": "需求 DB-first 创建",
            },
            headers=headers,
        ).json()["data"]

        use_rebuilt_store_without_request_persist()
        detail = client.get(
            f"/api/requirements/{requirement['id']}",
            headers=headers,
        ).json()["data"]
        assert detail["title"] == requirement["title"]
        assert detail["status"] == "submitted"

        approved = client.post(
            f"/api/requirements/{requirement['id']}/approve",
            json={"comment": "进入需求池"},
            headers=headers,
        ).json()["data"]
        assert approved["status"] == "approved"
        planned = client.patch(
            f"/api/requirements/{requirement['id']}",
            json={"version_id": version["id"]},
            headers=headers,
        ).json()["data"]
        assert planned["status"] == "planned"
        closed = client.post(
            f"/api/requirements/{requirement['id']}/close",
            headers=headers,
        ).json()["data"]
        assert closed["status"] == "closed"

        use_rebuilt_store_without_request_persist()
        closed_detail = client.get(
            f"/api/requirements/{requirement['id']}",
            headers=headers,
        ).json()["data"]
        assert closed_detail["status"] == "closed"
        assert closed_detail["version_id"] == version["id"]

        rejected_candidate = client.post(
            "/api/requirements",
            json={
                "content": "用于验证拒绝和删除也直接写 repository。",
                "product_id": product["id"],
                "title": "需求 DB-first 驳回",
            },
            headers=headers,
        ).json()["data"]
        rejected = client.post(
            f"/api/requirements/{rejected_candidate['id']}/reject",
            json={"rejection_reason": "边界不清晰"},
            headers=headers,
        ).json()["data"]
        assert rejected["status"] == "rejected"

        delete_candidate = client.post(
            "/api/requirements",
            json={
                "content": "用于验证删除直接写 repository。",
                "product_id": product["id"],
                "title": "需求 DB-first 删除",
            },
            headers=headers,
        ).json()["data"]
        delete_response = client.delete(
            f"/api/requirements/{delete_candidate['id']}",
            headers=headers,
        )
        assert delete_response.status_code == 200

        use_rebuilt_store_without_request_persist()
        deleted_detail = client.get(
            f"/api/requirements/{delete_candidate['id']}",
            headers=headers,
        )
        assert deleted_detail.status_code == 404
        rejected_detail = client.get(
            f"/api/requirements/{rejected_candidate['id']}",
            headers=headers,
        ).json()["data"]
        assert rejected_detail["status"] == "rejected"
        assert any(
            write == f"save:{requirement['id']}:closed"
            for write in repository.requirement_direct_writes
        )
        assert f"delete:{delete_candidate['id']}" in repository.requirement_direct_writes
    finally:
        app.state.store = original_store
        app.state.user_repository = original_users


def test_generate_task_writes_requirement_and_ai_task_without_request_persist():
    original_store = app.state.store
    original_users = app.state.user_repository
    repository = FakeSnapshotRepository()

    def use_rebuilt_store_without_request_persist() -> None:
        rebuilt_store = PersistentMemoryStore.from_repository(repository)
        rebuilt_store.persist = lambda: None
        app.state.store = rebuilt_store

    use_rebuilt_store_without_request_persist()
    app.state.user_repository = MemoryUserRepository.seeded()

    try:
        headers = auth_headers()
        product = client.post(
            "/api/products",
            json={"code": "TASK-DBFIRST", "name": "任务 DB-first 产品"},
            headers=headers,
        ).json()["data"]
        version = client.post(
            f"/api/products/{product['id']}/versions",
            json={"code": "v1", "name": "v1", "status": "active"},
            headers=headers,
        ).json()["data"]
        requirement = client.post(
            "/api/requirements",
            json={
                "content": "生成任务时需求和 AI task 必须同事务写入。",
                "product_id": product["id"],
                "title": "任务 DB-first 生成",
            },
            headers=headers,
        ).json()["data"]
        client.post(
            f"/api/requirements/{requirement['id']}/approve",
            json={"comment": "进入需求池"},
            headers=headers,
        )
        planned = client.patch(
            f"/api/requirements/{requirement['id']}",
            json={"version_id": version["id"]},
            headers=headers,
        ).json()["data"]
        assert planned["status"] == "planned"

        generated = client.post(
            f"/api/requirements/{requirement['id']}/generate-task",
            headers=headers,
        ).json()["data"]

        use_rebuilt_store_without_request_persist()
        app.state.store.requirements = {}
        app.state.store.ai_tasks = {}
        repository.task_workflow_source_row_reads = 0
        requirement_detail = client.get(
            f"/api/requirements/{requirement['id']}",
            headers=headers,
        ).json()["data"]
        task_detail = client.get(
            f"/api/ai-tasks/{generated['task_id']}",
            headers=headers,
        ).json()["data"]

        assert requirement_detail["status"] == "designing"
        assert requirement_detail["task_ids"] == [generated["task_id"]]
        assert task_detail["status"] == "draft"
        assert task_detail["requirement_id"] == requirement["id"]
        assert task_detail["product_context"]["product"]["id"] == product["id"]
        assert repository.task_workflow_source_row_reads == 2
        assert (
            f"save:{requirement['id']}:{generated['task_id']}:draft"
            in repository.ai_task_direct_writes
        )
    finally:
        app.state.store = original_store
        app.state.user_repository = original_users


def test_requirement_and_task_writes_use_postgres_runtime_source_rows():
    original_store = app.state.store
    original_users = app.state.user_repository
    repository = FakeSnapshotRepository()
    app.state.store = PostgresRuntimeStore(repository)
    app.state.user_repository = MemoryUserRepository.seeded()

    try:
        headers = auth_headers()
        product = client.post(
            "/api/products",
            json={"code": "REQ-PG-RUNTIME", "name": "需求 Runtime 产品"},
            headers=headers,
        ).json()["data"]
        version = client.post(
            f"/api/products/{product['id']}/versions",
            json={"code": "v1", "name": "v1", "status": "active"},
            headers=headers,
        ).json()["data"]
        module = client.post(
            f"/api/products/{product['id']}/modules",
            json={"code": "core", "name": "核心模块", "status": "active"},
            headers=headers,
        ).json()["data"]

        requirement = client.post(
            "/api/requirements",
            json={
                "content": "空启动容器下仍应从 repository source rows 校验产品上下文。",
                "module_code": module["code"],
                "product_id": product["id"],
                "title": "Runtime source rows 需求",
            },
            headers=headers,
        ).json()["data"]
        approved = client.post(
            f"/api/requirements/{requirement['id']}/approve",
            json={"comment": "进入需求池"},
            headers=headers,
        ).json()["data"]
        planned = client.patch(
            f"/api/requirements/{requirement['id']}",
            json={"version_id": version["id"]},
            headers=headers,
        ).json()["data"]
        generated = client.post(
            f"/api/requirements/{requirement['id']}/generate-task",
            headers=headers,
        ).json()["data"]

        assert approved["status"] == "approved"
        assert planned["status"] == "planned"
        assert generated["task_status"] == "draft"
        assert repository.task_workflow_source_row_reads >= 4
        assert (
            f"save:{requirement['id']}:{generated['task_id']}:draft"
            in repository.ai_task_direct_writes
        )
        task = repository.ai_tasks_payload["ai_tasks"][generated["task_id"]]
        assert task["product_context"]["product"]["id"] == product["id"]
        assert task["product_context"]["module"]["code"] == module["code"]
    finally:
        app.state.store = original_store
        app.state.user_repository = original_users


def test_start_task_writes_review_graph_and_checkpoint_without_request_persist():
    original_store = app.state.store
    original_users = app.state.user_repository
    repository = FakeSnapshotRepository()

    def use_rebuilt_store_without_request_persist() -> None:
        rebuilt_store = PersistentMemoryStore.from_repository(repository)
        rebuilt_store.persist = lambda: None
        app.state.store = rebuilt_store

    use_rebuilt_store_without_request_persist()
    app.state.user_repository = MemoryUserRepository.seeded()

    try:
        headers = auth_headers()
        product = client.post(
            "/api/products",
            json={"code": "START-DBFIRST", "name": "启动 DB-first 产品"},
            headers=headers,
        ).json()["data"]
        version = client.post(
            f"/api/products/{product['id']}/versions",
            json={"code": "v1", "name": "v1", "status": "active"},
            headers=headers,
        ).json()["data"]
        requirement = client.post(
            "/api/requirements",
            json={
                "content": "启动任务必须直接写 Review、Graph Run 和 Checkpoint。",
                "product_id": product["id"],
                "title": "任务启动 DB-first",
                "version_id": version["id"],
            },
            headers=headers,
        ).json()["data"]
        client.post(
            f"/api/requirements/{requirement['id']}/approve",
            json={"comment": "进入设计"},
            headers=headers,
        )
        generated = client.post(
            f"/api/requirements/{requirement['id']}/generate-task",
            headers=headers,
        ).json()["data"]
        use_rebuilt_store_without_request_persist()
        draft_detail = client.get(
            f"/api/ai-tasks/{generated['task_id']}",
            headers=headers,
        ).json()["data"]

        app.state.store.ai_tasks = {}
        app.state.store.graph_runs = {}
        app.state.store.human_reviews = {}
        repository.task_workflow_source_row_reads = 0
        started = client.post(
            f"/api/ai-tasks/{generated['task_id']}/start",
            headers=headers,
        ).json()["data"]
        assert repository.task_workflow_source_row_reads == 1

        use_rebuilt_store_without_request_persist()
        app.state.store.graph_runs = {}
        app.state.store.human_reviews = {}
        app.state.store.ai_tasks = {}
        repository.task_workflow_source_row_reads = 0
        detail = client.get(
            f"/api/ai-tasks/{generated['task_id']}",
            headers=headers,
        ).json()["data"]
        graph_runs = client.get(
            f"/api/graph-runs?ai_task_id={generated['task_id']}",
            headers=headers,
        ).json()["data"]
        pending_reviews = client.get("/api/reviews/pending", headers=headers).json()["data"][
            "items"
        ]
        review_detail = client.get(
            f"/api/reviews/{started['review_id']}",
            headers=headers,
        ).json()["data"]

        assert detail["status"] == "waiting_review"
        assert detail["pending_review"]["id"] == started["review_id"]
        assert detail["current_step"] == "interrupt_for_human_review"
        assert detail["checkpoint_id"] == started["checkpoint_id"]
        assert detail["updated_at"] != draft_detail["updated_at"]
        assert [run["id"] for run in graph_runs["items"]] == [started["graph_run_id"]]
        assert graph_runs["items"][0]["checkpoint_id"] == started["checkpoint_id"]
        assert [review["id"] for review in pending_reviews] == [started["review_id"]]
        assert review_detail["id"] == started["review_id"]
        assert review_detail["task"]["id"] == generated["task_id"]
        assert repository.task_workflow_source_row_reads == 3
        assert (
            f"start:{generated['task_id']}:{started['review_id']}:"
            f"{started['graph_run_id']}:{started['checkpoint_id']}"
            in repository.workflow_direct_writes
        )
    finally:
        app.state.store = original_store
        app.state.user_repository = original_users


def _create_generated_design_task(
    headers: dict[str, str],
    *,
    product_code: str,
    product_name: str,
    requirement_title: str,
) -> dict:
    product = client.post(
        "/api/products",
        json={"code": product_code, "name": product_name},
        headers=headers,
    ).json()["data"]
    version = client.post(
        f"/api/products/{product['id']}/versions",
        json={"code": "v1", "name": "v1", "status": "active"},
        headers=headers,
    ).json()["data"]
    requirement = client.post(
        "/api/requirements",
        json={
            "content": f"{requirement_title} 必须在失败时直接写 repository。",
            "product_id": product["id"],
            "title": requirement_title,
            "version_id": version["id"],
        },
        headers=headers,
    ).json()["data"]
    client.post(
        f"/api/requirements/{requirement['id']}/approve",
        json={"comment": "进入设计"},
        headers=headers,
    )
    return client.post(
        f"/api/requirements/{requirement['id']}/generate-task",
        headers=headers,
    ).json()["data"]


def test_create_followup_task_writes_requirement_and_ai_task_without_request_persist():
    original_store = app.state.store
    original_users = app.state.user_repository
    repository = FakeSnapshotRepository()

    def use_rebuilt_store_without_request_persist() -> None:
        rebuilt_store = PersistentMemoryStore.from_repository(repository)
        rebuilt_store.persist = lambda: None
        app.state.store = rebuilt_store

    use_rebuilt_store_without_request_persist()
    app.state.user_repository = MemoryUserRepository.seeded()

    try:
        headers = auth_headers()
        generated = _create_generated_design_task(
            headers,
            product_code="FOLLOWUP-DBFIRST",
            product_name="后续任务 DB-first 产品",
            requirement_title="后续任务创建 DB-first",
        )
        started = client.post(
            f"/api/ai-tasks/{generated['task_id']}/start",
            headers=headers,
        ).json()["data"]
        client.post(
            f"/api/reviews/{started['review_id']}/approve",
            json={"version": 1},
            headers=headers,
        )
        use_rebuilt_store_without_request_persist()
        design_detail = client.get(
            f"/api/ai-tasks/{generated['task_id']}",
            headers=headers,
        ).json()["data"]

        followup = client.post(
            "/api/ai-tasks",
            json={
                "input": {"product_detail_design_task_id": generated["task_id"]},
                "requirement_id": design_detail["requirement_id"],
                "task_type": "technical_solution",
                "title": "技术方案后续任务 DB-first",
            },
            headers=headers,
        ).json()["data"]

        use_rebuilt_store_without_request_persist()
        followup_detail = client.get(
            f"/api/ai-tasks/{followup['id']}",
            headers=headers,
        ).json()["data"]
        requirement_detail = client.get(
            f"/api/requirements/{design_detail['requirement_id']}",
            headers=headers,
        ).json()["data"]

        assert followup_detail["status"] == "draft"
        assert followup_detail["task_type"] == "technical_solution"
        assert followup_detail["input"]["product_detail_design_task_id"] == generated["task_id"]
        assert requirement_detail["status"] == "ready_for_dev"
        assert requirement_detail["task_ids"] == [generated["task_id"], followup["id"]]
        assert (
            f"save:{design_detail['requirement_id']}:{followup['id']}:draft"
            in repository.ai_task_direct_writes
        )
    finally:
        app.state.store = original_store
        app.state.user_repository = original_users


def test_start_task_config_failure_writes_failed_state_without_request_persist(monkeypatch):
    original_store = app.state.store
    original_users = app.state.user_repository
    repository = FakeSnapshotRepository()

    def use_rebuilt_store_without_request_persist() -> None:
        rebuilt_store = PersistentMemoryStore.from_repository(repository)
        rebuilt_store.persist = lambda: None
        app.state.store = rebuilt_store

    monkeypatch.setattr(main.settings, "model_gateway_base_url", "")
    monkeypatch.setattr(main.settings, "model_gateway_api_key", "")
    use_rebuilt_store_without_request_persist()
    app.state.user_repository = MemoryUserRepository.seeded()

    try:
        headers = auth_headers()
        generated = _create_generated_design_task(
            headers,
            product_code="CONFIG-FAIL-DBFIRST",
            product_name="配置失败 DB-first 产品",
            requirement_title="模型配置失败 DB-first",
        )
        draft_detail = client.get(
            f"/api/ai-tasks/{generated['task_id']}",
            headers=headers,
        ).json()["data"]

        response = client.post(f"/api/ai-tasks/{generated['task_id']}/start", headers=headers)
        assert response.status_code == 400
        assert response.json()["detail"]["code"] == "MODEL_GATEWAY_CONFIG_INVALID"

        use_rebuilt_store_without_request_persist()
        detail = client.get(
            f"/api/ai-tasks/{generated['task_id']}",
            headers=headers,
        ).json()["data"]
        assert detail["status"] == "failed"
        assert detail["current_step"] == "model_gateway_config_invalid"
        assert detail["updated_at"] != draft_detail["updated_at"]
        assert f"task:{generated['task_id']}:failed" in repository.task_state_direct_writes
        assert any(
            event["event_type"] == "ai_task.failed"
            for event in repository.audit_events_payload["audit_events"]
        )
    finally:
        app.state.store = original_store
        app.state.user_repository = original_users


def test_start_task_call_failure_and_retry_write_failed_logs_without_request_persist(monkeypatch):
    original_store = app.state.store
    original_users = app.state.user_repository
    repository = FakeSnapshotRepository()

    def use_rebuilt_store_without_request_persist() -> None:
        rebuilt_store = PersistentMemoryStore.from_repository(repository)
        rebuilt_store.persist = lambda: None
        app.state.store = rebuilt_store

    def fail_urlopen(_request, timeout):
        raise OSError("connection refused")

    monkeypatch.setattr(model_gateway_service, "urlopen", fail_urlopen)
    use_rebuilt_store_without_request_persist()
    app.state.user_repository = MemoryUserRepository.seeded()

    try:
        headers = auth_headers()
        generated = _create_generated_design_task(
            headers,
            product_code="CALL-FAIL-DBFIRST",
            product_name="调用失败 DB-first 产品",
            requirement_title="模型调用失败 DB-first",
        )

        first_failed = client.post(f"/api/ai-tasks/{generated['task_id']}/start", headers=headers)
        assert first_failed.status_code == 502
        assert first_failed.json()["detail"]["code"] == "MODEL_GATEWAY_FAILED"

        use_rebuilt_store_without_request_persist()
        retry_failed = client.post(f"/api/ai-tasks/{generated['task_id']}/start", headers=headers)
        assert retry_failed.status_code == 502
        assert retry_failed.json()["detail"]["code"] == "MODEL_GATEWAY_FAILED"

        use_rebuilt_store_without_request_persist()
        detail = client.get(
            f"/api/ai-tasks/{generated['task_id']}",
            headers=headers,
        ).json()["data"]
        logs = client.get(
            f"/api/model-gateway/logs?ai_task_id={generated['task_id']}",
            headers=headers,
        ).json()["data"]["items"]
        event_types = [
            event["event_type"] for event in repository.audit_events_payload["audit_events"]
        ]
        assert detail["status"] == "failed"
        assert detail["current_step"] == "model_gateway_failed"
        assert len(logs) == 2
        assert all(log["status"] == "failed" for log in logs)
        assert all(log["error"] == "Model gateway request failed" for log in logs)
        assert event_types.count("model_gateway.called") == 2
        assert "ai_task.retry_started" in event_types
        assert repository.task_state_direct_writes.count(f"task:{generated['task_id']}:failed") == 2
    finally:
        app.state.store = original_store
        app.state.user_repository = original_users


def test_approve_review_writes_completion_records_without_request_persist():
    original_store = app.state.store
    original_users = app.state.user_repository
    repository = FakeSnapshotRepository()

    def use_rebuilt_store_without_request_persist() -> None:
        rebuilt_store = PersistentMemoryStore.from_repository(repository)
        rebuilt_store.persist = lambda: None
        app.state.store = rebuilt_store

    use_rebuilt_store_without_request_persist()
    app.state.user_repository = MemoryUserRepository.seeded()

    try:
        headers = auth_headers()
        product = client.post(
            "/api/products",
            json={"code": "APPROVE-DBFIRST", "name": "审批 DB-first 产品"},
            headers=headers,
        ).json()["data"]
        version = client.post(
            f"/api/products/{product['id']}/versions",
            json={"code": "v1", "name": "v1", "status": "active"},
            headers=headers,
        ).json()["data"]
        requirement = client.post(
            "/api/requirements",
            json={
                "content": "审批 Review 后所有完成态记录必须直接写 repository。",
                "product_id": product["id"],
                "title": "Review 审批 DB-first",
                "version_id": version["id"],
            },
            headers=headers,
        ).json()["data"]
        client.post(
            f"/api/requirements/{requirement['id']}/approve",
            json={"comment": "进入设计"},
            headers=headers,
        )
        generated = client.post(
            f"/api/requirements/{requirement['id']}/generate-task",
            headers=headers,
        ).json()["data"]
        started = client.post(
            f"/api/ai-tasks/{generated['task_id']}/start",
            headers=headers,
        ).json()["data"]
        use_rebuilt_store_without_request_persist()
        waiting_detail = client.get(
            f"/api/ai-tasks/{generated['task_id']}",
            headers=headers,
        ).json()["data"]

        app.state.store.ai_tasks = {}
        app.state.store.graph_runs = {}
        app.state.store.graph_checkpoints = {}
        app.state.store.human_reviews = {}
        repository.task_workflow_source_row_reads = 0
        approved = client.post(
            f"/api/reviews/{started['review_id']}/approve",
            json={"version": 1},
            headers=headers,
        ).json()["data"]
        assert approved["task_status"] == "completed"
        assert repository.task_workflow_source_row_reads == 1

        use_rebuilt_store_without_request_persist()
        detail = client.get(
            f"/api/ai-tasks/{generated['task_id']}",
            headers=headers,
        ).json()["data"]
        requirement_detail = client.get(
            f"/api/requirements/{requirement['id']}",
            headers=headers,
        ).json()["data"]
        graph_runs = client.get(
            f"/api/graph-runs?ai_task_id={generated['task_id']}",
            headers=headers,
        ).json()["data"]["items"]

        assert detail["status"] == "completed"
        assert detail["pending_review"] is None
        assert detail["reviews"]["items"][0]["status"] == "approved"
        assert detail["reviews"]["items"][0]["decided_at"]
        assert detail["current_step"] == "complete_archive"
        assert detail["updated_at"] != waiting_detail["updated_at"]
        assert detail["knowledge_deposits"]["items"][0]["status"] == "pending"
        assert requirement_detail["status"] == "ready_for_dev"
        assert graph_runs[0]["status"] == "completed"
        assert graph_runs[0]["current_step"] == "complete_archive"
        assert (
            f"review:{generated['task_id']}:{started['review_id']}:completed"
            in repository.workflow_direct_writes
        )
    finally:
        app.state.store = original_store
        app.state.user_repository = original_users


def test_mock_writeback_writes_repository_without_request_persist():
    original_store = app.state.store
    original_users = app.state.user_repository
    repository = FakeSnapshotRepository()

    def use_rebuilt_store_without_request_persist() -> None:
        rebuilt_store = PersistentMemoryStore.from_repository(repository)
        rebuilt_store.persist = lambda: None
        app.state.store = rebuilt_store

    use_rebuilt_store_without_request_persist()
    app.state.user_repository = MemoryUserRepository.seeded()

    try:
        headers = auth_headers()
        generated = _create_generated_design_task(
            headers,
            product_code="WRITEBACK-DBFIRST",
            product_name="Mock Writeback DB-first 产品",
            requirement_title="Mock Writeback DB-first",
        )
        started = client.post(
            f"/api/ai-tasks/{generated['task_id']}/start",
            headers=headers,
        ).json()["data"]
        approved = client.post(
            f"/api/reviews/{started['review_id']}/approve",
            json={"version": 1},
            headers=headers,
        ).json()["data"]
        assert approved["task_status"] == "completed"

        use_rebuilt_store_without_request_persist()
        written = client.post(
            f"/api/writeback/results/{generated['task_id']}",
            headers=headers,
        ).json()["data"]

        assert written["status"] == "completed"
        assert written["idempotency_key"] == f"mock_issue:{generated['task_id']}"
        assert repository.mock_writebacks_payload is not None
        assert (
            repository.mock_writebacks_payload["mock_writebacks"][written["idempotency_key"]]
            == written
        )
        assert any(
            event["event_type"] == "mock_issue.written"
            and event["ai_task_id"] == generated["task_id"]
            for event in repository.audit_events_payload["audit_events"]
        )

        use_rebuilt_store_without_request_persist()
        app.state.store.ai_tasks = {}
        app.state.store.mock_writebacks = {}
        repository.task_workflow_source_row_reads = 0
        restored = client.get(
            f"/api/writeback/results/{generated['task_id']}",
            headers=headers,
        ).json()["data"]

        assert restored == written
        assert repository.task_workflow_source_row_reads == 1
    finally:
        app.state.store = original_store
        app.state.user_repository = original_users


def test_edit_approve_review_writes_completion_records_without_request_persist():
    original_store = app.state.store
    original_users = app.state.user_repository
    repository = FakeSnapshotRepository()

    def use_rebuilt_store_without_request_persist() -> None:
        rebuilt_store = PersistentMemoryStore.from_repository(repository)
        rebuilt_store.persist = lambda: None
        app.state.store = rebuilt_store

    use_rebuilt_store_without_request_persist()
    app.state.user_repository = MemoryUserRepository.seeded()

    try:
        headers = auth_headers()
        product = client.post(
            "/api/products",
            json={"code": "EDIT-APPROVE-DBFIRST", "name": "编辑审批 DB-first 产品"},
            headers=headers,
        ).json()["data"]
        version = client.post(
            f"/api/products/{product['id']}/versions",
            json={"code": "v1", "name": "v1", "status": "active"},
            headers=headers,
        ).json()["data"]
        requirement = client.post(
            "/api/requirements",
            json={
                "content": "编辑审批 Review 后完成态记录也必须直接写 repository。",
                "product_id": product["id"],
                "title": "Review 编辑审批 DB-first",
                "version_id": version["id"],
            },
            headers=headers,
        ).json()["data"]
        client.post(
            f"/api/requirements/{requirement['id']}/approve",
            json={"comment": "进入设计"},
            headers=headers,
        )
        generated = client.post(
            f"/api/requirements/{requirement['id']}/generate-task",
            headers=headers,
        ).json()["data"]
        started = client.post(
            f"/api/ai-tasks/{generated['task_id']}/start",
            headers=headers,
        ).json()["data"]
        use_rebuilt_store_without_request_persist()
        waiting_detail = client.get(
            f"/api/ai-tasks/{generated['task_id']}",
            headers=headers,
        ).json()["data"]

        app.state.store.ai_tasks = {}
        app.state.store.graph_runs = {}
        app.state.store.graph_checkpoints = {}
        app.state.store.human_reviews = {}
        repository.task_workflow_source_row_reads = 0
        edited = client.post(
            f"/api/reviews/{started['review_id']}/edit-approve",
            json={
                "version": 1,
                "edited_content": {
                    "summary": "人工编辑后的方案摘要",
                    "acceptance_criteria": ["保存 edited_approved 决策"],
                },
            },
            headers=headers,
        ).json()["data"]
        assert edited["task_status"] == "completed"
        assert repository.task_workflow_source_row_reads == 1

        use_rebuilt_store_without_request_persist()
        detail = client.get(
            f"/api/ai-tasks/{generated['task_id']}",
            headers=headers,
        ).json()["data"]
        requirement_detail = client.get(
            f"/api/requirements/{requirement['id']}",
            headers=headers,
        ).json()["data"]
        graph_runs = client.get(
            f"/api/graph-runs?ai_task_id={generated['task_id']}",
            headers=headers,
        ).json()["data"]["items"]

        assert detail["status"] == "completed"
        assert detail["pending_review"] is None
        assert detail["output"]["summary"] == "人工编辑后的方案摘要"
        assert detail["reviews"]["items"][0]["status"] == "edited_approved"
        assert detail["reviews"]["items"][0]["edited_content"]["summary"] == "人工编辑后的方案摘要"
        assert detail["reviews"]["items"][0]["decided_at"]
        assert detail["current_step"] == "complete_archive"
        assert detail["updated_at"] != waiting_detail["updated_at"]
        assert detail["knowledge_deposits"]["items"][0]["content"] == "人工编辑后的方案摘要"
        assert requirement_detail["status"] == "ready_for_dev"
        assert graph_runs[0]["status"] == "completed"
        assert graph_runs[0]["current_step"] == "complete_archive"
        assert (
            f"review:{generated['task_id']}:{started['review_id']}:completed"
            in repository.workflow_direct_writes
        )
    finally:
        app.state.store = original_store
        app.state.user_repository = original_users


def test_reject_and_more_info_reviews_write_decisions_without_request_persist():
    original_store = app.state.store
    original_users = app.state.user_repository
    repository = FakeSnapshotRepository()

    def use_rebuilt_store_without_request_persist() -> None:
        rebuilt_store = PersistentMemoryStore.from_repository(repository)
        rebuilt_store.persist = lambda: None
        app.state.store = rebuilt_store

    use_rebuilt_store_without_request_persist()
    app.state.user_repository = MemoryUserRepository.seeded()

    try:
        headers = auth_headers()
        product = client.post(
            "/api/products",
            json={"code": "REVIEW-BRANCH-DBFIRST", "name": "Review 分支 DB-first 产品"},
            headers=headers,
        ).json()["data"]
        version = client.post(
            f"/api/products/{product['id']}/versions",
            json={"code": "v1", "name": "v1", "status": "active"},
            headers=headers,
        ).json()["data"]

        def create_started_task(title: str) -> tuple[dict, dict]:
            requirement = client.post(
                "/api/requirements",
                json={
                    "content": f"{title} 的 Review 分支必须直接写 repository。",
                    "product_id": product["id"],
                    "title": title,
                    "version_id": version["id"],
                },
                headers=headers,
            ).json()["data"]
            client.post(
                f"/api/requirements/{requirement['id']}/approve",
                json={"comment": "进入设计"},
                headers=headers,
            )
            generated = client.post(
                f"/api/requirements/{requirement['id']}/generate-task",
                headers=headers,
            ).json()["data"]
            started = client.post(
                f"/api/ai-tasks/{generated['task_id']}/start",
                headers=headers,
            ).json()["data"]
            use_rebuilt_store_without_request_persist()
            waiting_detail = client.get(
                f"/api/ai-tasks/{generated['task_id']}",
                headers=headers,
            ).json()["data"]
            return started, waiting_detail

        rejected_start, rejected_waiting_detail = create_started_task("Review reject DB-first")
        app.state.store.ai_tasks = {}
        app.state.store.graph_runs = {}
        app.state.store.graph_checkpoints = {}
        app.state.store.human_reviews = {}
        repository.task_workflow_source_row_reads = 0
        rejected = client.post(
            f"/api/reviews/{rejected_start['review_id']}/reject",
            json={"version": 1, "decision_reason": "方案风险过高"},
            headers=headers,
        ).json()["data"]
        assert rejected["task_status"] == "failed"
        assert repository.task_workflow_source_row_reads == 1

        use_rebuilt_store_without_request_persist()
        rejected_detail = client.get(
            f"/api/ai-tasks/{rejected_start['id']}",
            headers=headers,
        ).json()["data"]
        rejected_graph_runs = client.get(
            f"/api/graph-runs?ai_task_id={rejected_start['id']}",
            headers=headers,
        ).json()["data"]["items"]
        assert rejected_detail["status"] == "failed"
        assert rejected_detail["pending_review"] is None
        assert rejected_detail["reviews"]["items"][0]["status"] == "rejected"
        assert rejected_detail["reviews"]["items"][0]["decision_reason"] == "方案风险过高"
        assert rejected_detail["reviews"]["items"][0]["decided_at"]
        assert rejected_detail["updated_at"] != rejected_waiting_detail["updated_at"]
        assert rejected_graph_runs[0]["status"] == "failed"
        assert rejected_graph_runs[0]["current_step"] == "failed"

        more_info_start, more_info_waiting_detail = create_started_task("Review more-info DB-first")
        app.state.store.ai_tasks = {}
        app.state.store.graph_runs = {}
        app.state.store.graph_checkpoints = {}
        app.state.store.human_reviews = {}
        repository.task_workflow_source_row_reads = 0
        more_info = client.post(
            f"/api/reviews/{more_info_start['review_id']}/request-more-info",
            json={"version": 1, "questions": ["请补充边界条件和验收口径"]},
            headers=headers,
        ).json()["data"]
        assert more_info["task_status"] == "waiting_more_info"
        assert repository.task_workflow_source_row_reads == 1

        use_rebuilt_store_without_request_persist()
        more_info_detail = client.get(
            f"/api/ai-tasks/{more_info_start['id']}",
            headers=headers,
        ).json()["data"]
        more_info_graph_runs = client.get(
            f"/api/graph-runs?ai_task_id={more_info_start['id']}",
            headers=headers,
        ).json()["data"]["items"]
        assert more_info_detail["status"] == "waiting_more_info"
        assert more_info_detail["pending_review"] is None
        assert more_info_detail["reviews"]["items"][0]["status"] == "requested_more_info"
        assert more_info_detail["reviews"]["items"][0]["questions"] == [
            "请补充边界条件和验收口径"
        ]
        assert more_info_detail["reviews"]["items"][0]["decided_at"]
        assert more_info_detail["updated_at"] != more_info_waiting_detail["updated_at"]
        assert more_info_graph_runs[0]["status"] == "interrupted"
        assert more_info_graph_runs[0]["current_step"] == "wait_for_more_info"
        assert (
            f"review:{rejected_start['id']}:{rejected_start['review_id']}:failed"
            in repository.workflow_direct_writes
        )
        assert (
            f"review:{more_info_start['id']}:{more_info_start['review_id']}:waiting_more_info"
            in repository.workflow_direct_writes
        )
    finally:
        app.state.store = original_store
        app.state.user_repository = original_users


def test_cancel_and_submit_more_info_write_task_state_without_request_persist():
    original_store = app.state.store
    original_users = app.state.user_repository
    repository = FakeSnapshotRepository()

    def use_rebuilt_store_without_request_persist() -> None:
        rebuilt_store = PersistentMemoryStore.from_repository(repository)
        rebuilt_store.persist = lambda: None
        app.state.store = rebuilt_store

    use_rebuilt_store_without_request_persist()
    app.state.user_repository = MemoryUserRepository.seeded()

    try:
        headers = auth_headers()
        product = client.post(
            "/api/products",
            json={"code": "TASK-STATE-DBFIRST", "name": "任务状态 DB-first 产品"},
            headers=headers,
        ).json()["data"]
        version = client.post(
            f"/api/products/{product['id']}/versions",
            json={"code": "v1", "name": "v1", "status": "active"},
            headers=headers,
        ).json()["data"]

        def create_started_task(title: str) -> dict:
            requirement = client.post(
                "/api/requirements",
                json={
                    "content": f"{title} 的任务状态必须直接写 repository。",
                    "product_id": product["id"],
                    "title": title,
                    "version_id": version["id"],
                },
                headers=headers,
            ).json()["data"]
            client.post(
                f"/api/requirements/{requirement['id']}/approve",
                json={"comment": "进入设计"},
                headers=headers,
            )
            generated = client.post(
                f"/api/requirements/{requirement['id']}/generate-task",
                headers=headers,
            ).json()["data"]
            started = client.post(
                f"/api/ai-tasks/{generated['task_id']}/start",
                headers=headers,
            ).json()["data"]
            use_rebuilt_store_without_request_persist()
            return started

        cancelled_start = create_started_task("Cancel DB-first")
        app.state.store.ai_tasks = {}
        app.state.store.graph_runs = {}
        app.state.store.graph_checkpoints = {}
        app.state.store.human_reviews = {}
        repository.task_workflow_source_row_reads = 0
        cancelled = client.post(
            f"/api/ai-tasks/{cancelled_start['id']}/cancel",
            headers=headers,
        ).json()["data"]
        assert cancelled["status"] == "cancelled"
        assert repository.task_workflow_source_row_reads == 1

        use_rebuilt_store_without_request_persist()
        cancelled_detail = client.get(
            f"/api/ai-tasks/{cancelled_start['id']}",
            headers=headers,
        ).json()["data"]
        cancelled_graph_runs = client.get(
            f"/api/graph-runs?ai_task_id={cancelled_start['id']}",
            headers=headers,
        ).json()["data"]["items"]
        assert cancelled_detail["status"] == "cancelled"
        assert cancelled_detail["pending_review"] is None
        assert cancelled_detail["reviews"]["items"][0]["status"] == "cancelled"
        assert cancelled_detail["reviews"]["items"][0]["decided_at"]
        assert cancelled_graph_runs[0]["status"] == "cancelled"
        assert cancelled_graph_runs[0]["current_step"] == "cancelled"

        more_info_start = create_started_task("Submit more-info DB-first")
        client.post(
            f"/api/reviews/{more_info_start['review_id']}/request-more-info",
            json={"version": 1, "questions": ["请补充验收边界"]},
            headers=headers,
        )
        use_rebuilt_store_without_request_persist()
        app.state.store.ai_tasks = {}
        app.state.store.graph_runs = {}
        app.state.store.graph_checkpoints = {}
        app.state.store.human_reviews = {}
        repository.task_workflow_source_row_reads = 0
        more_info = client.post(
            f"/api/ai-tasks/{more_info_start['id']}/more-info",
            json={"answers": [{"question": "请补充验收边界", "answer": "补充 P0 验收边界"}]},
            headers=headers,
        ).json()["data"]
        assert more_info["status"] == "draft"
        assert repository.task_workflow_source_row_reads == 1

        use_rebuilt_store_without_request_persist()
        more_info_detail = client.get(
            f"/api/ai-tasks/{more_info_start['id']}",
            headers=headers,
        ).json()["data"]
        assert more_info_detail["status"] == "draft"
        assert more_info_detail["current_step"] == "draft"
        assert more_info_detail["input"]["more_info_answers"] == [
            {"question": "请补充验收边界", "answer": "补充 P0 验收边界"}
        ]
        assert (
            f"task:{cancelled_start['id']}:cancelled" in repository.task_state_direct_writes
        )
        assert f"task:{more_info_start['id']}:draft" in repository.task_state_direct_writes
    finally:
        app.state.store = original_store
        app.state.user_repository = original_users


def test_knowledge_routes_write_repository_without_request_persist():
    original_store = app.state.store
    original_users = app.state.user_repository
    repository = FakeSnapshotRepository()

    def use_empty_postgres_runtime_store() -> PostgresRuntimeStore:
        runtime_store = PostgresRuntimeStore(repository)
        app.state.store = runtime_store
        return runtime_store

    use_empty_postgres_runtime_store()
    app.state.user_repository = MemoryUserRepository.seeded()

    try:
        headers = auth_headers()
        created = client.post(
            "/api/knowledge/documents",
            json={
                "content": "retrieval marker\n\nDB-first 知识文档必须直接写 repository。",
                "doc_type": "system",
                "permission_roles": ["admin", "knowledge_owner"],
                "tags": ["db-first"],
                "title": "知识 DB-first 创建",
            },
            headers=headers,
        ).json()["data"]

        use_empty_postgres_runtime_store()
        documents = client.get("/api/knowledge/documents", headers=headers).json()["data"][
            "items"
        ]
        search_results = client.post(
            "/api/knowledge/search",
            json={"query": "retrieval marker"},
            headers=headers,
        ).json()["data"]["items"]
        assert [document["id"] for document in documents] == [created["id"]]
        assert documents[0]["chunk_count"] == 2
        assert search_results[0]["document_id"] == created["id"]
        assert repository.model_gateway_payload["model_gateway_logs"]

        patched = client.patch(
            f"/api/knowledge/documents/{created['id']}",
            json={
                "content": "new-search-token\n\n更新后的知识内容。",
                "title": "知识 DB-first 修改",
            },
            headers=headers,
        ).json()["data"]
        assert patched["title"] == "知识 DB-first 修改"

        use_empty_postgres_runtime_store()
        patched_detail = client.get("/api/knowledge/documents", headers=headers).json()["data"][
            "items"
        ][0]
        patched_search_results = client.post(
            "/api/knowledge/search",
            json={"query": "new-search-token"},
            headers=headers,
        ).json()["data"]["items"]
        assert patched_detail["title"] == "知识 DB-first 修改"
        assert patched_search_results[0]["document_id"] == created["id"]

        client.patch(
            f"/api/knowledge/documents/{created['id']}",
            json={"index_error": "人工标记索引失败", "index_status": "index_failed"},
            headers=headers,
        )
        use_empty_postgres_runtime_store()
        failed_detail = client.get(
            "/api/knowledge/documents?index_status=index_failed",
            headers=headers,
        ).json()["data"]["items"][0]
        assert failed_detail["chunk_count"] == 0
        retried = client.post(
            f"/api/knowledge/documents/{created['id']}/retry-index",
            headers=headers,
        ).json()["data"]
        assert retried["index_status"] == "vector_indexed"

        repository.knowledge_payload.setdefault("knowledge_deposits", {})[
            "deposit_dbfirst_approve"
        ] = {
            "ai_task_id": "task_knowledge_dbfirst",
            "content": "沉淀采纳内容 retrieval marker",
            "id": "deposit_dbfirst_approve",
            "knowledge_document_id": None,
            "status": "pending",
            "title": "待采纳知识沉淀",
        }
        current_store = use_empty_postgres_runtime_store()
        current_store.knowledge_deposits = {}
        approved_deposit = client.post(
            "/api/knowledge/deposits/deposit_dbfirst_approve/approve",
            json={
                "permission_roles": ["admin", "knowledge_owner"],
                "title": "采纳后的知识文档",
            },
            headers=headers,
        ).json()["data"]
        assert approved_deposit["status"] == "approved"
        approved_document_id = approved_deposit["knowledge_document_id"]

        use_empty_postgres_runtime_store()
        deposits = client.get("/api/knowledge/deposits", headers=headers).json()["data"]["items"]
        approved = next(deposit for deposit in deposits if deposit["id"] == approved_deposit["id"])
        assert approved["knowledge_document_id"] == approved_document_id
        assert approved["updated_at"]

        client.delete(f"/api/knowledge/documents/{approved_document_id}", headers=headers)
        use_empty_postgres_runtime_store()
        deposits_after_delete = client.get("/api/knowledge/deposits", headers=headers).json()[
            "data"
        ]["items"]
        approved_after_delete = next(
            deposit for deposit in deposits_after_delete if deposit["id"] == approved_deposit["id"]
        )
        assert approved_after_delete["knowledge_document_id"] is None

        repository.knowledge_payload.setdefault("knowledge_deposits", {})[
            "deposit_dbfirst_reject"
        ] = {
            "ai_task_id": "task_knowledge_dbfirst",
            "content": "沉淀拒绝内容",
            "id": "deposit_dbfirst_reject",
            "knowledge_document_id": None,
            "status": "pending",
            "title": "待拒绝知识沉淀",
        }
        current_store = use_empty_postgres_runtime_store()
        current_store.knowledge_deposits = {}
        rejected_deposit = client.post(
            "/api/knowledge/deposits/deposit_dbfirst_reject/reject",
            json={"reason": "内容重复"},
            headers=headers,
        ).json()["data"]
        assert rejected_deposit["status"] == "rejected"

        use_empty_postgres_runtime_store()
        rejected = next(
            deposit
            for deposit in client.get("/api/knowledge/deposits", headers=headers).json()["data"][
                "items"
            ]
            if deposit["id"] == "deposit_dbfirst_reject"
        )
        assert rejected["rejection_reason"] == "内容重复"
        assert any(
            event["event_type"] == "knowledge_deposit.rejected"
            for event in repository.audit_events_payload["audit_events"]
        )
    finally:
        app.state.store = original_store
        app.state.user_repository = original_users


def test_assistant_chat_writes_repository_without_request_persist(monkeypatch):
    original_store = app.state.store
    original_users = app.state.user_repository
    repository = FakeSnapshotRepository()
    repository.model_gateway_payload = {
        "model_gateway_configs": {
            "model_gateway_config_assistant": {
                "api_key": "sk-assistant-test",
                "base_url": "https://api.example.com/v1",
                "default_chat_model": "gpt-assistant",
                "default_embedding_model": "text-embedding-assistant",
                "embedding_connection_mode": "disabled",
                "id": "model_gateway_config_assistant",
                "is_default": True,
                "max_retries": 1,
                "name": "Assistant test gateway",
                "provider": "openai_compatible",
                "status": "active",
                "timeout_seconds": 30,
            }
        },
        "model_gateway_logs": [],
    }

    class FakeResponse:
        def __init__(self, answer: str):
            self.answer = answer

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self) -> bytes:
            return json.dumps(
                {
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {
                                        "answer": self.answer,
                                        "suggestions": ["查看需求", "查看任务"],
                                    },
                                    ensure_ascii=False,
                                )
                            }
                        }
                    ],
                    "usage": {"completion_tokens": 9, "prompt_tokens": 21, "total_tokens": 30},
                },
                ensure_ascii=False,
            ).encode("utf-8")

    def use_empty_postgres_runtime_store() -> None:
        app.state.store = PostgresRuntimeStore(repository)

    def successful_urlopen(request, timeout):
        body = json.loads(request.data.decode("utf-8"))
        user_message = body["messages"][1]["content"]
        return FakeResponse(f"已记录：{json.loads(user_message)['message']}")

    use_empty_postgres_runtime_store()
    app.state.user_repository = MemoryUserRepository.seeded()
    monkeypatch.setattr(assistant_router, "urlopen", successful_urlopen)

    try:
        headers = auth_headers()
        first = client.post(
            "/api/assistant/chat",
            json={"conversation_id": "conv_dbfirst", "message": "查询 AI Brain 进度"},
            headers=headers,
        ).json()["data"]
        assert first["conversation_id"] == "conv_dbfirst"

        use_empty_postgres_runtime_store()
        conversations = client.get("/api/assistant/conversations", headers=headers).json()[
            "data"
        ]["items"]
        messages = client.get(
            "/api/assistant/conversations/conv_dbfirst/messages",
            headers=headers,
        ).json()["data"]["items"]
        assert [conversation["id"] for conversation in conversations] == ["conv_dbfirst"]
        assert conversations[0]["message_count"] == 2
        assert [message["role"] for message in messages] == ["user", "assistant"]
        assert messages[1]["content"] == "已记录：查询 AI Brain 进度"

        second = client.post(
            "/api/assistant/chat",
            json={"conversation_id": "conv_dbfirst", "message": "继续记录下一步"},
            headers=headers,
        ).json()["data"]
        assert second["conversation_id"] == "conv_dbfirst"

        use_empty_postgres_runtime_store()
        updated_conversation = client.get("/api/assistant/conversations", headers=headers).json()[
            "data"
        ]["items"][0]
        updated_messages = client.get(
            "/api/assistant/conversations/conv_dbfirst/messages",
            headers=headers,
        ).json()["data"]["items"]
        assert updated_conversation["message_count"] == 4
        assert updated_messages[-1]["content"] == "已记录：继续记录下一步"

        def failing_urlopen(_request, timeout):
            raise OSError("assistant gateway unavailable")

        monkeypatch.setattr(assistant_router, "urlopen", failing_urlopen)
        failed = client.post(
            "/api/assistant/chat",
            json={"message": "触发失败日志"},
            headers=headers,
        )
        assert failed.status_code == 502
        assert failed.json()["detail"]["code"] == "ASSISTANT_CHAT_FAILED"

        use_empty_postgres_runtime_store()
        logs = client.get(
            "/api/model-gateway/logs?purpose=assistant_chat",
            headers=headers,
        ).json()["data"]["items"]
        assert [log["status"] for log in logs].count("succeeded") == 2
        assert any(log["status"] == "failed" for log in logs)
        assert any(
            event["event_type"] == "assistant.chat_completed"
            for event in repository.audit_events_payload["audit_events"]
        )
        assert any(
            event["event_type"] == "model_gateway.called"
            and event["payload"]["status"] == "failed"
            for event in repository.audit_events_payload["audit_events"]
        )
    finally:
        app.state.store = original_store
        app.state.user_repository = original_users


def test_assistant_history_uses_repository_when_runtime_store_is_stale():
    original_store = app.state.store
    original_users = app.state.user_repository
    repository = FakeSnapshotRepository()
    repository.assistant_chat_payload = {
        "assistant_conversations": {
            "conversation_repo_admin": {
                "created_at": "2026-06-03T08:00:00+00:00",
                "id": "conversation_repo_admin",
                "last_message_at": "2026-06-03T08:01:00+00:00",
                "message_count": 2,
                "product_id": "product_119",
                "title": "Admin 会话",
                "updated_at": "2026-06-03T08:01:00+00:00",
                "user_id": "user_admin",
            },
            "conversation_repo_reviewer": {
                "created_at": "2026-06-03T09:00:00+00:00",
                "id": "conversation_repo_reviewer",
                "last_message_at": "2026-06-03T09:01:00+00:00",
                "message_count": 1,
                "product_id": None,
                "title": "Reviewer 会话",
                "updated_at": "2026-06-03T09:01:00+00:00",
                "user_id": "user_reviewer",
            },
        },
        "assistant_messages": {
            "assistant_message_repo_admin_001": {
                "content": "admin question",
                "conversation_id": "conversation_repo_admin",
                "created_at": "2026-06-03T08:00:00+00:00",
                "id": "assistant_message_repo_admin_001",
                "role": "user",
                "suggestions": [],
                "user_id": "user_admin",
            },
            "assistant_message_repo_admin_002": {
                "content": "admin answer",
                "conversation_id": "conversation_repo_admin",
                "created_at": "2026-06-03T08:01:00+00:00",
                "id": "assistant_message_repo_admin_002",
                "model": "gpt-read",
                "role": "assistant",
                "suggestions": ["查看任务"],
                "user_id": "user_admin",
            },
            "assistant_message_repo_reviewer_001": {
                "content": "reviewer question",
                "conversation_id": "conversation_repo_reviewer",
                "created_at": "2026-06-03T09:00:00+00:00",
                "id": "assistant_message_repo_reviewer_001",
                "role": "user",
                "suggestions": [],
                "user_id": "user_reviewer",
            },
        },
    }
    stale_store = PersistentMemoryStore.from_repository(repository)
    stale_store.assistant_conversations = {}
    stale_store.assistant_messages = {}
    app.state.store = stale_store
    app.state.user_repository = MemoryUserRepository.seeded()

    try:
        admin_conversations = client.get(
            "/api/assistant/conversations",
            headers=auth_headers(),
        ).json()["data"]["items"]
        assert [item["id"] for item in admin_conversations] == ["conversation_repo_admin"]
        assert admin_conversations[0]["message_count"] == 2

        admin_messages = client.get(
            "/api/assistant/conversations/conversation_repo_admin/messages",
            headers=auth_headers(),
        ).json()["data"]["items"]
        assert [item["id"] for item in admin_messages] == [
            "assistant_message_repo_admin_001",
            "assistant_message_repo_admin_002",
        ]
        assert admin_messages[1]["model"] == "gpt-read"
        assert admin_messages[1]["suggestions"] == ["查看任务"]

        reviewer_conversations = client.get(
            "/api/assistant/conversations",
            headers=auth_headers("reviewer@example.com", "reviewer123"),
        ).json()["data"]["items"]
        assert [item["id"] for item in reviewer_conversations] == [
            "conversation_repo_reviewer"
        ]
        cross_user_messages = client.get(
            "/api/assistant/conversations/conversation_repo_admin/messages",
            headers=auth_headers("reviewer@example.com", "reviewer123"),
        )
        assert cross_user_messages.status_code == 404
    finally:
        app.state.store = original_store
        app.state.user_repository = original_users


def test_gitlab_snapshot_writes_repository_without_request_persist(monkeypatch):
    original_store = app.state.store
    original_users = app.state.user_repository
    repository = FakeSnapshotRepository()

    def use_empty_postgres_runtime_store() -> PostgresRuntimeStore:
        runtime_store = PostgresRuntimeStore(repository)
        app.state.store = runtime_store
        return runtime_store

    def seed_snapshot_context() -> None:
        product = {
            "code": "GITLAB-DBFIRST",
            "id": "product_gitlab_dbfirst",
            "name": "GitLab DB-first 产品",
            "status": "active",
        }
        version = {
            "code": "v1",
            "id": "version_gitlab_dbfirst",
            "name": "v1",
            "product_id": "product_gitlab_dbfirst",
            "status": "active",
        }
        git_repository = {
            "default_branch": "main",
            "git_provider": "gitlab",
            "id": "repo_gitlab_dbfirst",
            "name": "主仓库",
            "product_id": "product_gitlab_dbfirst",
            "repo_type": "code",
            "root_path": "/",
            "status": "active",
        }
        requirement = {
            "content": "GitLab snapshot DB-first",
            "created_by": "user_admin",
            "id": "requirement_gitlab_dbfirst",
            "priority": "P1",
            "product_id": "product_gitlab_dbfirst",
            "status": "ready_for_dev",
            "task_ids": ["task_gitlab_solution_dbfirst"],
            "title": "GitLab snapshot DB-first",
            "version_id": "version_gitlab_dbfirst",
        }
        technical_solution = {
            "created_by": "user_admin",
            "current_step": "complete_archive",
            "graph_run_ids": [],
            "id": "task_gitlab_solution_dbfirst",
            "input_json": {},
            "output_json": {"kind": "technical_solution", "summary": "已确认技术方案"},
            "product_context": {},
            "product_id": "product_gitlab_dbfirst",
            "requirement_id": "requirement_gitlab_dbfirst",
            "requirement_snapshot": {"id": "requirement_gitlab_dbfirst"},
            "review_ids": [],
            "status": "completed",
            "task_type": "technical_solution",
            "title": "已确认技术方案",
            "version_id": "version_gitlab_dbfirst",
        }
        repository.product_config_payload = {
            "product_git_repositories": {"repo_gitlab_dbfirst": git_repository},
            "product_modules": {},
            "product_versions": {"version_gitlab_dbfirst": version},
            "products": {"product_gitlab_dbfirst": product},
            "related_systems": {},
        }
        repository.requirements_payload = {
            "requirements": {"requirement_gitlab_dbfirst": requirement}
        }
        repository.ai_tasks_payload = {
            "ai_tasks": {"task_gitlab_solution_dbfirst": technical_solution}
        }

    def preview_with_files(files: list[dict]) -> dict:
        return {
            "author": {"name": "Dev", "username": "dev"},
            "base_sha": "base",
            "changed_file_count": len(files),
            "changed_files_summary": files,
            "diff_refs": {"base_sha": "base", "head_sha": "head"},
            "head_sha": "head",
            "mr_iid": 42,
            "project_id": "100",
            "project_path": "org/repo",
            "source_branch": "feature/db-first",
            "target_branch": "main",
            "title": "DB-first MR",
            "web_url": "https://gitlab.example.com/org/repo/-/merge_requests/42",
            "writeback_allowed": False,
        }

    seed_snapshot_context()
    use_empty_postgres_runtime_store()
    app.state.user_repository = MemoryUserRepository.seeded()
    monkeypatch.setattr(
        git_review_service,
        "gitlab_preview",
        lambda _repository, _mr_iid: preview_with_files(
            [{"additions": 3, "deletions": 1, "path": "apps/api/app/main.py"}]
        ),
    )

    try:
        headers = auth_headers()
        preview_response = client.get(
            "/api/devops/gitlab/merge-requests/repo_gitlab_dbfirst/42/preview",
            headers=headers,
        )
        assert preview_response.status_code == 200

        snapshot = client.post(
            "/api/devops/gitlab/merge-requests/repo_gitlab_dbfirst/42/snapshot",
            json={
                "requirement_id": "requirement_gitlab_dbfirst",
                "technical_solution_task_id": "task_gitlab_solution_dbfirst",
            },
            headers=headers,
        ).json()["data"]

        use_empty_postgres_runtime_store()
        assert list(repository.gitlab_review_payload["gitlab_mr_snapshots"]) == [snapshot["id"]]

        reused = client.post(
            "/api/devops/gitlab/merge-requests/repo_gitlab_dbfirst/42/snapshot",
            json={
                "requirement_id": "requirement_gitlab_dbfirst",
                "technical_solution_task_id": "task_gitlab_solution_dbfirst",
            },
            headers=headers,
        ).json()["data"]
        assert reused["id"] == snapshot["id"]

        use_empty_postgres_runtime_store()
        assert list(repository.gitlab_review_payload["gitlab_mr_snapshots"]) == [snapshot["id"]]

        monkeypatch.setattr(
            git_review_service,
            "gitlab_preview",
            lambda _repository, _mr_iid: preview_with_files(
                [
                    {"additions": 1, "deletions": 0, "path": f"file_{index}.py"}
                    for index in range(51)
                ]
            ),
        )
        failed = client.post(
            "/api/devops/gitlab/merge-requests/repo_gitlab_dbfirst/99/snapshot",
            json={
                "requirement_id": "requirement_gitlab_dbfirst",
                "technical_solution_task_id": "task_gitlab_solution_dbfirst",
            },
            headers=headers,
        )
        assert failed.status_code == 413

        use_empty_postgres_runtime_store()
        assert list(repository.gitlab_review_payload["gitlab_mr_snapshots"]) == [snapshot["id"]]
        event_types = [
            event["event_type"] for event in repository.audit_events_payload["audit_events"]
        ]
        assert "gitlab_mr.previewed" in event_types
        assert "gitlab_mr.snapshotted" in event_types
        assert "gitlab_mr.snapshot_reused" in event_types
        assert "gitlab_mr.snapshot_failed" in event_types
    finally:
        app.state.store = original_store
        app.state.user_repository = original_users


def test_github_list_and_preview_audits_write_repository_without_request_persist(monkeypatch):
    original_store = app.state.store
    original_users = app.state.user_repository
    repository = FakeSnapshotRepository()

    def use_empty_postgres_runtime_store() -> PostgresRuntimeStore:
        runtime_store = PostgresRuntimeStore(repository)
        app.state.store = runtime_store
        return runtime_store

    use_empty_postgres_runtime_store()
    repository.product_config_payload = {
        "product_git_repositories": {
            "repo_github_dbfirst": {
                "credential_ref": "ghp_direct_local_token",
                "default_branch": "main",
                "git_provider": "github",
                "id": "repo_github_dbfirst",
                "name": "GitHub 主仓库",
                "product_id": "product_github_dbfirst",
                "project_path": "zeek428/e-ai-brain",
                "remote_url": "git@github.com:zeek428/e-ai-brain.git",
                "repo_type": "code",
                "root_path": "/",
                "status": "active",
            }
        },
        "product_modules": {},
        "product_versions": {},
        "products": {
            "product_github_dbfirst": {
                "code": "GITHUB-DBFIRST",
                "id": "product_github_dbfirst",
                "name": "GitHub DB-first 产品",
                "status": "active",
            }
        },
        "related_systems": {},
    }
    use_empty_postgres_runtime_store()
    app.state.user_repository = MemoryUserRepository.seeded()

    def github_pull_requests(
        repo: dict,
        *,
        state: str,
        limit: int,
    ) -> list[dict]:
        return [
            {
                "author": {"name": "zeek428", "username": "zeek428"},
                "base_sha": "base",
                "created_at": "2026-06-03T08:00:00Z",
                "head_sha": "head",
                "number": 3,
                "project_path": "zeek428/e-ai-brain",
                "repository_id": repo["id"],
                "source_branch": "feature/db-first",
                "state": state,
                "target_branch": "main",
                "title": "DB-first PR",
                "updated_at": "2026-06-03T09:00:00Z",
                "web_url": "https://github.com/zeek428/e-ai-brain/pull/3",
                "writeback_allowed": False,
            }
        ][:limit]

    def github_preview(repo: dict, pr_number: int) -> dict:
        return {
            "author": {"name": "zeek428", "username": "zeek428"},
            "base_sha": "base",
            "changed_file_count": 1,
            "changed_files_summary": [
                {"additions": 4, "deletions": 1, "path": "apps/api/app/main.py"}
            ],
            "diff_refs": {"base_sha": "base", "head_sha": "head"},
            "head_sha": "head",
            "mr_iid": pr_number,
            "project_id": None,
            "project_path": "zeek428/e-ai-brain",
            "repository_id": repo["id"],
            "source_branch": "feature/db-first",
            "target_branch": "main",
            "title": "DB-first PR",
            "web_url": "https://github.com/zeek428/e-ai-brain/pull/3",
            "writeback_allowed": False,
        }

    monkeypatch.setattr(git_review_service, "github_pull_requests", github_pull_requests)
    monkeypatch.setattr(git_review_service, "github_preview", github_preview)

    try:
        headers = auth_headers()
        listed = client.get(
            "/api/devops/github/pull-requests/repo_github_dbfirst?state=all&limit=2",
            headers=headers,
        )
        assert listed.status_code == 200

        use_empty_postgres_runtime_store()
        preview = client.get(
            "/api/devops/github/pull-requests/repo_github_dbfirst/3/preview",
            headers=headers,
        )
        assert preview.status_code == 200

        use_empty_postgres_runtime_store()
        event_types = [
            event["event_type"] for event in repository.audit_events_payload["audit_events"]
        ]
        assert "github_pr.listed" in event_types
        assert "github_pr.previewed" in event_types
    finally:
        app.state.store = original_store
        app.state.user_repository = original_users


def test_repository_read_snapshot_get_does_not_persist_stale_runtime_store():
    original_store = app.state.store
    original_users = app.state.user_repository
    repository = FakeSnapshotRepository()
    now = "2026-06-03T12:30:00+00:00"
    repository.product_config_payload = {
        "product_git_repositories": {},
        "product_modules": {},
        "product_versions": {},
        "products": {
            "product_read_get": {
                "code": "READ-GET",
                "created_at": now,
                "id": "product_read_get",
                "name": "GET 读模型产品",
                "status": "active",
                "updated_at": now,
            }
        },
        "related_systems": {},
    }
    repository.requirements_payload = {
        "requirements": {
            "requirement_read_get": {
                "content": "GET 读接口不能把过期运行时 store 持久化回 repository。",
                "created_at": now,
                "created_by": "user_admin",
                "id": "requirement_read_get",
                "priority": "P1",
                "product_id": "product_read_get",
                "status": "ready_for_dev",
                "task_ids": ["task_read_get"],
                "title": "GET 读模型不回写过期 store",
                "updated_at": now,
            }
        }
    }
    repository.ai_tasks_payload = {
        "ai_tasks": {
            "task_read_get": {
                "created_at": now,
                "created_by": "user_admin",
                "current_step": "complete_archive",
                "graph_run_ids": [],
                "id": "task_read_get",
                "input_json": {},
                "output_json": {},
                "product_context": {},
                "product_id": "product_read_get",
                "requirement_id": "requirement_read_get",
                "requirement_snapshot": {"id": "requirement_read_get"},
                "review_ids": [],
                "status": "completed",
                "task_type": "product_detail_design",
                "title": "GET 读模型任务",
                "updated_at": now,
            }
        }
    }

    headers = auth_headers()
    stale_store = PersistentMemoryStore.from_repository(repository)
    stale_store.requirements = {}
    stale_store.ai_tasks = {}
    app.state.store = stale_store
    app.state.user_repository = MemoryUserRepository.seeded()

    try:
        dashboard = client.get(
            "/api/dashboard/it-team?product_id=product_read_get",
            headers=headers,
        ).json()["data"]
        assert dashboard["summary"]["requirements"] == 1
        assert repository.dashboard_source_row_reads == 1
        assert repository.dashboard_snapshot_direct_writes
        assert "requirement_read_get" in repository.requirements_payload["requirements"]
        assert "task_read_get" in repository.ai_tasks_payload["ai_tasks"]
    finally:
        app.state.store = original_store
        app.state.user_repository = original_users


def test_operational_lists_use_repository_when_runtime_store_is_stale():
    original_store = app.state.store
    original_users = app.state.user_repository
    repository = FakeSnapshotRepository()
    repository.collector_runs_payload = {
        "collector_runs": {
            "collector_run_repo_001": {
                "collector_type": "gitlab_daily_code_metric",
                "created_at": "2026-06-03T08:00:00+00:00",
                "created_by": "user_admin",
                "error_message": None,
                "finished_at": "2026-06-03T08:10:00+00:00",
                "id": "collector_run_repo_001",
                "payload_summary": {"repository_path": "rd/api"},
                "product_id": "product_ops_repo",
                "records_imported": 5,
                "source_system": "gitlab",
                "started_at": "2026-06-03T08:00:00+00:00",
                "status": "succeeded",
                "updated_at": "2026-06-03T08:10:00+00:00",
            },
            "collector_run_repo_002": {
                "collector_type": "jenkins_release",
                "created_at": "2026-06-03T09:00:00+00:00",
                "created_by": "user_admin",
                "error_message": None,
                "finished_at": None,
                "id": "collector_run_repo_002",
                "payload_summary": {},
                "product_id": "product_other",
                "records_imported": 0,
                "source_system": "jenkins",
                "started_at": "2026-06-03T09:00:00+00:00",
                "status": "running",
                "updated_at": "2026-06-03T09:00:00+00:00",
            },
        }
    }
    repository.pending_attribution_payload = {
        "pending_attribution_items": {
            "pending_attr_repo_001": {
                "collector_run_id": "collector_run_repo_001",
                "confidence": 0.91,
                "created_at": "2026-06-03T08:12:00+00:00",
                "created_by": "user_admin",
                "id": "pending_attr_repo_001",
                "raw_payload": {"repository_path": "rd/api"},
                "raw_subject_id": "metric-1",
                "resolution_action": "link_existing_context",
                "resolution_note": "归属产品",
                "resolved_at": "2026-06-03T08:15:00+00:00",
                "resolved_by": "user_admin",
                "resolved_module_code": None,
                "resolved_product_id": "product_ops_repo",
                "resolved_requirement_id": None,
                "resolved_subject_id": None,
                "resolved_subject_type": None,
                "source_system": "gitlab",
                "source_type": "gitlab_daily_code_metric",
                "status": "resolved",
                "suggested_module_code": None,
                "suggested_product_id": "product_ops_repo",
                "summary": "GitLab 指标待归属",
                "updated_at": "2026-06-03T08:15:00+00:00",
            },
            "pending_attr_repo_002": {
                "collector_run_id": None,
                "confidence": 0.4,
                "created_at": "2026-06-03T08:20:00+00:00",
                "created_by": "user_admin",
                "id": "pending_attr_repo_002",
                "raw_payload": {},
                "raw_subject_id": "metric-2",
                "resolution_action": None,
                "resolution_note": None,
                "resolved_at": None,
                "resolved_by": None,
                "resolved_module_code": None,
                "resolved_product_id": None,
                "resolved_requirement_id": None,
                "resolved_subject_id": None,
                "resolved_subject_type": None,
                "source_system": "gitlab",
                "source_type": "user_feedback",
                "status": "pending",
                "suggested_module_code": None,
                "suggested_product_id": None,
                "summary": "其他待归属",
                "updated_at": "2026-06-03T08:20:00+00:00",
            },
        }
    }
    repository.gitlab_daily_code_metrics_payload = {
        "gitlab_daily_code_metrics": {
            "gitlab_metric_repo_001": {
                "active_author_count": 3,
                "additions": 120,
                "author_metrics": [{"author": "alice", "commit_count": 2}],
                "changed_files": 8,
                "collected_at": "2026-06-03T08:30:00+00:00",
                "commit_count": 6,
                "created_at": "2026-06-03T08:30:00+00:00",
                "created_by": "user_admin",
                "deletions": 30,
                "id": "gitlab_metric_repo_001",
                "merge_request_count": 2,
                "metric_date": "2026-06-03",
                "product_id": "product_ops_repo",
                "repository_id": "repo_ops_repo",
                "risk_count": 1,
                "source_channel": "manual_import",
                "status": "collected",
                "updated_at": "2026-06-03T08:30:00+00:00",
            }
        }
    }
    repository.jenkins_release_records_payload = {
        "jenkins_release_records": {
            "jenkins_release_repo_001": {
                "build_id": "build-001",
                "created_at": "2026-06-03T08:40:00+00:00",
                "created_by": "user_admin",
                "deployed_at": "2026-06-03T08:50:00+00:00",
                "environment": "staging",
                "id": "jenkins_release_repo_001",
                "job_name": "deploy-api",
                "product_id": "product_ops_repo",
                "status": "success",
                "updated_at": "2026-06-03T08:50:00+00:00",
                "version_id": "version_ops_repo",
            }
        }
    }
    repository.online_log_metrics_payload = {
        "online_log_metrics": {
            "online_log_metric_repo_001": {
                "core_event_count": 80,
                "created_at": "2026-06-03T09:00:00+00:00",
                "created_by": "user_admin",
                "environment": "prod",
                "error_count": 2,
                "error_rate": 0.02,
                "id": "online_log_metric_repo_001",
                "module_code": "assistant",
                "product_id": "product_ops_repo",
                "request_count": 100,
                "status": "normal",
                "top_errors": [{"code": "E_TIMEOUT", "count": 2}],
                "updated_at": "2026-06-03T09:00:00+00:00",
                "window_end": "2026-06-03T09:00:00+00:00",
                "window_start": "2026-06-03T08:00:00+00:00",
            }
        }
    }
    stale_store = PersistentMemoryStore.from_repository(repository)
    stale_store.collector_runs = {}
    stale_store.pending_attribution_items = {}
    stale_store.gitlab_daily_code_metrics = {}
    stale_store.jenkins_release_records = {}
    stale_store.online_log_metrics = {}
    app.state.store = stale_store
    app.state.user_repository = MemoryUserRepository.seeded()

    try:
        headers = auth_headers()
        collectors = client.get(
            "/api/collectors/runs?collector_type=gitlab_daily_code_metric"
            "&product_id=product_ops_repo&status=succeeded&source_system=gitlab",
            headers=headers,
        ).json()["data"]["items"]
        assert [item["id"] for item in collectors] == ["collector_run_repo_001"]

        pending = client.get(
            "/api/attribution/pending-items?source_type=gitlab_daily_code_metric"
            "&status=resolved&resolved_product_id=product_ops_repo"
            "&collector_run_id=collector_run_repo_001",
            headers=headers,
        ).json()["data"]["items"]
        assert [item["id"] for item in pending] == ["pending_attr_repo_001"]

        gitlab_metrics = client.get(
            "/api/devops/gitlab/daily-code-metrics?product_id=product_ops_repo"
            "&repository_id=repo_ops_repo&date=2026-06-03",
            headers=headers,
        ).json()["data"]["items"]
        assert [item["id"] for item in gitlab_metrics] == ["gitlab_metric_repo_001"]
        assert gitlab_metrics[0]["author_metrics"] == [
            {"author": "alice", "commit_count": 2}
        ]

        releases = client.get(
            "/api/devops/jenkins/releases?product_id=product_ops_repo"
            "&version_id=version_ops_repo&status=success&environment=staging",
            headers=headers,
        ).json()["data"]["items"]
        assert [item["id"] for item in releases] == ["jenkins_release_repo_001"]

        online_logs = client.get(
            "/api/ops/online-log-metrics?product_id=product_ops_repo"
            "&module_code=assistant&environment=prod"
            "&from=2026-06-03T08:00:00Z&to=2026-06-03T09:00:00Z",
            headers=headers,
        ).json()["data"]["items"]
        assert [item["id"] for item in online_logs] == ["online_log_metric_repo_001"]
        assert online_logs[0]["top_errors"] == [{"code": "E_TIMEOUT", "count": 2}]
    finally:
        app.state.store = original_store
        app.state.user_repository = original_users


def test_operational_routes_write_repository_without_request_persist():
    original_store = app.state.store
    original_users = app.state.user_repository
    repository = FakeSnapshotRepository()

    def use_empty_postgres_runtime_store() -> PostgresRuntimeStore:
        runtime_store = PostgresRuntimeStore(repository)
        app.state.store = runtime_store
        return runtime_store

    use_empty_postgres_runtime_store()
    app.state.user_repository = MemoryUserRepository.seeded()

    try:
        headers = auth_headers()
        product = client.post(
            "/api/products",
            json={"code": "OPS-DBFIRST", "name": "运营 DB-first 产品"},
            headers=headers,
        ).json()["data"]
        version = client.post(
            f"/api/products/{product['id']}/versions",
            json={"code": "v1", "name": "v1"},
            headers=headers,
        ).json()["data"]
        module = client.post(
            f"/api/products/{product['id']}/modules",
            json={"code": "checkout", "name": "结算模块"},
            headers=headers,
        ).json()["data"]
        repository_record = client.post(
            f"/api/products/{product['id']}/git-repositories",
            json={
                "default_branch": "main",
                "git_provider": "gitlab",
                "name": "运营仓库",
                "project_path": "rd/ops-dbfirst",
                "remote_url": "https://gitlab.internal/rd/ops-dbfirst.git",
                "repo_type": "code",
                "root_path": "/",
            },
            headers=headers,
        ).json()["data"]

        use_empty_postgres_runtime_store()
        collector = client.post(
            "/api/collectors/runs",
            json={
                "collector_type": "gitlab_daily_code_metric",
                "payload_summary": {"repository_path": "rd/ops-dbfirst"},
                "product_id": product["id"],
                "source_system": "gitlab",
                "status": "running",
            },
            headers=headers,
        ).json()["data"]

        use_empty_postgres_runtime_store()
        patched_collector = client.patch(
            f"/api/collectors/runs/{collector['id']}",
            json={"records_imported": 6, "status": "succeeded"},
            headers=headers,
        ).json()["data"]
        assert patched_collector["status"] == "succeeded"

        use_empty_postgres_runtime_store()
        collector_list = client.get(
            f"/api/collectors/runs?product_id={product['id']}&status=succeeded",
            headers=headers,
        ).json()["data"]["items"]
        assert collector_list[0]["records_imported"] == 6

        pending = client.post(
            "/api/attribution/pending-items",
            json={
                "collector_run_id": collector["id"],
                "confidence": 0.62,
                "raw_payload": {"repository_path": "unknown/repo"},
                "raw_subject_id": "metric-ext-1",
                "source_system": "gitlab",
                "source_type": "gitlab_daily_code_metric",
                "summary": "待归属 GitLab 指标",
                "suggested_product_id": product["id"],
            },
            headers=headers,
        ).json()["data"]

        use_empty_postgres_runtime_store()
        resolved = client.post(
            f"/api/attribution/pending-items/{pending['id']}/resolve",
            json={
                "resolution_action": "link_existing_context",
                "resolution_note": "归属到 AI Brain 运营测试产品",
                "resolved_product_id": product["id"],
            },
            headers=headers,
        ).json()["data"]
        assert resolved["status"] == "resolved"

        use_empty_postgres_runtime_store()
        pending_list = client.get(
            f"/api/attribution/pending-items?status=resolved&resolved_product_id={product['id']}",
            headers=headers,
        ).json()["data"]["items"]
        assert pending_list[0]["id"] == pending["id"]

        gitlab_metric = client.post(
            "/api/devops/gitlab/daily-code-metrics",
            json={
                "active_author_count": 2,
                "additions": 120,
                "author_metrics": [{"author": "alice", "commit_count": 2}],
                "changed_files": 8,
                "commit_count": 3,
                "deletions": 12,
                "metric_date": "2026-06-03",
                "merge_request_count": 1,
                "product_id": product["id"],
                "repository_id": repository_record["id"],
                "risk_count": 0,
                "source_channel": "manual_import",
                "status": "collected",
            },
            headers=headers,
        ).json()["data"]

        use_empty_postgres_runtime_store()
        gitlab_metrics = client.get(
            f"/api/devops/gitlab/daily-code-metrics?repository_id={repository_record['id']}",
            headers=headers,
        ).json()["data"]["items"]
        assert gitlab_metrics[0]["id"] == gitlab_metric["id"]

        release = client.post(
            "/api/devops/jenkins/releases",
            json={
                "build_id": "build-dbfirst-1",
                "build_number": 1,
                "duration_seconds": 420,
                "environment": "staging",
                "job_name": "ai-brain-deploy",
                "product_id": product["id"],
                "started_at": "2026-06-03T10:00:00Z",
                "status": "success",
                "version_id": version["id"],
            },
            headers=headers,
        ).json()["data"]

        use_empty_postgres_runtime_store()
        releases = client.get(
            f"/api/devops/jenkins/releases?product_id={product['id']}&status=success",
            headers=headers,
        ).json()["data"]["items"]
        assert releases[0]["id"] == release["id"]

        online_metric = client.post(
            "/api/ops/online-log-metrics",
            json={
                "core_event_count": 500,
                "environment": "prod",
                "error_count": 5,
                "module_code": module["code"],
                "p95_latency_ms": 250.0,
                "product_id": product["id"],
                "request_count": 1000,
                "status": "collected",
                "top_errors": [{"count": 5, "message": "Timeout"}],
                "window_end": "2026-06-03T11:00:00Z",
                "window_start": "2026-06-03T10:00:00Z",
            },
            headers=headers,
        ).json()["data"]

        use_empty_postgres_runtime_store()
        online_metrics = client.get(
            f"/api/ops/online-log-metrics?product_id={product['id']}&module_code={module['code']}",
            headers=headers,
        ).json()["data"]["items"]
        assert online_metrics[0]["id"] == online_metric["id"]

        event_types = [
            event["event_type"] for event in repository.audit_events_payload["audit_events"]
        ]
        for event_type in [
            "collector_run.created",
            "collector_run.updated",
            "pending_attribution.created",
            "pending_attribution.resolved",
            "gitlab_daily_code_metric.created",
            "jenkins_release.created",
            "online_log_metric.created",
        ]:
            assert event_type in event_types
    finally:
        app.state.store = original_store
        app.state.user_repository = original_users


def test_insight_planning_routes_write_repository_without_request_persist():
    original_store = app.state.store
    original_users = app.state.user_repository
    repository = FakeSnapshotRepository()

    def use_empty_postgres_runtime_store() -> PostgresRuntimeStore:
        runtime_store = PostgresRuntimeStore(repository)
        app.state.store = runtime_store
        return runtime_store

    use_empty_postgres_runtime_store()
    app.state.user_repository = MemoryUserRepository.seeded()

    try:
        admin_headers = auth_headers()
        reviewer_headers = auth_headers("reviewer@example.com", "reviewer123")
        product = client.post(
            "/api/products",
            json={"code": "INSIGHT-DBFIRST", "name": "洞察 DB-first 产品"},
            headers=admin_headers,
        ).json()["data"]
        version = client.post(
            f"/api/products/{product['id']}/versions",
            json={"code": "2026Q3", "name": "2026 Q3", "status": "planning"},
            headers=admin_headers,
        ).json()["data"]
        module = client.post(
            f"/api/products/{product['id']}/modules",
            json={"code": "knowledge", "name": "知识中心"},
            headers=admin_headers,
        ).json()["data"]

        use_empty_postgres_runtime_store()
        usage = client.post(
            "/api/insights/usage-metrics",
            json={
                "active_users": 12,
                "event_count": 36,
                "feature_code": "semantic-search",
                "module_code": module["code"],
                "product_id": product["id"],
                "user_segment": "rd",
                "window_end": "2026-06-03T11:00:00Z",
                "window_start": "2026-06-03T10:00:00Z",
            },
            headers=admin_headers,
        ).json()["data"]

        use_empty_postgres_runtime_store()
        usage_items = client.get(
            f"/api/insights/usage-metrics?product_id={product['id']}&module_code={module['code']}",
            headers=admin_headers,
        ).json()["data"]["items"]
        assert usage_items[0]["id"] == usage["id"]

        feedback = client.post(
            "/api/insights/user-feedback",
            json={
                "content": "知识检索最近方案命中率偏低。",
                "feedback_type": "improvement",
                "module_code": module["code"],
                "product_id": product["id"],
                "satisfaction_score": 2,
                "sentiment": "negative",
            },
            headers=reviewer_headers,
        ).json()["data"]

        use_empty_postgres_runtime_store()
        patched_feedback = client.patch(
            f"/api/insights/user-feedback/{feedback['id']}",
            json={"status": "triaged", "triage_note": "进入迭代建议证据池。"},
            headers=admin_headers,
        ).json()["data"]
        assert patched_feedback["status"] == "triaged"

        use_empty_postgres_runtime_store()
        feedback_items = client.get(
            f"/api/insights/user-feedback?product_id={product['id']}&status=triaged",
            headers=admin_headers,
        ).json()["data"]["items"]
        assert feedback_items[0]["id"] == feedback["id"]

        bug = client.post(
            "/api/bugs",
            json={
                "description": "搜索排序偶发返回过期方案。",
                "module_code": module["code"],
                "product_id": product["id"],
                "severity": "major",
                "source": "manual_test",
                "title": "搜索排序返回过期方案",
                "version_id": version["id"],
            },
            headers=admin_headers,
        ).json()["data"]

        use_empty_postgres_runtime_store()
        generated = client.post(
            "/api/planning/iteration-suggestions",
            json={
                "module_codes": [module["code"]],
                "planning_cycle": "2026Q3",
                "product_id": product["id"],
                "version_id": version["id"],
            },
            headers=admin_headers,
        ).json()["data"]
        suggestion = generated["items"][0]
        assert [
            (evidence["subject_type"], evidence["subject_id"])
            for evidence in suggestion["evidence"]
        ] == [("user_feedback", feedback["id"]), ("bug", bug["id"])]

        use_empty_postgres_runtime_store()
        listed_suggestions = client.get(
            f"/api/planning/iteration-suggestions?product_id={product['id']}&status=suggested",
            headers=admin_headers,
        ).json()["data"]["items"]
        assert listed_suggestions[0]["id"] == suggestion["id"]

        decided = client.post(
            f"/api/planning/iteration-suggestions/{suggestion['id']}/decide",
            json={
                "comment": "采纳为真实需求。",
                "convert_to_requirement": True,
                "decision": "edited_accepted",
                "edited_scope": "先优化知识检索召回与排序。",
                "edited_title": "优化知识检索召回与排序",
            },
            headers=admin_headers,
        ).json()["data"]
        assert decided["status"] == "converted_to_requirement"

        use_empty_postgres_runtime_store()
        requirements = client.get(
            f"/api/requirements?product_id={product['id']}",
            headers=admin_headers,
        ).json()["data"]["items"]
        assert requirements[0]["id"] == decided["converted_requirement_id"]
        assert requirements[0]["title"] == "优化知识检索召回与排序"
        converted_suggestions = client.get(
            f"/api/planning/iteration-suggestions?product_id={product['id']}",
            headers=admin_headers,
        ).json()["data"]["items"]
        assert converted_suggestions[0]["converted_requirement_id"] == requirements[0]["id"]

        event_types = [
            event["event_type"] for event in repository.audit_events_payload["audit_events"]
        ]
        for event_type in [
            "usage_metric.created",
            "user_feedback.created",
            "user_feedback.updated",
            "iteration_suggestion.generated",
            "requirement.created",
            "iteration_suggestion.decided",
        ]:
            assert event_type in event_types
    finally:
        app.state.store = original_store
        app.state.user_repository = original_users


def test_insight_planning_lists_use_repository_when_runtime_store_is_stale():
    original_store = app.state.store
    original_users = app.state.user_repository
    repository = FakeSnapshotRepository()
    repository.user_usage_metrics_payload = {
        "user_usage_metrics": {
            "usage_repo_001": {
                "active_users": 21,
                "created_at": "2026-06-03T08:00:00+00:00",
                "created_by": "user_admin",
                "error_count": 1,
                "event_count": 88,
                "feature_code": "chat",
                "id": "usage_repo_001",
                "module_code": "assistant",
                "product_id": "product_insight_repo",
                "updated_at": "2026-06-03T08:30:00+00:00",
                "user_segment": "rd",
                "window_end": "2026-06-03T08:30:00+00:00",
                "window_start": "2026-06-03T08:00:00+00:00",
            },
            "usage_repo_002": {
                "active_users": 9,
                "created_at": "2026-06-03T09:00:00+00:00",
                "created_by": "user_admin",
                "error_count": 0,
                "event_count": 22,
                "feature_code": "chat",
                "id": "usage_repo_002",
                "module_code": "assistant",
                "product_id": "product_other",
                "updated_at": "2026-06-03T09:30:00+00:00",
                "user_segment": "rd",
                "window_end": "2026-06-03T09:30:00+00:00",
                "window_start": "2026-06-03T09:00:00+00:00",
            },
        }
    }
    repository.user_feedback_payload = {
        "user_feedback": {
            "feedback_repo_001": {
                "content": "AI 助手需要保留上下文。",
                "created_at": "2026-06-03T08:10:00+00:00",
                "created_by": "user_admin",
                "feature_code": "chat",
                "feedback_type": "improvement",
                "id": "feedback_repo_001",
                "module_code": "assistant",
                "product_id": "product_insight_repo",
                "source_channel": "manual",
                "status": "triaged",
                "tags": ["assistant"],
                "updated_at": "2026-06-03T08:20:00+00:00",
            },
            "feedback_repo_002": {
                "content": "其他产品反馈。",
                "created_at": "2026-06-03T08:15:00+00:00",
                "created_by": "user_admin",
                "feedback_type": "bug",
                "id": "feedback_repo_002",
                "product_id": "product_other",
                "source_channel": "manual",
                "status": "open",
                "tags": [],
                "updated_at": "2026-06-03T08:15:00+00:00",
            },
        }
    }
    repository.iteration_planning_payload = {
        "iteration_plan_decisions": {},
        "iteration_plan_suggestions": {
            "suggestion_repo_001": {
                "business_value": "提升助手可用性。",
                "confidence_level": "medium",
                "created_at": "2026-06-03T08:40:00+00:00",
                "created_by": "user_admin",
                "dependencies": [],
                "estimated_effort": "medium",
                "evidence": [
                    {"subject_id": "feedback_repo_001", "subject_type": "user_feedback"}
                ],
                "evidence_insufficient": False,
                "id": "suggestion_repo_001",
                "module_codes": ["assistant"],
                "planning_cycle": "2026Q3",
                "priority": "P1",
                "priority_score": 81,
                "product_id": "product_insight_repo",
                "recommendation_reason": "真实反馈集中。",
                "risk_signals": ["user_feedback_signal"],
                "status": "suggested",
                "title": "优化 AI 助手上下文",
                "updated_at": "2026-06-03T08:45:00+00:00",
            },
            "suggestion_repo_002": {
                "business_value": "其他产品优化。",
                "confidence_level": "low",
                "created_at": "2026-06-03T08:35:00+00:00",
                "created_by": "user_admin",
                "dependencies": [],
                "estimated_effort": "small",
                "evidence": [],
                "evidence_insufficient": True,
                "id": "suggestion_repo_002",
                "module_codes": [],
                "planning_cycle": "2026Q3",
                "priority": "P2",
                "priority_score": 40,
                "product_id": "product_other",
                "recommendation_reason": "其他证据。",
                "risk_signals": [],
                "status": "suggested",
                "title": "其他迭代建议",
                "updated_at": "2026-06-03T08:35:00+00:00",
            },
        },
    }
    stale_store = PersistentMemoryStore.from_repository(repository)
    stale_store.user_usage_metrics = {}
    stale_store.user_feedback = {}
    stale_store.iteration_plan_suggestions = {}
    app.state.store = stale_store
    app.state.user_repository = MemoryUserRepository.seeded()

    try:
        headers = auth_headers()
        usage = client.get(
            "/api/insights/usage-metrics?product_id=product_insight_repo"
            "&module_code=assistant&feature_code=chat&user_segment=rd"
            "&from=2026-06-03T08:00:00Z&to=2026-06-03T08:30:00Z",
            headers=headers,
        ).json()["data"]["items"]
        assert [item["id"] for item in usage] == ["usage_repo_001"]

        feedback = client.get(
            "/api/insights/user-feedback?product_id=product_insight_repo"
            "&module_code=assistant&feature_code=chat&status=triaged"
            "&created_by=user_admin",
            headers=headers,
        ).json()["data"]["items"]
        assert [item["id"] for item in feedback] == ["feedback_repo_001"]

        suggestions = client.get(
            "/api/planning/iteration-suggestions?product_id=product_insight_repo"
            "&planning_cycle=2026Q3&status=suggested",
            headers=headers,
        ).json()["data"]["items"]
        assert [item["id"] for item in suggestions] == ["suggestion_repo_001"]
        assert suggestions[0]["evidence"][0]["subject_id"] == "feedback_repo_001"
    finally:
        app.state.store = original_store
        app.state.user_repository = original_users
