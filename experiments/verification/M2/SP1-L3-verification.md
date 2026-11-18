# SP1 L3 Verification — Read-only Memory Isolation

Date executed: 2026-11-18  
Harness: `experiments/verification/M2` (independent of `mpu_demo.c`)  
Logs: `experiments/verification/M2/results/`

## What SP1 tests (baseline semantics)

In the MPU demo, an unprivileged task has RO access to `ucSharedMemory`. It deliberately writes that cell; an MPU MemFault is expected; `ucROTaskFaultTracker` is cleared by `vHandleMemoryFault`. Demo reporting:

- `SP1 PASS` iff the tracker was cleared (fault occurred).

## Independent oracle

Implemented in `sp1/l3_sp1.c`. Does **not** consume demo `SP1 PASS` strings.

`HOLD` iff **both**:

1. `memfault_seen=1` — fault tracker cleared by the verification MemFault handler after the attack store.
2. `value_unchanged=1` — volatile reload of the cell equals the pre-store value.

Otherwise `VIOLATION_DETECTED`.

## Exact test procedure

```bash
cd experiments/verification/M2
make PROPERTY=sp1 CONTROL=pos DEBUG=1
timeout 6s qemu-system-arm -machine mps2-an385 -cpu cortex-m3 \
  -kernel ./build/sp1_pos/RTOSDemo.axf -serial stdio -monitor none \
  -semihosting -semihosting-config enable=on,target=native -nographic

make PROPERTY=sp1 CONTROL=neg DEBUG=1
# same QEMU command with ./build/sp1_neg/RTOSDemo.axf

# Baseline corroboration (demo binary; not the independent oracle):
make -C ../../../FreeRTOS/Demo/CORTEX_MPU_M3_MPS2_QEMU_GCC DEBUG=1
# QEMU with that demo's RTOSDemo.axf
```

Or: `./scripts/run_l3.sh`.

| Control | Build difference | Expected oracle |
|---------|------------------|-----------------|
| Positive | Region = privileged-RW / unprivileged-RO | `L3_SP1_ORACLE: HOLD` |
| Negative | Same task, region = RW (isolated build only) | `L3_SP1_ORACLE: VIOLATION_DETECTED` |

## Expected vs observed

| Case | Expected | Observed |
|------|----------|----------|
| Positive evidence | memfault=1, value_unchanged=1 | **Seen** (`results/sp1_pos.uart.log`) |
| Positive oracle | HOLD | **HOLD** (repeated) |
| Negative evidence | memfault=0, value_unchanged=0 | **Seen** (`results/sp1_neg.uart.log`) |
| Negative oracle | VIOLATION_DETECTED | **VIOLATION_DETECTED** (repeated) |
| Baseline demo UART | SP1 PASS lines | **SP1 PASS** (`results/baseline_mpu_demo.uart.log`) |

### Positive-control result

**PASS** — independent oracle `HOLD`; baseline demo also prints `SP1 PASS`.

### Negative-control result

**PASS (oracle sensitivity)** — with RW mapping, oracle reports `VIOLATION_DETECTED` (not vacuously HOLD).

## Independence

- Sources under `experiments/verification/M2` only; demo/pilot `mpu_demo.c` not modified.
- Oracle uses verification-owned shared cell, fault tracker, and UART tags (`L3_SP1_*`), not demo PASS strings.
- Negative control is a separate binary (`build/sp1_neg`), not a mutation of the baseline tree.

## L3 verdict (SP1)

**L3 PASS** — positive HOLD and negative VIOLATION_DETECTED both executed in QEMU.

## Limitations

- QEMU MPS2 model, not silicon.
- Fault evidence uses the FreeRTOS-style expected-fault recovery pattern (PC skip); not a full CFSR dump.
- Baseline corroboration currently runs the T3 pilot binary on this branch (SP1 logic unchanged; also prints `T3_CYCLE`).
