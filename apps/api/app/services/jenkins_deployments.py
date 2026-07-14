from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime, timedelta
from time import perf_counter
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urljoin, urlsplit, urlunsplit
from urllib.request import Request, urlopen

from app.api.deps import api_error
from app.services.operational_records import read_memory_dict, record_audit_event
from app.services.plugin_invocation_runtime import _build_headers_with_sources
from app.services.task_workflow_context import task_workflow_write_store

JENKINS_PREFLIGHT_MAX_AGE_SECONDS = 600
_JENKINS_PREFLIGHT_CONFIG_KEY = "_ai_brain_deployment_preflight"
_SECRET_CONFIG_KEY = re.compile(
    r"(?:authorization|credential|password|private[_-]?key|secret|token)",
    re.IGNORECASE,
)


def _parse_utc_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _repository(current_store: Any) -> Any | None:
    return getattr(current_store, "repository", None)


def _connection_by_id(current_store: Any, connection_id: str) -> dict[str, Any]:
    connection = read_memory_dict(current_store, "plugin_connections").get(connection_id)
    if connection is not None:
        return dict(connection)
    repository = _repository(current_store)
    list_connections = getattr(repository, "list_plugin_connections", None)
    if callable(list_connections):
        for candidate in list_connections(status="active"):
            if candidate.get("id") == connection_id:
                return dict(candidate)
    raise api_error(404, "NOT_FOUND", "Jenkins connection not found")


def _save_plugin_connection(
    current_store: Any,
    connection: dict[str, Any],
    *,
    audit_event: dict[str, Any] | None = None,
) -> None:
    repository = _repository(current_store)
    save_record = getattr(repository, "save_plugin_connection_record", None)
    if callable(save_record):
        save_record(connection, audit_event=audit_event)
    read_memory_dict(current_store, "plugin_connections")[str(connection["id"])] = connection


def _fingerprint_value(value: Any, *, key: str = "") -> Any:
    if _SECRET_CONFIG_KEY.search(key):
        return "<redacted>"
    if isinstance(value, dict):
        return {
            str(item_key): _fingerprint_value(item_value, key=str(item_key))
            for item_key, item_value in sorted(value.items(), key=lambda item: str(item[0]))
            if str(item_key) != _JENKINS_PREFLIGHT_CONFIG_KEY
        }
    if isinstance(value, list):
        return [_fingerprint_value(item, key=key) for item in value]
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    return str(value)


def jenkins_connection_config_fingerprint(connection: dict[str, Any]) -> str:
    canonical = {
        "auth_config": _fingerprint_value(connection.get("auth_config") or {}),
        "auth_type": str(connection.get("auth_type") or ""),
        "endpoint_url": str(connection.get("endpoint_url") or ""),
        "request_config": _fingerprint_value(connection.get("request_config") or {}),
        "status": str(connection.get("status") or ""),
        "timeout_seconds": int(connection.get("timeout_seconds") or 30),
    }
    encoded = json.dumps(canonical, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _jenkins_preflight_record(connection: dict[str, Any], job_name: str) -> dict[str, Any] | None:
    request_config = connection.get("request_config")
    if not isinstance(request_config, dict):
        return None
    preflight = request_config.get(_JENKINS_PREFLIGHT_CONFIG_KEY)
    if not isinstance(preflight, dict):
        return None
    jobs = preflight.get("jobs")
    if not isinstance(jobs, dict):
        return None
    record = jobs.get(job_name)
    return dict(record) if isinstance(record, dict) else None


def jenkins_deployment_preflight_state(
    connection: dict[str, Any],
    *,
    job_name: str,
    max_age_seconds: int = JENKINS_PREFLIGHT_MAX_AGE_SECONDS,
    now: datetime | None = None,
) -> dict[str, Any]:
    record = _jenkins_preflight_record(connection, job_name)
    if record is None:
        return {"ready": False, "status": "not_probed"}
    state: dict[str, Any] = {
        "checked_at": record.get("checked_at"),
        "duration_ms": record.get("duration_ms"),
        "error_code": record.get("error_code"),
        "ready": False,
        "status": str(record.get("status") or "failed"),
    }
    if (
        record.get("connection_config_fingerprint")
        != jenkins_connection_config_fingerprint(connection)
    ):
        return {**state, "status": "configuration_changed"}
    if state["status"] != "succeeded":
        return state
    checked_at = _parse_utc_datetime(record.get("checked_at"))
    if checked_at is None:
        return {**state, "status": "invalid"}
    age_seconds = max(0, int(((now or datetime.now(UTC)) - checked_at).total_seconds()))
    if age_seconds > max_age_seconds:
        return {**state, "age_seconds": age_seconds, "status": "stale"}
    return {**state, "age_seconds": age_seconds, "ready": True}


def _store_jenkins_preflight(
    current_store: Any,
    *,
    connection: dict[str, Any],
    job_name: str,
    record: dict[str, Any],
    user_id: str,
) -> dict[str, Any]:
    request_config = dict(connection.get("request_config") or {})
    previous = request_config.get(_JENKINS_PREFLIGHT_CONFIG_KEY)
    jobs = dict(previous.get("jobs") or {}) if isinstance(previous, dict) else {}
    jobs[job_name] = record
    updated = {
        **connection,
        "request_config": {
            **request_config,
            _JENKINS_PREFLIGHT_CONFIG_KEY: {"jobs": jobs},
        },
        "updated_at": datetime.now(UTC).isoformat(),
    }
    event = record_audit_event(
        current_store,
        event_type=f"deployment.jenkins_preflight.{record['status']}",
        actor_id=user_id,
        subject_type="plugin_connection",
        subject_id=str(connection["id"]),
        payload={"job_name": job_name, "status": record["status"]},
    )
    _save_plugin_connection(current_store, updated, audit_event=event)
    return updated


def probe_jenkins_deployment_connection(
    *,
    current_store: Any,
    connection_id: str,
    job_name: str,
    user_id: str,
) -> dict[str, Any]:
    """Perform a non-mutating Jenkins API and Job accessibility preflight."""
    connection = _connection_by_id(current_store, connection_id)
    normalized_job_name = str(job_name or "").strip()
    if connection.get("status") != "active":
        raise api_error(409, "JENKINS_CONNECTION_UNAVAILABLE", "Jenkins connection is disabled")
    if not normalized_job_name:
        raise api_error(400, "VALIDATION_ERROR", "jenkins_job_name is required")
    endpoint = str(connection.get("endpoint_url") or "").rstrip("/")
    started_at = perf_counter()
    status = "succeeded"
    error_code: str | None = None
    try:
        _request_json(connection, f"{endpoint}/api/json")
        job_payload = _request_json(
            connection,
            f"{endpoint}/{_job_path(normalized_job_name)}/api/json",
        )
        if not job_payload.get("name"):
            raise ValueError("Jenkins Job did not return a name")
    except HTTPError as exc:
        status = "failed"
        error_code = (
            "JENKINS_AUTHORIZATION_FAILED"
            if exc.code in {401, 403}
            else "JENKINS_JOB_UNAVAILABLE"
        )
    except URLError:
        status = "failed"
        error_code = "JENKINS_CONNECTIVITY_FAILED"
    except Exception:  # noqa: BLE001 - external preflight errors are reduced to bounded evidence.
        status = "failed"
        error_code = "JENKINS_PREFLIGHT_FAILED"
    record = {
        "checked_at": datetime.now(UTC).isoformat(),
        "connection_config_fingerprint": jenkins_connection_config_fingerprint(connection),
        "duration_ms": int((perf_counter() - started_at) * 1000),
        "error_code": error_code,
        "status": status,
    }
    updated_connection = _store_jenkins_preflight(
        current_store,
        connection=connection,
        job_name=normalized_job_name,
        record=record,
        user_id=user_id,
    )
    return {
        "connection_id": connection_id,
        "job_name": normalized_job_name,
        "probe": jenkins_deployment_preflight_state(
            updated_connection,
            job_name=normalized_job_name,
        ),
    }


def require_jenkins_deployment_preflight(
    *,
    connection: dict[str, Any],
    job_name: str,
    max_age_seconds: int,
) -> dict[str, Any]:
    state = jenkins_deployment_preflight_state(
        connection,
        job_name=job_name,
        max_age_seconds=max_age_seconds,
    )
    if not state["ready"]:
        raise api_error(
            409,
            "JENKINS_CONNECTIVITY_UNVERIFIED",
            "Configured Jenkins Job requires a successful recent connectivity preflight",
            {"job_name": job_name, "max_age_seconds": max_age_seconds, "probe": state},
        )
    return state


def _save_plugin_invocation_log(current_store: Any, record: dict[str, Any]) -> None:
    repository = _repository(current_store)
    save_record = getattr(repository, "save_plugin_invocation_log_record", None)
    if callable(save_record):
        save_record(record)
    read_memory_dict(current_store, "plugin_invocation_logs")[str(record["id"])] = record


def _save_deployment_run(
    current_store: Any,
    record: dict[str, Any],
    *,
    audit_event: dict[str, Any] | None = None,
) -> None:
    repository = _repository(current_store)
    save_record = getattr(repository, "save_deployment_run_record", None)
    if callable(save_record):
        save_record(record, audit_events=[audit_event] if audit_event else None)
    read_memory_dict(current_store, "deployment_runs")[str(record["id"])] = record


def _save_deployment_request(
    current_store: Any,
    record: dict[str, Any],
    *,
    audit_event: dict[str, Any] | None = None,
) -> None:
    repository = _repository(current_store)
    save_record = getattr(repository, "save_deployment_request_record", None)
    if callable(save_record):
        save_record(record, audit_events=[audit_event] if audit_event else None)
    read_memory_dict(current_store, "deployment_requests")[str(record["id"])] = record


def _jenkins_headers(connection: dict[str, Any]) -> dict[str, str]:
    headers, _ = _build_headers_with_sources(connection, {"request_config": {}}, {})
    if "Authorization" not in headers:
        raise api_error(
            400,
            "JENKINS_CREDENTIAL_UNAVAILABLE",
            "Jenkins credential reference cannot be resolved",
        )
    return headers


def _job_path(job_name: str) -> str:
    segments = [segment.strip() for segment in job_name.split("/") if segment.strip()]
    if not segments:
        raise api_error(400, "VALIDATION_ERROR", "jenkins_job_name is required")
    return "/".join(f"job/{quote(segment, safe='')}" for segment in segments)


def _request(
    connection: dict[str, Any],
    *,
    data: bytes | None = None,
    method: str,
    url: str,
):
    request = Request(
        url,
        data=data,
        headers={
            **_jenkins_headers(connection),
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method=method,
    )
    return urlopen(request, timeout=int(connection.get("timeout_seconds") or 30))


def _request_json(connection: dict[str, Any], url: str) -> dict[str, Any]:
    with _request(connection, method="GET", url=url) as response:
        raw = response.read().decode("utf-8")
    try:
        payload = json.loads(raw) if raw else {}
    except json.JSONDecodeError as exc:
        raise api_error(502, "JENKINS_RESPONSE_INVALID", "Jenkins returned invalid JSON") from exc
    return payload if isinstance(payload, dict) else {}


def _jenkins_origin(value: str) -> tuple[str, str, int | None]:
    parsed = urlsplit(value)
    scheme = parsed.scheme.lower()
    if scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Jenkins URL must use HTTP or HTTPS")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("Jenkins URL must not contain user information")
    default_port = 443 if scheme == "https" else 80
    return scheme, parsed.hostname.lower(), parsed.port or default_port


def _resolve_jenkins_resource_url(endpoint: str, candidate: str) -> str:
    resolved = urljoin(endpoint, candidate)
    if _jenkins_origin(resolved) != _jenkins_origin(endpoint):
        raise ValueError("Jenkins resource URL is outside the configured endpoint origin")
    return resolved


def _validated_jenkins_resource_url(endpoint: str, candidate: str) -> str:
    try:
        return _resolve_jenkins_resource_url(endpoint, candidate)
    except ValueError as exc:
        raise api_error(
            502,
            "JENKINS_RESOURCE_URL_INVALID",
            "Jenkins returned a resource URL outside the configured endpoint",
        ) from exc


def _next_sync_at(attempts: int) -> str:
    seconds = min(60, max(2, 2 ** min(attempts, 5)))
    return (datetime.now(UTC) + timedelta(seconds=seconds)).isoformat()


def _jenkins_queue_cancel_url(queue_url: str) -> str:
    parsed = urlsplit(queue_url)
    segments = [segment for segment in parsed.path.split("/") if segment]
    try:
        queue_index = segments.index("queue")
        if segments[queue_index + 1] != "item":
            raise ValueError
        queue_id = segments[queue_index + 2]
    except (IndexError, ValueError) as exc:
        raise api_error(
            409,
            "JENKINS_QUEUE_URL_INVALID",
            "Jenkins queue URL is invalid",
        ) from exc
    cancel_path = "/" + "/".join([*segments[: queue_index + 1], "cancelItem"])
    return urlunsplit(
        (parsed.scheme, parsed.netloc, cancel_path, urlencode({"id": queue_id}), "")
    )


def _record_jenkins_trigger_failure(
    current_store: Any,
    *,
    deployment: dict[str, Any],
    error_type: str,
    failure_reason: str,
    run: dict[str, Any],
    user: dict[str, Any],
) -> None:
    now = datetime.now(UTC).isoformat()
    failed_run = {
        **run,
        "failure_reason": failure_reason,
        "finished_at": now,
        "logs": [
            *[dict(item) for item in run.get("logs") or [] if isinstance(item, dict)],
            {"level": "error", "message": failure_reason, "timestamp": now},
        ],
        "next_sync_at": None,
        "status": "failed",
        "sync_lease_owner": None,
        "sync_lease_until": None,
        "updated_at": now,
    }
    failed_deployment = {
        **deployment,
        "failure_reason": failure_reason,
        "finished_at": now,
        "status": "failed",
        "updated_at": now,
    }
    run_event = record_audit_event(
        current_store,
        event_type="deployment.run.jenkins_trigger_failed",
        actor_id=user["id"],
        subject_type="deployment_run",
        subject_id=str(run["id"]),
        payload={"deployment_request_id": deployment["id"], "error_type": error_type},
    )
    deployment_event = record_audit_event(
        current_store,
        event_type="deployment.request.jenkins_trigger_failed",
        actor_id=user["id"],
        subject_type="deployment_request",
        subject_id=str(deployment["id"]),
        payload={"deployment_run_id": run["id"], "error_type": error_type},
    )
    _save_deployment_run(current_store, failed_run, audit_event=run_event)
    _save_deployment_request(
        current_store,
        failed_deployment,
        audit_event=deployment_event,
    )


def trigger_jenkins_deployment(
    *,
    current_store: Any,
    deployment: dict[str, Any],
    run: dict[str, Any],
    user: dict[str, Any],
    operation: str = "deploy",
    record_failure: bool = True,
) -> dict[str, Any]:
    snapshot = dict(deployment.get("scheme_snapshot") or {})
    connection_id = str(snapshot.get("jenkins_connection_id") or "").strip()
    connection = _connection_by_id(current_store, connection_id)
    if connection.get("status") != "active":
        raise api_error(409, "JENKINS_CONNECTION_UNAVAILABLE", "Jenkins connection is disabled")
    rollback_config = (
        snapshot.get("rollback_config")
        if isinstance(snapshot.get("rollback_config"), dict)
        else {}
    )
    health_config = (
        snapshot.get("health_check_config")
        if isinstance(snapshot.get("health_check_config"), dict)
        else {}
    )
    job_name = str(
        (
            rollback_config.get("job_name")
            if operation == "rollback"
            else health_config.get("job_name")
            if operation == "verify"
            else snapshot.get("jenkins_job_name")
        )
        or ""
    ).strip()
    if not job_name:
        raise api_error(
            409,
            "JENKINS_ROLLBACK_NOT_CONFIGURED"
            if operation == "rollback"
            else "JENKINS_JOB_NOT_CONFIGURED",
            "Jenkins rollback job is not configured"
            if operation == "rollback"
            else "Jenkins health verification job is not configured"
            if operation == "verify"
            else "Jenkins deployment job is not configured",
        )
    if operation == "deploy":
        from app.services.ai_executor_runner_deployment_probes import (
            deployment_probe_max_age_seconds,
        )

        require_jenkins_deployment_preflight(
            connection=connection,
            job_name=job_name,
            max_age_seconds=deployment_probe_max_age_seconds(
                environment=str(deployment.get("environment") or "prod"),
                risk_level=str(deployment.get("risk_level") or "medium"),
                scheme=snapshot,
            ),
        )
    endpoint = str(connection.get("endpoint_url") or "").rstrip("/") + "/"
    trigger_url = urljoin(endpoint, f"{_job_path(job_name)}/buildWithParameters")
    config = snapshot.get("config") if isinstance(snapshot.get("config"), dict) else {}
    configured_parameters = (
        dict(
            rollback_config.get("parameters")
            if operation == "rollback"
            else health_config.get("parameters")
            if operation == "verify"
            else config.get("parameters")
        )
        if isinstance(
            rollback_config.get("parameters")
            if operation == "rollback"
            else health_config.get("parameters")
            if operation == "verify"
            else config.get("parameters"),
            dict,
        )
        else {}
    )
    parameters = {
        **configured_parameters,
        "AI_BRAIN_DEPLOYMENT_REQUEST_ID": deployment["id"],
        "AI_BRAIN_DEPLOYMENT_RUN_ID": run["id"],
        "AI_BRAIN_ENVIRONMENT": deployment.get("environment") or "prod",
        "AI_BRAIN_OPERATION": operation,
    }
    body = urlencode(
        {
            str(key): str(value)
            for key, value in parameters.items()
            if value is not None
        }
    ).encode("utf-8")
    try:
        with _request(connection, data=body, method="POST", url=trigger_url) as response:
            queue_location = response.headers.get("Location")
    except Exception as exc:
        failure_reason = f"Jenkins trigger failed: {type(exc).__name__}"
        if record_failure:
            _record_jenkins_trigger_failure(
                current_store,
                deployment=deployment,
                error_type=type(exc).__name__,
                failure_reason=failure_reason,
                run=run,
                user=user,
            )
        raise api_error(
            502,
            "JENKINS_TRIGGER_FAILED",
            failure_reason,
        ) from exc
    if not queue_location:
        if record_failure:
            _record_jenkins_trigger_failure(
                current_store,
                deployment=deployment,
                error_type="missing_queue_location",
                failure_reason="Jenkins did not return queue URL",
                run=run,
                user=user,
            )
        raise api_error(502, "JENKINS_QUEUE_LOCATION_MISSING", "Jenkins did not return queue URL")
    try:
        queue_url = _resolve_jenkins_resource_url(endpoint, str(queue_location))
    except ValueError as exc:
        failure_reason = "Jenkins returned an invalid queue URL"
        if record_failure:
            _record_jenkins_trigger_failure(
                current_store,
                deployment=deployment,
                error_type="invalid_queue_url",
                failure_reason=failure_reason,
                run=run,
                user=user,
            )
        raise api_error(
            502,
            "JENKINS_RESOURCE_URL_INVALID",
            failure_reason,
        ) from exc
    now = datetime.now(UTC).isoformat()
    invocation_log = {
        "id": current_store.new_id("plugin_invocation_log"),
        "plugin_id": connection.get("plugin_id"),
        "connection_id": connection_id,
        "action_id": None,
        "scheduled_job_id": None,
        "scheduled_job_run_id": None,
        "trigger_type": "deployment",
        "status": "succeeded",
        "request_summary": {
            "deployment_request_id": deployment["id"],
            "job_name": job_name,
            "operation": operation,
            "parameter_names": sorted(parameters),
        },
        "response_summary": {"queue_url": queue_url},
        "latency_ms": None,
        "error_code": None,
        "error_message": None,
        "trace_id": None,
        "created_by": user["id"],
        "created_at": now,
        "updated_at": now,
    }
    _save_plugin_invocation_log(current_store, invocation_log)
    updated_run = {
        **run,
        "external_job_name": job_name,
        "external_queue_url": queue_url,
        "next_sync_at": now,
        "plugin_invocation_log_id": invocation_log["id"],
        "status": "queued",
        "sync_attempts": 0,
        "sync_lease_owner": None,
        "sync_lease_until": None,
        "updated_at": now,
    }
    event = record_audit_event(
        current_store,
        event_type="deployment.run.jenkins_queued",
        actor_id=user["id"],
        subject_type="deployment_run",
        subject_id=str(run["id"]),
        payload={"job_name": job_name, "queue_url": queue_url},
    )
    _save_deployment_run(current_store, updated_run, audit_event=event)
    return updated_run


def _deployment_and_run(
    current_store: Any,
    *,
    deployment_request_id: str,
    deployment_run_id: str,
) -> tuple[Any, dict[str, Any], dict[str, Any]]:
    write_store = task_workflow_write_store(current_store)
    deployment = read_memory_dict(write_store, "deployment_requests").get(deployment_request_id)
    run = read_memory_dict(write_store, "deployment_runs").get(deployment_run_id)
    if (
        deployment is None
        or run is None
        or run.get("deployment_request_id") != deployment_request_id
    ):
        raise api_error(404, "NOT_FOUND", "Deployment run not found")
    if run.get("executor_channel") != "integration" or run.get("deployment_method") != "jenkins":
        raise api_error(409, "DEPLOYMENT_EXECUTOR_INVALID", "Deployment run is not Jenkins")
    return write_store, dict(deployment), dict(run)


def sync_jenkins_deployment(
    *,
    current_store: Any,
    deployment_request_id: str,
    deployment_run_id: str,
    actor_id: str,
) -> dict[str, Any]:
    write_store, deployment, run = _deployment_and_run(
        current_store,
        deployment_request_id=deployment_request_id,
        deployment_run_id=deployment_run_id,
    )
    snapshot = dict(deployment.get("scheme_snapshot") or {})
    connection = _connection_by_id(current_store, str(snapshot.get("jenkins_connection_id") or ""))
    endpoint = str(connection.get("endpoint_url") or "").rstrip("/") + "/"
    attempts = int(run.get("sync_attempts") or 0) + 1
    now = datetime.now(UTC).isoformat()
    task_status = "running"
    error_message: str | None = None
    logs = [dict(item) for item in run.get("logs") or [] if isinstance(item, dict)]

    if not run.get("external_build_url"):
        queue_url = str(run.get("external_queue_url") or "").rstrip("/")
        if not queue_url:
            raise api_error(409, "JENKINS_QUEUE_URL_MISSING", "Jenkins queue URL is missing")
        queue_url = _validated_jenkins_resource_url(endpoint, queue_url)
        queue_payload = _request_json(connection, f"{queue_url}/api/json")
        if queue_payload.get("cancelled"):
            task_status = "cancelled"
            error_message = str(queue_payload.get("why") or "Jenkins queue item cancelled")
        else:
            executable = (
                queue_payload.get("executable")
                if isinstance(queue_payload.get("executable"), dict)
                else {}
            )
            build_url = str(executable.get("url") or "").strip()
            if build_url:
                build_url = _validated_jenkins_resource_url(endpoint, build_url)
                run["external_build_url"] = build_url
                run["external_build_id"] = str(executable.get("number") or "")
                logs.append(
                    {
                        "level": "info",
                        "message": f"Jenkins build {run['external_build_id']} started",
                        "timestamp": now,
                    }
                )
            run.update(
                {
                    "logs": logs,
                    "next_sync_at": _next_sync_at(attempts),
                    "status": "running" if build_url else run.get("status", "queued"),
                    "sync_attempts": attempts,
                    "sync_lease_owner": None,
                    "sync_lease_until": None,
                    "updated_at": now,
                }
            )
            _save_deployment_run(write_store, run)
            if build_url:
                return {
                    "deployment": deployment,
                    "run": run,
                }
            return {"deployment": deployment, "run": run}
    else:
        build_url = _validated_jenkins_resource_url(
            endpoint,
            str(run["external_build_url"]),
        ).rstrip("/")
        build_payload = _request_json(connection, f"{build_url}/api/json")
        if bool(build_payload.get("building")):
            task_status = "running"
        else:
            result = str(build_payload.get("result") or "").upper()
            if result == "SUCCESS":
                task_status = "succeeded"
            elif result in {"ABORTED", "NOT_BUILT"}:
                task_status = "cancelled"
                error_message = f"Jenkins build result: {result}"
            else:
                task_status = "failed"
                error_message = f"Jenkins build result: {result or 'UNKNOWN'}"

    logs.append(
        {
            "level": "info" if task_status == "succeeded" else "warning",
            "message": f"Jenkins synchronization status: {task_status}",
            "timestamp": now,
        }
    )
    run.update(
        {
            "logs": logs,
            "next_sync_at": _next_sync_at(attempts) if task_status == "running" else None,
            "sync_attempts": attempts,
            "sync_lease_owner": None,
            "sync_lease_until": None,
            "updated_at": now,
        }
    )
    _save_deployment_run(write_store, run)
    from app.services.operational_deployments import sync_deployment_runner_task

    sync_deployment_runner_task(
        current_store=current_store,
        runner_id=f"jenkins:{snapshot.get('jenkins_connection_id')}",
        task={
            "deployment_run_id": deployment_run_id,
            "error_message": error_message,
            "executor_type": "jenkins",
            "finished_at": now if task_status in {"succeeded", "cancelled", "failed"} else None,
            "id": None,
            "logs": logs,
            "preserve_runner_task_id": True,
            "result_json": {
                "health_checks": [
                    {
                        "code": "jenkins_health_job",
                        "passed": task_status == "succeeded",
                    }
                ]
                if run.get("operation") == "verify"
                else [],
                "health_status": (
                    "passed" if task_status == "succeeded" else "failed"
                )
                if run.get("operation") == "verify"
                else None,
                "operation": run.get("operation") or "deploy",
            },
            "status": task_status,
        },
    )
    refreshed_store = task_workflow_write_store(current_store)
    refreshed_deployment = read_memory_dict(refreshed_store, "deployment_requests")[
        deployment_request_id
    ]
    refreshed_run = read_memory_dict(refreshed_store, "deployment_runs")[deployment_run_id]
    return {"deployment": refreshed_deployment, "run": refreshed_run}


def cancel_jenkins_deployment(
    *,
    current_store: Any,
    deployment_request_id: str,
    deployment_run_id: str,
    actor_id: str,
) -> dict[str, Any]:
    write_store, deployment, run = _deployment_and_run(
        current_store,
        deployment_request_id=deployment_request_id,
        deployment_run_id=deployment_run_id,
    )
    snapshot = dict(deployment.get("scheme_snapshot") or {})
    connection = _connection_by_id(current_store, str(snapshot.get("jenkins_connection_id") or ""))
    endpoint = str(connection.get("endpoint_url") or "").rstrip("/") + "/"
    if run.get("external_build_url"):
        build_url = _validated_jenkins_resource_url(
            endpoint,
            str(run["external_build_url"]),
        )
        cancel_url = f"{build_url.rstrip('/')}/stop"
    elif run.get("external_queue_url"):
        queue_url = _validated_jenkins_resource_url(
            endpoint,
            str(run["external_queue_url"]),
        )
        cancel_url = _jenkins_queue_cancel_url(queue_url)
    else:
        raise api_error(409, "JENKINS_EXTERNAL_REFERENCE_MISSING", "Jenkins reference is missing")
    try:
        with _request(connection, data=b"", method="POST", url=cancel_url):
            pass
    except Exception as exc:
        now = datetime.now(UTC).isoformat()
        failure_reason = f"Jenkins cancel failed: {type(exc).__name__}"
        logs = [dict(item) for item in run.get("logs") or [] if isinstance(item, dict)]
        logs.append(
            {
                "level": "error",
                "message": failure_reason,
                "timestamp": now,
            }
        )
        run.update(
            {
                "logs": logs,
                "next_sync_at": now,
                "status": "running" if run.get("external_build_url") else "queued",
                "sync_lease_owner": None,
                "sync_lease_until": None,
                "updated_at": now,
            }
        )
        deployment.update(
            {
                "failure_reason": None,
                "status": "deploying",
                "updated_at": now,
            }
        )
        deployment.pop("finished_at", None)
        run_event = record_audit_event(
            write_store,
            event_type="deployment.run.jenkins_cancel_failed",
            actor_id=actor_id,
            subject_type="deployment_run",
            subject_id=deployment_run_id,
            payload={
                "deployment_request_id": deployment_request_id,
                "error_type": type(exc).__name__,
            },
        )
        deployment_event = record_audit_event(
            write_store,
            event_type="deployment.request.jenkins_cancel_failed",
            actor_id=actor_id,
            subject_type="deployment_request",
            subject_id=deployment_request_id,
            payload={"deployment_run_id": deployment_run_id, "error_type": type(exc).__name__},
        )
        _save_deployment_run(write_store, run, audit_event=run_event)
        _save_deployment_request(
            write_store,
            deployment,
            audit_event=deployment_event,
        )
        raise api_error(
            502,
            "JENKINS_CANCEL_FAILED",
            failure_reason,
        ) from exc
    now = datetime.now(UTC).isoformat()
    logs = [dict(item) for item in run.get("logs") or [] if isinstance(item, dict)]
    logs.append(
        {
            "level": "warning",
            "message": "Jenkins cancellation requested",
            "timestamp": now,
        }
    )
    run.update(
        {
            "logs": logs,
            "next_sync_at": now,
            "status": "cancelling",
            "sync_lease_owner": None,
            "sync_lease_until": None,
            "updated_at": now,
        }
    )
    event = record_audit_event(
        write_store,
        event_type="deployment.run.jenkins_cancel_requested",
        actor_id=actor_id,
        subject_type="deployment_run",
        subject_id=deployment_run_id,
        payload={"deployment_request_id": deployment_request_id},
    )
    _save_deployment_run(write_store, run, audit_event=event)
    return run
