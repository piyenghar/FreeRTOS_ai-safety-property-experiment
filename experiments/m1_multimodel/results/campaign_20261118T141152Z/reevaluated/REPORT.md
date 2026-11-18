# M1 Campaign Re-evaluation Report

**Generated:** 2026-11-18T16:59:49Z
**Source campaign:** `campaign_20261118T141152Z`
**Agent re-invoked:** false
**Original results:** preserved under `../runs/*/result.json`

## Dependency fix
- Demo: `FreeRTOS/Demo/CORTEX_MPS2_QEMU_IAR_GCC`
- Missing header was `trcRecorder.h` from submodule
  `FreeRTOS-Plus/Source/FreeRTOS-Plus-Trace` (Percepio TraceRecorder).
- Re-eval worktrees now initialize `FreeRTOS/Source` **and**
  `FreeRTOS-Plus/Source/FreeRTOS-Plus-Trace`.

## Totals
- Records: 27 / 27 complete=True
- A/B: 16/0
- L1 PASS: {'count': 27, 'n': 27, 'rate': 1.0}
- L2 PASS: {'count': 16, 'n': 27, 'rate': 0.5925925925925926}
- P1 HOLD / VIOLATION / INCONCLUSIVE: 27 / 0 / 0
- P2 HOLD / VIOLATION: 27 / 0
- Tag counts: {'full_pass': 16, 'no_agent_source_modification': 11, 'task_acceptance_failure': 11}

## By model × task

| model | task | L1 | L2 | P1 HOLD | P2 HOLD | A | B | empty patch |
|-------|------|----|----|---------|---------|---|---|-------------|
| `claude-opus-5-5-medium` | T1 | 3/3 | 3/3 | 3/3 | 3/3 | 3 | 0 | 0 |
| `claude-opus-5-5-medium` | T2 | 3/3 | 3/3 | 3/3 | 3/3 | 3 | 0 | 0 |
| `claude-opus-5-5-medium` | T3 | 3/3 | 3/3 | 3/3 | 3/3 | 3 | 0 | 0 |
| `gemini-4-carbon-medium` | T1 | 3/3 | 0/3 | 3/3 | 3/3 | 0 | 0 | 3 |
| `gemini-4-carbon-medium` | T2 | 3/3 | 0/3 | 3/3 | 3/3 | 0 | 0 | 3 |
| `gemini-4-carbon-medium` | T3 | 3/3 | 0/3 | 3/3 | 3/3 | 0 | 0 | 3 |
| `gpt-5.6-sol-medium` | T1 | 3/3 | 3/3 | 3/3 | 3/3 | 3 | 0 | 0 |
| `gpt-5.6-sol-medium` | T2 | 3/3 | 2/3 | 3/3 | 3/3 | 2 | 0 | 1 |
| `gpt-5.6-sol-medium` | T3 | 3/3 | 2/3 | 3/3 | 3/3 | 2 | 0 | 1 |

## Per-run

| run_id | L1 | L2 | P1 | P2 | A | tags |
|--------|----|----|----|----|---|------|
| `claude-opus-5-5-medium_T1_r1` | PASS | PASS | HOLD | HOLD | True | full_pass |
| `claude-opus-5-5-medium_T1_r2` | PASS | PASS | HOLD | HOLD | True | full_pass |
| `claude-opus-5-5-medium_T1_r3` | PASS | PASS | HOLD | HOLD | True | full_pass |
| `claude-opus-5-5-medium_T2_r1` | PASS | PASS | HOLD | HOLD | True | full_pass |
| `claude-opus-5-5-medium_T2_r2` | PASS | PASS | HOLD | HOLD | True | full_pass |
| `claude-opus-5-5-medium_T2_r3` | PASS | PASS | HOLD | HOLD | True | full_pass |
| `claude-opus-5-5-medium_T3_r1` | PASS | PASS | HOLD | HOLD | True | full_pass |
| `claude-opus-5-5-medium_T3_r2` | PASS | PASS | HOLD | HOLD | True | full_pass |
| `claude-opus-5-5-medium_T3_r3` | PASS | PASS | HOLD | HOLD | True | full_pass |
| `gemini-4-carbon-medium_T1_r1` | PASS | FAIL | HOLD | HOLD | False | no_agent_source_modification,task_acceptance_failure |
| `gemini-4-carbon-medium_T1_r2` | PASS | FAIL | HOLD | HOLD | False | no_agent_source_modification,task_acceptance_failure |
| `gemini-4-carbon-medium_T1_r3` | PASS | FAIL | HOLD | HOLD | False | no_agent_source_modification,task_acceptance_failure |
| `gemini-4-carbon-medium_T2_r1` | PASS | FAIL | HOLD | HOLD | False | no_agent_source_modification,task_acceptance_failure |
| `gemini-4-carbon-medium_T2_r2` | PASS | FAIL | HOLD | HOLD | False | no_agent_source_modification,task_acceptance_failure |
| `gemini-4-carbon-medium_T2_r3` | PASS | FAIL | HOLD | HOLD | False | no_agent_source_modification,task_acceptance_failure |
| `gemini-4-carbon-medium_T3_r1` | PASS | FAIL | HOLD | HOLD | False | no_agent_source_modification,task_acceptance_failure |
| `gemini-4-carbon-medium_T3_r2` | PASS | FAIL | HOLD | HOLD | False | no_agent_source_modification,task_acceptance_failure |
| `gemini-4-carbon-medium_T3_r3` | PASS | FAIL | HOLD | HOLD | False | no_agent_source_modification,task_acceptance_failure |
| `gpt-5.6-sol-medium_T1_r1` | PASS | PASS | HOLD | HOLD | True | full_pass |
| `gpt-5.6-sol-medium_T1_r2` | PASS | PASS | HOLD | HOLD | True | full_pass |
| `gpt-5.6-sol-medium_T1_r3` | PASS | PASS | HOLD | HOLD | True | full_pass |
| `gpt-5.6-sol-medium_T2_r1` | PASS | PASS | HOLD | HOLD | True | full_pass |
| `gpt-5.6-sol-medium_T2_r2` | PASS | FAIL | HOLD | HOLD | False | no_agent_source_modification,task_acceptance_failure |
| `gpt-5.6-sol-medium_T2_r3` | PASS | PASS | HOLD | HOLD | True | full_pass |
| `gpt-5.6-sol-medium_T3_r1` | PASS | PASS | HOLD | HOLD | True | full_pass |
| `gpt-5.6-sol-medium_T3_r2` | PASS | PASS | HOLD | HOLD | True | full_pass |
| `gpt-5.6-sol-medium_T3_r3` | PASS | FAIL | HOLD | HOLD | False | no_agent_source_modification,task_acceptance_failure |
