# M2 Independent L3 Verification (SP1 / SP2)

Isolated QEMU/ARM-GCC builds that check FreeRTOS MPU safety properties without
modifying `FreeRTOS/Demo/CORTEX_MPU_M3_MPS2_QEMU_GCC/mpu_demo.c` or pilot branches.

**Applicability:** this harness tests its own standalone firmware, not T1/T2/T3
`mpu_demo.c` binaries. See [APPLICABILITY.md](APPLICABILITY.md). Do not claim
pilot L3 is independently verified by these runs alone.

## Quick run

```bash
./scripts/run_l3.sh
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
