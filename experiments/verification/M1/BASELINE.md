# M1 Range-Checking Baseline

Date: 2026-11-18  
Subject function: `prvCheckReceivedValueWithinExpectedRange()` in
`FreeRTOS/Demo/Common/Minimal/QueueSet.c`  
**QueueSet.c was not modified.**

## 1. Processor-specific QEMU demo

**Demo:** `FreeRTOS/Demo/CORTEX_MPS2_QEMU_IAR_GCC`  
**Build:** `build/gcc` (`arm-none-eabi-gcc`, Cortex-M3)  
**QEMU:** `-machine mps2-an385 -cpu cortex-m3`  
**Binary:** `build/gcc/output/RTOSDemo.out`

Evidence the range checker is linked (from `results/symbols_queueset.txt`):

```text
0000b5f4 t prvCheckReceivedValueWithinExpectedRange
0000bde8 T vStartQueueSetTasks
0000be3c T xAreQueueSetTasksStillRunning
```

`main_full()` starts QueueSet tasks; the tick hook feeds the set from ISR.
Default `mainCREATE_SIMPLE_BLINKY_DEMO_ONLY` is `1` (blinky); the baseline
runner temporarily selects full demo (`0`) then restores.

## 2. Compilation and execution (actual)

| Step | Result |
|------|--------|
| `make` in `build/gcc` | **PASS** — `text 72666`, `data 274`, `bss 125184` |
| QEMU 20 s | **PASS** — UART check task: |
| | `PASS : 5243 (449)` |
| | `PASS : 10050 (829)` |
| | `PASS : 15062 (1192)` |
| QueueSet failure message | **Not observed** |
| ASSERT lines | **Not observed** |

Logs: `results/baseline_full_demo.uart.log`, `build.log`.

The check task aggregates many demos; a global `PASS` implies
`xAreQueueSetTasksStillRunning() == pdPASS` (QueueSet status still good),
so the in-range acceptance path of the range checker held under load.

## 3. Independently testable properties

### P1 — Correct acceptance within range

**Statement:** If `|ulReceived - ulExpectedReceived| <= queuesetALLOWABLE_RX_DEVIATION` (3),
`prvCheckReceivedValueWithinExpectedRange` returns `pdPASS` and its
`configASSERT` does not fire.

**Baseline evidence:** QEMU full-demo run produced repeated `PASS` with QueueSet
still running (no range-failure assert / QueueSet FAIL message).

### P2 — Correct rejection outside range

**Statement:** If `|ulReceived - ulExpectedReceived| > 3`, the function’s
`configASSERT` fires (asserts enabled in this demo) and it returns `pdFALSE`,
so the caller sets `xQueueSetTasksStatus = pdFAIL`.

**Baseline evidence:** Documented from source + host boundary oracle
(`results/range_boundary_oracle.json`). The stock demo does **not** inject
out-of-range values, so P2 is specified but **not dynamically exercised** in
this baseline run (future M1 pilots / negative controls).

## 4. Boundaries and assertion behaviour

| Constant | Value | Role |
|----------|-------|------|
| `queuesetALLOWABLE_RX_DEVIATION` | **3** | Max allowed `\|received - expected\|` |
| `queuesetIGNORED_BOUNDARY` | **6** (`3*2`) | Near wrap/partition edges, caller skips the checker |
| `queuesetINITIAL_ISR_TX_VALUE` | **0xFFFF** | Task domain below; ISR domain at/above |

Behaviour inside the checker:

1. If `ulReceived > ulExpectedReceived`:  
   `configASSERT((ulReceived - ulExpectedReceived) <= 3)`;  
   return `pdFALSE` if deviation `> 3`, else `pdPASS`.
2. Else:  
   `configASSERT((ulExpectedReceived - ulReceived) <= 3)`;  
   return `pdFALSE` if deviation `> 3`, else `pdPASS`.

On this demo, `configASSERT` maps to `vAssertCalled()` which prints
`ASSERT! Line …` and loops (see `main.c`).

Host oracle self-check: accept for deviation 0–3, reject for 4–5
(`range_boundary_oracle.py` → PASS).

## 5. Limitations

- Full-demo `PASS` is multi-demo aggregate; it confirms QueueSet health but is
  not a dedicated per-call trace of the range function.
- Out-of-range rejection is not triggered by the unmodified demo traffic.
- Enabling the baseline requires a temporary `main.c` blinky/full switch
  (restored after the run); range-check code untouched.

## Reproduce

See `build_commands.md` or `./scripts/run_m1_baseline.sh`.
