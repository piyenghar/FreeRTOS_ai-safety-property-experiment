@m1_common_constraints.md

# Task M1-R4 — Unify deviation check (behaviour-preserving refactor)

Refactor `prvCheckReceivedValueWithinExpectedRange()` in `QueueSet.c` so the
duplicated mirrored branches (received > expected vs else) become a single
absolute-deviation decision, without changing P1/P2 behaviour.

## Required outcomes

1. Introduce a file-local helper that computes the absolute deviation between
   `ulReceived` and `ulExpectedReceived` (the same unsigned distance used by
   today’s checks).
2. Rewrite the range-check function to use that helper and a **single**
   assert/reject decision against `queuesetALLOWABLE_RX_DEVIATION`.
3. Preserve behaviour:
   - `|rx − expected| <= 3` → return `pdPASS`, no `configASSERT` fire
   - `|rx − expected| > 3` → `configASSERT` fires and the call rejects (`pdFALSE`)
4. Keep `#define queuesetALLOWABLE_RX_DEVIATION 3` (do not change its value).
5. Do not add unrelated features.
6. Include the exact token **`M1_R4_EXTRACT`** in a comment near the helper or
   refactored function (traceability only; L2 also checks structure).

## Verification you must run

1. **L1:** `make` succeeds for the MPS2 QEMU GCC demo.
2. **L2:** Advanced L2 for M1-R4 (structural): helper called from the check;
   single allowable-deviation assert in the check body; token present;
   QEMU check-task `PASS` without `ASSERT!` (timeout 124 OK).
3. **L3:** Mentally re-check P1/P2 unchanged (host L3 will re-run independently).

## Final summary

Report: refactor intent, helper name, files changed, build/QEMU evidence, and
any real range-check failures plus corrections.
