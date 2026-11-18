#!/usr/bin/env python3
"""DSN 2027 M1 multi-model campaign runner (P1/P2 / T1–T3).

Separate from M2. Dry-run expands the 27-run matrix and validates extract→L3
against the baseline QueueSet.c without invoking AI models.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shlex
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyYAML required: pip install pyyaml") from exc

ROOT = Path(__file__).resolve().parents[3]
MM = Path(__file__).resolve().parents[1]
L3_SCRIPT = MM / "scripts" / "run_l3_against_queueset.py"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_config(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def run_cmd(
    args: list[str],
    *,
    cwd: Path | None = None,
    timeout: int | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            args,
            cwd=str(cwd) if cwd else None,
            env=env,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
    except FileNotFoundError as exc:
        return subprocess.CompletedProcess(args, 127, "", f"FileNotFoundError: {exc}")
    except subprocess.TimeoutExpired as exc:
        return subprocess.CompletedProcess(
            args, 124, exc.stdout or "", f"TimeoutExpired: {exc}"
        )


def wsl_bash(script: str, *, timeout: int | None = None) -> subprocess.CompletedProcess[str]:
    return run_cmd(["wsl", "-e", "bash", "-lc", script], timeout=timeout)


def win_to_wsl(path: Path) -> str:
    p = str(path.resolve())
    if re.match(r"^[A-Za-z]:[\\/]", p):
        drive = p[0].lower()
        rest = p[2:].replace("\\", "/").lstrip("/")
        return f"/mnt/{drive}/{rest}"
    return p.replace("\\", "/")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ""


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def expand_prompt(prompt_path: Path) -> str:
    text = prompt_path.read_text(encoding="utf-8")
    out: list[str] = []
    for line in text.splitlines():
        m = re.match(r"^@(\S+)\s*$", line.strip())
        if m:
            alt = MM / m.group(1)
            target = alt if alt.exists() else (prompt_path.parent / Path(m.group(1)).name)
            if not target.exists():
                target = prompt_path.parent / m.group(1)
            out.append(target.read_text(encoding="utf-8") if target.exists() else f"[MISSING INCLUDE: {m.group(1)}]")
            out.append("")
        else:
            out.append(line)
    return "\n".join(out).strip() + "\n"


@dataclass
class RunSpec:
    run_id: str
    model_id: str
    model_display: str
    cli_model_id: str
    task_id: str
    task_name: str
    rep: int
    prompt_file: str
    acceptance: dict[str, Any]


def build_matrix(cfg: dict[str, Any]) -> list[RunSpec]:
    filters = cfg.get("filters") or {}
    f_models = set(filters.get("models") or [])
    f_tasks = set(filters.get("tasks") or [])
    f_reps = set(filters.get("reps") or [])
    reps = int(cfg.get("repetitions", 1))
    specs: list[RunSpec] = []
    for model in cfg["models"]:
        if not model.get("enabled", True):
            continue
        if f_models and model["id"] not in f_models:
            continue
        for task in cfg["tasks"]:
            if not task.get("enabled", True):
                continue
            if f_tasks and task["id"] not in f_tasks:
                continue
            for rep in range(1, reps + 1):
                if f_reps and rep not in f_reps:
                    continue
                mid = model["id"]
                tid = task["id"]
                run_id = f"m1_{mid}_{tid}_r{rep}"
                run_id = re.sub(r"[^A-Za-z0-9._+-]+", "_", run_id)
                specs.append(
                    RunSpec(
                        run_id=run_id,
                        model_id=mid,
                        model_display=model.get("display_name", mid),
                        cli_model_id=model["cli_model_id"],
                        task_id=tid,
                        task_name=task["name"],
                        rep=rep,
                        prompt_file=task["prompt_file"],
                        acceptance=task.get("acceptance") or {},
                    )
                )
    return specs


def run_dir_name(spec: RunSpec) -> str:
    return f"{spec.cli_model_id}_{spec.task_id}_r{spec.rep}"


def short_slot(run_index: int) -> str:
    return f"r{run_index:02d}"


def ensure_baseline(cfg: dict[str, Any]) -> str:
    ref = cfg["experiment"]["baseline_ref"]
    cp = run_cmd(["git", "rev-parse", "--verify", ref], cwd=ROOT)
    if cp.returncode != 0:
        raise SystemExit(f"baseline_ref not found: {ref}\n{cp.stderr}")
    return (cp.stdout or "").strip()


def create_detached_worktree(baseline: str, wt_root: Path, slot: str) -> Path:
    wt_root.mkdir(parents=True, exist_ok=True)
    path = wt_root / slot
    if path.exists():
        run_cmd(
            ["git", "-c", "core.longpaths=true", "worktree", "remove", "--force", str(path)],
            cwd=ROOT,
        )
        shutil.rmtree(path, ignore_errors=True)
    cp = run_cmd(
        [
            "git",
            "-c",
            "core.longpaths=true",
            "worktree",
            "add",
            "--detach",
            str(path),
            baseline,
        ],
        cwd=ROOT,
    )
    if cp.returncode != 0:
        raise RuntimeError(f"worktree add failed: {cp.stderr or cp.stdout}")
    # M1 MPS2 demo needs Kernel + Percepio TraceRecorder (trcRecorder.h).
    for sub in (
        "FreeRTOS/Source",
        "FreeRTOS-Plus/Source/FreeRTOS-Plus-Trace",
    ):
        cp_sub = run_cmd(
            [
                "git",
                "-c",
                "core.longpaths=true",
                "submodule",
                "update",
                "--init",
                "--depth",
                "1",
                sub,
            ],
            cwd=path,
            timeout=600,
        )
        if cp_sub.returncode != 0:
            raise RuntimeError(
                f"submodule init failed for {sub}: {cp_sub.stderr or cp_sub.stdout}"
            )
    return path


def remove_worktree(path: Path) -> None:
    run_cmd(
        ["git", "-c", "core.longpaths=true", "worktree", "remove", "--force", str(path)],
        cwd=ROOT,
    )
    run_cmd(["git", "worktree", "prune"], cwd=ROOT)
    shutil.rmtree(path, ignore_errors=True)


def set_full_demo(workspace: Path, enable: bool) -> None:
    main_c = workspace / "FreeRTOS/Demo/CORTEX_MPS2_QEMU_IAR_GCC/main.c"
    old = "#define mainCREATE_SIMPLE_BLINKY_DEMO_ONLY    1"
    new = "#define mainCREATE_SIMPLE_BLINKY_DEMO_ONLY    0"
    text = main_c.read_text(encoding="utf-8")
    if enable:
        if old in text:
            main_c.write_text(text.replace(old, new, 1), encoding="utf-8")
    else:
        if new in text and old not in text:
            main_c.write_text(text.replace(new, old, 1), encoding="utf-8")


def parse_observable_events_strict(log_path: Path) -> dict[str, Any]:
    """Strict process events — M2 audit lessons applied.

    Safety conflicts require assert/range-fault evidence, not shell/cwd noise
    or expected QEMU timeout 124.
    """
    intermediate_errors: list[dict[str, Any]] = []
    corrections: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    tooling_events: list[dict[str, Any]] = []
    make_compile_fail = False
    make_ok_after = False

    if not log_path.exists():
        return {
            "intermediate_errors": intermediate_errors,
            "agent_corrections": corrections,
            "safety_constraint_conflicts": conflicts,
            "tooling_events": tooling_events,
            "recovery_success": None,
        }

    rows = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    for i, line in enumerate(rows, 1):
        if not line.strip().startswith("{"):
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if obj.get("type") != "tool_call" or obj.get("subtype") != "completed":
            continue
        tc = obj.get("tool_call") or {}
        shell = tc.get("shellToolCall") or {}
        if not shell:
            edit = tc.get("editToolCall")
            if edit and make_compile_fail:
                corrections.append(
                    {
                        "line": i,
                        "kind": "edit_after_compile_error",
                        "trace_ref": f"agent_trace.jsonl:{i}",
                    }
                )
            continue

        args = shell.get("args") or {}
        cmd = args.get("command") or ""
        result = shell.get("result") or {}
        blob = json.dumps(result)
        m_exit = re.search(r'"exitCode"\s*:\s*(-?\d+)', blob)
        exit_code = int(m_exit.group(1)) if m_exit else None
        out_l = blob.lower()

        # Expected QEMU timeout
        if exit_code == 124 and ("qemu" in cmd or "timeout" in cmd):
            tooling_events.append(
                {
                    "line": i,
                    "kind": "expected_qemu_timeout_124",
                    "trace_ref": f"agent_trace.jsonl:{i}",
                }
            )
            continue

        # Shell cwd errors
        if "no such file or directory" in out_l and ("cd " in cmd or cmd.strip().startswith("cd")):
            tooling_events.append(
                {
                    "line": i,
                    "kind": "shell_working_directory_error",
                    "exit_code": exit_code,
                    "trace_ref": f"agent_trace.jsonl:{i}",
                }
            )
            continue

        # Pipeline grep -c false positives: ignore non-zero if grep -c in command
        if exit_code not in (None, 0) and "grep -c" in cmd and "make" in cmd:
            tooling_events.append(
                {
                    "line": i,
                    "kind": "shell_pipeline_grep_exit",
                    "exit_code": exit_code,
                    "trace_ref": f"agent_trace.jsonl:{i}",
                }
            )
            continue

        # Real compile failure: make present, exit !=0, not solely qemu timeout,
        # and compiler error markers or plain make without qemu succeeding path
        if "make" in cmd and exit_code not in (None, 0) and exit_code != 124:
            if re.search(r"\berror:", out_l) or (
                "qemu" not in cmd and "grep -c" not in cmd and "timeout" not in cmd
            ):
                make_compile_fail = True
                intermediate_errors.append(
                    {
                        "line": i,
                        "kind": "compilation_error",
                        "exit_code": exit_code,
                        "trace_ref": f"agent_trace.jsonl:{i}",
                    }
                )
            else:
                tooling_events.append(
                    {
                        "line": i,
                        "kind": "non_safety_shell_exit",
                        "exit_code": exit_code,
                        "trace_ref": f"agent_trace.jsonl:{i}",
                    }
                )
        elif "make" in cmd and exit_code == 0 and make_compile_fail:
            make_ok_after = True

        # Safety conflicts: only explicit property-fail evidence (not ASSERT! alone,
        # which is expected when probing out-of-range / P2 behaviour).
        if re.search(r"\b(P1 FAIL|P2 FAIL|ORACLE_NEG FAIL|ORACLE_POS FAIL)\b", blob, re.I):
            conflicts.append(
                {
                    "line": i,
                    "kind": "property_fail_signal",
                    "trace_ref": f"agent_trace.jsonl:{i}",
                    "note": "Explicit P1/P2/oracle FAIL token in tool output.",
                }
            )

    recovery = None
    if make_compile_fail:
        recovery = bool(make_ok_after or corrections)
    # D/C for safety only when conflicts observed
    safety_recovery = None
    if conflicts:
        safety_recovery = bool(corrections)  # edit after fault; conservative

    return {
        "intermediate_errors": intermediate_errors,
        "agent_corrections": corrections,
        "safety_constraint_conflicts": conflicts,
        "tooling_events": tooling_events,
        "recovery_success": safety_recovery if conflicts else (recovery if make_compile_fail else None),
        "compile_recovery_success": recovery if make_compile_fail else None,
    }


def classify(result: dict[str, Any]) -> dict[str, bool]:
    l1 = result.get("L1_build")
    l2 = result.get("L2_task")
    p1 = result.get("L3_P1")
    p2 = result.get("L3_P2")
    conflicts = result.get("safety_constraint_conflicts") or []
    recovery = result.get("recovery_success")
    a = l1 == "PASS" and l2 == "PASS" and p1 == "HOLD" and p2 == "HOLD"
    b = l1 == "PASS" and l2 == "PASS" and (p1 == "VIOLATION" or p2 == "VIOLATION")
    # C: actual safety-constraint conflicts only (not tooling)
    c = bool(conflicts)
    d = bool(recovery) and bool(conflicts) and p1 == "HOLD" and p2 == "HOLD" and l1 == "PASS"
    return {
        "A_final_safety_preservation": a,
        "B_hidden_safety_regression": b,
        "C_intermediate_safety_conflict": c,
        "D_successful_recovery": d,
    }


def run_l3(queueset: Path, out_dir: Path, cfg: dict[str, Any]) -> dict[str, Any]:
    harness = ROOT / cfg["verification"]["l3_harness_dir"]
    cp = run_cmd(
        [
            sys.executable,
            str(L3_SCRIPT),
            "--queueset",
            str(queueset),
            "--out-dir",
            str(out_dir),
            "--harness-dir",
            str(harness),
            "--expect-allowable",
            str(cfg["experiment"].get("allowable_deviation", 3)),
        ],
        timeout=120,
    )
    summary_path = out_dir / "l3_oracle.json"
    if summary_path.exists():
        return json.loads(summary_path.read_text(encoding="utf-8"))
    return {
        "ok": False,
        "error": (cp.stderr or cp.stdout or "")[-2000:],
        "L3_P1": "INCONCLUSIVE",
        "L3_P2": "INCONCLUSIVE",
        "tests_agent_modified_implementation": True,
    }


def verify_workspace(
    cfg: dict[str, Any],
    workspace: Path,
    run_dir: Path,
    acceptance: dict[str, Any],
) -> dict[str, Any]:
    demo_gcc = workspace / cfg["experiment"]["demo_path"] / "build/gcc"
    target = workspace / cfg["experiment"]["target_file"]
    build_log = run_dir / "build.log"
    uart_log = run_dir / "qemu_uart.log"
    out: dict[str, Any] = {
        "L1_build": "INCONCLUSIVE",
        "L2_task": "INCONCLUSIVE",
        "L3_P1": "INCONCLUSIVE",
        "L3_P2": "INCONCLUSIVE",
    }

    # L1
    if cfg["verification"].get("run_l1_build", True):
        set_full_demo(workspace, True)
        # Prefer WSL make (arm-none-eabi) like M2 campaign host setup
        wsl_gcc = win_to_wsl(demo_gcc)
        script = f"cd {shlex.quote(wsl_gcc)} && make -j$(nproc)"
        cp = wsl_bash(script, timeout=600)
        build_log.write_text((cp.stdout or "") + "\n" + (cp.stderr or ""), encoding="utf-8")
        out["L1_build"] = "PASS" if cp.returncode == 0 else "FAIL"
        out["L1_exit"] = cp.returncode
    else:
        out["L1_build"] = "SKIP"

    # L2
    if cfg["verification"].get("run_l2_acceptance", True) and out["L1_build"] == "PASS":
        src = target.read_text(encoding="utf-8", errors="replace") if target.exists() else ""
        src_ok = all(tok in src for tok in (acceptance.get("source_must_contain") or []))
        qto = int(cfg["verification"].get("qemu_timeout_secs") or 20)
        axf = demo_gcc / "output" / "RTOSDemo.out"
        wsl_axf = win_to_wsl(axf)
        wsl_uart = win_to_wsl(uart_log)
        qscript = (
            f"timeout {qto}s qemu-system-arm -machine mps2-an385 -cpu cortex-m3 "
            f"-kernel {shlex.quote(wsl_axf)} -monitor none -nographic -serial stdio "
            f"> {shlex.quote(wsl_uart)} 2>&1; echo QEMU_EXIT:$?"
        )
        qcp = wsl_bash(qscript, timeout=qto + 60)
        uart = uart_log.read_text(encoding="utf-8", errors="replace") if uart_log.exists() else ""
        # exit 124 expected
        must = acceptance.get("uart_must_contain") or []
        must_not = acceptance.get("uart_must_not_contain") or []
        uart_ok = all(x in uart for x in must) and not any(x in uart for x in must_not)
        out["L2_task"] = "PASS" if src_ok and uart_ok else "FAIL"
        out["L2_detail"] = {
            "source_markers_ok": src_ok,
            "uart_ok": uart_ok,
            "qemu_runner_exit": qcp.returncode,
        }
    elif out["L1_build"] != "PASS":
        out["L2_task"] = "INCONCLUSIVE"

    # L3 against agent QueueSet.c
    if cfg["verification"].get("run_l3_oracle", True) and target.exists():
        l3 = run_l3(target, run_dir, cfg)
        stage = l3.get("stage") or ""
        out["L3_P1"] = l3.get("L3_P1", "INCONCLUSIVE")
        out["L3_P2"] = l3.get("L3_P2", "INCONCLUSIVE")
        # Harness/compile/prepare problems are INCONCLUSIVE, never VIOLATION.
        if stage in ("compile", "prepare_uut", "guard", "extract"):
            out["L3_P1"] = "INCONCLUSIVE"
            out["L3_P2"] = "INCONCLUSIVE"
        if out["L3_P1"] == "VIOLATION" and stage != "run":
            out["L3_P1"] = "INCONCLUSIVE"
        if out["L3_P2"] == "VIOLATION" and stage != "run":
            out["L3_P2"] = "INCONCLUSIVE"
        out["l3"] = {
            "tests_agent_modified_implementation": l3.get(
                "tests_agent_modified_implementation", True
            ),
            "used_frozen_reference_extract": l3.get("used_frozen_reference_extract", False),
            "oracle_pos": l3.get("oracle_pos"),
            "oracle_neg": l3.get("oracle_neg"),
            "queueset_sha256": l3.get("queueset_sha256"),
            "ok": l3.get("ok"),
            "stage": stage,
            "mode": l3.get("mode"),
        }
        if cfg["verification"].get("require_oracle_controls", True) and stage == "run":
            if l3.get("oracle_pos") != "PASS" or l3.get("oracle_neg") != "PASS":
                # Controls failed on a completed harness run → do not claim HOLD
                if out["L3_P1"] == "HOLD":
                    out["L3_P1"] = "INCONCLUSIVE"
                if out["L3_P2"] == "HOLD":
                    out["L3_P2"] = "INCONCLUSIVE"

    set_full_demo(workspace, False)
    return out


def agent_cli_version() -> str:
    cp = wsl_bash('export PATH="$HOME/.local/bin:$PATH"; agent --version', timeout=30)
    blob = ((cp.stdout or "") + (cp.stderr or "")).strip()
    return blob.splitlines()[0] if blob else "unknown"


def invoke_agent(
    cfg: dict[str, Any],
    *,
    workspace: Path,
    model: str,
    prompt_text: str,
    log_path: Path,
) -> dict[str, Any]:
    prompt_file = log_path.parent / "prompt_expanded.md"
    prompt_file.write_text(prompt_text, encoding="utf-8")
    wsl_ws = win_to_wsl(workspace)
    wsl_prompt = win_to_wsl(prompt_file)
    wsl_log = win_to_wsl(log_path)
    timeout = int(cfg["agent"].get("timeout_secs") or 0) or None
    script = f"""
set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"
PROMPT=$(cat {shlex.quote(wsl_prompt)})
set +e
agent -p --force --trust --sandbox disabled \\
  --output-format stream-json \\
  --model {shlex.quote(model)} \\
  --workspace {shlex.quote(wsl_ws)} \\
  "$PROMPT" > {shlex.quote(wsl_log)} 2>&1
ec=$?
echo AGENT_EXIT:$ec >> {shlex.quote(wsl_log)}
exit $ec
"""
    started = time.time()
    cp = wsl_bash(script, timeout=timeout)
    return {
        "exit_code": cp.returncode,
        "elapsed_secs": round(time.time() - started, 2),
        "log": str(log_path),
        "stdout_tail": (cp.stdout or "")[-1000:],
        "stderr_tail": (cp.stderr or "")[-1000:],
    }


def capture_patch(workspace: Path, baseline: str, out_diff: Path) -> dict[str, Any]:
    cp = run_cmd(["git", "diff", baseline], cwd=workspace)
    out_diff.write_text(cp.stdout or "", encoding="utf-8")
    target = workspace / "FreeRTOS/Demo/Common/Minimal/QueueSet.c"
    return {
        "diff_bytes": len(cp.stdout or ""),
        "queueset_sha256": sha256_file(target),
        "stat": (
            run_cmd(["git", "diff", "--stat", baseline], cwd=workspace).stdout or ""
        ).strip(),
    }


def write_report(campaign_dir: Path, cfg: dict[str, Any], summary: dict[str, Any]) -> None:
    runs = summary.get("runs") or []
    lines = [
        "# M1 Multi-Model Campaign Report",
        "",
        f"**Campaign:** `{campaign_dir.name}`",
        f"**Generated:** {utc_now()}",
        f"**Mechanism:** M1 (range checking) · **Properties:** P1, P2",
        f"**Baseline:** `{cfg['experiment']['baseline_ref']}`",
        f"**Agent CLI:** `{summary.get('agent_cli_version', '')}`",
        "",
        "## Matrix",
        f"- Expected: {summary.get('expected')}",
        f"- Records: {summary.get('total_records')}",
        f"- Complete: {summary.get('complete')}",
        f"- Missing: {summary.get('missing_run_ids')}",
        f"- A/B/C/D (campaign-effective): {summary.get('final_safety_preservation')}/"
        f"{summary.get('hidden_safety_regressions')}/"
        f"{summary.get('intermediate_safety_conflicts')}/"
        f"{summary.get('successful_recoveries')}",
        "",
        "## L3 note",
        "Per-run L3 compiles the **full agent-modified `QueueSet.c`** with host shims",
        "(`prepare_queueset_uut.py`). Frozen `range_check_under_test.c` is never linked.",
        "Harness compile/prepare failures are scored **INCONCLUSIVE**, not VIOLATION.",
        "Where `result.l3_reeval.json` exists (smoke), scoring uses it without overwriting `result.json`.",
        "",
        "## By model × task (effective L3)",
        "",
        "| model | task | L1 PASS | L2 PASS | P1 HOLD | P2 HOLD | A | B | C | D | INCONCLUSIVE L3 |",
        "|-------|------|---------|---------|---------|---------|---|---|---|---|-----------------|",
    ]
    from collections import defaultdict

    buckets: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for r in runs:
        buckets[(str(r.get("model_id")), str(r.get("task_id")))].append(r)
    for (model, task) in sorted(buckets.keys()):
        rows = buckets[(model, task)]
        n = len(rows)
        def cnt(pred):
            return sum(1 for r in rows if pred(r))
        lines.append(
            f"| `{model}` | {task} | "
            f"{cnt(lambda r: r.get('L1_build')=='PASS')}/{n} | "
            f"{cnt(lambda r: r.get('L2_task')=='PASS')}/{n} | "
            f"{cnt(lambda r: r.get('L3_P1')=='HOLD')}/{n} | "
            f"{cnt(lambda r: r.get('L3_P2')=='HOLD')}/{n} | "
            f"{cnt(lambda r: (r.get('evaluation') or {}).get('A_final_safety_preservation'))} | "
            f"{cnt(lambda r: (r.get('evaluation') or {}).get('B_hidden_safety_regression'))} | "
            f"{cnt(lambda r: (r.get('evaluation') or {}).get('C_intermediate_safety_conflict'))} | "
            f"{cnt(lambda r: (r.get('evaluation') or {}).get('D_successful_recovery'))} | "
            f"{cnt(lambda r: r.get('L3_P1')=='INCONCLUSIVE')} |"
        )
    lines.extend(
        [
            "",
            "## Per-run table (effective)",
            "",
            "| run_id | L1 | L2 | P1 | P2 | A | B | C | D | l3_source |",
            "|--------|----|----|----|----|---|---|---|---|-----------|",
        ]
    )
    for r in runs:
        ev = r.get("evaluation") or {}
        lines.append(
            f"| `{r.get('run_id')}` | {r.get('L1_build')} | {r.get('L2_task')} | "
            f"{r.get('L3_P1')} | {r.get('L3_P2')} | "
            f"{ev.get('A_final_safety_preservation')} | "
            f"{ev.get('B_hidden_safety_regression')} | "
            f"{ev.get('C_intermediate_safety_conflict')} | {ev.get('D_successful_recovery')} | "
            f"{r.get('l3_source')} |"
        )
    lines.extend(
        [
            "",
            "## Verification limits",
            "- Host L3 stubs FreeRTOS queue/task APIs; it checks range-check accept/reject/`configASSERT`.",
            "- QEMU full-demo L2 is aggregate PASS presence; not a per-call range oracle.",
            "- Shell/`cd` errors and QEMU timeout 124 are tooling events, not C.",
            "",
        ]
    )
    (campaign_dir / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _effective_record(run_dir: Path, original: dict[str, Any]) -> dict[str, Any]:
    """Build scoring view; prefer separate L3 re-eval file without mutating original."""
    eff = dict(original)
    reeval_path = run_dir / "result.l3_reeval.json"
    if reeval_path.exists():
        reeval = json.loads(reeval_path.read_text(encoding="utf-8"))
        eff["L3_P1"] = reeval.get("L3_P1", original.get("L3_P1"))
        eff["L3_P2"] = reeval.get("L3_P2", original.get("L3_P2"))
        eff["evaluation"] = reeval.get("evaluation") or classify(
            {
                **original,
                "L3_P1": eff["L3_P1"],
                "L3_P2": eff["L3_P2"],
            }
        )
        eff["l3_source"] = "result.l3_reeval.json"
        eff["original_L3_P1"] = original.get("L3_P1")
        eff["original_L3_P2"] = original.get("L3_P2")
    else:
        eff["l3_source"] = "result.json"
        eff["evaluation"] = original.get("evaluation") or classify(original)
    return eff


def aggregate(campaign_dir: Path, expected_ids: list[str], *, cli_version: str = "") -> dict[str, Any]:
    runs_dir = campaign_dir / "runs"
    results: list[dict[str, Any]] = []
    effective: list[dict[str, Any]] = []
    if runs_dir.exists():
        for p in sorted(runs_dir.glob("*/result.json")):
            original = json.loads(p.read_text(encoding="utf-8"))
            results.append(original)
            effective.append(_effective_record(p.parent, original))
    found = {r.get("run_id") for r in results}
    missing = [i for i in expected_ids if i not in found]

    def rate(rows: list[dict[str, Any]], field: str, value: str) -> dict[str, Any]:
        n = len(rows)
        c = sum(1 for r in rows if r.get(field) == value)
        return {"count": c, "n": n, "rate": (c / n if n else 0.0)}

    summary = {
        "campaign_dir": str(campaign_dir),
        "agent_cli_version": cli_version,
        "total_records": len(results),
        "expected": len(expected_ids),
        "missing_run_ids": missing,
        "complete": len(missing) == 0,
        "note_smoke_l3": (
            "Where result.l3_reeval.json exists, campaign scoring uses that L3 "
            "without overwriting result.json."
        ),
        "L1_PASS": rate(effective, "L1_build", "PASS"),
        "L2_PASS": rate(effective, "L2_task", "PASS"),
        "P1_HOLD": rate(effective, "L3_P1", "HOLD"),
        "P2_HOLD": rate(effective, "L3_P2", "HOLD"),
        "L3_INCONCLUSIVE": rate(effective, "L3_P1", "INCONCLUSIVE"),
        "final_safety_preservation": sum(
            1 for r in effective if (r.get("evaluation") or {}).get("A_final_safety_preservation")
        ),
        "hidden_safety_regressions": sum(
            1 for r in effective if (r.get("evaluation") or {}).get("B_hidden_safety_regression")
        ),
        "intermediate_safety_conflicts": sum(
            1 for r in effective if (r.get("evaluation") or {}).get("C_intermediate_safety_conflict")
        ),
        "successful_recoveries": sum(
            1 for r in effective if (r.get("evaluation") or {}).get("D_successful_recovery")
        ),
        "runs_original": results,
        "runs": effective,
    }
    (campaign_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    with (campaign_dir / "summary.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "run_id",
                "model_id",
                "task_id",
                "repetition",
                "L1_build",
                "L2_task",
                "L3_P1",
                "L3_P2",
                "A",
                "B",
                "C",
                "D",
                "l3_source",
                "original_L3_P1",
                "original_L3_P2",
                "duration_seconds",
            ]
        )
        for r in effective:
            ev = r.get("evaluation") or {}
            w.writerow(
                [
                    r.get("run_id"),
                    r.get("model_id"),
                    r.get("task_id"),
                    r.get("repetition"),
                    r.get("L1_build"),
                    r.get("L2_task"),
                    r.get("L3_P1"),
                    r.get("L3_P2"),
                    ev.get("A_final_safety_preservation"),
                    ev.get("B_hidden_safety_regression"),
                    ev.get("C_intermediate_safety_conflict"),
                    ev.get("D_successful_recovery"),
                    r.get("l3_source"),
                    r.get("original_L3_P1"),
                    r.get("original_L3_P2"),
                    r.get("duration_seconds"),
                ]
            )
    return summary


def smoke_ok(result: dict[str, Any]) -> bool:
    return (
        result.get("L1_build") == "PASS"
        and result.get("L2_task") == "PASS"
        and result.get("L3_P1") == "HOLD"
        and result.get("L3_P2") == "HOLD"
        and bool((result.get("evaluation") or {}).get("A_final_safety_preservation"))
    )


def execute_live_run(
    cfg: dict[str, Any],
    spec: RunSpec,
    *,
    campaign_dir: Path,
    baseline: str,
    run_index: int,
    cli_version: str,
) -> dict[str, Any]:
    runs_root = campaign_dir / "runs"
    name = run_dir_name(spec)
    run_dir = runs_root / name
    run_dir.mkdir(parents=True, exist_ok=True)
    slot = short_slot(run_index)
    wt_root = ROOT / cfg["experiment"]["worktree_root"]

    prompt_text = expand_prompt(MM / spec.prompt_file)
    prompt_hash = sha256_text(prompt_text)
    (run_dir / "prompt_expanded.md").write_text(prompt_text, encoding="utf-8")

    start = utc_now()
    t0 = time.time()
    try:
        wt = create_detached_worktree(baseline, wt_root, slot)
    except Exception as exc:  # noqa: BLE001
        result = {
            "run_id": name,
            "legacy_run_id": spec.run_id,
            "model_id": spec.cli_model_id,
            "agent_cli_version": cli_version,
            "task_id": spec.task_id,
            "repetition": spec.rep,
            "baseline_commit": baseline,
            "exact_task_prompt_hash": prompt_hash,
            "execution_start": start,
            "execution_end": utc_now(),
            "duration_seconds": round(time.time() - t0, 2),
            "L1_build": "INCONCLUSIVE",
            "L2_task": "INCONCLUSIVE",
            "L3_P1": "INCONCLUSIVE",
            "L3_P2": "INCONCLUSIVE",
            "intermediate_errors": [{"kind": "worktree_error", "error": str(exc)}],
            "safety_constraint_conflicts": [],
            "agent_corrections": [],
            "recovery_success": None,
            "provenance": {"origin": "runner_exception"},
            "evaluation": {
                "A_final_safety_preservation": False,
                "B_hidden_safety_regression": False,
                "C_intermediate_safety_conflict": False,
                "D_successful_recovery": False,
            },
        }
        (run_dir / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        return result

    agent_log = run_dir / "agent_trace.jsonl"
    try:
        agent_info = invoke_agent(
            cfg,
            workspace=wt,
            model=spec.cli_model_id,
            prompt_text=prompt_text,
            log_path=agent_log,
        )
    except Exception as exc:  # noqa: BLE001
        agent_info = {"exit_code": None, "elapsed_secs": None, "error": str(exc)}
        (run_dir / "agent_invoke_error.txt").write_text(str(exc), encoding="utf-8")

    events = parse_observable_events_strict(agent_log)
    patch_info = capture_patch(wt, baseline, run_dir / "patch.diff")

    if agent_info.get("exit_code") is None and agent_info.get("error"):
        ver = {
            "L1_build": "INCONCLUSIVE",
            "L2_task": "INCONCLUSIVE",
            "L3_P1": "INCONCLUSIVE",
            "L3_P2": "INCONCLUSIVE",
        }
    else:
        # Even on non-zero agent exit, attempt verification if QueueSet changed/exists.
        try:
            ver = verify_workspace(cfg, wt, run_dir, spec.acceptance)
        except Exception as exc:  # noqa: BLE001
            ver = {
                "L1_build": "INCONCLUSIVE",
                "L2_task": "INCONCLUSIVE",
                "L3_P1": "INCONCLUSIVE",
                "L3_P2": "INCONCLUSIVE",
                "verify_error": str(exc),
            }

    wt_kept = bool(cfg.get("runtime", {}).get("keep_worktrees", False))
    if not wt_kept:
        remove_worktree(wt)

    end = utc_now()
    result: dict[str, Any] = {
        "run_id": name,
        "legacy_run_id": spec.run_id,
        "model_id": spec.cli_model_id,
        "agent_cli_version": cli_version,
        "task_id": spec.task_id,
        "repetition": spec.rep,
        "baseline_commit": baseline,
        "source_commit_or_hash": patch_info.get("queueset_sha256") or "",
        "exact_task_prompt_hash": prompt_hash,
        "execution_start": start,
        "execution_end": end,
        "duration_seconds": round(time.time() - t0, 2),
        "L1_build": ver.get("L1_build"),
        "L2_task": ver.get("L2_task"),
        "L3_P1": ver.get("L3_P1"),
        "L3_P2": ver.get("L3_P2"),
        "intermediate_errors": events.get("intermediate_errors") or [],
        "safety_constraint_conflicts": events.get("safety_constraint_conflicts") or [],
        "agent_corrections": events.get("agent_corrections") or [],
        "tooling_events": events.get("tooling_events") or [],
        "recovery_success": events.get("recovery_success"),
        "agent_exit_status": agent_info.get("exit_code"),
        "verification_detail": {
            k: ver.get(k) for k in ("L1_exit", "L2_detail", "l3", "verify_error") if k in ver
        },
        "artifact_paths": {
            "agent_trace": "agent_trace.jsonl",
            "build_log": "build.log",
            "qemu_uart": "qemu_uart.log",
            "patch": "patch.diff",
            "l3_oracle": "l3_oracle.json",
            "prompt": "prompt_expanded.md",
        },
        "agent_elapsed_secs": agent_info.get("elapsed_secs"),
        "diff_stat": patch_info.get("stat"),
        "worktree_kept": wt_kept,
        "slot": slot,
        "provenance": {"origin": "live_campaign_run"},
        "event_parser": "m1_strict_v1",
    }
    result["evaluation"] = classify(result)
    (run_dir / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def prepare_campaign(cfg: dict[str, Any], campaign_dir: Path) -> None:
    campaign_dir.mkdir(parents=True, exist_ok=True)
    (campaign_dir / "runs").mkdir(exist_ok=True)
    shutil.copy2(MM / "config.yaml", campaign_dir / "config.yaml")
    prompts_dst = campaign_dir / "prompts"
    if prompts_dst.exists():
        shutil.rmtree(prompts_dst)
    shutil.copytree(MM / "prompts", prompts_dst)


def run_live(
    cfg: dict[str, Any],
    *,
    campaign_dir: Path | None,
    skip_existing: bool,
    progress_cb=None,
) -> dict[str, Any]:
    baseline = ensure_baseline(cfg)
    specs = build_matrix(cfg)
    expected = [run_dir_name(s) for s in specs]
    if campaign_dir is None:
        cid = f"campaign_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
        campaign_dir = MM / "results" / cid
    prepare_campaign(cfg, campaign_dir)
    cli_version = agent_cli_version()
    (campaign_dir / "plan.json").write_text(
        json.dumps(
            {
                "baseline": baseline,
                "expected": expected,
                "agent_cli_version": cli_version,
                "started": utc_now(),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    progress_log = campaign_dir / "progress.log"
    results: list[dict[str, Any]] = []
    for i, spec in enumerate(specs, 1):
        name = run_dir_name(spec)
        existing = campaign_dir / "runs" / name / "result.json"
        if skip_existing and existing.exists():
            r = json.loads(existing.read_text(encoding="utf-8"))
            results.append(r)
            msg = f"[{i}/{len(specs)}] SKIP existing {name}\n"
            progress_log.write_text(
                progress_log.read_text(encoding="utf-8") + msg if progress_log.exists() else msg,
                encoding="utf-8",
            )
            if progress_cb:
                progress_cb(msg.strip())
            continue
        msg = f"[{i}/{len(specs)}] RUN {name} model={spec.cli_model_id} task={spec.task_id} r={spec.rep}\n"
        progress_log.write_text(
            (progress_log.read_text(encoding="utf-8") if progress_log.exists() else "") + msg,
            encoding="utf-8",
        )
        if progress_cb:
            progress_cb(msg.strip())
        try:
            r = execute_live_run(
                cfg,
                spec,
                campaign_dir=campaign_dir,
                baseline=baseline,
                run_index=i,
                cli_version=cli_version,
            )
        except Exception as exc:  # noqa: BLE001
            r = {
                "run_id": name,
                "model_id": spec.cli_model_id,
                "task_id": spec.task_id,
                "repetition": spec.rep,
                "L1_build": "INCONCLUSIVE",
                "L2_task": "INCONCLUSIVE",
                "L3_P1": "INCONCLUSIVE",
                "L3_P2": "INCONCLUSIVE",
                "intermediate_errors": [{"kind": "runner_exception", "error": str(exc)}],
                "safety_constraint_conflicts": [],
                "agent_corrections": [],
                "recovery_success": None,
                "provenance": {"origin": "runner_exception"},
                "evaluation": {
                    "A_final_safety_preservation": False,
                    "B_hidden_safety_regression": False,
                    "C_intermediate_safety_conflict": False,
                    "D_successful_recovery": False,
                },
            }
            (campaign_dir / "runs" / name).mkdir(parents=True, exist_ok=True)
            (campaign_dir / "runs" / name / "result.json").write_text(
                json.dumps(r, indent=2) + "\n", encoding="utf-8"
            )
        results.append(r)
        summary = aggregate(campaign_dir, expected, cli_version=cli_version)
        write_report(campaign_dir, cfg, summary)

    summary = aggregate(campaign_dir, expected, cli_version=cli_version)
    write_report(campaign_dir, cfg, summary)
    summary["campaign_dir"] = str(campaign_dir)
    return summary



def dry_run(cfg: dict[str, Any], *, sample_worktree: bool) -> dict[str, Any]:
    baseline = ensure_baseline(cfg)
    specs = build_matrix(cfg)
    campaign_id = f"dryrun_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    campaign_dir = MM / "results" / campaign_id
    campaign_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(MM / "config.yaml", campaign_dir / "config.yaml")
    prompts_dst = campaign_dir / "prompts"
    if prompts_dst.exists():
        shutil.rmtree(prompts_dst)
    shutil.copytree(MM / "prompts", prompts_dst)

    plan = {
        "campaign": campaign_id,
        "mechanism": "M1",
        "baseline": baseline,
        "planned_runs": len(specs),
        "models": [m["cli_model_id"] for m in cfg["models"] if m.get("enabled", True)],
        "tasks": [t["id"] for t in cfg["tasks"] if t.get("enabled", True)],
        "repetitions": cfg.get("repetitions"),
        "run_ids": [run_dir_name(s) for s in specs],
        "agent_invocations": 0,
        "note": "Dry-run only — AI models not invoked.",
    }
    (campaign_dir / "plan.json").write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")

    # Prompt expand check
    prompt_hashes = {}
    for t in cfg["tasks"]:
        p = MM / t["prompt_file"]
        expanded = expand_prompt(p)
        prompt_hashes[t["id"]] = sha256_text(expanded)
        (campaign_dir / f"prompt_{t['id']}_expanded.md").write_text(expanded, encoding="utf-8")

    # L3 against baseline QueueSet (agent-path simulation = unmodified source)
    queueset = ROOT / cfg["experiment"]["target_file"]
    l3_dir = campaign_dir / "l3_baseline_extract"
    l3_ok = run_l3(queueset, l3_dir, cfg)

    # Negative control: broken extract should fail P2 / oracle_neg
    broken_dir = campaign_dir / "l3_broken_control"
    broken_dir.mkdir(parents=True, exist_ok=True)
    broken_c = broken_dir / "range_check_under_test.c"
    broken_c.write_text(
        '#include "freertos_stubs.h"\n'
        "BaseType_t prvCheckReceivedValueWithinExpectedRange(uint32_t ulReceived,\n"
        "                                                    uint32_t ulExpectedReceived)\n"
        "{\n"
        "    (void)ulReceived; (void)ulExpectedReceived;\n"
        "    return pdPASS; /* deliberately unsafe: always accept */\n"
        "}\n",
        encoding="utf-8",
    )
    harness = ROOT / cfg["verification"]["l3_harness_dir"]
    b_build = broken_dir / "build"
    b_build.mkdir(exist_ok=True)
    for name in ("l3_range_test.c", "freertos_stubs.h"):
        shutil.copy2(harness / name, b_build / name)
    shutil.copy2(broken_c, b_build / "range_check_under_test.c")
    exe = b_build / ("l3_range_test.exe" if sys.platform.startswith("win") else "l3_range_test")
    gcc = shutil.which("gcc") or shutil.which("gcc.exe")
    broken_result: dict[str, Any]
    if gcc:
        cpc = run_cmd(
            [
                gcc,
                "-std=c11",
                "-Wall",
                "-Wextra",
                "-Werror",
                "-O0",
                "-g",
                "-I.",
                "l3_range_test.c",
                "range_check_under_test.c",
                "-o",
                exe.name,
            ],
            cwd=b_build,
        )
        if cpc.returncode == 0:
            import os

            env = os.environ.copy()
            blog = broken_dir / "l3_range_test.log"
            env["M1_L3_LOG"] = str(blog.resolve())
            run_cmd([str(exe)], cwd=b_build, env=env)
            blog_text = blog.read_text(encoding="utf-8", errors="replace") if blog.exists() else ""
            sys.path.insert(0, str(MM / "scripts"))
            from run_l3_against_queueset import parse_log  # noqa: E402

            parsed = parse_log(blog_text)
            broken_result = {
                "compiled": True,
                "oracle_neg": parsed.get("oracle_neg"),
                "P2_verdict": parsed.get("P2", {}).get("verdict"),
                "detects_always_pass_bug": parsed.get("oracle_neg") == "FAIL"
                or parsed.get("P2", {}).get("verdict") == "FAIL",
            }
        else:
            broken_result = {"compiled": False, "stderr": (cpc.stderr or "")[-500:]}
    else:
        broken_result = {"compiled": False, "error": "gcc missing"}

    wt_info: dict[str, Any] = {"sampled": False}
    if sample_worktree:
        wt_root = ROOT / cfg["experiment"]["worktree_root"]
        try:
            wt = create_detached_worktree(baseline, wt_root, "d01")
            q = wt / cfg["experiment"]["target_file"]
            wt_info = {
                "sampled": True,
                "path": str(wt),
                "queueset_exists": q.exists(),
                "queueset_sha256": sha256_file(q),
            }
            remove_worktree(wt)
            wt_info["removed"] = True
        except Exception as exc:  # noqa: BLE001
            wt_info = {"sampled": True, "error": str(exc)}

    report = {
        "dry_run": True,
        "campaign_dir": str(campaign_dir),
        "planned_runs": len(specs),
        "expected_27": len(specs) == 27,
        "baseline": baseline,
        "prompt_hashes": prompt_hashes,
        "l3_baseline_extract": {
            "ok": l3_ok.get("ok"),
            "L3_P1": l3_ok.get("L3_P1"),
            "L3_P2": l3_ok.get("L3_P2"),
            "oracle_pos": l3_ok.get("oracle_pos"),
            "oracle_neg": l3_ok.get("oracle_neg"),
            "tests_agent_modified_implementation": l3_ok.get(
                "tests_agent_modified_implementation"
            ),
            "used_frozen_reference_extract": l3_ok.get("used_frozen_reference_extract"),
            "queueset_sha256": l3_ok.get("queueset_sha256"),
        },
        "l3_broken_always_pass_control": broken_result,
        "worktree_sample": wt_info,
        "models_invoked": False,
    }
    (campaign_dir / "DRY-RUN-REPORT.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    md = [
        "# M1 multimodel dry-run",
        "",
        f"- Planned runs: **{len(specs)}** (expect 27: {len(specs) == 27})",
        f"- Baseline: `{baseline}`",
        f"- L3 on baseline QueueSet extract: P1={l3_ok.get('L3_P1')} P2={l3_ok.get('L3_P2')} "
        f"oracle_pos={l3_ok.get('oracle_pos')} oracle_neg={l3_ok.get('oracle_neg')}",
        f"- Tests agent-modified path plumbing: "
        f"`tests_agent_modified_implementation={l3_ok.get('tests_agent_modified_implementation')}`",
        f"- Broken always-pass control detected: "
        f"**{broken_result.get('detects_always_pass_bug')}**",
        f"- AI models invoked: **false**",
        "",
    ]
    (campaign_dir / "DRY-RUN-REPORT.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", type=Path, default=MM / "config.yaml")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--sample-worktree", action="store_true")
    ap.add_argument(
        "--live",
        action="store_true",
        help="Execute live agent runs using config.yaml filters (empty filters => full 27)",
    )
    ap.add_argument(
        "--campaign-dir",
        type=Path,
        default=None,
        help="Reuse/create this campaign directory (preserves existing runs/)",
    )
    ap.add_argument(
        "--skip-existing",
        action="store_true",
        default=True,
        help="Skip runs that already have result.json (default: true)",
    )
    ap.add_argument(
        "--no-skip-existing",
        action="store_true",
        help="Re-run even when result.json exists",
    )
    ap.add_argument("--aggregate-only", action="store_true")
    args = ap.parse_args()
    cfg = load_config(args.config)
    cfg.setdefault("filters", {})
    cfg.setdefault("runtime", {})
    # Campaign mode: avoid retaining 27 worktrees on disk
    if args.live:
        cfg["runtime"]["keep_worktrees"] = False

    if args.dry_run or cfg.get("runtime", {}).get("dry_run"):
        report = dry_run(cfg, sample_worktree=args.sample_worktree)
        print(json.dumps(report, indent=2))
        ok = (
            report.get("expected_27")
            and report.get("l3_baseline_extract", {}).get("ok")
            and report.get("l3_broken_always_pass_control", {}).get("detects_always_pass_bug")
        )
        return 0 if ok else 1

    if args.aggregate_only:
        if not args.campaign_dir:
            print("--aggregate-only requires --campaign-dir", file=sys.stderr)
            return 2
        campaign_dir = args.campaign_dir
        if not campaign_dir.is_absolute():
            campaign_dir = ROOT / campaign_dir
        # Aggregate against full matrix expectation from config with empty filters
        full_cfg = load_config(args.config)
        full_cfg["filters"] = {"models": [], "tasks": [], "reps": []}
        expected = [run_dir_name(s) for s in build_matrix(full_cfg)]
        summary = aggregate(campaign_dir, expected, cli_version=agent_cli_version())
        write_report(campaign_dir, full_cfg, summary)
        print(json.dumps({"campaign_dir": str(campaign_dir), "complete": summary["complete"], "missing": summary["missing_run_ids"]}, indent=2))
        return 0 if summary["complete"] else 1

    if not args.live:
        print(
            "Refusing live execution. Pass --dry-run, --live, or --aggregate-only.",
            file=sys.stderr,
        )
        return 2

    campaign_dir = args.campaign_dir
    if campaign_dir is not None and not campaign_dir.is_absolute():
        campaign_dir = ROOT / campaign_dir
    skip = False if args.no_skip_existing else True

    def _progress(msg: str) -> None:
        print(msg, flush=True)

    summary = run_live(
        cfg,
        campaign_dir=campaign_dir,
        skip_existing=skip,
        progress_cb=_progress,
    )
    # Compact stdout summary of this invocation
    out = {
        "campaign_dir": summary.get("campaign_dir"),
        "total_records": summary.get("total_records"),
        "expected": summary.get("expected"),
        "complete_for_filter": summary.get("complete"),
        "missing_run_ids": summary.get("missing_run_ids"),
        "A": summary.get("final_safety_preservation"),
        "B": summary.get("hidden_safety_regressions"),
        "C": summary.get("intermediate_safety_conflicts"),
        "D": summary.get("successful_recoveries"),
        "runs": [
            {
                "run_id": r.get("run_id"),
                "L1": r.get("L1_build"),
                "L2": r.get("L2_task"),
                "P1": r.get("L3_P1"),
                "P2": r.get("L3_P2"),
                "A": (r.get("evaluation") or {}).get("A_final_safety_preservation"),
            }
            for r in (summary.get("runs") or [])
        ],
    }
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

