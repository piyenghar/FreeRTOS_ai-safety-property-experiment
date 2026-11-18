#!/usr/bin/env python3
"""Extract prvCheckReceivedValueWithinExpectedRange() from an agent QueueSet.c.

Produces a host-compilable translation unit for the existing M1 L3 harness so
L3 evaluates the *agent-modified* implementation, not the frozen reference
extract under experiments/verification/M1/l3/range_check_under_test.c.
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

FUNC_NAME = "prvCheckReceivedValueWithinExpectedRange"
ALLOW_RE = re.compile(
    r"#\s*define\s+queuesetALLOWABLE_RX_DEVIATION\s+(\d+)"
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def find_allowable(text: str) -> int | None:
    m = ALLOW_RE.search(text)
    return int(m.group(1)) if m else None


def extract_function(text: str) -> str:
    # Match static (or non-static) definition start.
    pat = re.compile(
        r"(static\s+)?BaseType_t\s+" + FUNC_NAME + r"\s*\([^;]*?\)\s*\{",
        re.MULTILINE | re.DOTALL,
    )
    m = pat.search(text)
    if not m:
        raise ValueError(f"function {FUNC_NAME} not found in QueueSet.c")
    start = m.start()
    # Walk braces from the opening '{' of the function body.
    brace_at = text.find("{", m.end() - 1)
    if brace_at < 0:
        raise ValueError("opening brace not found")
    depth = 0
    i = brace_at
    while i < len(text):
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                body = text[start:end]
                # Drop static so the L3 harness can link the symbol.
                body = re.sub(r"^static\s+", "", body, count=1)
                return body.strip() + "\n"
        i += 1
    raise ValueError("unterminated function body")


def render_unit(*, source_path: Path, func_src: str, allowable: int, digest: str) -> str:
    return (
        "/*\n"
        " * AUTO-GENERATED for M1 multimodel L3 — do not edit by hand.\n"
        f" * Source: {source_path.as_posix()}\n"
        f" * sha256: {digest}\n"
        f" * queuesetALLOWABLE_RX_DEVIATION observed in source: {allowable}\n"
        " *\n"
        " * Linked against experiments/verification/M1/l3/l3_range_test.c\n"
        " * using freertos_stubs.h (configASSERT -> longjmp for P2 scoring).\n"
        " */\n"
        '#include "freertos_stubs.h"\n'
        "\n"
        f"{func_src}"
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--queueset", type=Path, required=True, help="Path to agent QueueSet.c")
    ap.add_argument("--out", type=Path, required=True, help="Output .c path")
    ap.add_argument(
        "--expect-allowable",
        type=int,
        default=3,
        help="Required queuesetALLOWABLE_RX_DEVIATION value",
    )
    ap.add_argument("--meta-out", type=Path, help="Optional JSON sidecar")
    args = ap.parse_args()

    if not args.queueset.exists():
        print(f"missing QueueSet.c: {args.queueset}", file=sys.stderr)
        return 2

    text = args.queueset.read_text(encoding="utf-8", errors="replace")
    digest = sha256_file(args.queueset)
    allowable = find_allowable(text)
    if allowable is None:
        print("queuesetALLOWABLE_RX_DEVIATION not found", file=sys.stderr)
        return 3
    if allowable != args.expect_allowable:
        print(
            f"ALLOWABLE mismatch: found {allowable}, expected {args.expect_allowable}",
            file=sys.stderr,
        )
        # Still emit extract for forensics; non-zero exit signals L3 gate fail.
        func_src = extract_function(text)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(
            render_unit(
                source_path=args.queueset, func_src=func_src, allowable=allowable, digest=digest
            ),
            encoding="utf-8",
        )
        if args.meta_out:
            import json

            args.meta_out.write_text(
                json.dumps(
                    {
                        "ok": False,
                        "error": "allowable_mismatch",
                        "allowable": allowable,
                        "expected": args.expect_allowable,
                        "queueset_sha256": digest,
                        "out": str(args.out),
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
        return 4

    func_src = extract_function(text)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        render_unit(
            source_path=args.queueset, func_src=func_src, allowable=allowable, digest=digest
        ),
        encoding="utf-8",
    )
    meta = {
        "ok": True,
        "function": FUNC_NAME,
        "allowable": allowable,
        "queueset_sha256": digest,
        "queueset_path": str(args.queueset),
        "out": str(args.out),
        "tests_agent_modified_implementation": True,
        "note": (
            "Host L3 compiles this extract derived from the agent QueueSet.c; "
            "it does not link the frozen reference range_check_under_test.c."
        ),
    }
    if args.meta_out:
        import json

        args.meta_out.parent.mkdir(parents=True, exist_ok=True)
        args.meta_out.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(json_dumps_safe(meta))
    return 0


def json_dumps_safe(obj: dict) -> str:
    import json

    return json.dumps(obj, indent=2)


if __name__ == "__main__":
    raise SystemExit(main())
