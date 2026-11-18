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
