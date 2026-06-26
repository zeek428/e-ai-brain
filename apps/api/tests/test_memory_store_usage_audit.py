from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_audit_module():
    script_path = Path(__file__).resolve().parents[3] / "scripts" / "audit_memory_store_usage.py"
    spec = importlib.util.spec_from_file_location("audit_memory_store_usage", script_path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_memory_store_usage_audit_classifies_reads_writes_and_helpers(tmp_path: Path):
    module = _load_audit_module()
    service_dir = tmp_path / "apps" / "api" / "app" / "services"
    service_dir.mkdir(parents=True)
    (service_dir / "demo.py").write_text(
        """
def demo(current_store):
    current_store.products["product_001"] = {"id": "product_001"}
    current_store.model_gateway_logs.append({"id": "model_log_001"})
    current_store.audit(event_type="product.updated")
    current_store.new_id("product")
    current_store.snapshot({"value": "ok"})
    return current_store.products.get("product_001")
""",
        encoding="utf-8",
    )

    findings = module.scan_memory_store_usage(tmp_path)
    indexed = {(item.attr, item.kind, item.risk) for item in findings}

    assert ("products", "write", "P0") in indexed
    assert ("model_gateway_logs", "write", "P0") in indexed
    assert ("audit", "helper", "P0") in indexed
    assert ("new_id", "helper", "P2") in indexed
    assert ("snapshot", "helper", "P2") in indexed
    assert ("products", "read", "P1") in indexed

    summary = module.summarize(findings)
    assert summary["by_risk"]["P0"] == 3
    assert summary["by_risk"]["P1"] == 1
    assert summary["by_risk"]["P2"] == 2


def test_memory_store_usage_audit_current_api_has_no_p0_or_p1_usage():
    module = _load_audit_module()
    repo_root = Path(__file__).resolve().parents[3]

    findings = module.scan_memory_store_usage(repo_root)
    blocking_findings = [item for item in findings if item.risk in {"P0", "P1"}]

    assert blocking_findings == []


def test_memory_store_usage_audit_fail_on_p1_blocks_p0_and_p1(tmp_path: Path):
    module = _load_audit_module()
    service_dir = tmp_path / "apps" / "api" / "app" / "services"
    service_dir.mkdir(parents=True)
    (service_dir / "demo.py").write_text(
        """
def demo(current_store):
    current_store.products["product_001"] = {"id": "product_001"}
    return current_store.products.get("product_001")
""",
        encoding="utf-8",
    )

    exit_code = module.main(["--root", str(tmp_path), "--format", "json", "--fail-on-p1"])

    assert exit_code == 1
