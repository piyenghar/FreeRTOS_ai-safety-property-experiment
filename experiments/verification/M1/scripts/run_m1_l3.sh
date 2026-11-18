#!/usr/bin/env bash
# Build and run independent M1 L3 range-check tests (host gcc).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
L3="$ROOT/experiments/verification/M1/l3"
RESULTS="$ROOT/experiments/verification/M1/results"
mkdir -p "$RESULTS"

cd "$L3"
make clean
make test

# Emit machine-readable summary from the log.
python3 - <<PY
import json, re
from pathlib import Path
log = Path(r"$RESULTS/l3_range_test.log").read_text(encoding="utf-8", errors="replace")
summary = {
    "P1": {},
    "P2": {},
    "ALL": {},
    "oracle_pos": None,
    "oracle_neg": None,
    "cases": [],
}
for line in log.splitlines():
    m = re.match(r"(P1|P2|CTRL) name=(\S+) rx=(\d+) exp=(\d+).*=> (PASS|FAIL)", line)
    if m:
        summary["cases"].append({
            "property": m.group(1),
            "name": m.group(2),
            "rx": int(m.group(3)),
            "exp": int(m.group(4)),
            "result": m.group(5),
        })
    m = re.match(r"SUMMARY (P1|P2|ALL) pass=(\d+) fail=(\d+) total=(\d+)", line)
    if m:
        summary[m.group(1)] = {
            "pass": int(m.group(2)),
            "fail": int(m.group(3)),
            "total": int(m.group(4)),
            "verdict": "PASS" if int(m.group(3)) == 0 else "FAIL",
        }
    m = re.match(r"ORACLE_(POS|NEG) (PASS|FAIL)", line)
    if m:
        key = "oracle_pos" if m.group(1) == "POS" else "oracle_neg"
        summary[key] = m.group(2)
out = Path(r"$RESULTS/l3_summary.json")
out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
print(json.dumps(summary, indent=2))
PY

echo "Done."
