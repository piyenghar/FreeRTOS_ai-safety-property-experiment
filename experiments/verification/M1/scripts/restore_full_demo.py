#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
MAIN = ROOT / "FreeRTOS/Demo/CORTEX_MPS2_QEMU_IAR_GCC/main.c"
BAK = MAIN.with_suffix(".c.m1bak")


def main() -> int:
    if not BAK.exists():
        print("no backup", file=sys.stderr)
        return 1
    MAIN.write_text(BAK.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"restored {MAIN}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
