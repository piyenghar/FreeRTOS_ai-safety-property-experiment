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
