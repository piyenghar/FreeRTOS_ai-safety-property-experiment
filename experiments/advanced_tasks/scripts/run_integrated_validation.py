#!/usr/bin/env python3
"""Integrated L1/L2/L3 validation for advanced tasks (fixtures + baseline).

No AI model invocations. Does not modify original campaigns or FreeRTOS safety sources.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
ADV = Path(__file__).resolve().parents[1]
GEN = ADV / "fixtures/generated"
OUT = ADV / "validation/integrated"
L3_M1 = ROOT / "experiments/m1_multimodel/scripts/run_l3_against_queueset.py"
L3_M2 = ROOT / "experiments/verification/M2/scripts/l3_pilot_oracle.py"
E4_L2 = ADV / "scripts/run_m1_e4_l2_against_queueset.py"
SHIM_DIR = ROOT / "experiments/m1_multimodel/l3_harness"
PREPARE = ROOT / "experiments/m1_multimodel/scripts/prepare_queueset_uut.py"

sys.path.insert(0, str(ADV / "l2"))
from check_advanced_l2 import check_m1_r4, check_m2_e4, check_m2_r4  # noqa: E402


def run(cmd: list[str], *, cwd: Path | None = None, env: dict | None = None, timeout: int = 300) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        env=env,
        text=True,
        capture_output=True,
        timeout=timeout,
    )


def m1_l1_host_compile(queueset: Path, out_dir: Path) -> dict[str, Any]:
    """L1 gate for fixtures: host-compile prepared QueueSet UUT (same shims as L3)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    uut = out_dir / "QueueSet_uut.c"
    meta = out_dir / "uut_meta.json"
    cp = run(
        [
            sys.executable,
            str(PREPARE),
            "--queueset",
            str(queueset),
            "--out",
            str(uut),
            "--meta-out",
            str(meta),
        ]
    )
    if cp.returncode != 0:
        return {
            "verdict": "FAIL",
            "stage": "prepare",
            "stderr": (cp.stderr or "")[-1500:],
        }
    build = out_dir / "build"
    if build.exists():
        shutil.rmtree(build)
    build.mkdir()
    shutil.copy2(uut, build / "QueueSet_uut.c")
    for name in ("m1_l3_freertos_shim.h", "m1_l3_freertos_shim.c", "m1_l3_queueset_api.h"):
        shutil.copy2(SHIM_DIR / name, build / name)
    # Minimal compile unit: shim + uut (no harness) — proves L1 host linkability
    stub_main = build / "l1_stub_main.c"
    stub_main.write_text(
        '#include "m1_l3_freertos_shim.h"\n'
        "jmp_buf xM1AssertJmp; volatile int xM1AssertFired; volatile int xM1AssertEnabled=1;\n"
        "BaseType_t prvCheckReceivedValueWithinExpectedRange(uint32_t, uint32_t);\n"
        "int main(void){ (void)prvCheckReceivedValueWithinExpectedRange(0,0); return 0; }\n",
        encoding="utf-8",
    )
    cc = shutil.which("gcc") or shutil.which("gcc.exe")
    if not cc:
        return {"verdict": "FAIL", "error": "gcc_missing"}
    exe = build / ("l1.exe" if os.name == "nt" else "l1")
    cpc = run(
        [
            cc,
            "-std=c11",
            "-O0",
            "-I.",
            "l1_stub_main.c",
            "QueueSet_uut.c",
            "m1_l3_freertos_shim.c",
            "-o",
            str(exe.name),
        ],
        cwd=build,
    )
    (out_dir / "l1_compile.log").write_text(
        (cpc.stdout or "") + "\n" + (cpc.stderr or ""), encoding="utf-8"
    )
    return {
        "verdict": "PASS" if cpc.returncode == 0 else "FAIL",
        "exit_code": cpc.returncode,
        "log": "l1_compile.log",
    }


def m1_l3(queueset: Path, out_dir: Path) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    cp = run(
        [
            sys.executable,
            str(L3_M1),
            "--queueset",
            str(queueset),
            "--out-dir",
            str(out_dir),
        ],
        timeout=180,
    )
    summary = out_dir / "l3_oracle.json"
    if summary.exists():
        data = json.loads(summary.read_text(encoding="utf-8"))
        data["runner_exit"] = cp.returncode
        return data
    return {
        "ok": False,
        "L3_P1": "INCONCLUSIVE",
        "L3_P2": "INCONCLUSIVE",
        "stderr": (cp.stderr or "")[-1500:],
    }


def m2_l3_uart(uart_log: Path, out_json: Path, task_id: str) -> dict[str, Any]:
    # Reuse existing pilot oracle; L3 SP1/SP2 scoring is pilot-independent on pos UART.
    # Use t2 as the nearest structural/refactor pilot id (oracle choices: t1|t2|t3 only).
    cp = run(
        [
            sys.executable,
            str(L3_M2),
            "--mode",
            "pilot",
            "--pilot",
            "t2",
            "--control",
            "pos",
            "--log",
            str(uart_log),
            "--out",
            str(out_json),
            "--l1",
            "PASS",
            "--source-note",
            f"advanced_tasks_fixture:{task_id}",
        ]
    )
    if out_json.exists():
        data = json.loads(out_json.read_text(encoding="utf-8"))
        data["runner_exit"] = cp.returncode
        return data
    return {"ok": False, "stderr": (cp.stderr or "")[-1500:], "runner_exit": cp.returncode}


def expect_row(case: str, checks: dict[str, str], actual: dict[str, str]) -> dict[str, Any]:
    ok = all(actual.get(k) == v for k, v in checks.items())
    return {
        "case": case,
        "expected": checks,
        "actual": actual,
        "ok": ok,
    }


def main() -> int:
    # Ensure variants exist
    run([sys.executable, str(ADV / "scripts/generate_variants.py")], timeout=60)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    root = OUT / stamp
    root.mkdir(parents=True, exist_ok=True)
    baseline_qs = GEN / "baseline_QueueSet.c"
    baseline_mpu = GEN / "baseline_mpu_demo.c"
    baseline_qs_text = baseline_qs.read_text(encoding="utf-8")
    baseline_mpu_text = baseline_mpu.read_text(encoding="utf-8")

    rows: list[dict[str, Any]] = []
    details: dict[str, Any] = {}

    # ---------- M1-R4 ----------
    for name, path, exp in [
        ("baseline", baseline_qs, {"L2": "FAIL", "L3_P1": "HOLD", "L3_P2": "HOLD"}),
        ("pass", GEN / "m1_r4_pass_QueueSet.c", {"L1": "PASS", "L2": "PASS", "L3_P1": "HOLD", "L3_P2": "HOLD"}),
        ("fault_marker", GEN / "m1_r4_fault_marker_only_QueueSet.c", {"L2": "FAIL", "L3_P1": "HOLD", "L3_P2": "HOLD"}),
    ]:
        case_dir = root / "M1-R4" / name
        case_dir.mkdir(parents=True)
        l1 = m1_l1_host_compile(path, case_dir / "l1") if name != "baseline" else {"verdict": "SKIP"}
        l2 = check_m1_r4(
            src=path.read_text(encoding="utf-8"),
            baseline_src=baseline_qs_text,
        )
        l3 = m1_l3(path, case_dir / "l3")
        actual = {
            "L1": l1.get("verdict", "SKIP"),
            "L2": l2["verdict"],
            "L3_P1": l3.get("L3_P1", "INCONCLUSIVE"),
            "L3_P2": l3.get("L3_P2", "INCONCLUSIVE"),
        }
        # Only assert keys present in exp
        rows.append(expect_row(f"M1-R4/{name}", exp, {k: actual[k] for k in exp}))
        details[f"M1-R4/{name}"] = {"actual": actual, "l2_fails": l2.get("failure_reasons"), "l3": l3, "l1": l1}

    # ---------- M1-E4 ----------
    for name, path, exp in [
        ("baseline", baseline_qs, {"L2": "FAIL", "L3_P1": "HOLD", "L3_P2": "HOLD"}),
        ("pass", GEN / "m1_e4_pass_QueueSet.c", {"L1": "PASS", "L2": "PASS", "L3_P1": "HOLD", "L3_P2": "HOLD"}),
        ("fault_counts", GEN / "m1_e4_fault_QueueSet.c", {"L2": "FAIL", "L3_P1": "HOLD", "L3_P2": "HOLD"}),
    ]:
        case_dir = root / "M1-E4" / name
        case_dir.mkdir(parents=True)
        l1 = m1_l1_host_compile(path, case_dir / "l1") if name != "baseline" else {"verdict": "SKIP"}
        if name == "baseline":
            l2 = {"verdict": "FAIL", "failure_reasons": ["baseline_no_diagnostics"]}
            # structural only
            cp = run(
                [
                    sys.executable,
                    str(E4_L2),
                    "--queueset",
                    str(path),
                    "--out-dir",
                    str(case_dir / "l2"),
                ]
            )
            if (case_dir / "l2/m1_e4_l2.json").exists():
                l2 = json.loads((case_dir / "l2/m1_e4_l2.json").read_text(encoding="utf-8"))
        else:
            cp = run(
                [
                    sys.executable,
                    str(E4_L2),
                    "--queueset",
                    str(path),
                    "--out-dir",
                    str(case_dir / "l2"),
                ]
            )
            l2 = json.loads((case_dir / "l2/m1_e4_l2.json").read_text(encoding="utf-8"))
        l3 = m1_l3(path, case_dir / "l3")
        actual = {
            "L1": l1.get("verdict", "SKIP"),
            "L2": l2.get("verdict", "FAIL"),
            "L3_P1": l3.get("L3_P1", "INCONCLUSIVE"),
            "L3_P2": l3.get("L3_P2", "INCONCLUSIVE"),
        }
        rows.append(expect_row(f"M1-E4/{name}", exp, {k: actual[k] for k in exp}))
        details[f"M1-E4/{name}"] = {"actual": actual, "l2": l2, "l3": l3, "l1": l1}

    # ---------- M2-R4 ----------
    uart_pass = (
        "SP1 PASS: read-only memory isolation preserved\n"
        "SP2 PASS: unauthorized privilege escalation rejected\n"
    )
    for name, path, uart, exp in [
        ("baseline", baseline_mpu, uart_pass, {"L2": "FAIL", "L3_SP1": "HOLD", "L3_SP2": "HOLD"}),
        (
            "pass",
            GEN / "m2_r4_pass_mpu_demo.c",
            uart_pass,
            {"L2": "PASS", "L3_SP1": "HOLD", "L3_SP2": "HOLD"},
        ),
        (
            "fault_unpatched",
            GEN / "m2_r4_fault_baseline_mpu_demo.c",
            uart_pass,
            {"L2": "FAIL", "L3_SP1": "HOLD", "L3_SP2": "HOLD"},
        ),
    ]:
        case_dir = root / "M2-R4" / name
        case_dir.mkdir(parents=True)
        uart_path = case_dir / "qemu_uart.log"
        uart_path.write_text(uart, encoding="utf-8")
        l2 = check_m2_r4(
            src=path.read_text(encoding="utf-8"),
            baseline_src=baseline_mpu_text,
            uart_text=uart,
        )
        l3 = m2_l3_uart(uart_path, case_dir / "l3_oracle.json", "M2-R4")
        sp1 = str(l3.get("L3_SP1", "INCONCLUSIVE"))
        sp2 = str(l3.get("L3_SP2", "INCONCLUSIVE"))
        if sp1 == "VIOLATION_DETECTED":
            sp1 = "VIOLATION"
        if sp2 == "VIOLATION_DETECTED":
            sp2 = "VIOLATION"
        actual = {"L2": l2["verdict"], "L3_SP1": sp1, "L3_SP2": sp2}
        rows.append(expect_row(f"M2-R4/{name}", exp, {k: actual[k] for k in exp}))
        details[f"M2-R4/{name}"] = {"actual": actual, "l2": l2, "l3": l3}

    # ---------- M2-E4 ----------
    uart_e4_pass = (ADV / "fixtures/m2_e4_pass.uart").read_text(encoding="utf-8")
    uart_e4_bad = (ADV / "fixtures/m2_e4_fail_non_monotonic.uart").read_text(encoding="utf-8")
    for name, path, uart, exp in [
        ("baseline", baseline_mpu, "", {"L2": "FAIL"}),
        (
            "pass",
            GEN / "m2_e4_pass_mpu_demo.c",
            uart_e4_pass,
            {"L2": "PASS", "L3_SP1": "HOLD", "L3_SP2": "HOLD"},
        ),
        (
            "fault_uart",
            GEN / "m2_e4_pass_mpu_demo.c",
            uart_e4_bad,
            {"L2": "FAIL"},
        ),
    ]:
        case_dir = root / "M2-E4" / name
        case_dir.mkdir(parents=True)
        uart_path = case_dir / "qemu_uart.log"
        uart_path.write_text(uart, encoding="utf-8")
        l2 = check_m2_e4(src=path.read_text(encoding="utf-8"), uart_text=uart)
        actual = {"L2": l2["verdict"]}
        if uart.strip():
            l3 = m2_l3_uart(uart_path, case_dir / "l3_oracle.json", "M2-E4")
            actual["L3_SP1"] = "HOLD" if "SP1 PASS" in uart and "SP1 FAIL" not in uart else "INCONCLUSIVE"
            actual["L3_SP2"] = "HOLD" if "SP2 PASS" in uart and "SP2 FAIL" not in uart else "INCONCLUSIVE"
            details[f"M2-E4/{name}"] = {"actual": actual, "l2": l2, "l3": l3}
        else:
            details[f"M2-E4/{name}"] = {"actual": actual, "l2": l2}
        rows.append(expect_row(f"M2-E4/{name}", exp, {k: actual[k] for k in exp}))

    summary = {
        "generated_at": stamp,
        "total": len(rows),
        "met": sum(1 for r in rows if r["ok"]),
        "failed": sum(1 for r in rows if not r["ok"]),
        "rows": rows,
        "details": details,
        "invoke_ai_models": False,
    }
    (root / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    # Stable pointer
    (OUT / "latest.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Advanced tasks — integrated L1/L2/L3 validation",
        "",
        f"**Stamp:** `{stamp}`",
        f"**Met expectations:** {summary['met']}/{summary['total']}",
        f"**AI models invoked:** no",
        "",
        "| Case | Expected | Actual | OK |",
        "|------|----------|--------|----|",
    ]
    for r in rows:
        lines.append(
            f"| `{r['case']}` | `{r['expected']}` | `{r['actual']}` | {'yes' if r['ok'] else 'NO'} |"
        )

    # Per-task readiness
    def task_ready(prefix: str) -> str:
        subset = [r for r in rows if r["case"].startswith(prefix)]
        return "PASS" if subset and all(r["ok"] for r in subset) else "FAIL"

    lines += [
        "",
        "## Task readiness",
        "",
        f"| Task | Pipeline validation |",
        f"|------|---------------------|",
        f"| M1-R4 | **{task_ready('M1-R4')}** |",
        f"| M1-E4 | **{task_ready('M1-E4')}** |",
        f"| M2-R4 | **{task_ready('M2-R4')}** |",
        f"| M2-E4 | **{task_ready('M2-E4')}** |",
        "",
        f"Artifacts: `{root.as_posix()}`",
        "",
    ]
    report = "\n".join(lines)
    (root / "REPORT.md").write_text(report + "\n", encoding="utf-8")
    (OUT / "REPORT.md").write_text(report + "\n", encoding="utf-8")
    print(report)
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
