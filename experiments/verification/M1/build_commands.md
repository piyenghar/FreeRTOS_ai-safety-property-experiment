# M1 baseline — build and run commands

## Target demo

`FreeRTOS/Demo/CORTEX_MPS2_QEMU_IAR_GCC` (GCC + QEMU `mps2-an385`)

This demo’s `main_full()` calls `vStartQueueSetTasks()` and the tick hook
calls `vQueueSetAccessQueueSetFromISR()`, which exercise
`prvCheckReceivedValueWithinExpectedRange()` in
`FreeRTOS/Demo/Common/Minimal/QueueSet.c`.

## One-shot (recommended)

```bash
cd /mnt/f/RDProjects/safetyProperties/FreeRTOS_ai-safety-property-experiment
./experiments/verification/M1/scripts/run_m1_baseline.sh
# optional: TIMEOUT_SECS=20
```

The script temporarily sets `mainCREATE_SIMPLE_BLINKY_DEMO_ONLY` to `0`
(full demo), builds, runs QEMU, then restores `main.c`. It does **not**
modify `QueueSet.c`.

## Manual steps

```bash
# 1) Enable full demo (QueueSet active)
python3 experiments/verification/M1/scripts/enable_full_demo.py

# 2) Build
cd FreeRTOS/Demo/CORTEX_MPS2_QEMU_IAR_GCC/build/gcc
make -j$(nproc)

# 3) Run (check task prints every 5 s)
timeout 20s qemu-system-arm \
  -machine mps2-an385 \
  -cpu cortex-m3 \
  -kernel ./output/RTOSDemo.out \
  -monitor none \
  -nographic \
  -serial stdio

# 4) Restore blinky-only default
python3 experiments/verification/M1/scripts/restore_full_demo.py
```

## Host-side range boundary oracle (offline)

```bash
python3 experiments/verification/M1/scripts/range_boundary_oracle.py
```

## Independent L3 (host gcc — does not touch QueueSet.c)

Windows (PowerShell):

```powershell
.\experiments\verification\M1\scripts\run_m1_l3.ps1
```

Manual:

```powershell
cd experiments\verification\M1\l3
mkdir build -Force
gcc -std=c11 -Wall -Wextra -Werror -O0 -g -I. `
  l3_range_test.c range_check_under_test.c -o build\l3_range_test.exe
$env:M1_L3_LOG = "..\results\l3_range_test.log"
.\build\l3_range_test.exe
```

Linux/WSL:

```bash
./experiments/verification/M1/scripts/run_m1_l3.sh
# or: cd experiments/verification/M1/l3 && make test
```

Evidence: `results/l3_range_test.log`, `results/l3_summary.json`. Report: `L3-verification.md`.
