#!/usr/bin/env python3
"""Verify the S2000 (AS220) TOU and Custom plan helpers.

Self-contained: the helpers are pure conversions, so this needs no account,
no device and no network. Run it directly:

    python tests/test_pps_plan_helpers.py

The TOU fixtures are the byte strings confirmed against the app in
https://github.com/thomluther/anker-solix-api/issues/322 ; the Custom fixtures
are the two structures quoted in the 0093 mapping comment.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from anker_solix_api.mqtt_pps import (
    decode_custom_plan,
    decode_tou_plan,
    encode_custom_plan,
    encode_tou_plan,
    update_plan_slots,
)

# (hex value of field a7, expected slots as (start_hour, end_hour, tariff))
TOU_FIXTURES = [
    ("0403000b010b14021418", [(0, 11, 3), (11, 20, 1), (20, 24, 2)]),
    ("0403000b010b18", [(0, 11, 3), (11, 24, 1)]),
    ("0403000a010a0e030e18", [(0, 10, 3), (10, 14, 1), (14, 24, 3)]),
    ("0402000401041003 1018".replace(" ", ""), [(0, 4, 2), (4, 16, 1), (16, 24, 3)]),
]

# (hex value of field a2, expected [(weekdays, [(start_time, end_time, load_mode)])])
# Both are the structures quoted in the 0093 mapping comment, prefixed with the
# 0x04 struct type byte.
CUSTOM_FIXTURES = [
    (
        "04011f020100006801026801d002",
        [
            (
                ["mon", "tue", "wed", "thu", "fri"],
                [("00:00", "06:00", 1), ("06:00", "12:00", 2)],
            )
        ],
    ),
    (
        "04021f020100006801026801d00260010200003c00",
        [
            (
                ["mon", "tue", "wed", "thu", "fri"],
                [("00:00", "06:00", 1), ("06:00", "12:00", 2)],
            ),
            (["sat", "sun"], [("00:00", "01:00", 2)]),
        ],
    ),
]

failures: list[str] = []


def check(label: str, got, want) -> None:
    """Compare and record a failure rather than aborting the whole run."""
    if got != want:
        failures.append(f"{label}\n     got:  {got}\n     want: {want}")
        print(f"  FAIL {label}")
    else:
        print(f"  ok   {label}")


print("TOU plan: decode captured values")
for hexval, want in TOU_FIXTURES:
    plan = decode_tou_plan(hexval)
    got = [
        (int(r["start_time"][:2]), int(r["end_time"][:2]), r["tariff"])
        for r in plan["ranges"]
    ]
    check(f"decode {hexval}", got, want)

print("\nTOU plan: re-encode must reproduce the original bytes")
for hexval, _ in TOU_FIXTURES:
    plan = decode_tou_plan(hexval)
    check(f"round-trip {hexval}", encode_tou_plan(plan).hex(), hexval)

print("\nTOU plan: limits are enforced")
for label, plan in [
    (
        "gap between slots",
        {
            "ranges": [
                {"start_time": "00:00", "end_time": "10:00", "tariff": 3},
                {"start_time": "11:00", "end_time": "24:00", "tariff": 1},
            ]
        },
    ),
    (
        "does not reach 24:00",
        {"ranges": [{"start_time": "00:00", "end_time": "20:00", "tariff": 3}]},
    ),
    (
        "does not start at 00:00",
        {"ranges": [{"start_time": "01:00", "end_time": "24:00", "tariff": 3}]},
    ),
    (
        "half-hour boundary",
        {
            "ranges": [
                {"start_time": "00:00", "end_time": "10:30", "tariff": 3},
                {"start_time": "10:30", "end_time": "24:00", "tariff": 1},
            ]
        },
    ),
    (
        "unknown tariff",
        {"ranges": [{"start_time": "00:00", "end_time": "24:00", "tariff": 9}]},
    ),
    ("empty plan", {"ranges": []}),
]:
    try:
        encode_tou_plan(plan)
        failures.append(f"{label}: expected ValueError, none raised")
        print(f"  FAIL {label} (no error raised)")
    except ValueError:
        print(f"  ok   rejected: {label}")

print("\nCustom plan: decode and round-trip captured values")
for hexval, want in CUSTOM_FIXTURES:
    plan = decode_custom_plan(hexval)
    got = [
        (
            g["weekdays"],
            [(r["start_time"], r["end_time"], r["load_mode"]) for r in g["ranges"]],
        )
        for g in plan["groups"]
    ]
    check(f"decode {hexval}", got, want)
    check(f"round-trip {hexval}", encode_custom_plan(plan).hex(), hexval)

print("\nCustom plan: gaps allowed, overlaps rejected")
gapped = {
    "weekdays": ["mon", "tue"],
    "ranges": [
        {"start_time": "00:00", "end_time": "08:00", "load_mode": 1},
        {"start_time": "10:00", "end_time": "20:00", "load_mode": 2},
    ],
}
try:
    encode_custom_plan(gapped)
    print("  ok   gap accepted")
except ValueError as err:
    failures.append(f"gap should be allowed: {err}")
    print(f"  FAIL gap rejected: {err}")

for label, plan in [
    (
        "overlapping slots",
        {
            "weekdays": ["mon"],
            "ranges": [
                {"start_time": "00:00", "end_time": "10:00", "load_mode": 1},
                {"start_time": "09:00", "end_time": "20:00", "load_mode": 2},
            ],
        },
    ),
    (
        "too many slots",
        {
            "weekdays": ["mon"],
            "ranges": [
                {
                    "start_time": f"{h:02d}:00",
                    "end_time": f"{h + 1:02d}:00",
                    "load_mode": 1,
                }
                for h in range(6)
            ],
        },
    ),
    (
        "too many groups",
        {
            "groups": [
                {
                    "weekdays": ["mon"],
                    "ranges": [
                        {"start_time": "00:00", "end_time": "01:00", "load_mode": 1}
                    ],
                }
            ]
            * 3
        },
    ),
    (
        "unknown weekday",
        {
            "weekdays": ["funday"],
            "ranges": [{"start_time": "00:00", "end_time": "01:00", "load_mode": 1}],
        },
    ),
    (
        "unknown load mode",
        {
            "weekdays": ["mon"],
            "ranges": [{"start_time": "00:00", "end_time": "01:00", "load_mode": 7}],
        },
    ),
]:
    try:
        encode_custom_plan(plan)
        failures.append(f"{label}: expected ValueError, none raised")
        print(f"  FAIL {label} (no error raised)")
    except ValueError:
        print(f"  ok   rejected: {label}")

print("\nSlot modification: individual parameters and whole objects")
base = [
    {"start_time": "00:00", "end_time": "08:00", "load_mode": 1},
    {"start_time": "08:00", "end_time": "24:00", "load_mode": 2},
]
check(
    "update one key, others preserved",
    update_plan_slots(base, {"end_time": "09:00"}, index=1)[0],
    {"start_time": "00:00", "end_time": "09:00", "load_mode": 1},
)
check(
    "append a whole slot",
    len(
        update_plan_slots(
            base, {"start_time": "20:00", "end_time": "22:00", "load_mode": 1}
        )
    ),
    3,
)
check("delete a slot", len(update_plan_slots(base, index=2, delete=True)), 1)
check("input list untouched", base[0]["end_time"], "08:00")
for label, kwargs in [
    ("update out of range", {"slot": {"load_mode": 1}, "index": 9}),
    ("delete out of range", {"index": 9, "delete": True}),
    ("no values and no delete", {}),
]:
    try:
        update_plan_slots(base, **kwargs)
        failures.append(f"{label}: expected ValueError, none raised")
        print(f"  FAIL {label} (no error raised)")
    except ValueError:
        print(f"  ok   rejected: {label}")

print()
if failures:
    print(f"{len(failures)} FAILURE(S):")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
print("all checks passed")
