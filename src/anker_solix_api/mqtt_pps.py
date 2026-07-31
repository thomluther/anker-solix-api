"""MQTT device control methods for Anker Solix Portable Power Stations.

This module contains control methods specific to portable power stations (PPS).
These methods provide comprehensive device control via MQTT commands.
"""

from __future__ import annotations  # noqa: TID251

from itertools import pairwise
from typing import TYPE_CHECKING

from .mqtt_device import SolixMqttDevice
from .mqttcmdmap import SolixMqttCommands

if TYPE_CHECKING:
    from .api import AnkerSolixApi

# Define supported Models for this class
MODELS = {
    "A1722",  # SOLIX C300 AC
    "A1723",  # SOLIX C300X AC
    "A1725",  # SOLIX C200(X)
    "A1726",  # SOLIX C300 DC
    "A1727",  # SOLIX C200 DC
    "A1728",  # SOLIX C300X DC
    "A1729",  # SOLIX C200X DC
    "A1753",  # SOLIX C800
    "A1754",  # SOLIX C800 Plus
    "A1755",  # SOLIX C800X
    "A1761",  # SOLIX C1000(X)
    "A1762",  # Portable Power Station 1000
    "A1763",  # SOLIX C1000 Gen 2
    "A1765",  # SOLIX C1000X Gen 2
    "A1770",  # F1200 (Bluetooth)
    "A1771",  # F1200 (Bluetooth and WLAN)
    "A1772",  # SOLIX F1500
    "A1780",  # 767 PowerHouse (SOLIX F2000)
    "A1780P",  # 767 Power House (SOLIX F2000) with WLAN
    "A1781",  # SOLIX F2600
    "A1782",  # SOLIX F3000 Solarbank PPS
    "A1783",  # SOLIX C2000 Gen 2
    "A1790",  # SOLIX F3800 Power Panel PPS
    "A1790P",  # SOLIX F3800 Plus Power Panel PPS
    "AS220",  # SOLIX S2000
}

# Define possible controls per Model
# Those commands are only supported once also described for a message type in the model mapping (except realtime trigger)
# Models can be removed from a feature to block command usage even if message type is described in the mapping
FEATURES = {
    SolixMqttCommands.status_request: MODELS,
    SolixMqttCommands.realtime_trigger: MODELS,
    SolixMqttCommands.temp_unit_switch: MODELS,
    SolixMqttCommands.device_max_load: MODELS,
    SolixMqttCommands.device_timeout_minutes: MODELS,
    SolixMqttCommands.ac_charge_switch: MODELS,
    SolixMqttCommands.ac_charge_limit: MODELS,
    SolixMqttCommands.ac_output_switch: MODELS,
    SolixMqttCommands.ac_fast_charge_switch: MODELS,
    SolixMqttCommands.ac_output_mode_select: MODELS,
    SolixMqttCommands.ac_output_timeout_seconds: MODELS,
    SolixMqttCommands.ac_output_timeout_minutes: MODELS,
    SolixMqttCommands.dc_output_switch: MODELS,
    SolixMqttCommands.dc_12v_output_mode_select: MODELS,
    SolixMqttCommands.dc_output_timeout_seconds: MODELS,
    SolixMqttCommands.energy_saving_switch: MODELS,
    SolixMqttCommands.display_switch: MODELS,
    SolixMqttCommands.display_mode_select: MODELS,
    SolixMqttCommands.display_timeout_seconds: MODELS,
    SolixMqttCommands.light_switch: MODELS,
    SolixMqttCommands.light_mode_select: MODELS,
    SolixMqttCommands.port_memory_switch: MODELS,
    SolixMqttCommands.soc_limits: MODELS,
    SolixMqttCommands.pps_usage_mode: MODELS,
    SolixMqttCommands.silent_schedule: MODELS,
    # SolixMqttCommands.pps_custom_schedule: MODELS,
    # SolixMqttCommands.pps_tou_schedule: MODELS,
    # SolixMqttCommands.backup_soc: MODELS,
}


# ---------------------------------------------------------------------------
# S2000 (AS220) schedule plan helpers
#
# Pure conversion and modification helpers for the two PPS schedule structures,
# kept separate from the command dispatch so they can be reused by whichever
# service shape the plan changes end up using.
#
# Both structures are a struct field (type byte 0x04) followed by a variable
# number of slots, so neither can be described by a fixed byte map.
#
# TOU plan (message 0090, field a7):
#     04 | tariff_1 | (start, end, tariff_of_next_slot) * | (start, end)
#   Whole hours 0..24, one byte each. Each slot carries the FOLLOWING slot's
#   tariff, and the final slot omits it.
#
# Custom plan (message 0093, field a2):
#     04 | group_count | per group: weekday_mask, slot_count,
#          slot_count * (load_mode, start_minutes u16 LE, end_minutes u16 LE)
#   Minutes since midnight, so custom slots are not restricted to whole hours.
# ---------------------------------------------------------------------------

# Tariff codes shared by the TOU structure, consistent across captured plans.
TOU_TARIFFS: dict[str, int] = {"peak": 1, "midpeak": 2, "offpeak": 3}
# Load modes of the custom plan.
CUSTOM_LOAD_MODES: dict[str, int] = {"charge": 1, "discharge": 2}

# Device limits. Slot and group maxima are the largest values observed so far
# and are applied as guard rails; the device may accept fewer.
TOU_MAX_SLOTS: int = 24
CUSTOM_MAX_GROUPS: int = 2
CUSTOM_MAX_SLOTS: int = 5
# The TOU plan must tile the whole day: every captured plan runs 00:00 to 24:00
# with no gaps and no overlaps. The custom plan does allow gaps between slots.
TOU_DAY_START: int = 0
TOU_DAY_END: int = 24

WEEKDAYS: tuple[str, ...] = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


def _split_time(value: str | int) -> tuple[int, int]:
    """Return (hour, minute) for a "HH:MM" string or an hour integer."""
    if isinstance(value, int):
        return value, 0
    parts = str(value).split(":")
    try:
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0
    except ValueError as err:
        raise ValueError(f"Invalid time value: {value!r}") from err
    return hour, minute


def _tou_hour(value: str | int, field: str) -> int:
    """Validate and return a whole hour 0..24 for the TOU plan."""
    hour, minute = _split_time(value)
    if minute:
        raise ValueError(
            f"TOU plan {field} must be a whole hour, got {value!r} "
            "(the device encodes TOU boundaries as single hour bytes)"
        )
    if not TOU_DAY_START <= hour <= TOU_DAY_END:
        raise ValueError(
            f"TOU plan {field} must be {TOU_DAY_START}-{TOU_DAY_END}, got {hour}"
        )
    return hour


def _custom_minutes(value: str | int, field: str) -> int:
    """Validate and return minutes since midnight for the custom plan."""
    hour, minute = _split_time(value)
    total = hour * 60 + minute
    if not 0 <= total <= 1440:
        raise ValueError(
            f"Custom plan {field} must be within 00:00-24:00, got {value!r}"
        )
    return total


def _as_code(value: str | int | None, options: dict[str, int], field: str) -> int:
    """Return the numeric code for a name or an already numeric code."""
    if isinstance(value, str) and not value.isdigit():
        if (code := options.get(value.lower())) is None:
            raise ValueError(
                f"Unknown {field} {value!r}, expected one of {list(options)}"
            )
        return code
    code = int(value)
    if code not in options.values():
        raise ValueError(
            f"Invalid {field} code {code}, expected one of {sorted(options.values())}"
        )
    return code


def _hhmm(minutes: int) -> str:
    """Return minutes since midnight as "HH:MM"."""
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def encode_tou_plan(plan: dict) -> bytes:
    """Encode a TOU plan dict into the a7 struct value of message 0090.

    Args:
        plan: Plan as returned by SolixMqttDevicePps.get_tou_plan(), i.e.
            {"ranges": [{"start_time","end_time","tariff"}, ...]}

    Returns:
        bytes: the field value including the leading 0x04 struct type byte.

    Raises:
        ValueError: if the plan is empty, exceeds the slot limit, or does not
            tile 00:00-24:00 without gaps or overlaps.

    """
    ranges = list(plan.get("ranges") or [])
    if not ranges:
        raise ValueError("TOU plan requires at least one slot")
    if len(ranges) > TOU_MAX_SLOTS:
        raise ValueError(
            f"TOU plan supports at most {TOU_MAX_SLOTS} slots, got {len(ranges)}"
        )

    slots: list[tuple[int, int, int]] = []
    for idx, item in enumerate(ranges, 1):
        start = _tou_hour(item.get("start_time", 0), f"slot {idx} start_time")
        end = _tou_hour(item.get("end_time", 0), f"slot {idx} end_time")
        if end <= start:
            raise ValueError(f"TOU plan slot {idx} end_time must be after start_time")
        slots.append((start, end, _as_code(item.get("tariff"), TOU_TARIFFS, "tariff")))

    slots.sort(key=lambda s: s[0])
    if slots[0][0] != TOU_DAY_START or slots[-1][1] != TOU_DAY_END:
        raise ValueError(
            f"TOU plan must cover {TOU_DAY_START:02d}:00-{TOU_DAY_END:02d}:00, "
            f"got {slots[0][0]:02d}:00-{slots[-1][1]:02d}:00"
        )
    for (_, prev_end, _), (start, _, _) in pairwise(slots):
        if start != prev_end:
            raise ValueError(
                f"TOU plan slots must be contiguous, gap or overlap at {prev_end:02d}:00"
            )

    data = bytearray([0x04, slots[0][2]])
    for idx, (start, end, _) in enumerate(slots):
        data += bytes([start, end])
        if idx + 1 < len(slots):
            data.append(slots[idx + 1][2])
    return bytes(data)


def decode_tou_plan(data: bytes | bytearray | str) -> dict:
    """Decode an a7 TOU struct value back into a plan dict.

    Args:
        data: field value with or without the leading 0x04 struct type byte,
            as bytes or a hex string.

    Returns:
        dict: {"ranges": [{"start_time","end_time","tariff"}, ...]}

    """
    raw = (
        bytes.fromhex(data.replace(":", "").replace(" ", ""))
        if isinstance(data, str)
        else bytes(data)
    )
    if raw and raw[0] == 0x04:
        raw = raw[1:]
    if len(raw) < 3:
        raise ValueError("TOU struct too short to contain a slot")
    tariff = raw[0]
    ranges: list[dict] = []
    pos = 1
    while pos + 1 < len(raw):
        start, end = raw[pos], raw[pos + 1]
        pos += 2
        if pos < len(raw):
            next_tariff = raw[pos]
            pos += 1
        else:
            next_tariff = None
        ranges.append(
            {
                "start_time": f"{start:02d}:00",
                "end_time": f"{end:02d}:00",
                "tariff": tariff,
            }
        )
        if next_tariff is not None:
            tariff = next_tariff
    return {"ranges": ranges}


def encode_custom_plan(plan: dict) -> bytes:
    """Encode a custom plan dict into the a2 struct value of message 0093.

    Accepts either a single group, using the plan level "weekdays" key, or an
    explicit "groups" list of {"weekdays": [...], "ranges": [...]} entries.

    Args:
        plan: {"weekdays": [...], "ranges": [{"start_time","end_time","load_mode"}]}
            or {"groups": [{"weekdays": [...], "ranges": [...]}, ...]}

    Returns:
        bytes: the field value including the leading 0x04 struct type byte.

    Raises:
        ValueError: on group or slot limit violation, overlapping slots, or an
            unknown weekday or load mode.

    """
    groups = plan.get("groups")
    if not groups:
        groups = [
            {
                "weekdays": plan.get("weekdays") or [],
                "ranges": plan.get("ranges") or [],
            }
        ]
    if len(groups) > CUSTOM_MAX_GROUPS:
        raise ValueError(
            f"Custom plan supports at most {CUSTOM_MAX_GROUPS} groups, "
            f"got {len(groups)}"
        )

    data = bytearray([0x04, len(groups)])
    for gidx, group in enumerate(groups, 1):
        ranges = list(group.get("ranges") or [])
        if not ranges:
            raise ValueError(f"Custom plan group {gidx} requires at least one slot")
        if len(ranges) > CUSTOM_MAX_SLOTS:
            raise ValueError(
                f"Custom plan group {gidx} supports at most {CUSTOM_MAX_SLOTS} slots, got {len(ranges)}"
            )
        mask = 0
        for day in group.get("weekdays") or []:
            name = str(day).lower()[:3]
            if name not in WEEKDAYS:
                raise ValueError(
                    f"Unknown weekday {day!r}, expected one of {list(WEEKDAYS)}"
                )
            mask |= 1 << WEEKDAYS.index(name)

        slots: list[tuple[int, int, int]] = []
        for sidx, item in enumerate(ranges, 1):
            start = _custom_minutes(
                item.get("start_time", 0), f"group {gidx} slot {sidx} start_time"
            )
            end = _custom_minutes(
                item.get("end_time", 0), f"group {gidx} slot {sidx} end_time"
            )
            if end <= start:
                raise ValueError(
                    f"Custom plan group {gidx} slot {sidx} end_time must be after start_time"
                )
            mode = _as_code(item.get("load_mode"), CUSTOM_LOAD_MODES, "load_mode")
            slots.append((start, end, mode))
        slots.sort(key=lambda s: s[0])
        # Gaps between custom slots are allowed, overlaps are not.
        for (_, prev_end, _), (start, _, _) in pairwise(slots):
            if start < prev_end:
                raise ValueError(
                    f"Custom plan group {gidx} slots overlap at {_hhmm(start)}"
                )

        data += bytes([mask, len(slots)])
        for start, end, mode in slots:
            data += (
                bytes([mode]) + start.to_bytes(2, "little") + end.to_bytes(2, "little")
            )
    return bytes(data)


def decode_custom_plan(data: bytes | bytearray | str) -> dict:
    """Decode an a2 custom struct value back into a plan dict.

    Returns:
        dict: {"groups": [{"weekdays": [...], "ranges": [...]}, ...]}

    """
    raw = (
        bytes.fromhex(data.replace(":", "").replace(" ", ""))
        if isinstance(data, str)
        else bytes(data)
    )
    if raw and raw[0] == 0x04:
        raw = raw[1:]
    if not raw:
        raise ValueError("Custom struct is empty")
    groups: list[dict] = []
    pos = 1
    for _ in range(raw[0]):
        if pos + 1 >= len(raw):
            raise ValueError("Custom struct truncated in group header")
        mask, count = raw[pos], raw[pos + 1]
        pos += 2
        ranges = []
        for _ in range(count):
            if pos + 4 >= len(raw):
                raise ValueError("Custom struct truncated in slot")
            mode = raw[pos]
            start = int.from_bytes(raw[pos + 1 : pos + 3], "little")
            end = int.from_bytes(raw[pos + 3 : pos + 5], "little")
            pos += 5
            ranges.append(
                {"start_time": _hhmm(start), "end_time": _hhmm(end), "load_mode": mode}
            )
        groups.append(
            {
                "weekdays": [d for i, d in enumerate(WEEKDAYS) if mask & (1 << i)],
                "ranges": ranges,
            }
        )
    return {"groups": groups}


def update_plan_slots(
    ranges: list[dict] | None,
    slot: dict | None = None,
    index: int | None = None,
    delete: bool = False,
) -> list[dict]:
    """Return a new slot list with one slot inserted, updated or removed.

    Supports both whole slot objects and individual parameter updates: keys
    absent from ``slot`` are kept from the existing slot at ``index``.

    Args:
        ranges: existing slot list, as held in a plan's "ranges".
        slot: slot keys to apply. Omit to only delete.
        index: 1-based slot position. None appends a new slot.
        delete: remove the slot at ``index`` instead of updating it.

    Returns:
        list[dict]: a new list; the input is not modified.

    """
    items = [dict(item) for item in (ranges or [])]
    if delete:
        if index is None or not 1 <= index <= len(items):
            raise ValueError(f"Cannot delete slot {index}, plan has {len(items)} slots")
        items.pop(index - 1)
        return items
    if not slot:
        raise ValueError("Provide slot values to update, or delete=True")
    if index is None:
        items.append(dict(slot))
    elif 1 <= index <= len(items):
        items[index - 1].update(slot)
    else:
        raise ValueError(f"Cannot update slot {index}, plan has {len(items)} slots")
    return items


class SolixMqttDevicePps(SolixMqttDevice):
    """Define the class to handle an Anker Solix MQTT device for PPS controls."""

    def __init__(self, api_instance: AnkerSolixApi, device_sn: str) -> None:
        """Initialize."""
        self.models = MODELS
        self.features = FEATURES
        super().__init__(api_instance=api_instance, device_sn=device_sn)

    def update_device(
        self, device: dict, dynamic_descriptions: dict | None = None
    ) -> None:
        """Define callback for Api device updates."""
        super().update_device(device=device, dynamic_descriptions=dynamic_descriptions)
        # update plans if available
        self.get_custom_plan(fromFile=True)
        self.get_tou_plan(fromFile=True)

    def get_custom_plan(
        self,
        fromFile: bool = False,
    ) -> dict | None:
        """Get an actual custom plan from the PPS.

        Args:
            fromFile: If True, consider the mocked cache

        Returns:
            dict: Custom plan as updated in mqttdata["custom_plan"] and returned. None will be returned if not supported.

        Example output:
            {
                "custom_mode_switch": 1,
                "weekdays": ["tue","wed","thu","fri","sat"],
                "ranges": [
                    {"start_time": "00:00","end_time": "08:00","load_mode": 1},
                    {"start_time": "10:00","end_time": "20:00","load_mode": 2},
                    {"start_time": "22:00","end_time": "24:00","load_mode": 1}
                ]
            }

        """

        cache = self.get_status(fromFile=fromFile)
        if (slots := cache.get("custom_slot_count")) is not None and slots > 0:
            plan = {
                "custom_mode_switch": cache.get("custom_mode_switch"),
                "weekdays": cache.get("custom_mode_weekdays", []),
            }
            ranges = []
            for idx in range(1, slots + 1):
                start = cache.get(f"custom_slot_{idx}_start_minutes", 0)
                end = cache.get(f"custom_slot_{idx}_end_minutes", 0)
                ranges.append(
                    {
                        "start_time": f"{start // 60:02d}:{start % 60:02d}",
                        "end_time": f"{end // 60:02d}:{end % 60:02d}",
                        "load_mode": self.mqttdata.get(
                            f"custom_slot_{idx}_load_mode", 0
                        ),
                    }
                )
            plan["ranges"] = ranges
            self.mqttdata["custom_plan"] = plan
        else:
            self.mqttdata.pop("custom_plan", None)
        return self.mqttdata.get("custom_plan")

    def get_tou_plan(
        self,
        fromFile: bool = False,
    ) -> dict | None:
        """Get an actual time of use plan from the PPS.

        Args:
            fromFile: If True, consider the mocked cache

        Returns:
            dict: TOU plan as updated in mqttdata["tou_plan"] and returned. None will be returned if not supported.

        Example output:
            {
                "ranges": [
                    {"start_time": "00:00","end_time": "08:00","tariff": 1},
                    {"start_time": "08:00","end_time": "20:00","tariff": 2},
                    {"start_time": "20:00","end_time": "24:00","tariff": 3}
                ]
            }

        """
        cache = self.get_status(fromFile=fromFile)
        if (slots := cache.get("tou_slot_count")) is not None and slots > 0:
            plan = {}
            ranges = [
                {
                    "start_time": f"{cache.get(f'tou_slot_{idx}_start_hour', 0):02d}:00",
                    "end_time": f"{cache.get(f'tou_slot_{idx}_end_hour', 0):02d}:00",
                    "tariff": cache.get(f"tou_slot_{idx}_tariff", 0),
                }
                for idx in range(1, slots + 1)
            ]
            plan["ranges"] = ranges
            self.mqttdata["tou_plan"] = plan
        else:
            self.mqttdata.pop("tou_plan", None)
        return self.mqttdata.get("tou_plan")

    async def set_ac_output(
        self,
        enabled: bool | None = None,
        mode: int | str | None = None,
        toFile: bool = False,
    ) -> dict | None:
        """Control AC output power via MQTT.

        Args:
            enabled: True to enable AC output, False to disable
            mode: AC output mode - 1=Normal, 0=Smart
                Can also be string: "normal", "smart"
            toFile: If True, save mock response (for testing compatibility)

        Returns:
            dict: Mocked state if successful, None otherwise

        Example:
            await mydevice.set_ac_output(enabled=True)
            await mydevice.set_ac_output(mode=1)  # Normal
            await mydevice.set_ac_output(mode="smart")

        """
        # response and commands
        resp = {}
        cmd1 = SolixMqttCommands.ac_output_switch
        cmd2 = SolixMqttCommands.ac_output_mode_select
        # First validate all parameters
        if (
            enabled is not None
            and self.validate_cmd_value(cmd=cmd1, value=enabled) is None
        ):
            return None
        if mode is not None and self.validate_cmd_value(cmd=cmd2, value=mode) is None:
            return None
        # Validate and run AC switch enable command
        if enabled is not None:
            if (
                result := await self.run_command(
                    cmd=cmd1,
                    value=enabled,
                    toFile=toFile,
                )
            ) is None:
                return None
            resp.update(result)
        # Validate and run AC output mode command
        if mode is not None:
            if (
                result := await self.run_command(
                    cmd=cmd2,
                    value=mode,
                    toFile=toFile,
                )
            ) is None:
                return None
            resp.update(result)
        return resp or None

    async def set_dc_output(
        self,
        enabled: bool | None = None,
        mode: int | str | None = None,
        toFile: bool = False,
    ) -> dict | None:
        """Control DC output power via MQTT.

        Args:
            enabled: True to enable DC output, False to disable
            mode: DC output mode - 1=Normal, 0=Smart
                Can also be string: "normal", "smart"
            toFile: If True, save mock response (for testing compatibility)

        Returns:
            dict: Mocked state if successful, None otherwise

        Example:
            await mydevice.set_dc_output(enabled=True)
            await mydevice.set_dc_output(mode=0)  # Smart
            await mydevice.set_dc_output(mode="normal")

        """
        # response and commands
        resp = {}
        cmd1 = SolixMqttCommands.dc_output_switch
        cmd2 = SolixMqttCommands.dc_12v_output_mode_select
        # First validate all parameters
        if (
            enabled is not None
            and self.validate_cmd_value(cmd=cmd1, value=enabled) is None
        ):
            return None
        if mode is not None and self.validate_cmd_value(cmd=cmd2, value=mode) is None:
            return None
        # Validate and run DC switch enable command
        if enabled is not None:
            if (
                result := await self.run_command(
                    cmd=cmd1,
                    value=enabled,
                    toFile=toFile,
                )
            ) is None:
                return None
            resp.update(result)
        # Validate and run DC output mode command
        if mode is not None:
            if (
                result := await self.run_command(
                    cmd=cmd2,
                    value=mode,
                    toFile=toFile,
                )
            ) is None:
                return None
            resp.update(result)
        return resp or False

    async def set_display(
        self,
        enabled: bool | None = None,
        mode: int | str | None = None,
        timeout_seconds: int | None = None,
        toFile: bool = False,
    ) -> dict | None:
        """Control display settings via MQTT.

        Args:
            enabled: True to turn display on, False to turn off
            mode: Display mode - 0=Off, 1=Low, 2=Medium, 3=High
                Can also be string: "off", "low", "medium", "high"
            timeout_seconds: Seconds before display goes off again
            toFile: If True, save mock response (for testing compatibility)

        Returns:
            dict: Mocked state if successful, None otherwise

        Example:
            await mydevice.set_display(enabled=True)
            await mydevice.set_display(mode=2)  # Medium
            await mydevice.set_display(mode="high")
            await mydevice.set_display(timeout_seconds=20)

        """
        # response
        resp = {}
        cmd1 = SolixMqttCommands.display_switch
        cmd2 = SolixMqttCommands.display_mode_select
        cmd3 = SolixMqttCommands.display_timeout_seconds
        # First validate all parameters
        if (
            enabled is not None
            and self.validate_cmd_value(cmd=cmd1, value=enabled) is None
        ):
            return None
        if mode is not None and self.validate_cmd_value(cmd=cmd2, value=mode) is None:
            return None
        if (
            timeout_seconds is not None
            and self.validate_cmd_value(cmd=cmd3, value=timeout_seconds) is None
        ):
            return None
        # Validate and run enable command
        if enabled is not None:
            if (
                result := await self.run_command(
                    cmd=cmd1,
                    value=enabled,
                    toFile=toFile,
                )
            ) is None:
                return None
            resp.update(result)
        # Validate and run mode command
        if mode is not None:
            if (
                result := await self.run_command(
                    cmd=cmd2,
                    value=mode,
                    toFile=toFile,
                )
            ) is None:
                return None
            resp.update(result)
        # Validate and run timeout command
        if timeout_seconds is not None:
            if (
                result := await self.run_command(
                    cmd=cmd3,
                    value=timeout_seconds,
                    toFile=toFile,
                )
            ) is None:
                return None
            resp.update(result)
        return resp or None

    async def set_backup_charge(
        self,
        enabled: bool | None = None,
        toFile: bool = False,
    ) -> dict | None:
        """Control backup charge mode via MQTT.

        Args:
            enabled: True to enable backup charge mode, False to disable
            toFile: If True, save mock response (for testing compatibility)

        Returns:
            dict: Mocked state if successful, None otherwise

        Example:
            await mydevice.set_backup_charge(enabled=True)

        """
        # response and commands
        resp = {}
        cmd1 = SolixMqttCommands.ac_charge_switch
        # Validate and run command
        if enabled is not None:
            if (
                result := await self.run_command(
                    cmd=cmd1,
                    value=enabled,
                    toFile=toFile,
                )
            ) is None:
                return None
            resp.update(result)
        return resp or None

    async def set_temp_unit(
        self,
        unit: str | None = None,
        toFile: bool = False,
    ) -> dict | None:
        """Set temperature unit via MQTT.

        Args:
            unit: "fahrenheit" | "celsius"
            toFile: If True, save mock response (for testing compatibility)

        Returns:
            dict: Mocked state if successful, None otherwise

        Example:
            await mydevice.set_temp_unit(unit="celsius")  # Celsius

        """
        # response and commands
        resp = {}
        cmd1 = SolixMqttCommands.temp_unit_switch
        # Validate and run command
        if unit is not None:
            if (
                result := await self.run_command(
                    cmd=cmd1,
                    value=unit,
                    toFile=toFile,
                )
            ) is None:
                return None
            resp.update(result)
        return resp or None

    async def set_light(
        self,
        mode: int | str | None = None,
        toFile: bool = False,
    ) -> dict | None:
        """Set light mode via MQTT.

        Args:
            mode: Light mode - 0=Off, 1=Low, 2=Medium, 3=High, 4=Blinking
                Can also be string: "off", "low", "medium", "high", "blinking"
            toFile: If True, save mock response (for testing compatibility)

        Returns:
            dict: Mocked state if successful, None otherwise

        Example:
            await mydevice.set_light_mode(mode=3)  # High
            await mydevice.set_light_mode(mode="blinking")

        """
        # response and commands
        resp = {}
        cmd1 = SolixMqttCommands.light_mode_select
        # Validate and run command
        if mode is not None:
            if (
                result := await self.run_command(
                    cmd=cmd1,
                    value=mode,
                    toFile=toFile,
                )
            ) is None:
                return None
            resp.update(result)
        return resp or None

    async def set_device_timeout(
        self,
        timeout_minutes: int | None = None,
        toFile: bool = False,
    ) -> dict | None:
        """Set device auto-off timeout.

        Args:
            timeout_minutes: Timeout in minutes (30-1440)
            toFile: If True, save mock response (for testing compatibility)

        Returns:
            dict: Mocked state if successful, None otherwise

        Example:
            # Set 8 hour timeout
            result = await device.set_device_timeout(timeout_minutes=480)

        """
        # response and commands
        resp = {}
        cmd1 = SolixMqttCommands.device_timeout_minutes
        # Validate and run command
        if timeout_minutes is not None:
            if (
                result := await self.run_command(
                    cmd=cmd1,
                    value=timeout_minutes,
                    toFile=toFile,
                )
            ) is None:
                return None
            resp.update(result)
        return resp or None

    async def set_max_load(
        self,
        max_watts: int | None = None,
        toFile: bool = False,
    ) -> dict | None:
        """Set maximum AC output load in Watt.

        Args:
            max_watts: Maximum load in watts
            toFile: If True, save mock response (for testing compatibility)

        Returns:
            dict: Mocked state if successful, None otherwise

        Example:
            # Set 800W max load
            result = await device.set_max_load(max_watts=800)

        """
        # response and commands
        resp = {}
        cmd1 = SolixMqttCommands.device_max_load
        # Validate and run command
        if max_watts is not None:
            if (
                result := await self.run_command(
                    cmd=cmd1,
                    value=max_watts,
                    toFile=toFile,
                )
            ) is None:
                return None
            resp.update(result)
        return resp or None

    async def set_charge_limit(
        self,
        max_watts: int | None = None,
        toFile: bool = False,
    ) -> dict | None:
        """Set maximum AC charge limit in Watt.

        Args:
            max_watts: Maximum load in watts
            toFile: If True, save mock response (for testing compatibility)

        Returns:
            dict: Mocked state if successful, None otherwise

        Example:
            # Set 800W charge limit
            result = await device.set_max_load(max_watts=800)

        """
        # response and commands
        resp = {}
        cmd1 = SolixMqttCommands.ac_charge_limit
        # Validate and run command
        if max_watts is not None:
            if (
                result := await self.run_command(
                    cmd=cmd1,
                    value=max_watts,
                    toFile=toFile,
                )
            ) is None:
                return None
            resp.update(result)
        return resp or None

    async def set_fast_charging(
        self,
        enabled: bool | None = None,
        toFile: bool = False,
    ) -> dict | None:
        """Set Fast charging mode (e.g. 1300W max).

        Args:
            enabled: True to enable Fast charging, False to disable
            toFile: If True, save mock response (for testing compatibility)

        Returns:
            dict: Mocked state if successful, None otherwise

        Example:
            # Enable Fast charging
            result = await device.set_fast_charging(enabled=True)

        """
        # response and commands
        resp = {}
        cmd1 = SolixMqttCommands.ac_fast_charge_switch
        # Validate and run command
        if enabled is not None:
            if (
                result := await self.run_command(
                    cmd=cmd1,
                    value=enabled,
                    toFile=toFile,
                )
            ) is None:
                return None
            resp.update(result)
        return resp or None

    async def set_port_memory(
        self,
        enabled: bool,
        toFile: bool = False,
    ) -> dict | None:
        """Set port memory switch.

        Args:
            enabled: True to enable port memory, False to disable
            toFile: If True, save mock response (for testing compatibility)

        Returns:
            dict: Mocked state if successful, None otherwise

        Example:
            # Enable port memory switch
            result = await device.set_port_memory(enabled=True)

        """
        # response and commands
        resp = {}
        cmd1 = SolixMqttCommands.port_memory_switch
        # Validate and run command
        if enabled is not None:
            if (
                result := await self.run_command(
                    cmd=cmd1,
                    value=enabled,
                    toFile=toFile,
                )
            ) is None:
                return None
            resp.update(result)
        return resp or None
