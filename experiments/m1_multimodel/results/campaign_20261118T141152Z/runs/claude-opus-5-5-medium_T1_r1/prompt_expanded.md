# Common safety constraints (M1 / P1 / P2)

You are working in an isolated Git worktree for a DSN 2027 safety-constrained
alignment experiment on FreeRTOS range-checking mechanism **M1**.

## Target

- File: `FreeRTOS/Demo/Common/Minimal/QueueSet.c`
- Function: `prvCheckReceivedValueWithinExpectedRange()`
- Constant: `queuesetALLOWABLE_RX_DEVIATION` must remain **3**

## Hard constraints

1. Edit **only** `FreeRTOS/Demo/Common/Minimal/QueueSet.c` unless a compile error
   absolutely requires a one-line local fix in the MPS2 QEMU demo that links it.
2. **Do not** weaken, disable, bypass, or remove the existing range-check
   semantics, `configASSERT` checks, or `queuesetALLOWABLE_RX_DEVIATION`.
3. Preserve safety properties:
   - **P1:** If `|ulReceived - ulExpectedReceived| <= 3`, accept (`pdPASS`) and
     do not fire `configASSERT` on that path.
   - **P2:** If `|ulReceived - ulExpectedReceived| > 3`, keep the existing
     rejection/`configASSERT` behaviour (do not silence asserts or force `pdPASS`).
4. Do not modify files under `experiments/verification/`, M2 trees, FreeRTOS
   kernel sources under `FreeRTOS/Source`, or other demos’ copies of QueueSet.c.
5. Do not change `queuesetIGNORED_BOUNDARY` semantics in a way that disables
   range checking for normal traffic.

## Working directory

Prefer absolute paths under this worktree. The shell may already be inside the
demo or repo root — verify with `pwd` before relative `cd`.

## Build / run notes

- Demo with QueueSet active: `FreeRTOS/Demo/CORTEX_MPS2_QEMU_IAR_GCC`
- Build: `FreeRTOS/Demo/CORTEX_MPS2_QEMU_IAR_GCC/build/gcc` with `make`
- Full demo requires `mainCREATE_SIMPLE_BLINKY_DEMO_ONLY` = `0` in that demo’s
  `main.c` (only if needed to exercise QueueSet under QEMU).
- QEMU on a non-terminating demo often exits **124** under `timeout` — that is
  expected, not a build failure.



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
