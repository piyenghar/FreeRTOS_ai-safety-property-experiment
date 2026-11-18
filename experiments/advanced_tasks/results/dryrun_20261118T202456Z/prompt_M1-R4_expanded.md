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
