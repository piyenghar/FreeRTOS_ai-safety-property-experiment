#!/usr/bin/env python3
"""Run M1-E4 behavioural L2 against an actual (possibly agent-modified) QueueSet.c."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ADV = Path(__file__).resolve().parents[1]
PREPARE = ADV / "scripts/prepare_m1_e4_uut.py"
HARNESS = ADV / "l2/m1_e4_behavioural_harness_queueset.c"
SHIM_DIR = ROOT / "experiments/m1_multimodel/l3_harness"
STRUCTURAL = ADV / "l2/check_advanced_l2.py"


def run(cmd: list[str], *, cwd: Path | None = None, env: dict | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(cwd) if cwd else None, env=env, text=True, capture_output=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--queueset", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--baseline", type=Path, default=ROOT / "FreeRTOS/Demo/Common/Minimal/QueueSet.c")
    args = ap.parse_args()

    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_path = out_dir / "m1_e4_l2.json"

    # Structural gate first (token + API)
    src = args.queueset.read_text(encoding="utf-8", errors="replace")
    sys.path.insert(0, str(ADV / "l2"))
    from check_advanced_l2 import check_m1_e4_structural  # noqa: E402

    fails, detail = check_m1_e4_structural(src)
    if fails:
        payload = {
            "verdict": "FAIL",
            "stage": "structural",
            "failure_reasons": fails,
            "detail": detail,
            "tests_agent_modified_implementation": True,
        }
        summary_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(payload, indent=2))
        return 1

    uut_c = out_dir / "QueueSet_m1_e4_uut.c"
    uut_meta = out_dir / "uut_meta.json"
    cp = run(
        [
            sys.executable,
            str(PREPARE),
            "--queueset",
            str(args.queueset.resolve()),
            "--out",
            str(uut_c),
            "--meta-out",
            str(uut_meta),
        ]
    )
    if cp.returncode != 0:
        payload = {
            "verdict": "FAIL",
            "stage": "prepare_uut",
            "failure_reasons": ["prepare_failed"],
            "stderr": (cp.stderr or "")[-2000:],
            "stdout": (cp.stdout or "")[-2000:],
        }
        summary_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(payload, indent=2))
        return 1

    build_dir = out_dir / "l2_build"
    if build_dir.exists():
        shutil.rmtree(build_dir)
    build_dir.mkdir(parents=True)
    for name in (
        "m1_l3_freertos_shim.h",
        "m1_l3_freertos_shim.c",
        "m1_l3_queueset_api.h",
    ):
        shutil.copy2(SHIM_DIR / name, build_dir / name)
    shutil.copy2(uut_c, build_dir / "QueueSet_uut.c")
    shutil.copy2(HARNESS, build_dir / "harness.c")

    cc = shutil.which("gcc") or shutil.which("gcc.exe")
    if not cc:
        payload = {"verdict": "FAIL", "stage": "compile", "failure_reasons": ["gcc_missing"]}
        summary_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(payload, indent=2))
        return 2

    exe = build_dir / ("m1_e4_l2.exe" if os.name == "nt" else "m1_e4_l2")
    cpc = run(
        [
            cc,
            "-std=c11",
            "-Wall",
            "-Wextra",
            "-O0",
            "-g",
            "-I.",
            "harness.c",
            "QueueSet_uut.c",
            "m1_l3_freertos_shim.c",
            "-o",
            str(exe.name),
        ],
        cwd=build_dir,
    )
    (out_dir / "l2_compile.log").write_text(
        (cpc.stdout or "") + "\n" + (cpc.stderr or ""), encoding="utf-8"
    )
    if cpc.returncode != 0:
        payload = {
            "verdict": "FAIL",
            "stage": "compile",
            "failure_reasons": ["behavioural_compile_failed"],
            "compile_log": "l2_compile.log",
        }
        summary_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(payload, indent=2))
        return 3

    cpr = run([str(exe)], cwd=build_dir)
    ok = cpr.returncode == 0 and "PASS" in ((cpr.stdout or "") + (cpr.stderr or ""))
    payload = {
        "verdict": "PASS" if ok else "FAIL",
        "stage": "behavioural",
        "failure_reasons": [] if ok else ["behavioural_acceptance_failed"],
        "stdout": cpr.stdout,
        "stderr": cpr.stderr,
        "returncode": cpr.returncode,
        "tests_agent_modified_implementation": True,
        "used_frozen_reference_extract": False,
        "queueset": str(args.queueset.resolve()),
        "structural": detail,
    }
    summary_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
