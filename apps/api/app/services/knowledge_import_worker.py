from __future__ import annotations

import logging
import queue
import threading
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException

from app.services.knowledge_deposits import knowledge_write_store
from app.services.knowledge_management import (
    get_knowledge_import_job_from_memory,
    put_knowledge_import_job_to_memory,
    run_knowledge_import_job_result,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class KnowledgeImportWorkItem:
    job_id: str
    user: dict[str, Any]


def _system_import_user() -> dict[str, Any]:
    return {
        "id": "system_knowledge_import_worker",
        "username": "system_knowledge_import_worker",
        "display_name": "Knowledge Import Worker",
        "roles": ["admin"],
        "scope_summary": [],
    }


def _worker_user_for_import_job(import_job: dict[str, Any]) -> dict[str, Any]:
    user_id = str(import_job.get("created_by") or _system_import_user()["id"])
    return {
        "id": user_id,
        "username": user_id,
        "display_name": "Knowledge Import Worker",
        "roles": ["admin"],
        "scope_summary": [],
    }


def _knowledge_import_job_records(current_store: Any) -> list[dict[str, Any]]:
    jobs = getattr(current_store, "knowledge_import_jobs", {})
    if isinstance(jobs, dict):
        return list(jobs.values())
    return list(jobs or [])


class KnowledgeImportWorker:
    def __init__(
        self,
        *,
        app: Any,
        lock_ttl_seconds: float = 300.0,
        poll_interval_seconds: float = 1.0,
    ) -> None:
        self.app = app
        self.lock_ttl_seconds = max(1.0, lock_ttl_seconds)
        self.poll_interval_seconds = max(0.01, poll_interval_seconds)
        self.worker_id = f"knowledge-import-worker-{uuid.uuid4().hex[:12]}"
        self._queue: queue.Queue[KnowledgeImportWorkItem] = queue.Queue()
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._queued_job_ids: set[str] = set()
        self._active_job_id: str | None = None
        self.processed_count = 0
        self.failed_count = 0

    @property
    def is_running(self) -> bool:
        thread = self._thread
        return thread is not None and thread.is_alive()

    def start(self) -> None:
        if self.is_running:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop,
            name="knowledge-import-worker",
            daemon=True,
        )
        self._thread.start()

    def stop(self, *, timeout_seconds: float | None = None) -> None:
        self._stop_event.set()
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout_seconds if timeout_seconds is not None else 5.0)

    def enqueue(self, *, job_id: str, user: dict[str, Any]) -> bool:
        if not job_id:
            return False
        user_snapshot = dict(user)
        with self._lock:
            if job_id in self._queued_job_ids or job_id == self._active_job_id:
                return False
            self._queued_job_ids.add(job_id)
            self._queue.put(KnowledgeImportWorkItem(job_id=job_id, user=user_snapshot))
        return True

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "enabled": True,
                "running": self.is_running,
                "worker_id": self.worker_id,
                "pending_count": self._queue.qsize(),
                "active_job_id": self._active_job_id,
                "queued_job_ids": sorted(self._queued_job_ids),
                "processed_count": self.processed_count,
                "failed_count": self.failed_count,
            }

    def enqueue_existing_queued_jobs(self, *, user: dict[str, Any] | None = None) -> int:
        current_store = knowledge_write_store(self.app.state.store)
        count = 0
        for import_job in _knowledge_import_job_records(current_store):
            if import_job.get("status") == "queued":
                import_user = user or _worker_user_for_import_job(import_job)
                if self.enqueue(job_id=import_job["id"], user=import_user):
                    count += 1
        return count

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                item = self._queue.get(timeout=self.poll_interval_seconds)
            except queue.Empty:
                try:
                    self.enqueue_existing_queued_jobs()
                except Exception:  # noqa: BLE001
                    logger.exception("Knowledge import worker sweep failed")
                continue
            self._process_item(item)
            self._queue.task_done()

    def _process_item(self, item: KnowledgeImportWorkItem) -> None:
        with self._lock:
            self._queued_job_ids.discard(item.job_id)
            self._active_job_id = item.job_id
        try:
            if not self._claim_item(item):
                logger.info("Skip unclaimed knowledge import job %s", item.job_id)
                return
            result = run_knowledge_import_job_result(
                current_store=knowledge_write_store(self.app.state.store),
                job_id=item.job_id,
                user=item.user,
            )
            self.processed_count += 1
            if result.get("import_job", {}).get("status") == "failed":
                self.failed_count += 1
        except HTTPException as exc:
            if _http_error_code(exc) == "IMPORT_JOB_STATE_INVALID":
                logger.info("Skip non-runnable knowledge import job %s", item.job_id)
            else:
                self.failed_count += 1
                logger.exception("Knowledge import job %s failed with API error", item.job_id)
        except Exception:  # noqa: BLE001
            self.failed_count += 1
            logger.exception("Knowledge import job %s failed unexpectedly", item.job_id)
        finally:
            with self._lock:
                if self._active_job_id == item.job_id:
                    self._active_job_id = None

    def _claim_item(self, item: KnowledgeImportWorkItem) -> bool:
        repository = getattr(self.app.state.store, "repository", None)
        claim = getattr(repository, "claim_knowledge_import_job", None)
        if callable(claim):
            return bool(
                claim(
                    job_id=item.job_id,
                    worker_id=self.worker_id,
                    lock_ttl_seconds=self.lock_ttl_seconds,
                ),
            )

        current_store = knowledge_write_store(self.app.state.store)
        import_job = get_knowledge_import_job_from_memory(current_store, item.job_id)
        if import_job is None or import_job.get("status") != "queued":
            return False
        import_job = {
            **import_job,
            "locked_by": self.worker_id,
            "locked_until": (
                datetime.now(UTC) + timedelta(seconds=self.lock_ttl_seconds)
            ).isoformat(),
            "attempt_count": int(import_job.get("attempt_count", 0) or 0) + 1,
        }
        put_knowledge_import_job_to_memory(current_store, import_job)
        return True


def _http_error_code(exc: HTTPException) -> str | None:
    if isinstance(exc.detail, dict):
        code = exc.detail.get("code")
        return str(code) if code is not None else None
    return None


def enqueue_knowledge_import_job(app: Any, *, job_id: str, user: dict[str, Any]) -> bool:
    worker = getattr(app.state, "knowledge_import_worker", None)
    enqueue = getattr(worker, "enqueue", None)
    if not callable(enqueue):
        return False
    return bool(enqueue(job_id=job_id, user=user))


def enqueue_existing_queued_import_jobs(app: Any) -> int:
    worker = getattr(app.state, "knowledge_import_worker", None)
    enqueue_existing = getattr(worker, "enqueue_existing_queued_jobs", None)
    if callable(enqueue_existing):
        return int(enqueue_existing())
    enqueue = getattr(worker, "enqueue", None)
    if not callable(enqueue):
        return 0
    current_store = knowledge_write_store(app.state.store)
    count = 0
    for import_job in _knowledge_import_job_records(current_store):
        if import_job.get("status") == "queued":
            user = _worker_user_for_import_job(import_job)
            if enqueue(job_id=import_job["id"], user=user):
                count += 1
    return count


def start_knowledge_import_worker(app: Any, settings: Any) -> KnowledgeImportWorker | None:
    if not getattr(settings, "knowledge_import_worker_enabled", False):
        return None
    worker = getattr(app.state, "knowledge_import_worker", None)
    if not isinstance(worker, KnowledgeImportWorker):
        worker = KnowledgeImportWorker(
            app=app,
            poll_interval_seconds=getattr(
                settings,
                "knowledge_import_worker_poll_interval_seconds",
                1.0,
            ),
            lock_ttl_seconds=getattr(
                settings,
                "knowledge_import_worker_lock_ttl_seconds",
                300.0,
            ),
        )
        app.state.knowledge_import_worker = worker
    worker.start()
    enqueued = enqueue_existing_queued_import_jobs(app)
    if enqueued:
        logger.info("Enqueued %s pending knowledge import jobs on startup", enqueued)
    return worker


def stop_knowledge_import_worker(app: Any) -> None:
    worker = getattr(app.state, "knowledge_import_worker", None)
    stop = getattr(worker, "stop", None)
    if callable(stop):
        stop()


def knowledge_import_worker_status(app: Any, settings: Any) -> dict[str, Any]:
    worker = getattr(app.state, "knowledge_import_worker", None)
    status = getattr(worker, "status", None)
    if callable(status):
        return status()
    return {
        "enabled": bool(getattr(settings, "knowledge_import_worker_enabled", False)),
        "running": False,
        "worker_id": None,
        "pending_count": 0,
        "active_job_id": None,
        "queued_job_ids": [],
        "processed_count": 0,
        "failed_count": 0,
    }
