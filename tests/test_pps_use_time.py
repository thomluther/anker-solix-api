"""Mock tests for set_pps_use_time() (e.g. A1763 PPS TOU).

Verifies the the safety invariants:
- a price change upserts only the target segment's tariff price and preserves
  every other range and price entry
- a failed cloud write does not update the cached (local) plan

Runs without a live account: get_device_attributes / set_device_attributes are
mocked, so this is a pure unit test for the plan logic.
"""

import asyncio
import copy
from datetime import datetime
import json
import logging

from anker_solix_api.schedule import set_pps_use_time
from context import common

_LOGGER: logging.Logger = logging.getLogger(__name__)
_LOGGER.addHandler(logging.StreamHandler())
_LOGGER.setLevel(logging.DEBUG)  # enable for detailed API output
CONSOLE: logging.Logger = common.CONSOLE

SN = "1234567890"
DEFAULT_TYPE = 2
DEFAULT_PRICE = "0.00"

# Baseline plan: 3 slots (00-09 peak, 09-19 off, 19-24 peak)
PLAN = {
    "ranges": [
        {"start_time": "00:00", "end_time": "09:00", "type": 1},
        {"start_time": "09:00", "end_time": "19:00", "type": 3},
        {"start_time": "19:00", "end_time": "24:00", "type": 1},
    ],
    "prices": [{"price": "0.4", "type": 1}, {"price": "0.001", "type": 3}],
    "unit": "$",
    "reserve_power": 6,
}

PLAN_EMPTY = {
    "ranges": [],
    "prices": [],
    "unit": "$",
    "reserve_power": 10,
}

PLAN_FULL = {
    "ranges": [
        {"start_time": "00:00", "end_time": "09:00", "type": 2},
        {"start_time": "09:00", "end_time": "12:00", "type": 1},
        {"start_time": "12:00", "end_time": "14:00", "type": 3},
        {"start_time": "14:00", "end_time": "16:00", "type": 1},
        {"start_time": "16:00", "end_time": "20:00", "type": 2},
        {"start_time": "20:00", "end_time": "24:00", "type": 3},
    ],
    "prices": [
        {"price": "0.4", "type": 1},
        {"price": "0.2", "type": 2},
        {"price": "0.1", "type": 3},
    ],
    "unit": "€",
    "reserve_power": 10,
}


class FakeApi:
    """Minimal AnkerSolixApi stand-in that mocks the two attribute calls.

    Maintains a `cache` of the device's current pps_use_time plan to mirror the
    real Api's behavior: the cache is only updated after a *successful* cloud
    write, so a failed write leaves the cached (local) state unchanged.
    """

    def __init__(self, fail_write: bool = False) -> None:
        """Init the class."""
        self._logger = _LOGGER

        class _Session:
            nickname = "mock"

        self.apisession = _Session()
        self.fail_write = fail_write
        self.written: dict = {}
        self.devices: dict = {SN: {}}
        self.account: dict = {"default_currency": {"symbol": "€"}}
        self.write_called = False
        # the device's current plan (the "cache" the real Api maintains)
        self.plan = copy.deepcopy(PLAN)

    def change_plan(self, plan: dict) -> None:
        """Change the fake api plan and cache for new tests."""
        self.plan = copy.deepcopy(plan)
        self.devices[SN].update({"pps_use_time": json.dumps(self.plan)})

    async def get_device_attributes(self, deviceSn, attributes, fromFile=False) -> dict:
        """Fake device attributes query."""
        resp = {"attributes": {"pps_use_time": json.dumps(self.plan)}}
        self.devices[SN].update(resp.get("attributes", {}))
        return resp

    async def set_device_attributes(
        self, deviceSn, attributes, query_attributes=None, toFile=False
    ) -> bool | dict:
        """Fake device attributes set."""
        self.write_called = True
        if self.fail_write:
            # cloud write failed: the cache is NOT updated
            return False
        self.written = attributes["pps_use_time"]
        self.plan = json.loads(self.written)
        return await self.get_device_attributes(deviceSn, attributes, fromFile=toFile)


async def test_price_write_preserves_other_ranges_and_prices(api: FakeApi) -> None:
    """Test price change does not modify other parts."""
    # Changing a slot's tariff price upserts only that tariff type's price and
    # preserves every other range and price entry (no rebuild/normalize).
    await set_pps_use_time(api, SN, start_hour=10, tariff_price="0.05")
    plan = json.loads(api.written)
    # ranges are unchanged
    assert plan["ranges"] == PLAN["ranges"], f"ranges changed: {plan['ranges']}"
    # slot 2 is type 3 (off); its price was updated
    prices = {p["type"]: p["price"] for p in plan["prices"]}
    assert prices[3] == "0.05", f"slot 2 (type 3) price not updated: {prices}"
    # the other price entry (type 1) is preserved verbatim
    assert prices[1] == "0.4", f"type 1 price not preserved: {prices}"
    CONSOLE.info("Price-preservation test passed")


async def test_range_split(api: FakeApi) -> None:
    """Test price change does not modify other parts."""
    # Changing a slot's tariff price upserts only that tariff type's price and
    # preserves every other range and price entry (no rebuild/normalize).
    await set_pps_use_time(api, SN, start_hour=10, end_hour=12, tariff_type=2)
    plan = json.loads(api.written)
    # ranges are split
    assert len(plan["ranges"]) > len(PLAN["ranges"]), (
        f"No range split: {plan['ranges']}"
    )
    # slot 3 is new type, should have default price adjusted to min lower price
    prices = {p["type"]: p["price"] for p in plan["prices"]}
    assert prices[3] == "0.05", f"slot 3 (type 2) price not default: {prices}"
    # Test variable limit does not allow more splits
    await set_pps_use_time(
        api, SN, start_hour=12, end_hour=14, tariff_type=1, max_ranges=5
    )
    plan = json.loads(api.written)
    assert len(plan["ranges"]) == 5, "Range split ignored max ranges of 5"
    # Test split ignored if same tariff type is used
    await set_pps_use_time(
        api, SN, start_hour=14, end_hour=16, tariff_type=3, max_ranges=5
    )
    plan = json.loads(api.written)
    ranges = plan["ranges"]
    assert len(ranges) == 5, "Range split although same tariff type used"
    assert ranges[3]["start_time"] == "12:00", (
        f"Wrong start time for slot 4: {ranges[3]} but expected 12:00"
    )
    assert ranges[3]["end_time"] == "19:00", (
        f"Wrong end time for slot 4: {ranges[3]} but expected 19:00"
    )
    # Test first slot split
    await set_pps_use_time(
        api,
        SN,
        start_hour=0,
        end_hour=6,
        tariff_type=2,
        tariff_price=0.40,
        currency="EUR",
    )
    plan = json.loads(api.written)
    ranges = plan["ranges"]
    prices = {p["type"]: p["price"] for p in plan["prices"]}
    assert len(ranges) == 6, "First range was not split"
    assert ranges[1]["start_time"] == "06:00", (
        f"Wrong start time for slot 2: {ranges[1]} but expected 06:00"
    )
    assert prices[2] == "0.4", (
        f"slot 1 (type 2) price not changed: {prices} but expected 0.4"
    )
    assert plan["unit"] == "EUR", f"Unit not changed: {plan['unit']} but expected EUR"
    # Test first slot expanded
    await set_pps_use_time(api, SN, start_hour=0, end_hour=8)
    plan = json.loads(api.written)
    ranges = plan["ranges"]
    prices = {p["type"]: p["price"] for p in plan["prices"]}
    assert len(ranges) == 6, "Slot count was changed"
    assert ranges[1]["start_time"] == "08:00", (
        f"Wrong start time for slot 2: {ranges[1]} but expected 08:00"
    )
    # Test first slot expanded and merged 2nd slot
    await set_pps_use_time(api, SN, start_hour=0, end_hour=11, tariff_type=1)
    plan = json.loads(api.written)
    ranges = plan["ranges"]
    prices = {p["type"]: p["price"] for p in plan["prices"]}
    assert len(ranges) == 4, "Slot not merged"
    assert ranges[1]["start_time"] == "11:00", (
        f"Wrong start time for slot 2: {ranges[1]} but expected 11:00"
    )
    CONSOLE.info("Range split test passed")


async def test_failed_write_does_not_update_cache(api: FakeApi) -> None:
    """Test failed write does not change cache."""
    # A failed cloud write must not update the cached (local) plan.
    api.fail_write = True
    original_cache = copy.deepcopy(api.devices.get(SN, {}).get("pps_use_time", {}))
    result = await set_pps_use_time(api, SN, tariff_price="0.3")
    # the write failed, so the result is a failure indicator (False)
    assert result is False, f"failed write should return False, got {result!r}"
    # the cached plan is unchanged (no optimistic local state)
    assert api.devices.get(SN, {}).get("pps_use_time", {}) == original_cache, (
        "failed write must not update the cache"
    )
    api.fail_write = False
    CONSOLE.info("Failed-write cache test passed")


async def test_backup_reserve(api: FakeApi) -> None:
    """Test backup reserve."""
    # The backup reserve must be adjusted within allowed range based on min and max soc
    await set_pps_use_time(api, SN, backup_soc=5)
    plan = json.loads(api.written)
    assert plan["reserve_power"] == 10, (
        f"Reserve changed: {plan['reserve_power']} but expected 10"
    )
    await set_pps_use_time(api, SN, backup_soc=15)
    plan = json.loads(api.written)
    assert plan["reserve_power"] == 15, (
        f"Reserve not changed: {plan['reserve_power']} but expected 15"
    )
    await set_pps_use_time(api, SN, backup_soc=99)
    plan = json.loads(api.written)
    assert plan["reserve_power"] == 95, (
        f"Reserve exceeded max soc: {plan['reserve_power']} but expected 95"
    )
    # decrease max soc but do not change reserve
    api.devices[SN]["mqtt_data"] = {"max_soc": 85, "power_cutoff": 10}
    await set_pps_use_time(api, SN, tariff_type=2, tariff_price=0.25)
    plan = json.loads(api.written)
    prices = {p["type"]: p["price"] for p in plan["prices"]}
    assert plan["reserve_power"] == 85, (
        f"Reserve exceeded max soc: {plan['reserve_power']} but expected 85"
    )
    assert prices[2] == "0.25", f"Type 2 price not changed: {prices} but expected 0.25"
    # test backup soc adjustment if below min soc
    await set_pps_use_time(api, SN, backup_soc=1)
    plan = json.loads(api.written)
    assert plan["reserve_power"] == 15, (
        f"Reserve below min soc: {plan['reserve_power']} but expected 15"
    )
    CONSOLE.info("All backup reserve tests passed")


async def test_price_changes(api: FakeApi) -> None:
    """Test price and tariff changes."""
    # Test correct interval is selected with given start time (first with type 1) and change type 1 price changed but not interval times
    await set_pps_use_time(api, SN, start_hour=10, tariff_price=0.44)
    plan = json.loads(api.written)
    ranges = plan["ranges"]
    prices = {p["type"]: p["price"] for p in plan["prices"]}
    assert len(ranges) == 4, "Slot split even if no full range specified"
    assert ranges[0]["end_time"] == "11:00", (
        f"Wrong start time for slot 1: {ranges[0]} but expected 11:00"
    )
    assert prices[1] == "0.44", f"Type 1 price not changed: {prices} but expected 0.44"
    # Test correct interval is selected with given end time (third with type 3) and change type 3 price changed but not interval times
    await set_pps_use_time(api, SN, end_hour=18, tariff_price=0.03)
    plan = json.loads(api.written)
    ranges = plan["ranges"]
    prices = {p["type"]: p["price"] for p in plan["prices"]}
    assert len(ranges) == 4, "Slot split even if no full range specified"
    assert ranges[2]["end_time"] == "19:00", (
        f"Wrong end time for slot 3: {ranges[2]} but expected 19:00"
    )
    assert prices[3] == "0.03", f"Type 3 price not changed: {prices} but expected 0.03"
    # Test actual interval is selected and its type is changed (this may change slot number by tariff mergers)
    await set_pps_use_time(api, SN, tariff_type=2)
    plan = json.loads(api.written)
    ranges = plan["ranges"]
    prices = {p["type"]: p["price"] for p in plan["prices"]}
    now_hour = f"{datetime.now().hour:02d}:00"
    slot = next(
        iter(slot for slot in ranges if str(slot.get("end_time", "")) > now_hour), {}
    )
    assert 3 <= len(ranges) <= 4, (
        f"Unexpcted slot split or merge even if no full range specified; {ranges}"
    )
    assert slot.get("start_time") <= now_hour and slot.get("end_time") >= now_hour, (
        f"Did not select correct slot of actual hour '{now_hour}': {slot}"
    )
    assert slot.get("type") == 2, f"Actual slot tariff was not changed to 2: {slot}"
    # Test only tariff price is changes without plan changes
    old_ranges = ranges.copy()
    await set_pps_use_time(api, SN, tariff_type=2, tariff_price=0.21)
    plan = json.loads(api.written)
    ranges = plan["ranges"]
    prices = {p["type"]: p["price"] for p in plan["prices"]}
    assert old_ranges == ranges, (
        f"tariff type change without times must not change the ranges: {ranges}"
    )
    assert prices[2] == "0.21", f"Type 2 price not changed: {prices} but expected 0.21"
    CONSOLE.info("All price and tariff tests passed")


async def test_plan_deletion_options(api: FakeApi) -> None:
    """Test plan deletion options."""
    # Test tariff slot deletion scope to merge same remaining tariff slots and remove the price type
    api.change_plan(PLAN_FULL)
    await set_pps_use_time(api, SN, delete=True, tariff_type=3)
    plan = json.loads(api.written)
    ranges = plan["ranges"]
    prices = {p["type"]: p["price"] for p in plan["prices"]}
    assert len(ranges) == 3, (
        f"Slot deletion and merge did not work for type 3 removal: {ranges}"
    )
    assert ranges[1]["start_time"] == "09:00" and ranges[1]["end_time"] == "16:00", (
        f"Adjacent slots with type 1 did not merge: {ranges}"
    )
    assert prices.get(3) is None, f"Type 3 price not deleted: {prices}"
    assert len(prices) == 2, f"Other price types were changed unexpectedly: {prices}"
    # Test slot deletion option, test hour definition as string
    api.change_plan(PLAN_FULL)
    await set_pps_use_time(api, SN, delete=True, start_hour="17")
    plan = json.loads(api.written)
    ranges = plan["ranges"]
    prices = {p["type"]: p["price"] for p in plan["prices"]}
    assert len(ranges) == 5, (
        f"Slot deletion and merge did not work for slot hour 17 removal: {ranges}"
    )
    assert len(prices) == 3, f"Price types were changed unexpectedly: {prices}"
    # Test next slot deletion option, test hour definition as string and removal of type 2 prices
    await set_pps_use_time(api, SN, delete=True, start_hour="3")
    plan = json.loads(api.written)
    ranges = plan["ranges"]
    prices = {p["type"]: p["price"] for p in plan["prices"]}
    assert len(ranges) == 4, (
        f"Slot deletion and merge did not work for slot hour 3 removal: {ranges}"
    )
    assert prices.get(2) is None, f"Type 2 price not deleted: {prices}"
    assert len(prices) == 2, f"Other price types were changed unexpectedly: {prices}"
    # Test plan deletion option
    await set_pps_use_time(api, SN, delete=True)
    plan = json.loads(api.written)
    ranges = plan.get("ranges", [])
    prices = {p["type"]: p["price"] for p in plan["prices"]}
    assert len(ranges) == 1, f"Slot deletion did not work for plan removal: {ranges}"
    assert ranges[0]["start_time"] == "00:00" and ranges[0]["end_time"] == "24:00", (
        f"Default time range is not applied for plan deletion: {ranges}"
    )
    assert len(prices) == 1, f"Price deletion did not work for plan removal: {prices}"
    assert prices.get(DEFAULT_TYPE) == DEFAULT_PRICE, (
        f"Default type {DEFAULT_TYPE} or default price {DEFAULT_PRICE} not applied: {prices}"
    )
    CONSOLE.info("Remaining plan after deletion: %s", plan)
    CONSOLE.info("All plan deletion tests passed")


async def test_empty_plan_changes(api: FakeApi) -> None:
    """Test empty plan changes."""
    # Test full initial range is created with defaults and given type and price
    api.change_plan(PLAN_EMPTY)
    await set_pps_use_time(
        api, SN, start_hour=10, end_hour=12, tariff_type=1, tariff_price=0.44
    )
    plan = json.loads(api.written)
    ranges = plan["ranges"]
    prices = {p["type"]: p["price"] for p in plan["prices"]}
    assert len(ranges) == 3, f"Plan gaps are not filled: {ranges}"
    assert ranges[1].get("type") == 1, f"Slot 2 tariff was not set to 1: {ranges}"
    assert ranges[0]["start_time"] == "00:00", (
        f"Wrong start time for slot 1: {ranges[0]} but expected 00:00"
    )
    assert ranges[2]["end_time"] == "24:00", (
        f"Wrong end time for slot 3: {ranges[2]} but expected 24:00"
    )
    assert prices[1] == "0.44", f"Type 1 price not changed: {prices} but expected 0.44"
    assert prices.get(DEFAULT_TYPE) == DEFAULT_PRICE, (
        f"Default type {DEFAULT_TYPE} price not default: {prices} but expected {DEFAULT_PRICE}"
    )
    # Test full range is created with start range specification for different type and price
    api.change_plan(PLAN_EMPTY)
    await set_pps_use_time(
        api, SN, start_hour=0, end_hour=12, tariff_type=1, tariff_price=0.41
    )
    plan = json.loads(api.written)
    ranges = plan["ranges"]
    prices = {p["type"]: p["price"] for p in plan["prices"]}
    assert len(ranges) == 2, f"Plan gaps are not filled: {ranges}"
    assert ranges[0].get("type") == 1, f"Slot 1 tariff was not set to 1: {ranges}"
    assert ranges[1].get("type") == DEFAULT_TYPE, (
        f"Slot 2 tariff was not set to default {DEFAULT_TYPE}: {ranges}"
    )
    assert ranges[0]["end_time"] == "12:00", (
        f"Wrong end time for slot 1: {ranges[0]} but expected 12:00"
    )
    assert ranges[1]["start_time"] == "12:00", (
        f"Wrong start time for slot 2: {ranges[0]} but expected 12:00"
    )
    assert ranges[1]["end_time"] == "24:00", (
        f"Wrong end time for slot 2: {ranges[0]} but expected 24:00"
    )
    assert prices[1] == "0.41", f"Type 1 price not changed: {prices} but expected 0.41"
    assert prices.get(DEFAULT_TYPE) == "0.00", (
        f"Default type {DEFAULT_TYPE} price not default: {prices} but expected 0.00"
    )
    # Test full range is created, type is default since not specified times will be extended due to merge of same type slots
    api.change_plan(PLAN_EMPTY)
    await set_pps_use_time(api, SN, start_hour=0, end_hour=12, tariff_price=0.11)
    plan = json.loads(api.written)
    ranges = plan["ranges"]
    prices = {p["type"]: p["price"] for p in plan["prices"]}
    assert len(ranges) == 1, f"Expected full range slots are created: {ranges}"
    assert ranges[0].get("type") == DEFAULT_TYPE, (
        f"Slot 1 tariff did not use default type {DEFAULT_TYPE}: {ranges}"
    )
    assert ranges[0]["start_time"] == "00:00", (
        f"Wrong start time for slot 1: {ranges[0]} but expected 00:00"
    )
    assert ranges[0]["end_time"] == "24:00", (
        f"Wrong end time for slot 1: {ranges[0]} but expected 24:00"
    )
    assert prices.get(DEFAULT_TYPE) == "0.11", (
        f"Default type {DEFAULT_TYPE} price not changed: {prices} but expected 0.11"
    )
    CONSOLE.info("All empty plan tests passed")


async def main() -> None:
    """Run the test."""
    api = FakeApi()
    api.devices[SN]["mqtt_data"] = {"max_soc": 95, "power_cutoff": 5}
    api.change_plan(PLAN)
    await test_price_write_preserves_other_ranges_and_prices(api)
    await test_range_split(api)
    await test_backup_reserve(api)
    await test_price_changes(api)
    await test_failed_write_does_not_update_cache(api)
    await test_plan_deletion_options(api)
    await test_empty_plan_changes(api)
    CONSOLE.info("All PPS use-time tests passed")


if __name__ == "__main__":
    asyncio.run(main())
