from fastapi.testclient import TestClient

from app.core.store import MemoryStore
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
        self.code_inspection_payload: dict | None = None
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
        self.product_config_single_reads: list[str] = []
        self.requirement_direct_writes: list[str] = []
        self.ai_task_direct_writes: list[str] = []
        self.workflow_direct_writes: list[str] = []
        self.task_state_direct_writes: list[str] = []
        self.task_workflow_source_row_reads = 0
        self.dashboard_source_row_reads = 0
        self.dashboard_snapshot_direct_writes: list[str] = []
        self.lifecycle_source_row_reads = 0
        self.model_gateway_direct_writes: list[str] = []

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
        self.product_config_single_reads.append(f"get_product:{product_id}")
        product = self._product_config_collection("products").get(product_id)
        return dict(product) if product is not None else None

    def get_product_version(self, version_id: str) -> dict | None:
        self.product_config_single_reads.append(f"get_product_version:{version_id}")
        version = self._product_config_collection("product_versions").get(version_id)
        return dict(version) if version is not None else None

    def get_product_git_repository(self, repository_id: str) -> dict | None:
        self.product_config_single_reads.append(f"get_product_git_repository:{repository_id}")
        repository = self._product_config_collection("product_git_repositories").get(
            repository_id,
        )
        return dict(repository) if repository is not None else None

    def get_product_module(self, module_id: str) -> dict | None:
        self.product_config_single_reads.append(f"get_product_module:{module_id}")
        module = self._product_config_collection("product_modules").get(module_id)
        return dict(module) if module is not None else None

    def product_module_has_related_records(self, product_id: str, module_code: str) -> bool:
        self.product_config_single_reads.append(
            f"product_module_has_related_records:{product_id}:{module_code}",
        )
        related_payloads = (
            (self.requirements_payload or {}).get("requirements", {}),
            (self.ai_tasks_payload or {}).get("ai_tasks", {}),
            (self.bugs_payload or {}).get("bugs", {}),
        )
        return any(
            item.get("product_id") == product_id and item.get("module_code") == module_code
            for payload in related_payloads
            for item in payload.values()
        )

    def product_version_has_related_records(self, version_id: str) -> bool:
        self.product_config_single_reads.append(
            f"product_version_has_related_records:{version_id}",
        )
        related_payloads = (
            (self.requirements_payload or {}).get("requirements", {}),
            (self.ai_tasks_payload or {}).get("ai_tasks", {}),
            (self.bugs_payload or {}).get("bugs", {}),
            self._product_config_collection("product_version_branch_configs"),
        )
        return any(
            item.get("version_id") == version_id
            for payload in related_payloads
            for item in payload.values()
        )

    def get_related_system(self, system_id: str) -> dict | None:
        self.product_config_single_reads.append(f"get_related_system:{system_id}")
        system = self._product_config_collection("related_systems").get(system_id)
        return dict(system) if system is not None else None

    def get_related_system_by_code(self, code: str) -> dict | None:
        self.product_config_single_reads.append(f"get_related_system_by_code:{code}")
        for system in self._product_config_collection("related_systems").values():
            if system.get("code") == code:
                return dict(system)
        return None

    def _branch_config_projection(self, branch_config: dict) -> dict:
        repository = self._product_config_collection("product_git_repositories").get(
            branch_config.get("repository_id"),
            {},
        )
        return {
            **dict(branch_config),
            "repository_default_branch": repository.get("default_branch"),
            "repository_name": repository.get("name"),
            "repository_path": repository.get("project_path"),
            "repository_provider": repository.get("git_provider"),
        }

    def get_product_version_branch_config(self, branch_config_id: str) -> dict | None:
        self.product_config_single_reads.append(
            f"get_product_version_branch_config:{branch_config_id}",
        )
        branch_config = self._product_config_collection("product_version_branch_configs").get(
            branch_config_id,
        )
        return (
            self._branch_config_projection(branch_config)
            if branch_config is not None
            else None
        )

    def list_product_versions(
        self,
        product_id: str,
        *,
        active_only: bool = False,
    ) -> list[dict]:
        self.product_config_single_reads.append(
            f"list_product_versions:{product_id}:{active_only}",
        )
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
        self.product_config_single_reads.append(
            f"list_product_modules:{product_id}:{active_only}",
        )
        modules = sorted(
            (
                dict(item)
                for item in self._product_config_collection("product_modules").values()
                if item.get("product_id") == product_id
            ),
            key=lambda item: (item.get("display_order", 0), item["code"]),
        )
        return [item for item in modules if not active_only or item.get("status") == "active"]

    def list_product_version_branch_configs(self, version_id: str) -> list[dict]:
        branch_configs = sorted(
            (
                self._branch_config_projection(item)
                for item in self._product_config_collection(
                    "product_version_branch_configs",
                ).values()
                if item.get("version_id") == version_id
            ),
            key=lambda item: (item.get("repository_name") or "", item["working_branch"]),
        )
        return list(branch_configs)

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
        product_scope_ids: list[str] | None = None,
    ) -> list[dict]:
        product_scope_set = set(product_scope_ids) if product_scope_ids is not None else None
        systems = sorted(
            (
                dict(item)
                for item in self._product_config_collection("related_systems").values()
                if product_id is None or item.get("product_id") == product_id
                if product_scope_set is None or str(item.get("product_id")) in product_scope_set
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
            "code_inspection_reports": [
                dict(item)
                for item in (self.code_inspection_payload or {})
                .get("code_inspection_reports", {})
                .values()
            ],
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

    def get_model_gateway_config(self, config_id: str) -> dict | None:
        payload = self.model_gateway_payload or {}
        config = payload.get("model_gateway_configs", {}).get(config_id)
        return dict(config) if config is not None else None

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

    def upsert_model_gateway_config_record(
        self,
        config: dict,
        *,
        audit_event: dict | None = None,
    ) -> None:
        payload = self.model_gateway_payload or {
            "model_gateway_configs": {},
            "model_gateway_logs": [],
        }
        configs = payload.setdefault("model_gateway_configs", {})
        if config.get("is_default"):
            for existing_config in configs.values():
                existing_config["is_default"] = False
        configs[config["id"]] = dict(config)
        self.model_gateway_payload = payload
        self.model_gateway_direct_writes.append(f"upsert:{config['id']}")
        if audit_event is not None:
            self._append_direct_audit_event(audit_event)

    def delete_model_gateway_config_record(
        self,
        config_id: str,
        *,
        audit_event: dict | None = None,
    ) -> None:
        payload = self.model_gateway_payload or {
            "model_gateway_configs": {},
            "model_gateway_logs": [],
        }
        payload.setdefault("model_gateway_configs", {}).pop(config_id, None)
        self.model_gateway_payload = payload
        self.model_gateway_direct_writes.append(f"delete:{config_id}")
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

    def list_assistant_chat_runs(self, *, user_id: str) -> list[dict]:
        payload = self.assistant_chat_payload or {}
        runs = [
            dict(run)
            for run in payload.get("assistant_chat_runs", {}).values()
            if run.get("user_id") == user_id
        ]
        runs.sort(key=lambda item: (item.get("updated_at", ""), item["id"]), reverse=True)
        return runs

    def get_assistant_chat_run(self, *, run_id: str) -> dict | None:
        payload = self.assistant_chat_payload or {}
        run = payload.get("assistant_chat_runs", {}).get(run_id)
        return dict(run) if run is not None else None

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

    def list_assistant_action_drafts(self, *, user_id: str) -> list[dict]:
        payload = self.assistant_chat_payload or {}
        drafts = [
            dict(draft)
            for draft in payload.get("assistant_action_drafts", {}).values()
            if draft.get("created_by") == user_id or draft.get("user_id") == user_id
        ]
        drafts.sort(key=lambda item: (item.get("updated_at", ""), item["id"]), reverse=True)
        return drafts

    def get_assistant_action_draft(self, *, draft_id: str) -> dict | None:
        payload = self.assistant_chat_payload or {}
        draft = payload.get("assistant_action_drafts", {}).get(draft_id)
        return dict(draft) if draft is not None else None

    def save_assistant_chat_records(
        self,
        *,
        chat_run: dict | None = None,
        conversation: dict | None,
        messages: list[dict],
        audit_events: list[dict],
        model_log: dict | None = None,
    ) -> None:
        payload = self.assistant_chat_payload or {
            "assistant_chat_runs": {},
            "assistant_conversations": {},
            "assistant_messages": {},
        }
        if chat_run is not None:
            payload.setdefault("assistant_chat_runs", {})[chat_run["id"]] = dict(chat_run)
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

    def save_assistant_action_records(
        self,
        *,
        draft: dict,
        audit_events: list[dict],
        run: dict | None = None,
    ) -> None:
        payload = self.assistant_chat_payload or {
            "assistant_action_drafts": {},
            "assistant_action_runs": {},
            "assistant_chat_runs": {},
            "assistant_conversations": {},
            "assistant_messages": {},
        }
        payload.setdefault("assistant_action_drafts", {})[draft["id"]] = dict(draft)
        if run is not None:
            payload.setdefault("assistant_action_runs", {})[run["id"]] = dict(run)
        self.assistant_chat_payload = payload
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

    def get_user_feedback(self, feedback_id: str) -> dict | None:
        payload = self.user_feedback_payload or {"user_feedback": {}}
        feedback = payload.get("user_feedback", {}).get(feedback_id)
        return dict(feedback) if feedback is not None else None

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

    def save_user_feedback_requirement_conversion(
        self,
        *,
        audit_events: list[dict],
        feedback: dict,
        requirement: dict,
    ) -> None:
        feedback_payload = self.user_feedback_payload or {"user_feedback": {}}
        feedback_payload.setdefault("user_feedback", {})[feedback["id"]] = dict(feedback)
        self.user_feedback_payload = feedback_payload
        requirements_payload = self.requirements_payload or {"requirements": {}}
        requirements_payload.setdefault("requirements", {})[requirement["id"]] = dict(requirement)
        self.requirements_payload = requirements_payload
        for audit_event in audit_events:
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


def auth_headers(username: str = "admin@example.com", password: str = "admin123") -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


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
