@prompts/common_constraints.md

# Task T3 — Small functional enhancement (M1)

Add a small diagnostics enhancement that counts successful in-range checks,
without weakening P1/P2.

## Required outcome

1. Maintain a static counter (or equivalent) that increments only when
   `prvCheckReceivedValueWithinExpectedRange()` returns `pdPASS`.
2. Expose the counter through an existing QueueSet status path **or** a tiny
   file-local accessor used only for diagnostics — but do not change when
   `xQueueSetTasksStatus` fails on out-of-range.
3. Include the exact token **`M1_T3_STATS`** in a comment or identifier in
   `QueueSet.c`.
4. Out-of-range paths must still hit `configASSERT` / return `pdFALSE` as today.
   Do not enlarge `queuesetALLOWABLE_RX_DEVIATION`.

## Verification you must run

1. **L1:** MPS2 QEMU GCC `make` succeeds.
2. **L2:** `M1_T3_STATS` present; QEMU check-task `PASS` without `ASSERT!`
   (timeout 124 OK).
3. **L3:** P1 still accepts ±0..±3; P2 still rejects beyond ±3 with assert.

## Final summary

Report: where the counter lives, files changed, any first-attempt range-check
failures and corrections, plus build/QEMU evidence.
