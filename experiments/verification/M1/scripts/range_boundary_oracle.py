#!/usr/bin/env python3
"""Host-side oracle mirroring prvCheckReceivedValueWithinExpectedRange().

This does NOT modify FreeRTOS sources. It records the intended acceptance /
rejection boundaries from QueueSet.c for M1 property documentation and
self-checks the predicate on concrete examples.
"""
from __future__ import annotations

import json
from pathlib import Path

ALLOWABLE = 3  # queuesetALLOWABLE_RX_DEVIATION
IGNORED_BOUNDARY = ALLOWABLE * 2  # queuesetIGNORED_BOUNDARY
ISR_SPLIT = 0xFFFF  # queuesetINITIAL_ISR_TX_VALUE


def check_within_expected_range(received: int, expected: int) -> bool:
    """Same boolean outcome as prvCheckReceivedValueWithinExpectedRange().

    Note: the C function also configASSERTs the same condition before returning.
    """
    if received > expected:
        return (received - expected) <= ALLOWABLE
    return (expected - received) <= ALLOWABLE


def main() -> None:
    accept = []
    reject = []
    expected = 1000
    for delta in range(0, ALLOWABLE + 3):
        for sign in (+1, -1):
            if delta == 0 and sign < 0:
                continue
            received = expected + sign * delta
            ok = check_within_expected_range(received, expected)
            entry = {
                "ulReceived": received,
                "ulExpectedReceived": expected,
                "abs_deviation": abs(received - expected),
                "within_range": ok,
            }
            (accept if ok else reject).append(entry)

    report = {
        "function": "prvCheckReceivedValueWithinExpectedRange",
        "source": "FreeRTOS/Demo/Common/Minimal/QueueSet.c",
        "constants": {
            "queuesetALLOWABLE_RX_DEVIATION": ALLOWABLE,
            "queuesetIGNORED_BOUNDARY": IGNORED_BOUNDARY,
            "queuesetINITIAL_ISR_TX_VALUE": ISR_SPLIT,
        },
        "properties": {
            "P1_accept_within_range": {
                "statement": (
                    "If |ulReceived - ulExpectedReceived| <= 3, the check returns "
                    "pdPASS and configASSERT does not fire."
                ),
                "examples": accept,
            },
            "P2_reject_outside_range": {
                "statement": (
                    "If |ulReceived - ulExpectedReceived| > 3, configASSERT fires "
                    "(when asserts enabled) and the function returns pdFALSE, "
                    "causing xQueueSetTasksStatus = pdFAIL."
                ),
                "examples": reject,
            },
        },
        "caller_notes": {
            "ignored_near_wrap_boundaries": (
                "Callers skip invoking the checker when values are within "
                "queuesetIGNORED_BOUNDARY of wrap/partition edges."
            ),
            "task_value_domain": "0 .. 0xFFFE",
            "isr_value_domain": "0xFFFF .. ULONG_MAX",
        },
        "self_check": {
            "all_accept_have_dev_le_3": all(e["abs_deviation"] <= ALLOWABLE for e in accept),
            "all_reject_have_dev_gt_3": all(e["abs_deviation"] > ALLOWABLE for e in reject),
            "accept_count": len(accept),
            "reject_count": len(reject),
        },
    }

    out = Path(__file__).resolve().parents[1] / "results" / "range_boundary_oracle.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    assert report["self_check"]["all_accept_have_dev_le_3"]
    assert report["self_check"]["all_reject_have_dev_gt_3"]
    assert report["self_check"]["reject_count"] > 0
    assert report["self_check"]["accept_count"] > 0


if __name__ == "__main__":
    main()
