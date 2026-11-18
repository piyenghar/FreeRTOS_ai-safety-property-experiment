#!/usr/bin/env bash
# Launch DSN2027 M2 multi-model matrix (Linux/WSL).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$ROOT"
export PATH="$HOME/.local/bin:$PATH"
python3 -c 'import yaml' 2>/dev/null || pip3 install --user pyyaml
exec python3 experiments/multimodel/scripts/run_matrix.py "$@"
