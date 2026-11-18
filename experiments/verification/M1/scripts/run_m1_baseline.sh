#!/usr/bin/env bash
# Build and run CORTEX_MPS2_QEMU_IAR_GCC full demo (includes QueueSet.c).
# Temporarily selects main_full(); restores main.c afterward.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
DEMO="$ROOT/FreeRTOS/Demo/CORTEX_MPS2_QEMU_IAR_GCC"
GCC_DIR="$DEMO/build/gcc"
OUT="$ROOT/experiments/verification/M1"
RESULTS="$OUT/results"
TIMEOUT_SECS="${TIMEOUT_SECS:-20}"

mkdir -p "$RESULTS"

python3 "$OUT/scripts/enable_full_demo.py"

(
  cd "$GCC_DIR"
  make -j"$(nproc)" 2>&1 | tee "$OUT/build.log"
)

AXF="$GCC_DIR/output/RTOSDemo.out"
UART="$RESULTS/baseline_full_demo.uart.log"

set +e
timeout "${TIMEOUT_SECS}s" qemu-system-arm \
  -machine mps2-an385 \
  -cpu cortex-m3 \
  -kernel "$AXF" \
  -monitor none \
  -nographic \
  -serial stdio \
  >"$UART" 2>&1
rc=$?
set -e
echo "EXIT:${rc}" >>"$UART"

python3 "$OUT/scripts/restore_full_demo.py"

# Confirm QueueSet.o linked and range symbols present.
arm-none-eabi-nm "$AXF" | grep -E "prvCheckReceivedValueWithinExpectedRange|vStartQueueSetTasks|xAreQueueSetTasksStillRunning" \
  >"$RESULTS/symbols_queueset.txt" || true

echo "UART log: $UART"
cat "$UART"
