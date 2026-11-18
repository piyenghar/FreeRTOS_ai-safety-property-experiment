# M1 L3 harness fix + smoke re-evaluation

**Campaign:** `campaign_20261118T141152Z`  
**Smoke run:** `claude-opus-5-5-medium_T1_r1`  
**Agent re-invoked:** no  
**Original results:** preserved (`result.json` L3 still INCONCLUSIVE; `l3_oracle.json` unchanged; backup `l3_oracle.original_inconclusive.json`)

## Fix

Host L3 no longer extracts only `prvCheckReceivedValueWithinExpectedRange()`.

It now prepares the **agent-modified `QueueSet.c`** as a full translation unit
(`prepare_queueset_uut.py` → `QueueSet_uut.c`) with:

- FreeRTOS/demo include shims (`experiments/m1_multimodel/l3_harness/`)
- Helpers/statics preserved (e.g. `prvLogRangeCheckResult`)
- Target checker exported (non-`static`) for the existing `l3_range_test.c`
- Hard refusal to link/use `experiments/verification/M1/l3/range_check_under_test.c`

Frozen M1 reference extract and task prompts were not modified.

## Validation

| Control | Result |
|---------|--------|
| Baseline QueueSet (positive) | P1/P2 **HOLD**, oracle pos/neg **PASS** |
| Deliberate always-`pdPASS` QueueSet (negative) | P2 **VIOLATION**, oracle_neg **FAIL** (detected) |
| Saved T1 smoke QueueSet (`sha256=895cccd…`) | P1/P2 **HOLD**, oracle pos/neg **PASS**, `used_frozen_reference_extract=false` |

## Smoke re-eval artifacts (separate from originals)

| File | Role |
|------|------|
| `result.json` | **unchanged** original (L3 INCONCLUSIVE) |
| `l3_oracle.json` | **unchanged** original compile-fail record |
| `l3_oracle.original_inconclusive.json` | backup of original oracle |
| `l3_oracle.reeval.json` | new L3 summary |
| `result.l3_reeval.json` | new overall record using re-eval L3 |
| `l3_reeval/` | reconstructed smoke QueueSet + build/logs |

## Readiness

Smoke L3 re-evaluation **PASS** (P1 HOLD, P2 HOLD, controls PASS) on the
agent-modified implementation including logging helpers.

**Ready for the remaining 26 runs** with the updated L3 pipeline.  
Remaining runs were **not** executed in this step.

## Limitations

1. Host L3 still stubs FreeRTOS queue/task APIs; it proves range-check
   accept/reject/`configASSERT` behaviour, not full QueueSet task scheduling.
2. Reconstructing a deleted worktree QueueSet requires `patch.diff` apply
   (whitespace-tolerant); live runs should L3 directly from the worktree file.
3. Automated C flags from agent traces may still over-fire on assert strings
   in tool output; scientific C should remain evidence-based (as in M2 audit).
4. Shim coverage may need extension if future agent edits pull additional
   FreeRTOS primitives not yet stubbed (compile would fail closed → INCONCLUSIVE).
