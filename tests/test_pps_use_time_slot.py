#!/usr/bin/env python3
"""Mock test for the explicit `slot` targeting in set_pps_use_time() (A1763 PPS TOU).

Verifies the 1-based `slot` parameter added for explicit per-slot targeting:
- slot selects the target slot by index (start_hour/end_hour then only move the
  target slot's boundaries)
- out-of-range slot warns and falls back to slot 1
- no slot falls back to time-based / active-slot selection

Runs without a live account: get_device_attributes / set_device_attributes are
mocked, so this is a pure unit test of the slot-targeting logic.
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.resolve() / "src"))

from anker_solix_api.schedule import set_pps_use_time  # noqa: E402

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
    """Minimal AnkerSolixApi stand-in that mocks the two attribute calls."""

    def __init__(self):
        self._logger = _LOGGER

        class _Session:
            nickname = "mock"

        self.apisession = _Session()
        self.written: dict | None = None

    async def get_device_attributes(self, deviceSn, attributes, fromFile=False):
        return {"attributes": {"pps_use_time": json.dumps(PLAN)}}

    async def set_device_attributes(self, deviceSn, attributes, query_attributes=None, toFile=False):
        self.written = attributes["pps_use_time"]
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

    # out-of-range slot=99 warns and falls back to slot 1
    api = FakeApi()
    await set_pps_use_time(api, "SN", slot=99, tariff_type=2)
    assert _shapes(api) == [
        ("00:00", "09:00", 2),  # slot 1 now mid
        ("09:00", "19:00", 3),
        ("19:00", "24:00", 1),
    ], f"slot=99 fallback failed: {_shapes(api)}"

    # no slot: time-based / active-slot selection still works (writes something)
    api = FakeApi()
    await set_pps_use_time(api, "SN", tariff_type=2)
    assert api.written is not None, "no-slot active-slot write failed"

    _LOGGER.info("All PPS use-time slot targeting tests passed")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_slot_targeting())
