#!/usr/bin/env python3
"""Prepare agent-modified QueueSet.c as a host-compilable M1 L3 UUT.

Compiles the *actual* agent QueueSet.c (with helpers/statics intact) against
m1_l3 FreeRTOS shims. Does not use experiments/verification/M1/l3/range_check_under_test.c.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

FUNC = "prvCheckReceivedValueWithinExpectedRange"
ALLOW_RE = re.compile(r"#\s*define\s+queuesetALLOWABLE_RX_DEVIATION\s+(\d+)")
FROZEN_REF_NAME = "range_check_under_test.c"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(text: str, *, source_path: Path, digest: str, allowable: int) -> str:
    # Redirect FreeRTOS/demo includes to host shims.
    out = text
    out = out.replace('#include "FreeRTOS.h"', '#include "m1_l3_freertos_shim.h"')
    out = out.replace('#include "task.h"', "/* task.h provided by m1_l3_freertos_shim.h */")
    out = out.replace('#include "queue.h"', "/* queue.h provided by m1_l3_freertos_shim.h */")
    out = out.replace('#include "QueueSet.h"', '#include "m1_l3_queueset_api.h"')

    # Export the range-check symbol for the host harness (keep helpers static).
    out, n_decl = re.subn(
        rf"\bstatic\s+BaseType_t\s+{FUNC}\s*\(",
        f"BaseType_t {FUNC}(",
        out,
        count=2,  # forward decl + definition
    )
    if n_decl < 1:
        # Already non-static or unusual formatting — require the symbol to exist.
        if not re.search(rf"BaseType_t\s+{FUNC}\s*\(", out):
            raise ValueError(f"{FUNC} not found in QueueSet.c")

    header = (
        "/*\n"
        " * AUTO-GENERATED M1 L3 UUT — agent-modified QueueSet.c + include shims.\n"
        f" * Source: {source_path.as_posix()}\n"
        f" * sha256: {digest}\n"
        f" * queuesetALLOWABLE_RX_DEVIATION: {allowable}\n"
        " * used_frozen_reference_extract: false\n"
        f" * NOTE: Must never be replaced by verification/M1/l3/{FROZEN_REF_NAME}\n"
        " */\n"
        "#ifndef configUSE_QUEUE_SETS\n"
        "#define configUSE_QUEUE_SETS 1\n"
        "#endif\n\n"
    )
    return header + out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--queueset", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--expect-allowable", type=int, default=3)
    ap.add_argument("--meta-out", type=Path)
    ap.add_argument(
        "--forbid-path-substring",
        default="verification/M1/l3/range_check_under_test.c",
        help="Refuse if --queueset resolves to the frozen reference extract",
    )
    args = ap.parse_args()

    qs = args.queueset.resolve()
    if not qs.exists():
        print(f"missing QueueSet.c: {qs}", file=sys.stderr)
        return 2
    if args.forbid_path_substring.replace("\\", "/") in str(qs).replace("\\", "/"):
        print(
            f"refusing frozen reference path: {qs}",
            file=sys.stderr,
        )
        return 5
    if qs.name == FROZEN_REF_NAME:
        print("refusing to use range_check_under_test.c as QueueSet UUT", file=sys.stderr)
        return 5

    text = qs.read_text(encoding="utf-8", errors="replace")
    digest = sha256_file(qs)
    m = ALLOW_RE.search(text)
    if not m:
        print("queuesetALLOWABLE_RX_DEVIATION not found", file=sys.stderr)
        return 3
    allowable = int(m.group(1))
    meta = {
        "ok": allowable == args.expect_allowable,
        "mode": "full_queueset_uut",
        "function": FUNC,
        "allowable": allowable,
        "expected_allowable": args.expect_allowable,
        "queueset_sha256": digest,
        "queueset_path": str(qs),
        "out": str(args.out),
        "tests_agent_modified_implementation": True,
        "used_frozen_reference_extract": False,
        "preserves_helpers_and_statics": True,
    }
    if allowable != args.expect_allowable:
        if args.meta_out:
            args.meta_out.parent.mkdir(parents=True, exist_ok=True)
            args.meta_out.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(meta, indent=2))
        return 4

    prepared = prepare(text, source_path=qs, digest=digest, allowable=allowable)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(prepared, encoding="utf-8")
    meta["ok"] = True
    meta["uut_bytes"] = len(prepared.encode("utf-8"))
    if args.meta_out:
        args.meta_out.parent.mkdir(parents=True, exist_ok=True)
        args.meta_out.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(meta, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
