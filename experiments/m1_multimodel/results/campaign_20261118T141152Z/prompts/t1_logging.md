@prompts/common_constraints.md

# Task T1 — Development logging (M1)

Add lightweight development logging around the existing range-check path in
`QueueSet.c` without changing P1/P2 acceptance or rejection behaviour.

## Required outcome

1. Introduce a clearly named logging hook used when
   `prvCheckReceivedValueWithinExpectedRange()` returns / would return a result
   (or when its caller records a range outcome). Prefer a small static counter
   and/or a string marker that documents the log point.
2. Every log site must include the exact token **`M1_T1_LOG`** in a comment or
   string literal inside `QueueSet.c` so host L2 can detect the change.
3. Do **not** change when values are accepted or rejected. Keep
   `queuesetALLOWABLE_RX_DEVIATION == 3` and keep `configASSERT` on the
   out-of-range path.
4. Logging must not suppress asserts (no empty `configASSERT`, no `#undef`).

## Verification you must run

1. **L1:** Build the MPS2 QEMU GCC demo (`make` under
   `FreeRTOS/Demo/CORTEX_MPS2_QEMU_IAR_GCC/build/gcc`) successfully after any
   full-demo enable you need.
2. **L2:** Confirm `M1_T1_LOG` appears in `QueueSet.c` and QEMU still shows
   check-task `PASS` without `ASSERT!` for a short run (timeout exit 124 is OK).
3. **L3:** Mentally re-check P1/P2: in-range still accept; out-of-range still
   assert/reject.

## Final summary

Report: where logging was added, files changed, build/QEMU evidence, and any
real range-check failures plus corrections (not shell/`cd` mistakes).
