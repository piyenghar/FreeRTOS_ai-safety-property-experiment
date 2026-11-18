# SP2 L3 Verification — Unauthorized Privilege Escalation Prevention

Date executed: 2026-11-18  
Harness: `experiments/verification/M2` (independent of `mpu_demo.c`)  
Logs: `experiments/verification/M2/results/`

## What SP2 tests (baseline semantics)

With `configENFORCE_SYSTEM_CALLS_FROM_KERNEL_ONLY == 1` and MPU wrappers **v2** (`configUSE_MPU_WRAPPERS_V1 == 0`), the unprivileged RO task calls `portRAISE_PRIVILEGE()`, then writes `ucSharedMemory`. Under v2 the direct raise SVC is not granted, so the task stays unprivileged and the write still MemFaults. Demo reporting:

- `SP2 PASS` iff the second write also produced an expected MemFault (tracker cleared).

## Independent oracle

Implemented in `sp2/l3_sp2.c`. Does **not** consume demo `SP2 PASS` strings.

`HOLD` iff **all**:

1. `npriv_after_raise=1` — `CONTROL.nPRIV` still set after `portRAISE_PRIVILEGE()`.
2. `memfault_seen=1` — attack store still faults.
3. `value_unchanged=1` — volatile reload shows the store did not land.

Otherwise `VIOLATION_DETECTED`.

## Exact test procedure

```bash
cd experiments/verification/M2
make PROPERTY=sp2 CONTROL=pos DEBUG=1
timeout 8s qemu-system-arm -machine mps2-an385 -cpu cortex-m3 \
  -kernel ./build/sp2_pos/RTOSDemo.axf -serial stdio -monitor none \
  -semihosting -semihosting-config enable=on,target=native -nographic

make PROPERTY=sp2 CONTROL=neg DEBUG=1
# same QEMU command with ./build/sp2_neg/RTOSDemo.axf
```

| Control | Build difference | Expected oracle |
|---------|------------------|-----------------|
| Positive | Unprivileged restricted task (baseline-equivalent) | `L3_SP2_ORACLE: HOLD` |
| Negative | Same oracle code; task created with `portPRIVILEGE_BIT` (isolated build) | `L3_SP2_ORACLE: VIOLATION_DETECTED` |

### Why the negative control uses `portPRIVILEGE_BIT`

With wrappers v2, `portSVC_RAISE_PRIVILEGE` is not compiled into the SVC handler. Setting `configENFORCE_SYSTEM_CALLS_FROM_KERNEL_ONLY` to 0 therefore does **not** make `portRAISE_PRIVILEGE()` succeed. The negative control instead starts the task privileged so the oracle observes the post-condition of a successful escalation (nPRIV cleared, RO write succeeds). See `configs/sp2_neg/README.md`.

## Expected vs observed

| Case | Expected | Observed |
|------|----------|----------|
| Positive evidence | npriv=1, memfault=1, value_unchanged=1 | **Seen** (`results/sp2_pos.uart.log`, multiple cycles) |
| Positive oracle | HOLD | **HOLD** (repeated) |
| Negative evidence | npriv=0, memfault=0, value_unchanged=0 | **Seen** (`results/sp2_neg.uart.log`) |
| Negative oracle | VIOLATION_DETECTED | **VIOLATION_DETECTED** (repeated) |
| Baseline demo UART | SP2 PASS lines | **SP2 PASS** (`results/baseline_mpu_demo.uart.log`) |

### Positive-control result

**PASS** — independent oracle `HOLD`; baseline demo also prints `SP2 PASS`.

### Negative-control result

**PASS (oracle sensitivity)** — privileged task yields `VIOLATION_DETECTED`.

## Independence

- Verification sources only under `experiments/verification/M2`.
- Oracle uses CONTROL.nPRIV, verification fault tracker, and cell value — not demo PASS strings.
- Negative control is a separate binary (`build/sp2_neg`).

## L3 verdict (SP2)

**L3 PASS** — positive HOLD and negative VIOLATION_DETECTED both executed in QEMU.

## Limitations

- QEMU MPS2, not silicon.
- Negative control injects privilege at task creation rather than via a successful `portRAISE_PRIVILEGE` SVC (impossible under wrappers v2 without switching to v1).
- Demo SP2 itself only checks post-raise MemFault; the independent oracle adds an explicit nPRIV check.
- Baseline corroboration on this branch is the T3 pilot binary (SP2 logic unchanged).
