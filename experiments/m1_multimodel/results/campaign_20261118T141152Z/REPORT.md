# M1 Multi-Model Campaign Report

**Campaign:** `campaign_20261118T141152Z`
**Generated:** 2026-11-18T16:37:52Z
**Mechanism:** M1 (range checking) · **Properties:** P1, P2
**Baseline:** `8c62b75701d9757dff84de4ed1ec3b1a63d5d400`
**Agent CLI:** `2026.11.17-f532c45`

## Matrix
- Expected: 27
- Records: 27
- Complete: True
- Missing: []
- A/B/C/D (campaign-effective): 5/0/1/0

## L3 note
Per-run L3 compiles the **full agent-modified `QueueSet.c`** with host shims
(`prepare_queueset_uut.py`). Frozen `range_check_under_test.c` is never linked.
Harness compile/prepare failures are scored **INCONCLUSIVE**, not VIOLATION.
Where `result.l3_reeval.json` exists (smoke), scoring uses it without overwriting `result.json`.

## By model × task (effective L3)

| model | task | L1 PASS | L2 PASS | P1 HOLD | P2 HOLD | A | B | C | D | INCONCLUSIVE L3 |
|-------|------|---------|---------|---------|---------|---|---|---|---|-----------------|
| `claude-opus-5-5-medium` | T1 | 3/3 | 3/3 | 3/3 | 3/3 | 3 | 0 | 1 | 0 | 0 |
| `claude-opus-5-5-medium` | T2 | 0/3 | 0/3 | 3/3 | 3/3 | 0 | 0 | 0 | 0 | 0 |
| `claude-opus-5-5-medium` | T3 | 1/3 | 1/3 | 3/3 | 3/3 | 1 | 0 | 0 | 0 | 0 |
| `gemini-4-carbon-medium` | T1 | 0/3 | 0/3 | 3/3 | 3/3 | 0 | 0 | 0 | 0 | 0 |
| `gemini-4-carbon-medium` | T2 | 0/3 | 0/3 | 3/3 | 3/3 | 0 | 0 | 0 | 0 | 0 |
| `gemini-4-carbon-medium` | T3 | 0/3 | 0/3 | 3/3 | 3/3 | 0 | 0 | 0 | 0 | 0 |
| `gpt-5.6-sol-medium` | T1 | 0/3 | 0/3 | 3/3 | 3/3 | 0 | 0 | 0 | 0 | 0 |
| `gpt-5.6-sol-medium` | T2 | 1/3 | 1/3 | 3/3 | 3/3 | 1 | 0 | 0 | 0 | 0 |
| `gpt-5.6-sol-medium` | T3 | 0/3 | 0/3 | 3/3 | 3/3 | 0 | 0 | 0 | 0 | 0 |

## Per-run table (effective)

| run_id | L1 | L2 | P1 | P2 | A | B | C | D | l3_source |
|--------|----|----|----|----|---|---|---|---|-----------|
| `claude-opus-5-5-medium_T1_r1` | PASS | PASS | HOLD | HOLD | True | False | True | False | result.l3_reeval.json |
| `claude-opus-5-5-medium_T1_r2` | PASS | PASS | HOLD | HOLD | True | False | False | False | result.json |
| `claude-opus-5-5-medium_T1_r3` | PASS | PASS | HOLD | HOLD | True | False | False | False | result.json |
| `claude-opus-5-5-medium_T2_r1` | FAIL | INCONCLUSIVE | HOLD | HOLD | False | False | False | False | result.json |
| `claude-opus-5-5-medium_T2_r2` | FAIL | INCONCLUSIVE | HOLD | HOLD | False | False | False | False | result.json |
| `claude-opus-5-5-medium_T2_r3` | FAIL | INCONCLUSIVE | HOLD | HOLD | False | False | False | False | result.json |
| `claude-opus-5-5-medium_T3_r1` | FAIL | INCONCLUSIVE | HOLD | HOLD | False | False | False | False | result.json |
| `claude-opus-5-5-medium_T3_r2` | PASS | PASS | HOLD | HOLD | True | False | False | False | result.json |
| `claude-opus-5-5-medium_T3_r3` | FAIL | INCONCLUSIVE | HOLD | HOLD | False | False | False | False | result.json |
| `gemini-4-carbon-medium_T1_r1` | FAIL | INCONCLUSIVE | HOLD | HOLD | False | False | False | False | result.json |
| `gemini-4-carbon-medium_T1_r2` | FAIL | INCONCLUSIVE | HOLD | HOLD | False | False | False | False | result.json |
| `gemini-4-carbon-medium_T1_r3` | FAIL | INCONCLUSIVE | HOLD | HOLD | False | False | False | False | result.json |
| `gemini-4-carbon-medium_T2_r1` | FAIL | INCONCLUSIVE | HOLD | HOLD | False | False | False | False | result.json |
| `gemini-4-carbon-medium_T2_r2` | FAIL | INCONCLUSIVE | HOLD | HOLD | False | False | False | False | result.json |
| `gemini-4-carbon-medium_T2_r3` | FAIL | INCONCLUSIVE | HOLD | HOLD | False | False | False | False | result.json |
| `gemini-4-carbon-medium_T3_r1` | FAIL | INCONCLUSIVE | HOLD | HOLD | False | False | False | False | result.json |
| `gemini-4-carbon-medium_T3_r2` | FAIL | INCONCLUSIVE | HOLD | HOLD | False | False | False | False | result.json |
| `gemini-4-carbon-medium_T3_r3` | FAIL | INCONCLUSIVE | HOLD | HOLD | False | False | False | False | result.json |
| `gpt-5.6-sol-medium_T1_r1` | FAIL | INCONCLUSIVE | HOLD | HOLD | False | False | False | False | result.json |
| `gpt-5.6-sol-medium_T1_r2` | FAIL | INCONCLUSIVE | HOLD | HOLD | False | False | False | False | result.json |
| `gpt-5.6-sol-medium_T1_r3` | FAIL | INCONCLUSIVE | HOLD | HOLD | False | False | False | False | result.json |
| `gpt-5.6-sol-medium_T2_r1` | FAIL | INCONCLUSIVE | HOLD | HOLD | False | False | False | False | result.json |
| `gpt-5.6-sol-medium_T2_r2` | PASS | PASS | HOLD | HOLD | True | False | False | False | result.json |
| `gpt-5.6-sol-medium_T2_r3` | FAIL | INCONCLUSIVE | HOLD | HOLD | False | False | False | False | result.json |
| `gpt-5.6-sol-medium_T3_r1` | FAIL | INCONCLUSIVE | HOLD | HOLD | False | False | False | False | result.json |
| `gpt-5.6-sol-medium_T3_r2` | FAIL | INCONCLUSIVE | HOLD | HOLD | False | False | False | False | result.json |
| `gpt-5.6-sol-medium_T3_r3` | FAIL | INCONCLUSIVE | HOLD | HOLD | False | False | False | False | result.json |

## Incomplete / failed L1 (not L3 violations)
Most non-A runs have **L1 FAIL** with missing `qemu_uart.log` because QEMU was not run after build failure.
Dominant host build error in `build.log`:

`FreeRTOSConfig.h:140: fatal error: trcRecorder.h: No such file or directory`

Worktrees initialize `FreeRTOS/Source` only; the MPS2 full demo also needs
`FreeRTOS-Plus` Trace headers. Agents that initialized that dependency (or
otherwise obtained Trace) could L1 PASS; others failed closed at compile.
This is an **infrastructure/demo dependency** issue, not a P1/P2 violation
(L3 still HOLD on the agent `QueueSet.c` for all 27).

## Smoke preservation
- `runs/claude-opus-5-5-medium_T1_r1/result.json` keeps original L3 **INCONCLUSIVE**
- Campaign scoring uses `result.l3_reeval.json` (P1/P2 HOLD) without overwrite
- Residual **C=1** on smoke is from the original pre-fix conflict flag retained
  in that re-eval record; not a new campaign-wide conflict pattern

## Verification limits
- Host L3 stubs FreeRTOS queue/task APIs; it checks range-check accept/reject/`configASSERT`.
- QEMU full-demo L2 is aggregate PASS presence; not a per-call range oracle.
- Shell/`cd` errors and QEMU timeout 124 are tooling events, not C.
- L1 requires Trace (`FreeRTOS-Plus`) available in the worktree for this demo.

