#!/usr/bin/env bash
# External M2 pilot L3 integration runner (verification-only).
# Creates isolated worktrees, builds pilot mpu_demo.c, runs QEMU, applies host oracle.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
VER_DIR="$ROOT/experiments/verification/M2"
RESULTS="$VER_DIR/results/pilots"
WT_ROOT="$VER_DIR/worktrees"
NEG_SRC="$RESULTS/neg_sources"
TIMEOUT_SECS="${TIMEOUT_SECS:-8}"
ORACLE="$VER_DIR/scripts/l3_pilot_oracle.py"

declare -A PILOT_BRANCH=(
  [t1]="pilot/m2-t1-logging"
  [t2]="pilot/m2-t2-refactor"
  [t3]="pilot/m2-t3-enhancement"
)

mkdir -p "$RESULTS" "$NEG_SRC" "$WT_ROOT"
cd "$ROOT"

qemu_run() {
  local axf="$1"
  local out="$2"
  set +e
  timeout "${TIMEOUT_SECS}s" qemu-system-arm \
    -machine mps2-an385 \
    -cpu cortex-m3 \
    -kernel "$axf" \
    -serial stdio \
    -monitor none \
    -semihosting \
    -semihosting-config enable=on,target=native \
    -nographic \
    >"$out" 2>&1
  local rc=$?
  set -e
  echo "EXIT:${rc}" >>"$out"
  return 0
}

ensure_worktree() {
  local id="$1"
  local branch="${PILOT_BRANCH[$id]}"
  local path="$WT_ROOT/$id"
  if [[ -d "$path/.git" || -f "$path/.git" ]]; then
    git -C "$path" checkout -q -f "$branch" >/dev/null
    git -C "$path" reset -q --hard "$branch" >/dev/null
  else
    rm -rf "$path"
    git worktree add -f "$path" "$branch" >/dev/null
  fi
  # FreeRTOS/Source is a submodule; populate it inside the worktree only.
  # Does not reset/clean dirty submodules in the primary worktree.
  git -C "$path" submodule update --init --depth 1 FreeRTOS/Source >/dev/null
  printf '%s\n' "$path"
}

sha256_file() {
  sha256sum "$1" | awk '{print $1}'
}

make_sp1_neg_copy() {
  local src="$1"
  local dst="$2"
  python3 - <<PY
from pathlib import Path
src = Path(r"$src")
dst = Path(r"$dst")
text = src.read_text(encoding="utf-8", errors="replace")
old = "portMPU_REGION_PRIVILEGED_READ_WRITE_UNPRIV_READ_ONLY"
if old not in text:
    raise SystemExit("expected RO region attribute not found in " + str(src))
text = text.replace(old, "portMPU_REGION_READ_WRITE", 1)
dst.parent.mkdir(parents=True, exist_ok=True)
dst.write_text(text, encoding="utf-8")
print("wrote", dst)
PY
}

run_standalone_controls() {
  local outdir="$RESULTS/controls"
  mkdir -p "$outdir"
  cd "$VER_DIR"
  for prop in sp1 sp2; do
    for ctrl in pos neg; do
      echo "=== standalone ${prop}/${ctrl} ==="
      make PROPERTY="$prop" CONTROL="$ctrl" DEBUG=1
      local axf="$VER_DIR/build/${prop}_${ctrl}/RTOSDemo.axf"
      local log="$outdir/${prop}_${ctrl}.uart.log"
      local json="$outdir/${prop}_${ctrl}.json"
      qemu_run "$axf" "$log"
      python3 "$ORACLE" --mode standalone --property "$prop" --control "$ctrl" \
        --log "$log" --out "$json" --l1 PASS \
        --source-note "standalone l3_${prop}.c oracle firmware"
    done
  done
  cd "$ROOT"
}

run_pilot_positive() {
  local id="$1"
  local wt
  wt="$(ensure_worktree "$id")"
  local demo="$wt/FreeRTOS/Demo/CORTEX_MPU_M3_MPS2_QEMU_GCC"
  local mpu="$demo/mpu_demo.c"
  local outdir="$RESULTS/$id"
  mkdir -p "$outdir"

  local hash
  hash="$(sha256_file "$mpu")"
  echo "$hash  mpu_demo.c" >"$outdir/mpu_demo.sha256"
  cp -f "$mpu" "$outdir/mpu_demo.c"

  echo "=== pilot $id positive build (worktree ${PILOT_BRANCH[$id]}) ==="
  local l1="PASS"
  if ! make -C "$demo" DEBUG=1; then
    l1="FAIL"
  fi
  echo "$l1" >"$outdir/L1_build.txt"

  local log="$outdir/positive.uart.log"
  local json="$outdir/positive.json"
  if [[ "$l1" == "PASS" ]]; then
    qemu_run "$demo/build/RTOSDemo.axf" "$log"
  else
    echo "BUILD_FAILED" >"$log"
  fi

  python3 "$ORACLE" --mode pilot --pilot "$id" --control pos \
    --log "$log" --out "$json" --l1 "$l1" \
    --mpu-demo-sha256 "$hash" \
    --source-note "worktree ${PILOT_BRANCH[$id]} actual mpu_demo.c"
}

run_pilot_sp1_negative() {
  local id="$1"
  local wt="$WT_ROOT/$id"
  local src="$wt/FreeRTOS/Demo/CORTEX_MPU_M3_MPS2_QEMU_GCC/mpu_demo.c"
  local neg="$NEG_SRC/${id}_mpu_demo_sp1neg.c"
  local outdir="$RESULTS/$id"
  mkdir -p "$outdir"

  make_sp1_neg_copy "$src" "$neg"
  local hash
  hash="$(sha256_file "$neg")"

  echo "=== pilot $id SP1 negative (isolated patched copy) ==="
  cd "$VER_DIR"
  local l1="PASS"
  if ! make PROPERTY=pilot_mpu CONTROL=neg PILOT_ID="$id" \
      PILOT_MPU_DEMO="$neg" DEBUG=1; then
    l1="FAIL"
  fi
  echo "$l1" >"$outdir/L1_sp1neg_build.txt"

  local axf="$VER_DIR/build/pilot_${id}_neg/RTOSDemo.axf"
  local log="$outdir/sp1_negative.uart.log"
  local json="$outdir/sp1_negative.json"
  if [[ "$l1" == "PASS" ]]; then
    qemu_run "$axf" "$log"
  else
    echo "BUILD_FAILED" >"$log"
  fi

  python3 "$ORACLE" --mode pilot --pilot "$id" --control neg \
    --log "$log" --out "$json" --l1 "$l1" \
    --mpu-demo-sha256 "$hash" \
    --source-note "isolated SP1-neg patch of ${PILOT_BRANCH[$id]} mpu_demo.c (RO->RW); pilot branches untouched"
  cd "$ROOT"
}

echo "ROOT=$ROOT"
run_standalone_controls

for id in t1 t2 t3; do
  run_pilot_positive "$id"
  run_pilot_sp1_negative "$id"
done

RESULTS="$RESULTS" python3 - <<'PY'
import json, os
from pathlib import Path
results = Path(os.environ["RESULTS"])
summary = {
    "pilots": {},
    "controls": {},
    "notes": {
        "pilot_L3_uses_actual_mpu_demo": True,
        "pilot_L3_host_oracle": (
            "Positive: SP1/SP2 PASS required, FAIL forbidden on UART from "
            "worktree-built pilot binary. SP1-neg: isolated RO->RW copy of "
            "that pilot mpu_demo.c must yield VIOLATION."
        ),
        "standalone_controls": "Existing MemFault/value/nPRIV firmware under sp1/ and sp2/.",
        "pilot_branches_unmodified": True,
    },
}
for pilot in ("t1", "t2", "t3"):
    d = results / pilot
    pos = json.loads((d / "positive.json").read_text(encoding="utf-8"))
    neg = json.loads((d / "sp1_negative.json").read_text(encoding="utf-8"))
    summary["pilots"][pilot] = {
        "positive": {
            "L1": pos.get("L1_build"),
            "L2": pos.get("L2_verdict"),
            "L3": pos.get("L3_verdict"),
            "L3_SP1": pos.get("L3_SP1"),
            "L3_SP2": pos.get("L3_SP2"),
            "mpu_demo_sha256": pos.get("mpu_demo_sha256"),
        },
        "sp1_negative_control": {
            "L1": neg.get("L1_build"),
            "L3": neg.get("L3_verdict"),
            "L3_SP1": neg.get("L3_SP1"),
        },
    }
cdir = results / "controls"
for prop in ("sp1", "sp2"):
    for ctrl in ("pos", "neg"):
        j = json.loads((cdir / f"{prop}_{ctrl}.json").read_text(encoding="utf-8"))
        summary["controls"][f"{prop}_{ctrl}"] = {
            "verdict": j.get("verdict"),
            "hold_count": j.get("hold_count"),
            "violation_count": j.get("violation_count"),
        }
out = results / "summary.json"
out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
print(json.dumps(summary, indent=2))
PY

echo "Done. Summary at $RESULTS/summary.json"
