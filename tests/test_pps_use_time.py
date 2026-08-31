#!/usr/bin/env python3
"""Live round-trip test for the flexible set_pps_use_time() helper (A1763 PPS TOU).

Demonstrates the helper flexibility requested in issue #326:
  - individual parameter updates that modify the active or a given slot
    (tariff by int or by SolixTariffTypes name, price, start/end boundary moves
    with neighbor auto-adjust, slot delete with gap fill)
  - whole-slot plan replacement via ranges
  - plan-level reserve_power
  - plan validation (an invalid plan is rejected without writing)

Each step mutates, reads back, verifies, then restores the exact baseline, so
the device always ends at its original plan (safe to run against a live unit).
Set FOLDER to run against exported files instead of a live account.
"""

import asyncio
import json
import logging
from pathlib import Path  # noqa: F401
import traceback

from aiohttp import ClientSession
from anker_solix_api.api import AnkerSolixApi
from context import common

_LOGGER: logging.Logger = logging.getLogger(__name__)
CONSOLE: logging.Logger = common.CONSOLE
# Specify FOLDER with a system export including pps_use_time for testing from files
# FOLDER = Path(__file__).parent / "exports" / "Mqtt_C1000_Gen2"
FOLDER = None


def _plan(data: dict) -> dict:
    """Extract the pps_use_time plan dict from a get_device_attributes response."""
    pps = (data.get("attributes") or {}).get("pps_use_time")
    if isinstance(pps, str):
        pps = json.loads(pps)
    return pps if isinstance(pps, dict) else {}


def _shape(plan: dict) -> list:
    return [(r.get("start_time"), r.get("end_time"), r.get("type")) for r in plan.get("ranges", [])]


def _contiguous(plan: dict) -> bool:
    ranges = plan.get("ranges") or []
    if not ranges:
        return False
    if ranges[0].get("start_time") != "00:00" or ranges[-1].get("end_time") != "24:00":
        return False
    for i in range(len(ranges) - 1):
        if ranges[i].get("end_time") != ranges[i + 1].get("start_time"):
            return False
    for r in ranges:
        if not (r.get("start_time") and r.get("end_time") and r["start_time"] < r["end_time"]):
            return False
    return True


def _hhmm_to_min(value: str) -> int:
    hour, minute = value.split(":")
    return int(hour) * 60 + int(minute)


def _min_to_hhmm(minutes: int) -> str:
    minutes = max(0, min(1440, minutes))
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


class _Reporter:
    def __init__(self) -> None:
        self.passed = 0
        self.failed = 0

    def ok(self, label: str) -> None:
        self.passed += 1
        CONSOLE.info(f"    [PASS] {label}")

    def fail(self, label: str, detail: str = "") -> None:
        self.failed += 1
        CONSOLE.info(f"    [FAIL] {label} {detail}")


async def test_pps_use_time() -> None:  # noqa: C901
    """Run the safe set_pps_use_time round-trip against an A1763 device."""
    async with ClientSession() as websession:
        myapi = AnkerSolixApi(
            common.user(), common.password(), common.country(), websession, _LOGGER
        )
        use_file = bool(FOLDER)
        if use_file:
            myapi.testDir(FOLDER)

        await myapi.update_sites(fromFile=use_file)
        await myapi.update_device_details(fromFile=use_file)

        # find an A1763 (C1000 Gen 2) device
        device_sn = None
        for sn, device in myapi.devices.items():
            if device.get("device_pn") in ["A1761", "A1763", "A1765"]:
                device_sn = sn
                CONSOLE.info(f"Found C1000X device: {sn}")
                break
        if not device_sn:
            CONSOLE.info("No C1000X device found")
            return

        rep = _Reporter()
        toFile = use_file

        # read the baseline plan
        base_data = await myapi.get_device_attributes(
            deviceSn=device_sn, attributes=["pps_use_time"], fromFile=toFile
        )
        baseline = _plan(base_data)
        if not baseline.get("ranges"):
            CONSOLE.info("Device has no pps_use_time plan; nothing to test")
            return
        CONSOLE.info(f"Baseline plan: {_shape(baseline)}")
        baseline_json = json.dumps(baseline, separators=(",", ":"))

        async def restore() -> bool:
            """Write the exact baseline back and confirm it round-trips."""
            await myapi.set_device_attributes(
                deviceSn=device_sn,
                attributes={"pps_use_time": baseline_json},
                query_attributes=["pps_use_time"],
                toFile=toFile,
            )
            check = _plan(
                await myapi.get_device_attributes(
                    deviceSn=device_sn, attributes=["pps_use_time"], fromFile=toFile
                )
            )
            return check == baseline

        async def step(label: str, kwargs: dict, verify) -> None:
            """Apply a mutation, verify the result, then restore the baseline."""
            try:
                await myapi.set_pps_use_time(deviceSn=device_sn, toFile=toFile, **kwargs)
                plan = _plan(
                    await myapi.get_device_attributes(
                        deviceSn=device_sn, attributes=["pps_use_time"], fromFile=toFile
                    )
                )
                if verify(plan):
                    rep.ok(label)
                else:
                    rep.fail(label, f"got {_shape(plan)}")
            except Exception as err:  # noqa: BLE001
                rep.fail(label, f"error: {err}")
            finally:
                if not await restore():
                    rep.fail(f"{label}: baseline restore", "baseline not restored")

        ranges = baseline.get("ranges") or []
        n = len(ranges)

        # --- individual parameter updates (active / given slot) ---
        # 1. active-slot tariff (no time given) -> the slot containing now
        await step(
            "active-slot tariff (int)",
            {"tariff_type": 2},
            lambda p: _contiguous(p) and any(r.get("type") == 2 for r in p["ranges"]),
        )
        # 2. given-slot tariff by SolixTariffTypes name (slot at the first boundary)
        if n >= 2:
            await step(
                "given-slot tariff (name 'off_peak')",
                {"start_hour": ranges[0]["start_time"], "tariff_type": "off_peak"},
                lambda p: _contiguous(p) and p["ranges"][0].get("type") == 3,
            )
        # 3. given-slot price
        if n >= 2:
            await step(
                "given-slot price",
                {"start_hour": ranges[0]["start_time"], "tariff_price": 0.123},
                lambda p: _contiguous(p)
                and any(str(pr.get("price")).startswith("0.123") for pr in p.get("prices", [])),
            )
        # 4. move an interior boundary (start of slot 1) to the midpoint of slot 1,
        #    exercising the neighbor auto-adjust (slot 0 end follows)
        if n >= 3:
            s1_start = _hhmm_to_min(ranges[1]["start_time"])
            s1_end = _hhmm_to_min(ranges[1]["end_time"])
            new_start = _min_to_hhmm((s1_start + s1_end) // 2)
            await step(
                "move interior boundary (start_hour, neighbor auto-adjust)",
                {"start_hour": new_start},
                lambda p: _contiguous(p)
                and len(p["ranges"]) == n
                and p["ranges"][1].get("start_time") == new_start
                and p["ranges"][0].get("end_time") == new_start,
            )
        # 5. slot delete with gap fill (only when there is more than one slot)
        if n >= 2:
            await step(
                "slot delete (gap fill)",
                {"start_hour": ranges[0]["start_time"], "delete": True},
                lambda p: _contiguous(p) and len(p["ranges"]) == n - 1,
            )
        # 6. plan-level reserve_power (ranges untouched)
        await step(
            "reserve_power (plan-level)",
            {"reserve_power": 10},
            lambda p: p.get("reserve_power") == 10 and _shape(p) == _shape(baseline),
        )

        # --- whole-slot plan replacement via ranges ---
        if n >= 2:
            # 7. full replacement with a valid 2-slot plan (then restored)
            two = [
                {"start_time": "00:00", "end_time": "12:00", "type": 1},
                {"start_time": "12:00", "end_time": "24:00", "type": 3},
            ]
            await step(
                "full-replacement ranges (valid 2-slot)",
                {"ranges": two},
                lambda p: p.get("ranges") == two and _contiguous(p),
            )

        # --- validation: an invalid plan must be rejected without writing ---
        await step(
            "invalid plan rejected (gap, no write)",
            {"ranges": [
                {"start_time": "00:00", "end_time": "09:00", "type": 1},
                {"start_time": "10:00", "end_time": "24:00", "type": 3},  # gap 09-10
            ]},
            lambda p: p == baseline,  # rejected -> plan unchanged
        )

        # --- final: confirm the device is back at the exact baseline ---
        final = _plan(
            await myapi.get_device_attributes(
                deviceSn=device_sn, attributes=["pps_use_time"], fromFile=toFile
            )
        )
        if final == baseline:
            rep.ok("final state == baseline")
        else:
            rep.fail("final state == baseline", f"got {_shape(final)}")

        CONSOLE.info(
            f"\nRESULT: {rep.passed} passed, {rep.failed} failed"
            + ("" if rep.failed == 0 else "  <-- CHECK FAILURES")
        )
        if rep.failed:
            raise RuntimeError(f"{rep.failed} step(s) failed")


if __name__ == "__main__":
    try:
        asyncio.run(test_pps_use_time(), debug=False)
    except Exception as err:  # noqa: BLE001
        CONSOLE.info(f"{type(err)}: {err}")
        traceback.print_exc()