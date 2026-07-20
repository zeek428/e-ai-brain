from __future__ import annotations

import logging
import os
import threading
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from app.services import scheduled_job_store as job_store
from app.services.scheduled_job_config import next_run_at

logger = logging.getLogger(__name__)


def _scheduler_user(worker_id: str) -> dict[str, Any]:
    return {
        "id": worker_id,
        "permissions": [
            "system.plugins.manage",
            "system.scheduled_jobs.manage",
            "system.scheduled_jobs.run",
        ],
        "roles": ["admin"],
    }


def _due_at(job: dict[str, Any], *, now: datetime) -> bool:
    next_run = job.get("next_run_at")
    if not next_run or not job.get("enabled") or job.get("status") != "active":
        return False
    if job.get("schedule_type") == "manual":
        return False
    try:
        return datetime.fromisoformat(str(next_run).replace("Z", "+00:00")) <= now
    except (TypeError, ValueError):
        return False


def _claim_due_job(
    current_store: Any,
    *,
    job: dict[str, Any],
    now: datetime,
) -> dict[str, Any] | None:
    scheduled_for = str(job.get("next_run_at") or "")
    if not scheduled_for:
        return None
    try:
        scheduled_for_at = datetime.fromisoformat(scheduled_for.replace("Z", "+00:00"))
        future_next_run = next_run_at(job, now=scheduled_for_at)
    except Exception:  # noqa: BLE001 - an invalid schedule must not block other jobs.
        logger.exception("Unable to calculate next run time for scheduled job %s", job.get("id"))
        return None
    if not future_next_run:
        return None
    repository = getattr(current_store, "repository", None)
    claim_due = getattr(repository, "claim_due_scheduled_job", None)
    if callable(claim_due):
        claimed_job = claim_due(
            expected_next_run_at=scheduled_for,
            job_id=str(job["id"]),
            next_run_at=future_next_run,
            updated_at=now.isoformat(),
        )
        if claimed_job is None:
            return None
        return {"job_id": str(claimed_job["id"]), "scheduled_for": scheduled_for}

    stored_job = job_store.read_memory_dict(current_store, "scheduled_jobs").get(str(job["id"]))
    if not isinstance(stored_job, dict) or stored_job.get("next_run_at") != scheduled_for:
        return None
    claimed_job = {
        **stored_job,
        "next_run_at": future_next_run,
        "updated_at": now.isoformat(),
    }
    job_store.put_memory_record(current_store, "scheduled_jobs", claimed_job)
    job_store.persist_record(current_store, "save_scheduled_job_record", claimed_job)
    return {"job_id": str(claimed_job["id"]), "scheduled_for": scheduled_for}


def claim_due_scheduled_jobs(
    current_store: Any,
    *,
    limit: int,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    current_time = now or datetime.now(UTC)
    repository = getattr(current_store, "repository", None)
    list_due = getattr(repository, "list_due_scheduled_jobs", None)
    if callable(list_due):
        candidates = list_due(due_at=current_time.isoformat(), limit=limit)
    else:
        candidates = [
            job
            for job in job_store.read_memory_dict(current_store, "scheduled_jobs").values()
            if _due_at(job, now=current_time)
        ]
        candidates.sort(
            key=lambda item: (
                str(item.get("next_run_at") or ""),
                str(item.get("id") or ""),
            ),
        )
        candidates = candidates[:limit]
    claims: list[dict[str, Any]] = []
    for job in candidates:
        try:
            claim = _claim_due_job(current_store, job=job, now=current_time)
        except Exception:  # noqa: BLE001 - one invalid job must not block the queue.
            logger.exception("Unable to claim scheduled job %s", job.get("id"))
            continue
        if claim is not None:
            claims.append(claim)
    return claims


def run_due_scheduled_jobs_once(
    current_store: Any,
    *,
    limit: int,
    now: datetime | None = None,
    run_job: Callable[..., dict[str, Any]] | None = None,
    worker_id: str = "system_scheduled_job_worker",
) -> int:
    if run_job is None:
        from app.services.scheduled_jobs import run_scheduled_job_response

        run_job = run_scheduled_job_response
    claims = claim_due_scheduled_jobs(current_store, limit=limit, now=now)
    user = _scheduler_user(worker_id)
    for claim in claims:
        run_job(
            current_store=current_store,
            job_id=claim["job_id"],
            scheduled_for=claim["scheduled_for"],
            source_run_id=None,
            trigger_type="scheduler",
            user=user,
        )
    return len(claims)


def _run_claim(**kwargs: Any) -> dict[str, Any]:
    from app.services.scheduled_jobs import run_scheduled_job_response

    return run_scheduled_job_response(**kwargs)


def _dispatch_claim(application: Any, claim: dict[str, Any], worker_id: str) -> None:
    user = _scheduler_user(worker_id)
    try:
        _run_claim(
            current_store=application.state.store,
            job_id=claim["job_id"],
            scheduled_for=claim["scheduled_for"],
            source_run_id=None,
            trigger_type="scheduler",
            user=user,
        )
    except Exception:  # noqa: BLE001 - a failed job must not stop later scheduled jobs.
        logger.exception("Scheduled job execution failed for %s", claim.get("job_id"))


def _worker_loop(
    application: Any,
    stop_event: threading.Event,
    settings: Any,
    worker_id: str,
) -> None:
    interval = max(1.0, float(getattr(settings, "scheduled_job_worker_poll_interval_seconds", 5.0)))
    batch_size = max(1, int(getattr(settings, "scheduled_job_worker_batch_size", 10)))
    while not stop_event.is_set():
        try:
            claims = claim_due_scheduled_jobs(application.state.store, limit=batch_size)
            for claim in claims:
                threading.Thread(
                    target=_dispatch_claim,
                    args=(application, claim, worker_id),
                    daemon=True,
                    name=f"scheduled-job-dispatch-{claim['job_id']}",
                ).start()
        except Exception:  # noqa: BLE001 - keep the scheduling worker alive.
            logger.exception("Scheduled job worker iteration failed")
        stop_event.wait(interval)


def start_scheduled_job_worker(application: Any, settings: Any) -> None:
    if not getattr(settings, "scheduled_job_worker_enabled", False):
        return
    current = getattr(application.state, "scheduled_job_worker", None)
    if isinstance(current, dict) and isinstance(current.get("thread"), threading.Thread):
        return
    stop_event = threading.Event()
    worker_id = f"system_scheduled_job_worker:{os.getpid()}"
    thread = threading.Thread(
        target=_worker_loop,
        args=(application, stop_event, settings, worker_id),
        daemon=True,
        name="scheduled-job-worker",
    )
    application.state.scheduled_job_worker = {
        "stop_event": stop_event,
        "thread": thread,
        "worker_id": worker_id,
    }
    thread.start()


def stop_scheduled_job_worker(application: Any) -> None:
    current = getattr(application.state, "scheduled_job_worker", None)
    if not isinstance(current, dict):
        return
    stop_event = current.get("stop_event")
    thread = current.get("thread")
    if isinstance(stop_event, threading.Event):
        stop_event.set()
    if isinstance(thread, threading.Thread):
        thread.join(timeout=5)
    application.state.scheduled_job_worker = None
