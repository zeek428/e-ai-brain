#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

DEFAULT_SCAN_PATH = "apps/api/app"
HELPER_ATTRS = {"audit", "new_id", "snapshot"}
MUTATING_METHODS = {"append", "clear", "extend", "pop", "popitem", "remove", "setdefault", "update"}
UNKNOWN_DYNAMIC_ATTR = "<dynamic>"

# Explicitly permitted compatibility cache refreshes. These entries must be
# rebuildable from PostgreSQL and must not be treated as durable write sources.
ALLOWED_DERIVED_CACHE_WRITES = {
    (
        "apps/api/app/services/ai_executor_runner_approvals.py",
        "ai_executor_approval_requests",
    ),
}
ALLOWED_DERIVED_CACHE_SETATTR_FUNCTIONS = {
    (
        "apps/api/app/services/ai_executor_runner_persistence.py",
        "_replace_collection",
    ),
    (
        "apps/api/app/services/ai_executor_runner_approvals.py",
        "sync_ai_executor_approval_request_store",
    ),
    (
        "apps/api/app/services/assistant_knowledge_references.py",
        "refresh_knowledge_scope_collections_from_repository",
    ),
    ("apps/api/app/services/execution_traces.py", "_remember_trace_snapshot_refresh"),
}
ALLOWED_MEMORY_FALLBACK_SETATTR_FUNCTIONS = {
    ("apps/api/app/services/ai_executor_runner_approvals.py", "_memory_dict"),
    ("apps/api/app/services/assistant_action_drafts.py", "_memory_audit_events"),
    ("apps/api/app/services/assistant_action_drafts.py", "_memory_collection"),
    ("apps/api/app/services/assistant_chat.py", "_memory_collection"),
    ("apps/api/app/services/assistant_chat.py", "_memory_list"),
    ("apps/api/app/services/assistant_history.py", "_memory_collection"),
    ("apps/api/app/services/assistant_history.py", "_memory_list"),
    ("apps/api/app/services/assistant_references.py", "_memory_collection"),
    ("apps/api/app/services/assistant_references.py", "_memory_list"),
    ("apps/api/app/services/assistant_request_context.py", "_memory_collection"),
    ("apps/api/app/services/assistant_request_context.py", "_memory_list"),
    ("apps/api/app/services/assistant_role_quick_tasks.py", "_memory_collection"),
    ("apps/api/app/services/assistant_role_quick_tasks.py", "_memory_list"),
    ("apps/api/app/services/bugs.py", "_memory_collection"),
    ("apps/api/app/services/bugs.py", "_memory_list"),
    ("apps/api/app/services/code_inspections.py", "_memory_collection"),
    ("apps/api/app/services/code_inspections.py", "_memory_list"),
    ("apps/api/app/services/devops_metrics.py", "_memory_dict"),
    ("apps/api/app/services/git_review_snapshots.py", "_memory_collection"),
    ("apps/api/app/services/git_review_snapshots.py", "_memory_list"),
    ("apps/api/app/services/iteration_planning.py", "_memory_collection"),
    ("apps/api/app/services/iteration_planning.py", "_memory_list"),
    ("apps/api/app/services/knowledge_management.py", "_memory_collection"),
    ("apps/api/app/services/lifecycle_risks.py", "_memory_collection"),
    ("apps/api/app/services/mock_writeback.py", "_memory_dict"),
    ("apps/api/app/services/mock_writeback.py", "_memory_list"),
    ("apps/api/app/services/model_gateway_config_context.py", "_memory_dict"),
    ("apps/api/app/services/model_gateway_config_context.py", "_memory_list"),
    ("apps/api/app/services/model_gateway_logging.py", "_memory_list"),
    ("apps/api/app/services/operational_records.py", "_memory_list"),
    ("apps/api/app/services/operational_records.py", "read_memory_dict"),
    ("apps/api/app/services/plugin_store_helpers.py", "_memory_dict"),
    ("apps/api/app/services/plugin_store_helpers.py", "replace_collection"),
    ("apps/api/app/services/product_config_context.py", "_memory_dict"),
    ("apps/api/app/services/product_config_context.py", "_memory_list"),
    ("apps/api/app/services/product_git_repository_listing.py", "_memory_dict"),
    ("apps/api/app/services/product_listing.py", "_memory_dict"),
    ("apps/api/app/services/product_module_listing.py", "_memory_dict"),
    ("apps/api/app/services/product_version_listing.py", "_memory_dict"),
    ("apps/api/app/services/rd_task_executor_policies.py", "_memory_dict"),
    ("apps/api/app/services/rd_maintenance_fence.py", "_memory_states"),
    ("apps/api/app/services/related_system_listing.py", "_memory_dict"),
    ("apps/api/app/services/requirement_listing.py", "_memory_dict"),
    ("apps/api/app/services/requirements.py", "_memory_dict"),
    ("apps/api/app/services/requirements.py", "_memory_list"),
    ("apps/api/app/services/scheduled_job_store.py", "memory_dict"),
    ("apps/api/app/services/scheduled_job_store.py", "replace_collection"),
    ("apps/api/app/services/task_code_review_execution.py", "_memory_dict"),
    ("apps/api/app/services/task_graph_runtime.py", "_memory_dict"),
    ("apps/api/app/services/task_listing.py", "_memory_dict"),
    ("apps/api/app/services/task_persistence_helpers.py", "_memory_list"),
    ("apps/api/app/services/task_review_artifacts.py", "_memory_dict"),
    ("apps/api/app/services/user_feedback.py", "_memory_dict"),
    ("apps/api/app/services/user_insights.py", "_memory_dict"),
    ("apps/api/app/services/user_insights.py", "_memory_list"),
    ("apps/api/app/services/user_usage_metrics.py", "_memory_dict"),
    ("apps/api/app/services/version_status.py", "_memory_dict"),
}


@dataclass(frozen=True)
class MemoryStoreUsage:
    attr: str
    column: int
    context: str
    function: str | None
    kind: str
    line: int
    path: str
    risk: str


def _iter_python_files(root: Path, scan_path: str) -> list[Path]:
    target = (root / scan_path).resolve()
    if target.is_file():
        return [target]
    return sorted(
        path
        for path in target.rglob("*.py")
        if "__pycache__" not in path.parts and path.name != "__init__.py"
    )


def _parents(tree: ast.AST) -> dict[ast.AST, ast.AST]:
    result: dict[ast.AST, ast.AST] = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            result[child] = parent
    return result


def _is_current_store_attr(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == "current_store"
    )


def _attribute_line(lines: list[str], node: ast.Attribute) -> str:
    if 1 <= node.lineno <= len(lines):
        return lines[node.lineno - 1].strip()
    return ""


def _source_line(lines: list[str], lineno: int) -> str:
    if 1 <= lineno <= len(lines):
        return lines[lineno - 1].strip()
    return ""


def _is_assignment_target(node: ast.Attribute, parents: dict[ast.AST, ast.AST]) -> bool:
    if isinstance(node.ctx, (ast.Store, ast.Del)):
        return True
    current: ast.AST = node
    while current in parents:
        parent = parents[current]
        if isinstance(parent, (ast.Assign, ast.AnnAssign, ast.AugAssign, ast.Delete)):
            fields = []
            if isinstance(parent, ast.Assign):
                fields = list(parent.targets)
            elif isinstance(parent, ast.AnnAssign):
                fields = [parent.target]
            elif isinstance(parent, ast.AugAssign):
                fields = [parent.target]
            elif isinstance(parent, ast.Delete):
                fields = list(parent.targets)
            return any(current is field or _contains_node(field, node) for field in fields)
        if isinstance(parent, (ast.Subscript, ast.Attribute, ast.Tuple, ast.List)):
            current = parent
            continue
        break
    return False


def _contains_node(root: ast.AST, needle: ast.AST) -> bool:
    return any(child is needle for child in ast.walk(root))


def _called_helper(node: ast.Attribute, parents: dict[ast.AST, ast.AST]) -> bool:
    parent = parents.get(node)
    return isinstance(parent, ast.Call) and parent.func is node and node.attr in HELPER_ATTRS


def _called_mutating_method(node: ast.Attribute, parents: dict[ast.AST, ast.AST]) -> bool:
    parent = parents.get(node)
    grandparent = parents.get(parent) if parent is not None else None
    return (
        isinstance(parent, ast.Attribute)
        and parent.value is node
        and parent.attr in MUTATING_METHODS
        and isinstance(grandparent, ast.Call)
        and grandparent.func is parent
    )


def _usage_kind(node: ast.Attribute, parents: dict[ast.AST, ast.AST]) -> str:
    if _called_helper(node, parents):
        return "helper"
    if _is_assignment_target(node, parents) or _called_mutating_method(node, parents):
        return "write"
    return "read"


def _risk_for(kind: str, attr: str) -> str:
    if kind == "derived_cache_sync":
        return "P2"
    if kind == "write" or attr == "audit":
        return "P0"
    if kind == "read":
        return "P1"
    return "P2"


def _string_bindings(tree: ast.AST) -> dict[str, str]:
    bindings: dict[str, str] = {}
    ambiguous: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if not isinstance(node.value, ast.Constant) or not isinstance(node.value.value, str):
            for target in targets:
                if isinstance(target, ast.Name):
                    ambiguous.add(target.id)
            continue
        for target in targets:
            if not isinstance(target, ast.Name):
                continue
            existing = bindings.get(target.id)
            if existing is not None and existing != node.value.value:
                ambiguous.add(target.id)
            bindings[target.id] = node.value.value
    for name in ambiguous:
        bindings.pop(name, None)
    return bindings


def _setattr_current_store_attr(node: ast.AST, bindings: dict[str, str]) -> str | None:
    if not isinstance(node, ast.Call):
        return None
    if not isinstance(node.func, ast.Name) or node.func.id != "setattr":
        return None
    if len(node.args) < 2:
        return None
    target = node.args[0]
    if not isinstance(target, ast.Name) or target.id != "current_store":
        return None
    attr_arg = node.args[1]
    if isinstance(attr_arg, ast.Constant) and isinstance(attr_arg.value, str):
        return attr_arg.value
    if isinstance(attr_arg, ast.Name):
        return bindings.get(attr_arg.id, UNKNOWN_DYNAMIC_ATTR)
    return UNKNOWN_DYNAMIC_ATTR


def _enclosing_function_name(node: ast.AST, parents: dict[ast.AST, ast.AST]) -> str | None:
    current = node
    while current in parents:
        current = parents[current]
        if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return current.name
    return None


def _classify_usage(
    path: str,
    kind: str,
    attr: str,
    function_name: str | None = None,
) -> tuple[str, str]:
    if kind == "write" and (
        (path, attr) in ALLOWED_DERIVED_CACHE_WRITES
        or (
            function_name is not None
            and (path, function_name) in ALLOWED_DERIVED_CACHE_SETATTR_FUNCTIONS
        )
    ):
        kind = "derived_cache_sync"
    elif (
        kind == "write"
        and function_name is not None
        and (path, function_name) in ALLOWED_MEMORY_FALLBACK_SETATTR_FUNCTIONS
    ):
        kind = "helper"
    return kind, _risk_for(kind, attr)


def scan_memory_store_usage(
    root: Path,
    scan_path: str = DEFAULT_SCAN_PATH,
) -> list[MemoryStoreUsage]:
    findings: list[MemoryStoreUsage] = []
    for path in _iter_python_files(root, scan_path):
        source = path.read_text(encoding="utf-8")
        lines = source.splitlines()
        tree = ast.parse(source, filename=str(path))
        parents = _parents(tree)
        string_bindings = _string_bindings(tree)
        relative_path = str(path.relative_to(root))
        for node in ast.walk(tree):
            setattr_attr = _setattr_current_store_attr(node, string_bindings)
            if setattr_attr is not None:
                function_name = _enclosing_function_name(node, parents)
                kind, risk = _classify_usage(relative_path, "write", setattr_attr, function_name)
                findings.append(
                    MemoryStoreUsage(
                        attr=setattr_attr,
                        column=node.col_offset + 1,
                        context=_source_line(lines, node.lineno),
                        function=function_name,
                        kind=kind,
                        line=node.lineno,
                        path=relative_path,
                        risk=risk,
                    )
                )
                continue
            if _is_current_store_attr(node):
                assert isinstance(node, ast.Attribute)
                function_name = _enclosing_function_name(node, parents)
                kind = _usage_kind(node, parents)
                kind, risk = _classify_usage(relative_path, kind, node.attr, function_name)
                findings.append(
                    MemoryStoreUsage(
                        attr=node.attr,
                        column=node.col_offset + 1,
                        context=_attribute_line(lines, node),
                        function=function_name,
                        kind=kind,
                        line=node.lineno,
                        path=relative_path,
                        risk=risk,
                    )
                )
    return sorted(findings, key=lambda item: (item.risk, item.path, item.line, item.column))


def summarize(findings: list[MemoryStoreUsage]) -> dict[str, Any]:
    by_risk = Counter(item.risk for item in findings)
    by_kind = Counter(item.kind for item in findings)
    by_attr = Counter(item.attr for item in findings)
    by_file = Counter(item.path for item in findings)
    return {
        "by_attr": dict(by_attr.most_common()),
        "by_file": dict(by_file.most_common()),
        "by_kind": dict(by_kind),
        "by_risk": dict(by_risk),
        "total": len(findings),
    }


def _text_report(root: Path, findings: list[MemoryStoreUsage], *, limit: int) -> str:
    summary = summarize(findings)
    by_attr = defaultdict(Counter)
    for item in findings:
        by_attr[item.risk][item.attr] += 1
    lines = [
        "DB-first MemoryStore compatibility scan",
        f"Root: {root}",
        f"Findings: {summary['total']} "
        f"(P0={summary['by_risk'].get('P0', 0)}, "
        f"P1={summary['by_risk'].get('P1', 0)}, "
        f"P2={summary['by_risk'].get('P2', 0)})",
        "",
        "Top P0 attributes:",
    ]
    p0_attrs = by_attr["P0"].most_common(12)
    lines.extend(f"- {attr}: {count}" for attr, count in p0_attrs)
    if not p0_attrs:
        lines.append("- none")
    lines.extend(["", f"First {limit} P0 findings:"])
    p0_findings = [item for item in findings if item.risk == "P0"][:limit]
    lines.extend(
        (
            f"- {item.path}:{item.line}:{item.column} [{item.kind}] "
            f"current_store.{item.attr} :: {item.context}"
        )
        for item in p0_findings
    )
    if not p0_findings:
        lines.append("- none")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Scan production API code for current_store.* compatibility usage.",
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Repository root. Defaults to current directory.",
    )
    parser.add_argument("--scan-path", default=DEFAULT_SCAN_PATH, help="Relative path to scan.")
    parser.add_argument("--format", choices=("json", "text"), default="text")
    parser.add_argument("--limit", default=40, type=int, help="Number of P0 findings to print.")
    parser.add_argument(
        "--fail-on-p0",
        action="store_true",
        help="Exit non-zero when write/helper P0 usage remains.",
    )
    parser.add_argument(
        "--fail-on-p1",
        action="store_true",
        help="Exit non-zero when P0 or direct-read P1 usage remains.",
    )
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    findings = scan_memory_store_usage(root, args.scan_path)
    if args.format == "json":
        payload = {
            "findings": [asdict(item) for item in findings],
            "root": str(root),
            "scan_path": args.scan_path,
            "summary": summarize(findings),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(_text_report(root, findings, limit=args.limit))
    has_p0 = any(item.risk == "P0" for item in findings)
    has_p1 = any(item.risk == "P1" for item in findings)
    if args.fail_on_p1 and (has_p0 or has_p1):
        return 1
    return 1 if args.fail_on_p0 and has_p0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
