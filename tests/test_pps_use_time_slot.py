#!/usr/bin/env python3
"""Mock tests for slot targeting and price mutation in set_pps_use_time() (A1763 PPS TOU).

Verifies the 1-based `slot` parameter and the safety invariants:
- slot selects the target slot by index (start_hour/end_hour then only move the
  target slot's boundaries)
- an explicitly out-of-range slot raises ValueError and writes nothing (it never
  silently falls back to slot 1)
- no slot falls back to time-based / active-slot selection
- a price change upserts only the target segment's tariff price and preserves
  every other range and price entry
- a failed cloud write does not update the cached (local) plan

Runs without a live account: get_device_attributes / set_device_attributes are
mocked, so this is a pure unit test of the slot-targeting / price-mutation logic.
"""

import asyncio
import copy
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.resolve() / "src"))

from anker_solix_api.schedule import (  # noqa: E402
    set_pps_use_time,
    validate_pps_schedule,
)

_LOGGER = logging.getLogger(__name__)

# Baseline plan: 3 slots (00-09 peak, 09-19 off, 19-24 peak)
PLAN = {
    "ranges": [
        {"start_time": "00:00", "end_time": "09:00", "type": 1},
        {"start_time": "09:00", "end_time": "19:00", "type": 3},
        {"start_time": "19:00", "end_time": "24:00", "type": 1},
    ],
    "prices": [{"price": "0.2", "type": 1}, {"price": "0.001", "type": 3}],
    "unit": "$",
    "reserve_power": 6,
}


class FakeApi:
    """Minimal AnkerSolixApi stand-in that mocks the two attribute calls.

    Maintains a `cache` of the device's current pps_use_time plan to mirror the
    real Api's behavior: the cache is only updated after a *successful* cloud
    write, so a failed write leaves the cached (local) state unchanged.
    """

    def __init__(self, fail_write: bool = False):
        self._logger = _LOGGER

        class _Session:
            nickname = "mock"

        self.apisession = _Session()
        self.fail_write = fail_write
        self.written: dict | None = None
        self.write_called = False
        # the device's current plan (the "cache" the real Api maintains)
        self.cache = copy.deepcopy(PLAN)

    async def get_device_attributes(self, deviceSn, attributes, fromFile=False):
        return {"attributes": {"pps_use_time": json.dumps(self.cache)}}

    async def set_device_attributes(
        self, deviceSn, attributes, query_attributes=None, toFile=False
    ):
        self.write_called = True
        if self.fail_write:
            # cloud write failed: the cache is NOT updated
            return False
        self.written = attributes["pps_use_time"]
        self.cache = json.loads(attributes["pps_use_time"])
        return True


def _shapes(api: FakeApi) -> list:
    """The (start, end, type) shape of the written plan's slots."""
    plan = json.loads(api.written) if api.written else None
    if not plan:
        return []
    return [(r["start_time"], r["end_time"], r["type"]) for r in plan["ranges"]]


def _prices(api: FakeApi) -> dict:
    plan = json.loads(api.written) if api.written else None
    return {p["type"]: p["price"] for p in (plan or {}).get("prices", [])}


async def test_slot_targeting() -> None:
    # slot=2 (1-based) targets the 2nd slot (09-19, off); set its tariff to peak
    api = FakeApi()
    await set_pps_use_time(api, "SN", slot=2, tariff_type=1)
    assert _shapes(api) == [
        ("00:00", "09:00", 1),
        ("09:00", "19:00", 1),  # 2nd slot now peak
        ("19:00", "24:00", 1),
    ], f"slot=2 tariff=1 failed: {_shapes(api)}"

    # slot=3 targets the 3rd slot (19-24, peak); set its price to 0.5
    api = FakeApi()
    await set_pps_use_time(api, "SN", slot=3, tariff_price="0.5")
    assert _prices(api)[1] == "0.5", f"slot=3 price=0.5 failed: {_prices(api)}"

    # slot=1 end_hour=5 moves the 1st slot's end to 05:00 (2nd slot start follows)
    api = FakeApi()
    await set_pps_use_time(api, "SN", slot=1, end_hour=5)
    assert _shapes(api) == [
        ("00:00", "05:00", 1),
        ("05:00", "19:00", 3),
        ("19:00", "24:00", 1),
    ], f"slot=1 end=5 failed: {_shapes(api)}"

    # no slot: time-based / active-slot selection still works (writes something)
    api = FakeApi()
    await set_pps_use_time(api, "SN", tariff_type=2)
    assert api.written is not None, "no-slot active-slot write failed"

    _LOGGER.info("All PPS use-time slot targeting tests passed")


async def test_invalid_slot_does_not_modify_plan() -> None:
    # an explicitly out-of-range slot must raise and write nothing (no silent
    # fallback to slot 1)
    api = FakeApi()
    try:
        await set_pps_use_time(api, "SN", slot=99, tariff_price="0.3")
        raise AssertionError("slot=99 should raise ValueError")
    except ValueError:
        pass
    assert not api.write_called, "invalid slot must not write"
    assert api.cache == PLAN, "invalid slot must not modify the plan"
    _LOGGER.info("Invalid-slot rejection test passed")


async def test_price_write_preserves_other_ranges_and_prices() -> None:
    # Changing a slot's tariff price upserts only that tariff type's price and
    # preserves every other range and price entry (no rebuild/normalize).
    api = FakeApi()
    await set_pps_use_time(api, "SN", slot=2, tariff_price="0.3")
    plan = json.loads(api.written)
    # ranges are unchanged
    assert plan["ranges"] == PLAN["ranges"], f"ranges changed: {plan['ranges']}"
    # slot 2 is type 3 (off); its price was updated to 0.3
    prices = {p["type"]: p["price"] for p in plan["prices"]}
    assert prices[3] == "0.3", f"slot 2 (type 3) price not updated: {prices}"
    # the other price entry (type 1) is preserved verbatim
    assert prices[1] == "0.2", f"type 1 price not preserved: {prices}"
    _LOGGER.info("Price-preservation test passed")


async def test_failed_write_does_not_update_cache() -> None:
    # A failed cloud write must not update the cached (local) plan.
    api = FakeApi(fail_write=True)
    original_cache = copy.deepcopy(api.cache)
    result = await set_pps_use_time(api, "SN", slot=2, tariff_price="0.3")
    # the write failed, so the result is a failure indicator (False)
    assert result is False, f"failed write should return False, got {result!r}"
    # the cached plan is unchanged (no optimistic local state)
    assert api.cache == original_cache, "failed write must not update the cache"
    _LOGGER.info("Failed-write cache test passed")


def test_validator_edge_cases() -> None:
    # a 6-slot schedule tiling 00:00-24:00 is valid
    six = [
        {"start_time": "00:00", "end_time": "04:00", "type": 1},
        {"start_time": "04:00", "end_time": "08:00", "type": 3},
        {"start_time": "08:00", "end_time": "12:00", "type": 1},
        {"start_time": "12:00", "end_time": "16:00", "type": 2},
        {"start_time": "16:00", "end_time": "20:00", "type": 3},
        {"start_time": "20:00", "end_time": "24:00", "type": 1},
    ]
    assert validate_pps_schedule(six, None) == [], "6-slot schedule must be valid"

    # 7 slots exceeds the device limit
    seven = six + [{"start_time": "24:00", "end_time": "24:00", "type": 1}]
    assert validate_pps_schedule(seven, None) != [], "7 slots must be rejected"

    # a gap between slots is rejected
    gapped = [
        {"start_time": "00:00", "end_time": "06:00", "type": 1},
        {"start_time": "07:00", "end_time": "24:00", "type": 3},
    ]
    assert validate_pps_schedule(gapped, None) != [], "gap must be rejected"

    # a plan that does not start at 00:00 is rejected
    no_midnight = [
        {"start_time": "01:00", "end_time": "24:00", "type": 1},
    ]
    assert validate_pps_schedule(no_midnight, None) != [], "must start at 00:00"

    # a well-formed 1-slot plan tiling the whole day is valid
    one = [{"start_time": "00:00", "end_time": "24:00", "type": 3}]
    assert validate_pps_schedule(one, None) == [], "1-slot schedule must be valid"

    _LOGGER.info("Validator edge-case tests passed")


async def main() -> None:
    await test_slot_targeting()
    await test_invalid_slot_does_not_modify_plan()
    await test_price_write_preserves_other_ranges_and_prices()
    await test_failed_write_does_not_update_cache()
    test_validator_edge_cases()
    _LOGGER.info("All PPS use-time tests passed")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
