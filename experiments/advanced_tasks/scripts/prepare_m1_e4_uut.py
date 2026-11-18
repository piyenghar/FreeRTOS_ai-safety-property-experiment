#!/usr/bin/env python3
"""Prepare agent-modified QueueSet.c for M1-E4 behavioural L2.

Reuses the M1 L3 full-QueueSet prepare path, then exports
vM1E4GetRangeDiagnostics so the behavioural harness can link it.
Does not modify original QueueSet.c or safety oracles.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PREPARE_PATH = ROOT / "experiments/m1_multimodel/scripts/prepare_queueset_uut.py"
DIAG = "vM1E4GetRangeDiagnostics"


def _load_prepare():
    spec = importlib.util.spec_from_file_location("prepare_queueset_uut", PREPARE_PATH)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def export_diagnostics(text: str) -> tuple[str, int]:
    out, n = re.subn(
        rf"\bstatic\s+void\s+{DIAG}\s*\(",
        f"void {DIAG}(",
        text,
        count=2,
    )
    if n < 1 and not re.search(rf"void\s+{DIAG}\s*\(", out):
        raise ValueError(f"{DIAG} not found in QueueSet.c")
    return out, n


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--queueset", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--expect-allowable", type=int, default=3)
    ap.add_argument("--meta-out", type=Path)
    args = ap.parse_args()

    prep = _load_prepare()
    qs = args.queueset.resolve()
    if not qs.exists():
        print(f"missing QueueSet.c: {qs}", file=sys.stderr)
        return 2
    if qs.name == prep.FROZEN_REF_NAME:
        print("refusing frozen reference extract", file=sys.stderr)
        return 5

    text = qs.read_text(encoding="utf-8", errors="replace")
    digest = prep.sha256_file(qs)
    m = prep.ALLOW_RE.search(text)
    if not m:
        print("queuesetALLOWABLE_RX_DEVIATION not found", file=sys.stderr)
        return 3
    allowable = int(m.group(1))
    if allowable != args.expect_allowable:
        print(f"ALLOWABLE mismatch: {allowable}", file=sys.stderr)
        return 4
    if "M1_E4_DIAG" not in text:
        print("M1_E4_DIAG token missing", file=sys.stderr)
        return 6
    if DIAG not in text:
        print(f"{DIAG} missing", file=sys.stderr)
        return 7

    prepared = prep.prepare(text, source_path=qs, digest=digest, allowable=allowable)
    try:
        prepared, n_exp = export_diagnostics(prepared)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 7

    # Annotate header
    prepared = prepared.replace(
        "AUTO-GENERATED M1 L3 UUT",
        "AUTO-GENERATED M1-E4 L2 UUT",
        1,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(prepared, encoding="utf-8")
    meta = {
        "ok": True,
        "mode": "full_queueset_m1_e4_uut",
        "diagnostics_api": DIAG,
        "diagnostics_export_rewrites": n_exp,
        "allowable": allowable,
        "queueset_sha256": digest,
        "queueset_path": str(qs),
        "out": str(args.out),
        "tests_agent_modified_implementation": True,
        "used_frozen_reference_extract": False,
    }
    if args.meta_out:
        args.meta_out.parent.mkdir(parents=True, exist_ok=True)
        args.meta_out.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(meta, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
