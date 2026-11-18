# M2 Independent L3 Verification (SP1 / SP2)

Isolated QEMU/ARM-GCC builds that check FreeRTOS MPU safety properties without
modifying `FreeRTOS/Demo/CORTEX_MPU_M3_MPS2_QEMU_GCC/mpu_demo.c` or pilot branches.

**Applicability:** standalone `sp1/`/`sp2/` firmware calibrates oracles; pilot
integration builds each pilot’s actual `mpu_demo.c` in Git worktrees. See
[APPLICABILITY.md](APPLICABILITY.md) and `results/pilots/REPORT.md`.

## Quick run

```bash
# Standalone SP1/SP2 pos/neg oracle firmware
./scripts/run_l3.sh

# T1/T2/T3 worktree builds + host L3 oracle + controls
./scripts/run_pilot_integration.sh
```

## Reports

- [SP1-L3-verification.md](SP1-L3-verification.md)
- [SP2-L3-verification.md](SP2-L3-verification.md)

## Layout

| Path | Role |
|------|------|
| `sp1/l3_sp1.c` | SP1 independent oracle + pos/neg region variants |
| `sp2/l3_sp2.c` | SP2 independent oracle + privileged neg control |
| `common/` | UART helper, verification `app_main` |
| `results/*.uart.log` | Captured QEMU UART from executed runs |
| `build/` | Out-of-tree binaries (`sp1_pos`, `sp1_neg`, …) |
