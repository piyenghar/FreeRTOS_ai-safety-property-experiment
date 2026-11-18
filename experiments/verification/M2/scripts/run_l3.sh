#!/usr/bin/env bash
# Build and run independent L3 SP1/SP2 positive and negative controls in QEMU.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
VER_DIR="$ROOT/experiments/verification/M2"
DEMO_DIR="$ROOT/FreeRTOS/Demo/CORTEX_MPU_M3_MPS2_QEMU_GCC"
RESULTS="$VER_DIR/results"
TIMEOUT_SECS="${TIMEOUT_SECS:-6}"

mkdir -p "$RESULTS"
cd "$VER_DIR"

run_variant() {
  local prop="$1"
  local ctrl="$2"
  local out="$RESULTS/${prop}_${ctrl}.uart.log"
  local bin="$VER_DIR/build/${prop}_${ctrl}/RTOSDemo.axf"

  echo "=== Building PROPERTY=${prop} CONTROL=${ctrl} ==="
  make PROPERTY="$prop" CONTROL="$ctrl" DEBUG=1

  echo "=== Running QEMU -> ${out} ==="
  # shellcheck disable=SC2086
  set +e
  timeout "${TIMEOUT_SECS}s" qemu-system-arm \
    -machine mps2-an385 \
    -cpu cortex-m3 \
    -kernel "$bin" \
    -serial stdio \
    -monitor none \
    -semihosting \
    -semihosting-config enable=on,target=native \
    -nographic \
    >"$out" 2>&1
  local rc=$?
  set -e
  echo "EXIT:${rc}" | tee -a "$out"
  echo "--- UART (${prop}/${ctrl}) ---"
  cat "$out"
  echo "------------------------------"
}

run_baseline_positive() {
  local out="$RESULTS/baseline_mpu_demo.uart.log"
  echo "=== Baseline protected demo (positive corroboration) ==="
  make -C "$DEMO_DIR" DEBUG=1
  set +e
  timeout "${TIMEOUT_SECS}s" qemu-system-arm \
    -machine mps2-an385 \
    -cpu cortex-m3 \
    -kernel "$DEMO_DIR/build/RTOSDemo.axf" \
    -serial stdio \
    -monitor none \
    -semihosting \
    -semihosting-config enable=on,target=native \
    -nographic \
    >"$out" 2>&1
  local rc=$?
  set -e
  echo "EXIT:${rc}" | tee -a "$out"
  echo "--- UART (baseline) ---"
  cat "$out"
  echo "-----------------------"
}

run_baseline_positive
run_variant sp1 pos
run_variant sp1 neg
run_variant sp2 pos
run_variant sp2 neg

echo "All L3 verification runs complete. Logs in $RESULTS"
