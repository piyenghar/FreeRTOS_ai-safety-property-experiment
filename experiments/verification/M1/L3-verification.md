# M1 L3 — independent verification of QueueSet range checking

**Target:** `prvCheckReceivedValueWithinExpectedRange()`  
**Source (reference only):** `FreeRTOS/Demo/Common/Minimal/QueueSet.c`  
**Harness:** `experiments/verification/M1/l3/` (QueueSet.c **not** modified)

## Properties

| ID | Statement | Result |
|----|-----------|--------|
| **P1** | If \|ulReceived − ulExpected\| ≤ 3, return `pdPASS` and `configASSERT` does not fire | **PASS 14/14** |
| **P2** | If \|ulReceived − ulExpected\| > 3, `configASSERT` fires (when enabled); scored as expected rejection, not harness failure | **PASS 8/8** |

Oracle controls: **pos PASS**, **neg PASS**. Overall: **22/22 PASS**.

## Coverage

- Within deviation: ±0, ±1, ±2
- Exact boundaries: +3, −3 (P1)
- Outside: +4, −4, +5, −10 (P2)
- Unsigned edges: 0 / UINT32_MAX neighbourhood; large unsigned deviation (UINT32_MAX vs 0)
- ISR-split neighbourhood: 0xFFFF ± 0/3/4

## configASSERT handling

The production function `configASSERT`s the same predicate it returns on. With asserts enabled, out-of-range paths never return normally. The L3 harness maps `configASSERT` → `longjmp` and scores an **expected** assert as **P2 PASS**. An unexpected assert (on an in-range case) is a failure.

## Oracle sensitivity

| Control | Input | Expected | Observed |
|---------|-------|----------|----------|
| Positive | rx=1001, exp=1000 (dev=1) | accept, no assert | PASS |
| Negative | rx=1004, exp=1000 (dev=4) | assert (reject) | PASS |

Both controls must pass for the run to be accepted. Agreement with the host Python oracle (`scripts/range_boundary_oracle.py`, `ALLOWABLE=3`) on ±0..±5 at mid=1000.

## Build / run commands

Host MinGW gcc (no FreeRTOS toolchain required for L3):

```powershell
cd experiments\verification\M1\l3
mkdir build -Force
gcc -std=c11 -Wall -Wextra -Werror -O0 -g -I. `
  l3_range_test.c range_check_under_test.c `
  -o build\l3_range_test.exe
$env:M1_L3_LOG = "..\results\l3_range_test.log"
.\build\l3_range_test.exe
```

Or:

```powershell
.\experiments\verification\M1\scripts\run_m1_l3.ps1
```

On Linux/WSL with `make`:

```bash
./experiments/verification/M1/scripts/run_m1_l3.sh
```

## Evidence

| Artifact | Path |
|----------|------|
| Test log | `results/l3_range_test.log` |
| JSON summary | `results/l3_summary.json` |
| Host binary | `l3/build/l3_range_test.exe` |
| Baseline QEMU (prior) | `results/baseline_full_demo.uart.log` |
| Python boundary oracle | `results/range_boundary_oracle.json` |

## Limitations

1. **Logic extract, not linked QueueSet.o** — `range_check_under_test.c` mirrors the static function; QueueSet.c is not compiled into the host binary. Drift risk if QueueSet.c changes.
2. **No on-target P2 injection** — MPS2 full-demo baseline exercises in-range paths only; out-of-range `configASSERT` is proven on the host harness, not by fault-injecting QEMU.
3. **Assert stub ≠ board handler** — production `configASSERT` typically halts; L3 uses `longjmp` so many cases can run in one process.
4. **Caller skip zones** — `queuesetIGNORED_BOUNDARY` means callers may not invoke the checker near wrap/ISR split; L3 tests the checker itself, including ISR-split neighbourhood values.
5. **Unsigned arithmetic** — same `uint32_t` subtraction as C; no signed-wrap modelling beyond that.

## Non-goals (this step)

- No T1/T2/T3 pilots
- No edits to QueueSet.c, M2 trees, or submodules
- No commit/push
