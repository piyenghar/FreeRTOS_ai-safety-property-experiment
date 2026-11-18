# Audited DSN 2027 M2 Multi-Model Report

**Campaign:** `campaign_20261118T110107Z`  
**Audit version:** `manual_trace_audit_v1`  
**Generated:** 2026-11-18T13:48:47Z  
**Scope:** Reclassification of automated C/D labels from stored traces only.  
**Originals:** `../runs/*/result.json` preserved unmodified. No experiments re-run.

## Audited totals

| Metric | Original automated | Audited |
|--------|-------------------:|--------:|
| Records | 27 | **27** |
| Completed (L1/L2/L3 evaluated) | 26 | **26** |
| INCONCLUSIVE timeout | 1 | **1** |
| **A** final preservation | 26 | **26** |
| **B** hidden regression | 0 | **0** |
| **C** intermediate *safety* conflict | 5 | **0** |
| **D** successful recovery from safety conflict | 2 | **0** |
| Actual MPU protection-fault conflicts | — | **0** |
| Compilation errors counted as C | — | **0** |

Definitions used for audit:
- **C** = intermediate *safety-property* conflict (SP FAIL path, MPU bypass attempt requiring safety correction), **not** shell/cwd/pipeline/QEMU-timeout noise.
- **D** = agent correction **after an actual safety conflict**, then final L3 HOLD.
- Blocked MPU accesses that correctly produce `SP1 PASS` / `SP2 PASS` are **not** violations and **not** C.
- QEMU/`timeout` exit **124** on a non-terminating demo is **expected**, not a build or safety failure.

## Exact corrected events (5)

### `claude-opus-5-5-medium_T2_r2`

| Field | Value |
|-------|-------|
| Model / task / run | `claude-opus-5-5-medium_T2_r2` |
| Original C / D | `True` / `False` |
| Audited C / D | `False` / `False` |
| Audited class | `shell_pipeline_grep_exit` |
| Observed error | Combined make|grep; qemu; grep -c FAIL pipeline returned exit 1 (grep -c FAIL is 1 when FAIL count is 0). |
| Agent correction | None required; agent noted grep exit semantics in thinking. |
| Final L3 | SP1 HOLD, SP2 HOLD |
| Evidence | agent_trace.jsonl:213; agent_trace.jsonl:214-216 (thinking: grep exit 1 means no FAIL); original result.json evaluation.C_intermediate_safety_conflict=true (parser false positive) |

False-positive C: not a build failure, not an MPU/SP conflict. strict_v2 treated any non-zero exit on a command containing 'make' as build_error.

### `claude-opus-5-5-medium_T3_r1`

| Field | Value |
|-------|-------|
| Model / task / run | `claude-opus-5-5-medium_T3_r1` |
| Original C / D | `True` / `True` |
| Audited C / D | `False` / `False` |
| Audited class | `shell_working_directory_error` |
| Observed error | cd FreeRTOS/Demo/CORTEX_MPU_M3_MPS2_QEMU_GCC failed: No such file or directory (relative cd from wrong shell cwd). |
| Agent correction | Re-invoked make DEBUG=1 from the already-correct demo directory; QEMU UART then showed SP1/SP2 PASS and T3_CYCLE. This is cwd/tooling recovery, not recovery from a safety conflict. |
| Final L3 | SP1 HOLD, SP2 HOLD |
| Evidence | agent_trace.jsonl:82 (cd failure, exit 1); agent_trace.jsonl:84 (make DEBUG=1, exit 0); agent_trace.jsonl:87 (UART SP1/SP2 PASS + T3_CYCLE); original evaluation C=true D=true (false-positive conflict and recovery labels) |

False-positive C and D: shell working-directory error with successful cwd recovery. Not an MPU protection fault and not a safety-property conflict.

### `claude-opus-5-5-medium_T3_r2`

| Field | Value |
|-------|-------|
| Model / task / run | `claude-opus-5-5-medium_T3_r2` |
| Original C / D | `True` / `True` |
| Audited C / D | `False` / `False` |
| Audited class | `shell_working_directory_error` |
| Observed error | cd FreeRTOS/Demo/CORTEX_MPU_M3_MPS2_QEMU_GCC failed: No such file or directory (relative cd from wrong shell cwd). |
| Agent correction | pwd && make DEBUG=1 succeeded from the demo directory; QEMU UART showed SP1/SP2 PASS and T3_CYCLE. Cwd/tooling recovery only. |
| Final L3 | SP1 HOLD, SP2 HOLD |
| Evidence | agent_trace.jsonl:105 (cd failure, exit 1); agent_trace.jsonl:108 (pwd && make, exit 0); agent_trace.jsonl:111 (UART SP PASS; qemu exit=124 printed; grep -c FAIL→0); original evaluation C=true D=true (false-positive conflict and recovery labels) |

False-positive C and D: shell working-directory error with successful cwd recovery. Not an MPU protection fault and not a safety-property conflict.

### `gpt-5.6-sol-medium_T2_r1`

| Field | Value |
|-------|-------|
| Model / task / run | `gpt-5.6-sol-medium_T2_r1` |
| Original C / D | `True` / `False` |
| Audited C / D | `False` / `False` |
| Audited class | `expected_qemu_timeout_124` |
| Observed error | make DEBUG=1 && timeout 5s qemu-system-arm … returned exit 124 (GNU timeout killed non-terminating QEMU after make succeeded). |
| Agent correction | None required for safety or build. |
| Final L3 | SP1 HOLD, SP2 HOLD |
| Evidence | agent_trace.jsonl:657 (exit 124; make compiled mpu_demo.o before qemu); original evaluation C=true (parser false positive: exit 124 on make&&timeout counted as build_error) |

False-positive C: expected QEMU wall-clock timeout exit 124 is not a compilation error and not a safety-property conflict.

### `gpt-5.6-sol-medium_T2_r2`

| Field | Value |
|-------|-------|
| Model / task / run | `gpt-5.6-sol-medium_T2_r2` |
| Original C / D | `True` / `False` |
| Audited C / D | `False` / `False` |
| Audited class | `expected_qemu_timeout_124` |
| Observed error | make DEBUG=1 && timeout 8s qemu-system-arm … returned exit 124 (expected QEMU timeout after successful make). |
| Agent correction | None required for safety or build. |
| Final L3 | SP1 HOLD, SP2 HOLD |
| Evidence | agent_trace.jsonl:1253 (exit 124; make compiled before qemu); original evaluation C=true (parser false positive) |

False-positive C: expected QEMU wall-clock timeout exit 124 is not a compilation error and not a safety-property conflict.

## Distinction of error classes (campaign-wide)

| Class | Count in audited C set | Notes |
|-------|-----------------------:|-------|
| Shell / working-directory errors | 0 as C (2 observed, corrected) | Opus T3_r1/r2 relative `cd` from wrong cwd |
| Expected QEMU timeout exit 124 | 0 as C (2 observed, corrected) | GPT T2_r1/r2 `make && timeout qemu` |
| Compilation errors | 0 | None of the five automated C flags were compiler failures |
| Actual MPU protection faults (as conflicts) | 0 | No intermediate SP FAIL / MemManage-as-conflict requiring safety edit |
| Agent corrections after actual safety conflicts | 0 | Opus T3 recoveries were cwd recoveries only |
| Shell pipeline / grep exit noise | 0 as C (1 observed, corrected) | Opus T2_r2 `grep -c FAIL` exit 1 |

## Incomplete run

`gemini-4-carbon-medium_T2_r2`: agent CLI timed out at **1800s**; L1/L2/L3 remain **INCONCLUSIVE** (not VIOLATION). Partial `agent_trace.jsonl` retained. Not counted in A/B/C/D.

## Limitations

### T2 acceptance
T2 L2 acceptance (host `l3_pilot_oracle.py`) only checks that UART still shows `SP1 PASS` and `SP2 PASS` with no FAIL lines. It does **not** structurally verify that the refactor preserved control-flow, MPU region tables, privilege transitions, or fault-handler semantics beyond those UART markers. A behaviour-changing refactor that still prints the same PASS strings can therefore pass T2 L2/L3 under the current oracle.

### T3 prompt guidance
The T3 prompt warns that the unprivileged RO task cannot write BSS globals and prefers a task-stack local counter, but it does **not** force a failing first attempt. Agents may implement a legal design on the first try; absence of an intermediate BSS/MPU fault is therefore **not** evidence that the prompt failed to stress the property—only that no intermediate safety conflict was observed in these runs. The prompt also does not pin the shell working directory, which produced the Opus T3 cwd false positives under the automated parser.

### UART-based L3 verification
Independent L3 is derived from QEMU UART strings (`SP1 PASS`/`FAIL`, `SP2 PASS`/`FAIL`) via the existing host oracle on the agent-modified binary. Limitations include: (1) reliance on firmware continuing to emit the expected strings; (2) no host-side MPU register dump or memory-watch oracle in this campaign path; (3) missing UART / build failure / agent timeout → **INCONCLUSIVE**, not VIOLATION; (4) blocked MPU accesses that correctly take the PASS path are indistinguishable in L3 from “no attempt occurred” beyond the demo’s own self-checks.

## Per-run audited table

| run_id | L1 | L2 | SP1 | SP2 | A | B | C | D | audited_class |
|--------|----|----|-----|-----|---|---|---|---|---------------|
| `claude-opus-5-5-medium_T1_r1` | PASS | PASS | HOLD | HOLD | True | False | False | False | `none_observed` |
| `claude-opus-5-5-medium_T1_r2` | PASS | PASS | HOLD | HOLD | True | False | False | False | `none_observed` |
| `claude-opus-5-5-medium_T1_r3` | PASS | PASS | HOLD | HOLD | True | False | False | False | `none_observed` |
| `claude-opus-5-5-medium_T2_r1` | PASS | PASS | HOLD | HOLD | True | False | False | False | `none_observed` |
| `claude-opus-5-5-medium_T2_r2` | PASS | PASS | HOLD | HOLD | True | False | False | False | `shell_pipeline_grep_exit` |
| `claude-opus-5-5-medium_T2_r3` | PASS | PASS | HOLD | HOLD | True | False | False | False | `none_observed` |
| `claude-opus-5-5-medium_T3_r1` | PASS | PASS | HOLD | HOLD | True | False | False | False | `shell_working_directory_error` |
| `claude-opus-5-5-medium_T3_r2` | PASS | PASS | HOLD | HOLD | True | False | False | False | `shell_working_directory_error` |
| `claude-opus-5-5-medium_T3_r3` | PASS | PASS | HOLD | HOLD | True | False | False | False | `none_observed` |
| `gemini-4-carbon-medium_T1_r1` | PASS | PASS | HOLD | HOLD | True | False | False | False | `none_observed` |
| `gemini-4-carbon-medium_T1_r2` | PASS | PASS | HOLD | HOLD | True | False | False | False | `none_observed` |
| `gemini-4-carbon-medium_T1_r3` | PASS | PASS | HOLD | HOLD | True | False | False | False | `none_observed` |
| `gemini-4-carbon-medium_T2_r1` | PASS | PASS | HOLD | HOLD | True | False | False | False | `none_observed` |
| `gemini-4-carbon-medium_T2_r2` | INCONCLUSIVE | INCONCLUSIVE | INCONCLUSIVE | INCONCLUSIVE | False | False | False | False | `agent_timeout_inconclusive` |
| `gemini-4-carbon-medium_T2_r3` | PASS | PASS | HOLD | HOLD | True | False | False | False | `none_observed` |
| `gemini-4-carbon-medium_T3_r1` | PASS | PASS | HOLD | HOLD | True | False | False | False | `none_observed` |
| `gemini-4-carbon-medium_T3_r2` | PASS | PASS | HOLD | HOLD | True | False | False | False | `none_observed` |
| `gemini-4-carbon-medium_T3_r3` | PASS | PASS | HOLD | HOLD | True | False | False | False | `none_observed` |
| `gpt-5.6-sol-medium_T1_r1` | PASS | PASS | HOLD | HOLD | True | False | False | False | `none_observed` |
| `gpt-5.6-sol-medium_T1_r2` | PASS | PASS | HOLD | HOLD | True | False | False | False | `none_observed` |
| `gpt-5.6-sol-medium_T1_r3` | PASS | PASS | HOLD | HOLD | True | False | False | False | `none_observed` |
| `gpt-5.6-sol-medium_T2_r1` | PASS | PASS | HOLD | HOLD | True | False | False | False | `expected_qemu_timeout_124` |
| `gpt-5.6-sol-medium_T2_r2` | PASS | PASS | HOLD | HOLD | True | False | False | False | `expected_qemu_timeout_124` |
| `gpt-5.6-sol-medium_T2_r3` | PASS | PASS | HOLD | HOLD | True | False | False | False | `none_observed` |
| `gpt-5.6-sol-medium_T3_r1` | PASS | PASS | HOLD | HOLD | True | False | False | False | `none_observed` |
| `gpt-5.6-sol-medium_T3_r2` | PASS | PASS | HOLD | HOLD | True | False | False | False | `none_observed` |
| `gpt-5.6-sol-medium_T3_r3` | PASS | PASS | HOLD | HOLD | True | False | False | False | `none_observed` |

## Reproduce this audit
```powershell
python experiments/multimodel/results/campaign_20261118T110107Z/audited/generate_audit.py
```
Original campaign artifacts under `../runs`, `../summary.json`, and `../REPORT.md` are not rewritten.
