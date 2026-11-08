"""Use the actual CBDK scanner and Blender API auditor on the private cloud source.

No user source is sent to the public CBDK repository; it is read locally.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit("usage: cbdk_static.py CBDK_CHECKOUT ADDON_SOURCE EVIDENCE_DIR")
    cbdk_checkout = Path(sys.argv[1]).resolve()
    addon_source = Path(sys.argv[2]).resolve()
    output = Path(sys.argv[3]).resolve()
    output.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(cbdk_checkout))
    from cbdk.scanner import scan
    from cbdk.blender_audit import audit_blender_dependencies
    result = scan([addon_source])
    audited = audit_blender_dependencies(result)
    (output / "cbdk_scan.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "cbdk_audit.json").write_text(json.dumps(audited, ensure_ascii=False, indent=2), encoding="utf-8")
    parsed = all(f["status"] == "parsed" for f in result["files"])
    summary = {
        "parsed": parsed,
        "source_count": len(result["files"]),
        "symbol_count": len(result["symbols"]),
        "blender_related_symbols": audited["blender_related_symbols"],
        "context_sensitive_symbols": audited["context_sensitive_symbols"],
        "verification": "static_only",
        "runtime_test": "NOT_RUN",
    }
    (output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print("CBDK_CLOUD_STATIC: " + json.dumps(summary, ensure_ascii=False), flush=True)
    assert parsed and len(result["files"]) == 1
    assert len(result["symbols"]) >= 15

if __name__ == "__main__":
    main()
