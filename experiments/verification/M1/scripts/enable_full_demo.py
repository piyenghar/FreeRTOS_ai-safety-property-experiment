#!/usr/bin/env python3
"""Temporarily select main_full() so QueueSet range-checking runs under QEMU.

Does not modify QueueSet.c or the range-check mechanism. Restorable via
restore_full_demo.py / main.c.m1bak.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
MAIN = ROOT / "FreeRTOS/Demo/CORTEX_MPS2_QEMU_IAR_GCC/main.c"
BAK = MAIN.with_suffix(".c.m1bak")
OLD = "#define mainCREATE_SIMPLE_BLINKY_DEMO_ONLY    1"
NEW = "#define mainCREATE_SIMPLE_BLINKY_DEMO_ONLY    0"


def main() -> int:
    text = MAIN.read_text(encoding="utf-8")
    if NEW in text and OLD not in text:
        print("already enabled")
        return 0
    if OLD not in text:
        print("unexpected main.c contents", file=sys.stderr)
        return 1
    if not BAK.exists():
        BAK.write_text(text, encoding="utf-8")
    MAIN.write_text(text.replace(OLD, NEW, 1), encoding="utf-8")
    print(f"patched {MAIN}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
