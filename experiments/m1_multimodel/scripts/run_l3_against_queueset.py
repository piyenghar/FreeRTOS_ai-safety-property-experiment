#!/usr/bin/env python3
"""Build/run M1 L3 against an agent-modified QueueSet.c (full TU + shims).

Never links experiments/verification/M1/l3/range_check_under_test.c.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PREPARE = Path(__file__).resolve().parent / "prepare_queueset_uut.py"
DEFAULT_HARNESS = ROOT / "experiments/verification/M1/l3"
M1_L3 = ROOT / "experiments/m1_multimodel/l3_harness"
FROZEN_REF = DEFAULT_HARNESS / "range_check_under_test.c"


def run(cmd: list[str], *, cwd: Path | None = None, env: dict | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        env=env,
        text=True,
        capture_output=True,
    )


def parse_log(text: str) -> dict:
    def summary(prop: str) -> dict:
        m = re.search(rf"SUMMARY {prop} pass=(\d+) fail=(\d+) total=(\d+)", text)
        if not m:
            return {"pass": 0, "fail": 0, "total": 0, "verdict": "INCONCLUSIVE"}
        p, f, t = map(int, m.groups())
        return {
            "pass": p,
            "fail": f,
            "total": t,
            "verdict": "PASS" if f == 0 and t > 0 else "FAIL",
        }

    pos = "PASS" if re.search(r"ORACLE_POS PASS", text) else "FAIL"
    neg = "PASS" if re.search(r"ORACLE_NEG PASS", text) else "FAIL"
    p1 = summary("P1")
    p2 = summary("P2")
    all_s = summary("ALL")
    return {
        "P1": p1,
        "P2": p2,
        "ALL": all_s,
        "oracle_pos": pos,
        "oracle_neg": neg,
        "L3_P1": "HOLD"
        if p1["verdict"] == "PASS"
        else ("VIOLATION" if p1["verdict"] == "FAIL" else "INCONCLUSIVE"),
        "L3_P2": "HOLD"
        if p2["verdict"] == "PASS"
        else ("VIOLATION" if p2["verdict"] == "FAIL" else "INCONCLUSIVE"),
    }


def write_payload(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--queueset", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--harness-dir", type=Path, default=DEFAULT_HARNESS)
    ap.add_argument("--shim-dir", type=Path, default=M1_L3)
    ap.add_argument("--expect-allowable", type=int, default=3)
    ap.add_argument(
        "--summary-name",
        default="l3_oracle.json",
        help="Summary JSON filename inside out-dir",
    )
    args = ap.parse_args()

    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_path = out_dir / args.summary_name
    log_path = out_dir / "l3_range_test.log"
    build_dir = out_dir / "l3_build"
    if build_dir.exists():
        shutil.rmtree(build_dir)
    build_dir.mkdir(parents=True)

    qs = args.queueset.resolve()
    # Hard guard: never accept frozen reference extract as UUT input
    if qs == FROZEN_REF.resolve() or qs.name == "range_check_under_test.c":
        write_payload(
            summary_path,
            {
                "ok": False,
                "stage": "guard",
                "error": "refused frozen reference extract as UUT",
                "tests_agent_modified_implementation": False,
                "used_frozen_reference_extract": True,
                "L3_P1": "INCONCLUSIVE",
                "L3_P2": "INCONCLUSIVE",
            },
        )
        return 5

    uut_c = out_dir / "QueueSet_uut.c"
    uut_meta = out_dir / "uut_meta.json"
    cp = run(
        [
            sys.executable,
            str(PREPARE),
            "--queueset",
            str(qs),
            "--out",
            str(uut_c),
            "--meta-out",
            str(uut_meta),
            "--expect-allowable",
            str(args.expect_allowable),
        ]
    )
    if cp.returncode != 0:
        write_payload(
            summary_path,
            {
                "ok": False,
                "stage": "prepare_uut",
                "exit_code": cp.returncode,
                "stderr": (cp.stderr or "")[-2000:],
                "stdout": (cp.stdout or "")[-2000:],
                "tests_agent_modified_implementation": True,
                "used_frozen_reference_extract": False,
                "L3_P1": "INCONCLUSIVE",
                "L3_P2": "INCONCLUSIVE",
            },
        )
        return 1

    # Stage harness test + stubs (assert/recording) and shim sources.
    # Explicitly do NOT copy frozen range_check_under_test.c into the link.
    shutil.copy2(args.harness_dir / "l3_range_test.c", build_dir / "l3_range_test.c")
    shutil.copy2(args.harness_dir / "freertos_stubs.h", build_dir / "freertos_stubs.h")
    for name in (
        "m1_l3_freertos_shim.h",
        "m1_l3_freertos_shim.c",
        "m1_l3_queueset_api.h",
    ):
        shutil.copy2(args.shim_dir / name, build_dir / name)
    shutil.copy2(uut_c, build_dir / "QueueSet_uut.c")

    # Guard file list
    linked = sorted(p.name for p in build_dir.iterdir())
    if "range_check_under_test.c" in linked:
        write_payload(
            summary_path,
            {
                "ok": False,
                "stage": "guard",
                "error": "frozen reference appeared in build_dir",
                "used_frozen_reference_extract": True,
                "L3_P1": "INCONCLUSIVE",
                "L3_P2": "INCONCLUSIVE",
            },
        )
        return 5

    exe = build_dir / ("l3_range_test.exe" if os.name == "nt" else "l3_range_test")
    cc = shutil.which("gcc") or shutil.which("gcc.exe")
    if not cc:
        write_payload(
            summary_path,
            {
                "ok": False,
                "stage": "compile",
                "error": "gcc not found",
                "tests_agent_modified_implementation": True,
                "used_frozen_reference_extract": False,
                "L3_P1": "INCONCLUSIVE",
                "L3_P2": "INCONCLUSIVE",
            },
        )
        return 2

    cpc = run(
        [
            cc,
            "-std=c11",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-O0",
            "-g",
            "-I.",
            "l3_range_test.c",
            "QueueSet_uut.c",
            "m1_l3_freertos_shim.c",
            "-o",
            str(exe.name),
        ],
        cwd=build_dir,
    )
    (out_dir / "l3_compile.log").write_text(
        (cpc.stdout or "") + "\n" + (cpc.stderr or ""), encoding="utf-8"
    )
    if cpc.returncode != 0:
        write_payload(
            summary_path,
            {
                "ok": False,
                "stage": "compile",
                "exit_code": cpc.returncode,
                "tests_agent_modified_implementation": True,
                "used_frozen_reference_extract": False,
                "linked_sources": linked,
                "compile_log": "l3_compile.log",
                "L3_P1": "INCONCLUSIVE",
                "L3_P2": "INCONCLUSIVE",
            },
        )
        return 3

    env = os.environ.copy()
    env["M1_L3_LOG"] = str(log_path.resolve())
    cpr = run([str(exe)], cwd=build_dir, env=env)
    log_text = log_path.read_text(encoding="utf-8", errors="replace") if log_path.exists() else ""
    parsed = parse_log(log_text)
    meta = json.loads(uut_meta.read_text(encoding="utf-8")) if uut_meta.exists() else {}
    payload = {
        "ok": cpr.returncode == 0
        and parsed.get("oracle_pos") == "PASS"
        and parsed.get("oracle_neg") == "PASS"
        and parsed.get("ALL", {}).get("verdict") == "PASS",
        "stage": "run",
        "exit_code": cpr.returncode,
        "tests_agent_modified_implementation": True,
        "used_frozen_reference_extract": False,
        "mode": "full_queueset_uut",
        "queueset_sha256": meta.get("queueset_sha256"),
        "uut_path": str(uut_c),
        "harness_test_from": str(args.harness_dir / "l3_range_test.c"),
        "shim_dir": str(args.shim_dir),
        "linked_sources": linked,
        "frozen_reference_sha256_not_used": True,
        **parsed,
    }
    write_payload(summary_path, payload)
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
