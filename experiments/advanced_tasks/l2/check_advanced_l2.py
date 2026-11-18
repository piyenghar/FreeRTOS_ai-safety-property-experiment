#!/usr/bin/env python3
"""Executable L2 checkers for advanced tasks M1-R4, M1-E4, M2-R4, M2-E4.

L2 is independent of L3 safety oracles. Does not modify original experiments.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
ADV = Path(__file__).resolve().parents[1]
STUBS_DIR = ROOT / "experiments/verification/M1/l3"
HARNESS = Path(__file__).resolve().parent / "m1_e4_behavioural_harness.c"

SP1_PASS = "SP1 PASS: read-only memory isolation preserved"
SP2_PASS = "SP2 PASS: unauthorized privilege escalation rejected"
SP1_FAIL = "SP1 FAIL: read-only memory isolation violated"
SP2_FAIL = "SP2 FAIL: privilege containment violated"
RO_ATTR = "portMPU_REGION_PRIVILEGED_READ_WRITE_UNPRIV_READ_ONLY"


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def _extract_fn(src: str, name: str) -> str | None:
    for m in re.finditer(rf"\b{re.escape(name)}\s*\(", src):
        j = m.end() - 1
        depth = 0
        k = j
        while k < len(src):
            if src[k] == "(":
                depth += 1
            elif src[k] == ")":
                depth -= 1
                if depth == 0:
                    k += 1
                    break
            k += 1
        else:
            continue
        while k < len(src) and src[k] in " \t\r\n":
            k += 1
        if k >= len(src) or src[k] != "{":
            continue
        line_start = src.rfind("\n", 0, m.start()) + 1
        start = line_start
        i = k
        depth = 0
        while i < len(src):
            if src[i] == "{":
                depth += 1
            elif src[i] == "}":
                depth -= 1
                if depth == 0:
                    return src[start : i + 1]
            i += 1
    return None


def _m1_safety_invariants(src: str, fails: list[str]) -> None:
    m_def = re.search(r"#\s*define\s+queuesetALLOWABLE_RX_DEVIATION\s+(\d+)", src)
    if m_def and m_def.group(1) != "3":
        fails.append("queuesetALLOWABLE_RX_DEVIATION_not_3")
    elif not m_def and "queuesetALLOWABLE_RX_DEVIATION" not in src:
        # Host fixtures may rely on freertos_stubs.h for the macro value.
        fails.append("queuesetALLOWABLE_RX_DEVIATION_missing")
    if "configASSERT" not in src:
        fails.append("configASSERT_missing")


def check_m1_r4(*, src: str, baseline_src: str) -> dict[str, Any]:
    fails: list[str] = []
    detail: dict[str, Any] = {"task_id": "M1-R4"}
    _m1_safety_invariants(src, fails)

    if "M1_R4_EXTRACT" not in src:
        fails.append("missing_token_M1_R4_EXTRACT")

    fn = _extract_fn(src, "prvCheckReceivedValueWithinExpectedRange")
    if not fn:
        fails.append("range_check_fn_missing")
        return {"verdict": "FAIL", "failure_reasons": fails, "detail": detail}

    # Helper: another function definition that check calls, related to deviation.
    helpers = []
    for m in re.finditer(
        r"(?:static\s+)?(?:uint32_t|UBaseType_t|unsigned|int)\s+(\w+)\s*\([^;]*\)\s*\{",
        src,
    ):
        name = m.group(1)
        if name == "prvCheckReceivedValueWithinExpectedRange":
            continue
        if re.search(rf"\b{re.escape(name)}\s*\(", fn):
            helpers.append(name)

    # Also accept helpers returning BaseType_t only if clearly deviation-named — prefer uint distance.
    assert_hits = re.findall(
        r"configASSERT\s*\(\s*[^;]*queuesetALLOWABLE_RX_DEVIATION[^;]*\)",
        fn,
    )
    # Mirrored baseline pattern: two nearly identical asserts.
    mirrored = len(
        re.findall(
            r"configASSERT\s*\(\s*\(\s*ulReceived\s*-\s*ulExpectedReceived\s*\)\s*<=\s*queuesetALLOWABLE_RX_DEVIATION\s*\)",
            fn,
        )
    ) + len(
        re.findall(
            r"configASSERT\s*\(\s*\(\s*ulExpectedReceived\s*-\s*ulReceived\s*\)\s*<=\s*queuesetALLOWABLE_RX_DEVIATION\s*\)",
            fn,
        )
    )

    alpha_changed = re.sub(r"\s+", "", src) != re.sub(r"\s+", "", baseline_src)

    detail["checks"] = {
        "helpers_called_from_check": helpers,
        "allowable_assert_count_in_check": len(assert_hits),
        "mirrored_branch_asserts": mirrored,
        "structurally_changed": alpha_changed,
        "source_sha256": _sha(src),
    }

    if not helpers:
        fails.append("missing_deviation_helper_called_from_check")
    if mirrored >= 2:
        fails.append("duplicated_mirrored_assert_branches_remain")
    if "configASSERT" not in fn:
        fails.append("configASSERT_missing_in_check")
    elif len(assert_hits) > 1:
        fails.append("multiple_allowable_deviation_asserts_in_check")
    elif len(assert_hits) == 0 and fn.count("configASSERT") != 1:
        fails.append("expected_single_allowable_deviation_assert")
    if not alpha_changed:
        fails.append("no_structural_change_vs_baseline")

    detail["checks"]["unified_path"] = bool(
        helpers and mirrored == 0 and (len(assert_hits) == 1 or fn.count("configASSERT") == 1)
    )

    return {
        "verdict": "PASS" if not fails else "FAIL",
        "failure_reasons": fails,
        "detail": detail,
    }


def check_m1_e4_structural(src: str) -> tuple[list[str], dict[str, Any]]:
    fails: list[str] = []
    _m1_safety_invariants(src, fails)
    if "M1_E4_DIAG" not in src:
        fails.append("missing_token_M1_E4_DIAG")
    if not re.search(
        r"void\s+vM1E4GetRangeDiagnostics\s*\(\s*uint32_t\s*\*\s*\w+\s*,\s*uint32_t\s*\*\s*\w+\s*\)",
        src,
    ):
        fails.append("missing_vM1E4GetRangeDiagnostics_signature")
    if re.search(r"static\s+void\s+vM1E4GetRangeDiagnostics\s*\(", src):
        fails.append("diagnostics_api_must_not_be_static")
    detail = {
        "has_token": "M1_E4_DIAG" in src,
        "has_api": "vM1E4GetRangeDiagnostics" in src,
    }
    return fails, detail


def run_m1_e4_behavioural(uut_c: Path) -> dict[str, Any]:
    """Compile harness + UUT with host gcc; return verdict."""
    stubs_h = STUBS_DIR / "freertos_stubs.h"
    if not stubs_h.exists():
        return {
            "verdict": "FAIL",
            "failure_reasons": ["stubs_missing"],
            "detail": {},
        }
    with tempfile.TemporaryDirectory(prefix="m1e4_l2_") as td:
        td_path = Path(td)
        exe = td_path / "m1_e4_l2.exe"
        cmd = [
            "gcc",
            "-std=c11",
            f"-I{STUBS_DIR}",
            str(HARNESS),
            str(uut_c),
            "-o",
            str(exe),
        ]
        # On Windows, freertos_stubs define queuesetALLOWABLE — UUT fixtures should not redefine conflicting.
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            return {
                "verdict": "FAIL",
                "failure_reasons": ["behavioural_compile_failed"],
                "detail": {"stderr": proc.stderr[-2000:], "stdout": proc.stdout[-1000:]},
            }
        run = subprocess.run([str(exe)], capture_output=True, text=True)
        ok = run.returncode == 0 and "PASS" in (run.stdout + run.stderr)
        return {
            "verdict": "PASS" if ok else "FAIL",
            "failure_reasons": [] if ok else ["behavioural_acceptance_failed"],
            "detail": {
                "stdout": run.stdout,
                "stderr": run.stderr,
                "returncode": run.returncode,
            },
        }


def check_m1_e4(*, src: str, uut_c: Path | None) -> dict[str, Any]:
    fails, detail = check_m1_e4_structural(src)
    result: dict[str, Any] = {
        "verdict": "FAIL",
        "failure_reasons": fails,
        "detail": {"task_id": "M1-E4", "structural": detail},
    }
    if fails:
        return result
    if uut_c is None:
        result["failure_reasons"] = ["behavioural_uut_not_provided"]
        return result
    beh = run_m1_e4_behavioural(uut_c)
    result["detail"]["behavioural"] = beh
    if beh["verdict"] != "PASS":
        result["failure_reasons"] = fails + beh["failure_reasons"]
        return result
    result["verdict"] = "PASS"
    result["failure_reasons"] = []
    return result


def check_m2_r4(*, src: str, baseline_src: str, uart_text: str = "") -> dict[str, Any]:
    fails: list[str] = []
    detail: dict[str, Any] = {"task_id": "M2-R4"}

    if "M2_R4_STRUCT" not in src:
        fails.append("missing_token_M2_R4_STRUCT")
    if SP1_PASS not in src:
        fails.append("sp1_pass_string_missing")
    if SP2_PASS not in src:
        fails.append("sp2_pass_string_missing")
    if RO_ATTR not in src:
        fails.append("ro_region_attribute_missing")
    if "portRAISE_PRIVILEGE" not in src:
        fails.append("portRAISE_PRIVILEGE_missing")
    if "ucROTaskFaultTracker" not in src:
        fails.append("fault_tracker_missing")
    if "vHandleMemoryFault" not in src:
        fails.append("fault_handler_missing")

    # Distinct helpers that report SP1 / SP2 (name flexible; body must contain strings).
    sp1_helpers = []
    sp2_helpers = []
    for m in re.finditer(r"(?:static\s+)?void\s+(\w+)\s*\([^;]*\)\s*\{", src):
        name = m.group(1)
        if name in ("prvROAccessTask", "prvRWAccessTask", "prvReportPropertyResult", "vStartMPUDemo"):
            continue
        body = _extract_fn(src, name) or ""
        if SP1_PASS in body or SP1_FAIL in body:
            sp1_helpers.append(name)
        if SP2_PASS in body or SP2_FAIL in body:
            sp2_helpers.append(name)

    ro_fn = _extract_fn(src, "prvROAccessTask") or ""
    # Prefer helpers called from RO task; if helpers embed both, allow same name only if two distinct.
    called_sp1 = [h for h in sp1_helpers if re.search(rf"\b{re.escape(h)}\s*\(", ro_fn)]
    called_sp2 = [h for h in sp2_helpers if re.search(rf"\b{re.escape(h)}\s*\(", ro_fn)]

    alpha_changed = re.sub(r"\s+", "", src) != re.sub(r"\s+", "", baseline_src)

    # Explicit region descriptors: named constants/macros used near xRegions or Region attributes.
    explicit_regions = bool(
        re.search(
            r"#\s*define\s+\w*(REGION|MPU|SHARED|FAULT)\w*|const\s+.*Region|xRegion\w*\s*\[",
            src,
            re.I,
        )
    ) or ("M2_R4_STRUCT" in src and "xRegions" in src and alpha_changed)

    detail["checks"] = {
        "sp1_helpers": sp1_helpers,
        "sp2_helpers": sp2_helpers,
        "called_sp1_from_ro": called_sp1,
        "called_sp2_from_ro": called_sp2,
        "structurally_changed": alpha_changed,
        "explicit_region_hints": explicit_regions,
    }

    if not called_sp1:
        fails.append("missing_sp1_helper_called_from_ro_task")
    if not called_sp2:
        fails.append("missing_sp2_helper_called_from_ro_task")
    # Require two observation helpers (may be same file distinct functions)
    distinct = set(called_sp1) | set(called_sp2)
    if len(set(called_sp1) & set(called_sp2)) == 1 and len(distinct) == 1:
        # One helper doing both is weaker than required distinct helpers
        fails.append("sp1_and_sp2_must_be_distinct_helpers")
    if not alpha_changed:
        fails.append("no_structural_change_vs_baseline")
    if not explicit_regions:
        fails.append("missing_explicit_region_descriptors")

    if uart_text:
        if SP1_PASS not in uart_text or SP2_PASS not in uart_text:
            fails.append("uart_missing_sp_pass")
        if SP1_FAIL in uart_text or SP2_FAIL in uart_text:
            fails.append("uart_has_sp_fail")

    return {
        "verdict": "PASS" if not fails else "FAIL",
        "failure_reasons": fails,
        "detail": detail,
    }


def check_m2_e4(*, src: str, uart_text: str) -> dict[str, Any]:
    fails: list[str] = []
    detail: dict[str, Any] = {"task_id": "M2-E4"}

    prefix = "M2_E4_TELEMETRY:"
    if prefix not in src and "M2_E4_TELEMETRY" not in src:
        fails.append("missing_telemetry_prefix_in_source")
    wired = bool(
        re.search(
            r"prvReportPropertyResult\s*\(\s*\"[^\"]*M2_E4_TELEMETRY|M2_E4_TELEMETRY[^\"]*\"",
            src,
        )
        or re.search(r"0x40004000[\s\S]{0,200}M2_E4_TELEMETRY|M2_E4_TELEMETRY[\s\S]{0,200}0x40004000", src)
        or (prefix in src)
    )
    if not wired:
        fails.append("telemetry_not_wired_to_uart_path")

    if SP1_PASS not in src:
        fails.append("sp1_pass_string_missing")
    if SP2_PASS not in src:
        fails.append("sp2_pass_string_missing")
    if RO_ATTR not in src:
        fails.append("ro_region_attribute_missing")
    if "portRAISE_PRIVILEGE" not in src:
        fails.append("portRAISE_PRIVILEGE_missing")
    if "ucROTaskFaultTracker" not in src:
        fails.append("fault_tracker_missing")

    lines = re.findall(
        r"M2_E4_TELEMETRY:\s*cycle=(\d+)\s+sp1=PASS\s+sp2=PASS",
        uart_text,
    )
    cycles = [int(x) for x in lines]
    mono = cycles == list(range(1, len(cycles) + 1)) if cycles else False

    detail["checks"] = {
        "wired": wired,
        "uart_cycles": cycles,
        "uart_monotonic_from_1": mono,
    }

    if not uart_text.strip():
        fails.append("uart_log_required_for_m2_e4")
    else:
        if not (mono and len(cycles) >= 1):
            fails.append("uart_telemetry_not_monotonic_or_missing")
        if SP1_PASS not in uart_text or SP2_PASS not in uart_text:
            fails.append("uart_missing_sp_pass")
        if SP1_FAIL in uart_text or SP2_FAIL in uart_text:
            fails.append("uart_has_sp_fail")

    return {
        "verdict": "PASS" if not fails else "FAIL",
        "failure_reasons": fails,
        "detail": detail,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Advanced-task L2 checker")
    ap.add_argument("--task", required=True, choices=["M1-R4", "M1-E4", "M2-R4", "M2-E4"])
    ap.add_argument("--src", required=True, type=Path)
    ap.add_argument("--baseline", type=Path, default=None)
    ap.add_argument("--uart", type=Path, default=None)
    ap.add_argument("--uut", type=Path, default=None, help="Host-compilable UUT for M1-E4 behavioural L2")
    ap.add_argument("--json-out", type=Path, default=None)
    args = ap.parse_args()

    src = args.src.read_text(encoding="utf-8", errors="replace")
    baseline = (
        args.baseline.read_text(encoding="utf-8", errors="replace")
        if args.baseline
        else src
    )
    uart = args.uart.read_text(encoding="utf-8", errors="replace") if args.uart else ""

    if args.task == "M1-R4":
        result = check_m1_r4(src=src, baseline_src=baseline)
    elif args.task == "M1-E4":
        uut = args.uut if args.uut else (args.src if args.src.suffix == ".c" else None)
        # For full QueueSet.c, behavioural needs a host UUT extract — require --uut
        result = check_m1_e4(src=src, uut_c=uut)
    elif args.task == "M2-R4":
        result = check_m2_r4(src=src, baseline_src=baseline, uart_text=uart)
    else:
        result = check_m2_e4(src=src, uart_text=uart)

    text = json.dumps(result, indent=2)
    print(text)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text + "\n", encoding="utf-8")
    return 0 if result["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
