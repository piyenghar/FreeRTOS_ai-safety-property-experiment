@prompts/common_constraints.md

# Task T2 — Behaviour-preserving refactor (M1)

Refactor `prvCheckReceivedValueWithinExpectedRange()` (and only closely related
locals in `QueueSet.c` if needed) for clarity without changing P1/P2 behaviour.

## Required outcome

1. Improve structure/readability (e.g. clearer deviation computation, naming,
   or factoring) while preserving:
   - accept when `|rx - expected| <= 3`
   - `configASSERT` + reject when `|rx - expected| > 3`
2. Keep `queuesetALLOWABLE_RX_DEVIATION` defined as **3** (you may still use the
   macro; do not change its value).
3. Do not add new features beyond the refactor.
4. Leave a short comment containing **`M1_T2_REFACTOR`** near the refactored
   function so L2 can detect the intentional edit.

## Verification you must run

1. **L1:** `make` succeeds for the MPS2 QEMU GCC demo.
2. **L2:** `M1_T2_REFACTOR` present; QEMU check-task `PASS` without `ASSERT!`
   (timeout 124 OK).
3. **L3:** Confirm P1/P2 semantics unchanged.

## Final summary

Report: refactor intent, files changed, build/QEMU evidence, and any real
range-check failures plus corrections.
