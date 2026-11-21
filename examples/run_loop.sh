#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
echo "== gate selftest =="
python3 -m src.gate --selftest
echo "== run loop =="
python3 -m src.cli --out-dir artifacts/demo
echo "== artifacts =="
ls -1 artifacts/demo
