#!/usr/bin/env python
"""Example exec module to use the Anker API for continuously querying and displaying important parameters of Anker Solix sites and devices.

This module will prompt for the Anker account details if not pre-set in the header. Upon successful authentication,
you will see system and device parameters and values displayed and refreshed at regular interval.

Optionally you can enable MQTT in Live and File mode to mix-in konwn/described binary MQTT message values.

Note: When the system owning account is used, more details for the systems and devices can be queried and displayed.
MQTT messages can only be subscribed for owned devices, which does not work for system member accounts.
"""

import argparse
import asyncio
import contextlib
from datetime import datetime, timedelta
import json
import logging
from pathlib import Path
import sys

from aiohttp import ClientSession
from aiohttp.client_exceptions import ClientError
from api.api import AnkerSolixApi  # pylint: disable=no-name-in-module
from api.apitypes import (  # pylint: disable=no-name-in-module
    Color,
    SolarbankAiemsStatus,
    SolarbankLightMode,
    SolarbankUsageMode,
    SolixDeviceType,
    SolixPpsDisplayMode,
    SolixPpsOutputMode,
    SolixPriceProvider,
    SolixPriceTypes,
    SolixVehicle,
)
from api.errors import AnkerSolixError  # pylint: disable=no-name-in-module
from api.mqtt_device import SolixMqttDevice  # pylint: disable=no-name-in-module
from api.mqtt_factory import SolixMqttDeviceFactory  # pylint: disable=no-name-in-module
import common

# use Console logger from common module
CONSOLE: logging.Logger = common.CONSOLE
# enable debug mode for the console handler
# CONSOLE.handlers[0].setLevel(logging.DEBUG)

# use SAMELINE logger from common module
SAMELINE: logging.Logger = common.SAMELINE

# Interactive allows to select examples and exports as input for tests and debug
INTERACTIVE = True
# Enable to show Api calls and cache details for additional debugging
SHOWAPICALLS = False
# Realtime Trigger timeout for MQTT data
RTTIMEOUT = 60


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Anker Solix Monitor - Monitor your Anker Solix devices in real-time"
    )
    parser.add_argument(
        "--live-cloud",
        "--live",
        action="store_true",
        help="Use live cloud data (default: interactive mode asks for input source)",
    )
    parser.add_argument(
        "--enable-mqtt",
        "--mqtt",
        action="store_true",
        help="Enable MQTT session on startup for real-time device data",
    )
    parser.add_argument(
        "--realtime",
        "--rt",
        action="store_true",
        help="Enable real-time MQTT trigger on startup (requires --enable-mqtt)",
    )
    parser.add_argument(
        "--mqtt-display",
        action="store_true",
        help="Initially show pure MQTT data display instead of mixed API + MQTT display (requires --enable-mqtt)",
    )
    parser.add_argument(
        "--interval",
        "-i",
        type=int,
        default=30,
        choices=range(5, 601),
        metavar="[5-600]",
        help="Refresh interval in seconds (default: 30)",
    )
    parser.add_argument(
        "--energy-stats",
        "--energy",
        action="store_true",
        help="Include daily site energy statistics on API display",
    )
    parser.add_argument("--site-id", type=str, help="Monitor specific site ID only")
    parser.add_argument(
        "--device-id", type=str, help="Filter output for specific device ID only"
    )
    parser.add_argument(
        "--no-vehicles",
        "--no-ev",
        action="store_true",
        help="Disable electric vehicles on API display",
    )
    parser.add_argument(
        "--api-calls", action="store_true", help="Show API call statistics and details"
    )
    parser.add_argument(
        "--debug-http",
        action="store_true",
        help="Show HTTP request/response debug messages (very verbose)",
    )
    parser.add_argument(
        "--endpoint-limit",
        type=int,
        default=10,
        choices=range(51),
        metavar="[0-50]",
        help="Set API endpoint limit for request throttling (0=disabled, default: 10)",
    )
    args = parser.parse_args()
    # Validate argument combinations
    if args.realtime and not args.enable_mqtt:
        parser.error("--realtime requires --enable-mqtt to be specified")
    if args.mqtt_display and not args.enable_mqtt:
        parser.error("--mqtt-display requires --enable-mqtt to be specified")
    return args


class AnkerSolixApiMonitor:
    """Define the class for the monitor."""

    def __init__(self, args: argparse.Namespace | None = None) -> None:
        """Initialize."""
        # Parse command line arguments if not provided
        if not isinstance(args, argparse.Namespace):
            args = parse_arguments()
        # Set configuration based on command line arguments
        self.interactive: bool = INTERACTIVE and not args.live_cloud
        self.showApiCalls: bool = args.api_calls or SHOWAPICALLS
        self.showVehicles: bool = not args.no_vehicles
        self.use_file: bool = not args.live_cloud and INTERACTIVE
        self.api: AnkerSolixApi | None = None
        self.site_selected: str | None = args.site_id
        self.device_names: list = []
        self.device_filter: str | None = args.device_id
        self.energy_stats: bool = args.energy_stats
        self.refresh_interval: int = args.interval
        self.enable_mqtt: bool = args.enable_mqtt
        self.enable_realtime: bool = args.realtime
        self.endpoint_limit: int = args.endpoint_limit
        self.debug_http: bool = args.debug_http
        # Set MQTT display mode from command line
        self.showMqttDevice: bool = args.mqtt_display and args.enable_mqtt
        self.mqtt_devices: dict[str, SolixMqttDevice] = {}
        self.next_refr: datetime
        self.next_dev_refr: int = 0
        self.triggered: datetime | None = None
        self.rt_timeout: int = RTTIMEOUT
        self.folderdict: dict = {}
        self.delayed_sn_refresh: set = set()
        self.loop: asyncio.AbstractEventLoop

    def get_subfolders(self, folder: str | Path) -> list:
        """Get the full pathname of all subfolder for given folder as list."""
        if isinstance(folder, str):
            folder: Path = Path(folder)
        if folder.is_dir():
            return [f.resolve() for f in folder.iterdir() if f.is_dir()]
        return []

    def get_menu_options(self, details: bool = False) -> str:
        """Print the key menu and return the input."""
        if details:
            CONSOLE.info(
                f"\n%s\n{Color.YELLOW}{'File usage' if self.use_file else 'Live'} Monitor key menu:{Color.OFF}\n%s",
                100 * "-",
                100 * "-",
            )
            CONSOLE.info(f"[{Color.YELLOW}K{Color.OFF}]ey list to show this menu")
            CONSOLE.info(
                f"[{Color.YELLOW}E{Color.OFF}]lectric Vehicle display toggle ON (default) or OFF"
            )
            CONSOLE.info(f"[{Color.YELLOW}F{Color.OFF}]ilter toggle for device display")
            CONSOLE.info(f"[{Color.YELLOW}D{Color.OFF}]ebug actual Api cache")
            CONSOLE.info(f"[{Color.YELLOW}C{Color.OFF}]ustomize an Api cache entry")
            CONSOLE.info(
                f"[{Color.YELLOW}V{Color.OFF}]iew actual MQTT data cache and extracted device data"
            )
            CONSOLE.info(
                f"[{Color.YELLOW}A{Color.OFF}]pi call display toggle OFF (default) or ON"
            )
            CONSOLE.info(
                f"Toggle MQTT [{Color.YELLOW}S{Color.OFF}]ession OFF (default) or ON"
            )
            if self.use_file:
                CONSOLE.info(
                    f"Change MQTT message speed [{Color.YELLOW}+{Color.OFF}] faster / [{Color.YELLOW}-{Color.OFF}] slower"
                )
                CONSOLE.info(f"Immediate s[{Color.YELLOW}I{Color.OFF}]te refresh")
                CONSOLE.info(f"Immediate refresh for a[{Color.YELLOW}L{Color.OFF}]l")
                CONSOLE.info(
                    f"Select [{Color.YELLOW}N{Color.OFF}]next folder for monitoring"
                )
                CONSOLE.info(
                    f"Select [{Color.YELLOW}P{Color.OFF}]previous folder for monitoring"
                )
                CONSOLE.info(
                    f"Select [{Color.YELLOW}O{Color.OFF}]ther folder for monitoring"
                )
            else:
                CONSOLE.info(
                    f"[{Color.YELLOW}R{Color.OFF}]eal time MQTT data trigger (Timeout 1 min). Only possible if MQTT session is ON"
                )
            CONSOLE.info(
                f"[{Color.YELLOW}M{Color.OFF}]qtt device or Api device (default) display toggle"
            )
            CONSOLE.info(
                f"[{Color.RED}Q{Color.OFF}]uit, [{Color.RED}ESC{Color.OFF}] or [{Color.RED}CTRL-C{Color.OFF}] to stop monitor"
            )
            return input(f"Hit [{Color.GREEN}Enter{Color.OFF}] to continue...")
        if self.use_file:
            CONSOLE.info(
                f"[{Color.YELLOW}K{Color.OFF}]ey menu, [{Color.YELLOW}D{Color.OFF}]ebug/[{Color.YELLOW}C{Color.OFF}]ustomize cache, [{Color.YELLOW}E{Color.OFF}]V toggle, "
                f"[{Color.YELLOW}N{Color.OFF}]ext/[{Color.YELLOW}P{Color.OFF}]rev/[{Color.YELLOW}O{Color.OFF}]ther folder, "
                f"s[{Color.YELLOW}I{Color.OFF}]te/A[{Color.YELLOW}L{Color.OFF}]l refresh, "
                f"MQTT [{Color.YELLOW}S{Color.OFF}]ession ({Color.YELLOW}+{Color.OFF}/{Color.YELLOW}-{Color.OFF}), "
                f"[{Color.YELLOW}M{Color.OFF}]qtt display, [{Color.YELLOW}V{Color.OFF}]iew data, [{Color.YELLOW}A{Color.OFF}]pi calls, "
                f"[{Color.YELLOW}F{Color.OFF}]ilter device, [{Color.RED}ESC{Color.OFF}]/[{Color.RED}Q{Color.OFF}]uit"
            )
        else:
            CONSOLE.info(
                f"[{Color.YELLOW}K{Color.OFF}]ey menu, [{Color.YELLOW}D{Color.OFF}]ebug/[{Color.YELLOW}C{Color.OFF}]ustomize cache, [{Color.YELLOW}E{Color.OFF}]V toggle, "
                f"MQTT [{Color.YELLOW}S{Color.OFF}]ession toggle, [{Color.YELLOW}R{Color.OFF}]eal time trigger, "
                f"[{Color.YELLOW}M{Color.OFF}]qtt display toggle, [{Color.YELLOW}V{Color.OFF}]iew data, [{Color.YELLOW}A{Color.OFF}]pi calls toggle, "
                f"[{Color.YELLOW}F{Color.OFF}]ilter device, [{Color.RED}ESC{Color.OFF}]/[{Color.RED}Q{Color.OFF}]uit"
            )
        return ""

    def customize_cache(self) -> bool:
        """Customize a key in the Api cache and restart device details refresh."""
        CONSOLE.info("Site IDs and Device SNs for customization:")
        cache: dict = self.api.sites | self.api.devices
        for idx, item in enumerate(
            itemlist := list(cache.keys()),
            start=1,
        ):
            CONSOLE.info(
                f"({Color.YELLOW}{idx}{Color.OFF}) {item} - {cache.get(item).get('name') or (cache.get(item).get('site_info') or {}).get('site_name')}"
            )
        while True:
            select = input(
                f"Select {Color.YELLOW}ID{Color.OFF} or [{Color.RED}C{Color.OFF}]ancel: "
            )
            if select.upper() in ["C", "CANCEL"]:
                break
            if select.isdigit() and 1 <= (select := int(select)) <= len(itemlist):
                break
        if isinstance(select, int):
            item = itemlist[select - 1]
            key = input(
                f"Enter {Color.CYAN}key{Color.OFF} to be customized in '{Color.YELLOW}{item}{Color.OFF}': "
            )
            value = json.loads(
                f"{input(f"Enter '{Color.YELLOW}{key}{Color.OFF}' {Color.CYAN}value{Color.OFF} in JSON format: ").replace("'", '"')}"
            )
            self.api.customizeCacheId(id=item, key=key, value=value)
            CONSOLE.info(
                f"Customized part of {Color.YELLOW}{item}{Color.OFF}:\n"
                f"{json.dumps(self.api.getCaches().get(item).get('customized') or {}, indent=2)}"
            )
            input(f"Hit [{Color.YELLOW}Enter{Color.OFF}] to refresh all data...")
            self.next_dev_refr = 0
            self.next_refr = datetime.now().astimezone()
            return True
        return False

    async def print_wait_progress(self, seconds: int) -> None:
        """Print wait progress for data poller monitoring for given number of seconds."""
        for sec in range(seconds):
            now = datetime.now().astimezone()
            # IDLE may be used with different stdin which does not support cursor placement, skip time progress display in that case
            if sys.stdin is sys.__stdin__:
                SAMELINE.info(
                    f"Site refresh: {int((self.next_refr - now).total_seconds()):>3} sec,  Device details countdown: {int(self.next_dev_refr):>2}"
                )
                if self.next_refr < now:
                    break
            elif sec == 0 or self.next_refr < now:
                CONSOLE.info(
                    f"Site refresh: {int((self.next_refr - now).total_seconds()):>3} sec,  Device details countdown: {int(self.next_dev_refr):>2}",
                )
                if self.next_refr < now:
                    break
            await asyncio.sleep(1)

    def print_device_mqtt(
        self,
        deviceSn: str,
        *args,
        **kwargs,
    ) -> None:
        """Define Callback to print the extracted and refreshed device MQTT values from the Api cache."""
        if not (self.showMqttDevice and self.api.mqttsession):
            # Api data display active while message received, delay print to consolidate multiple messages
            if (
                self.delayed_sn_refresh
                or (self.next_refr - datetime.now().astimezone()).total_seconds() <= 2
            ):
                # add sn and skip refresh if delayed refresh still active
                self.delayed_sn_refresh.add(deviceSn)
                return
            self.delayed_sn_refresh.add(deviceSn)
            self.loop.create_task(self.print_api_data_delayed(delay=1))
            return
        common.clearscreen()
        col1 = 25
        col2 = 30
        col3 = 25
        for sn, dev in [
            (sn, dev)
            for sn, dev in self.api.devices.items()
            if dev.get("mqtt_data")
            and (not self.device_filter or self.device_filter == sn)
        ]:
            CONSOLE.info(
                f"{' ' + ((Color.YELLOW + 'UPDATED ' + datetime.now().strftime('%H:%M:%S --> ')) if sn == deviceSn else Color.MAG) + dev.get('alias', 'NoAlias') + ' - ' + dev.get('name', 'NoName') + ' (' + dev.get('device_pn', '') + ') ' + Color.OFF:-^109}"
            )
            fields = []
            topics = None
            for key, value in (dev.get("mqtt_data") or {}).items():
                if key != "topics":
                    fields.append((key, value))
                else:
                    topics = value
                if len(fields) >= 2:
                    # print row
                    CONSOLE.info(
                        f"{fields[0][0]:<{col1}}: {fields[0][1]!s:<{col2}} {fields[1][0]:<{col3}}: {fields[1][1]!s}"
                    )
                    fields.clear()
            if fields:
                CONSOLE.info(f"{fields[0][0]:<{col1}}: {fields[0][1]!s:<{col2}}")
            if topics:
                CONSOLE.info(f"{'Received Topics':<{col1}}: {topics!s}")
        CONSOLE.info(f"{'-' * 100}")
        # Print MQTT stats
        if self.use_file:
            CONSOLE.info(
                f"Active MQTT speed: {Color.CYAN}{self.folderdict.get('speed', 1):.2f}{Color.OFF}, Message cycle duration: {Color.CYAN}"
                f"{self.folderdict.get('duration', 0) / self.folderdict.get('speed', 1):.0f} sec ({self.folderdict.get('progress', 0):6.2f} %){Color.OFF}"
            )
        else:
            trigger_sec = (
                int((self.triggered - datetime.now()).total_seconds())
                if self.triggered
                else None
            )
            CONSOLE.info(
                f"Active MQTT topics: {Color.GREEN if self.api.mqttsession.subscriptions else Color.RED}"
                f"{str(self.api.mqttsession.subscriptions or ' None ')[1:-1]}{Color.OFF}"
            )
            CONSOLE.info(
                f"Realtime Triggered: {Color.GREEN + str(trigger_sec) + ' sec' if self.triggered is not None else Color.RED + 'OFF'}{Color.OFF}, "
                f"Devices: {Color.CYAN + str(self.api.mqttsession.triggered_devices or ' None ')[1:-1]}{Color.OFF}"
            )
        CONSOLE.info(f"MQTT {self.api.mqttsession.mqtt_stats!s}")
        CONSOLE.info(
            f"'Received Messages : {json.dumps(self.api.mqttsession.mqtt_stats.dev_messages)}"
        )
        self.get_menu_options()

    async def print_api_data_delayed(
        self, mqtt_mixin: bool = True, delay: int = 0
    ) -> None:
        """Print the Api data in formatted structures with a delay."""
        await asyncio.sleep(delay)
        common.clearscreen()
        self.print_api_data(mqtt_mixin=mqtt_mixin)

    def print_api_data(self, mqtt_mixin: bool = True) -> None:  # noqa: C901
        """Print the Api data in formatted structures."""
        if not self.api or self.showMqttDevice:
            return
        col1 = 15
        col2 = 23
        col3 = 15
        # define colors
        co = Color.OFF
        cc = Color.MAG  # calculated values
        shown_sites = set()
        for sn, dev in [
            (s, d)
            for s, d in self.api.devices.items()
            if (not self.site_selected or d.get("site_id") == self.site_selected)
            and (not self.device_filter or self.device_filter == s)
        ]:
            devtype = dev.get("type", "Unknown")
            admin = dev.get("is_admin", False)
            siteid = dev.get("site_id", "")
            site = self.api.sites.get(siteid) or {}
            customized = dev.get("customized") or {}
            mqtt = dev.get("mqtt_data") or {}
            # color for updated or mixin MQTT value
            c = (
                Color.YELLOW
                if mqtt_mixin and mqtt and sn in self.delayed_sn_refresh
                else ""
            )
            # color for MQTT only values
            cm = Color.CYAN if mqtt else ""
            if not (siteid and siteid in shown_sites):
                CONSOLE.info("=" * 80)
                if siteid:
                    shown_sites.add(siteid)
                    shift = site.get("energy_offset_tz")
                    shift = (
                        " --:--"
                        if shift is None
                        else f"{(shift // 3600):0=+3.0f}:{(shift % 3600 // 60) if shift else 0:0=z2.0f}"
                    )
                    CONSOLE.info(
                        f"{Color.YELLOW}{'System (' + shift + ')':<{col1}}: {(site.get('site_info') or {}).get('site_name', 'Unknown')}  (Site ID: {siteid}){co}"
                    )
                    site_type = str(site.get("site_type", ""))
                    CONSOLE.info(
                        f"{'Type ID':<{col1}}: {str((site.get('site_info') or {}).get('power_site_type', '--')) + (' (' + site_type.capitalize() + ')') if site_type else '':<{col2}} "
                        f"Device Models  : {','.join((site.get('site_info') or {}).get('current_site_device_models', []))}"
                    )
                    offset = site.get("energy_offset_seconds")
                    CONSOLE.info(
                        f"{'Energy Time':<{col1}}: {'----.--.-- --:--:--' if offset is None else (datetime.now() + timedelta(seconds=offset)).strftime('%Y-%m-%d %H:%M:%S'):<{col2}} "
                        f"{'Last Check':<{col3}}: {site.get('energy_offset_check') or '----.--.-- --:--:--'}"
                    )
                    if (sb := site.get("solarbank_info") or {}) and len(
                        sb.get("solarbank_list", [])
                    ) > 0:
                        # print solarbank totals
                        soc = f"{int(float(sb.get('total_battery_power') or 0) * 100)!s:>4} %"
                        unit = sb.get("power_unit") or "W"
                        update_time = sb.get("updated_time") or "Unknown"
                        CONSOLE.info(
                            f"{'Cloud-Updated':<{col1}}: {update_time:<{col2}} "
                            f"{'Valid Data':<{col3}}: {'YES' if site.get('data_valid') else 'NO'} (Requeries: {site.get('requeries')})"
                        )
                        CONSOLE.info(
                            f"{'SOC Total':<{col1}}: {soc:<{col2}} "
                            f"{'Dischrg Pwr Tot':<{col3}}: {sb.get('battery_discharge_power', '----'):>4} {unit}"
                        )
                        CONSOLE.info(
                            f"{'Solar  Pwr Tot':<{col1}}: {sb.get('total_photovoltaic_power', '----'):>4} {unit:<{col2 - 5}} "
                            f"{'Battery Pwr Tot':<{col3}}: {str(sb.get('total_charging_power')).split('.', maxsplit=1)[0]:>4} W"
                        )
                        CONSOLE.info(
                            f"{'Output Pwr Tot':<{col1}}: {str(sb.get('total_output_power', '----')).split('.', maxsplit=1)[0]:>4} {unit:<{col2 - 5}} "
                            f"{'Home Load Tot':<{col3}}: {sb.get('to_home_load') or '----':>4} W"
                        )
                        if "third_party_pv" in site:
                            CONSOLE.info(
                                f"{'Ext PV Surplus':<{col1}}: {site.get('third_party_pv', '----')!s:>4} {unit:<{col2 - 5}} "
                                f"{'Switch 0W':<{col3}}: {'ON' if site.get('switch_0w') else 'OFF'}"
                            )
                        # System config and power limit
                        details = site.get("site_details") or {}
                        if "legal_power_limit" in details:
                            CONSOLE.info(
                                f"{'Legal Pwr Limit':<{col1}}: {details.get('legal_power_limit', '----'):>4} {unit:<{col2 - 5}} "
                                f"{'Parallel Type':<{col3}}: {(details.get('parallel_type') or '---------')!s}"
                            )
                        features = site.get("feature_switch") or {}
                        if mode := site.get("scene_mode") or site.get(
                            "user_scene_mode"
                        ):
                            mode_name = next(
                                iter(
                                    [
                                        item.name
                                        for item in SolarbankUsageMode
                                        if item.value == mode
                                    ]
                                ),
                                ("Unknown" if mode else None),
                            )
                            feat1 = features.get("heating")
                            CONSOLE.info(
                                f"{'Active Mode':<{col1}}: {str(mode_name).capitalize() + ' (' + str(mode) + ')' if mode_name else '---------':<{col2}} "
                                f"{'Heating':<{col3}}: {'ON' if feat1 else '---' if feat1 is None else 'OFF'}"
                            )
                        if "offgrid_with_micro_inverter_alert" in features:
                            feat1 = features.get("offgrid_with_micro_inverter_alert")
                            feat2 = features.get("micro_inverter_power_exceed")
                            CONSOLE.info(
                                f"{'Offgrid Alert':<{col1}}: {'ON' if feat1 else '---' if feat1 is None else 'OFF':<{col2}} "
                                f"{'Inv. Pwr Exceed':<{col3}}: {'ON' if feat2 else '---' if feat2 is None else 'OFF'}"
                            )
                    if (hes := site.get("hes_info") or {}) and len(
                        hes.get("hes_list", [])
                    ) > 0:
                        # print hes totals
                        CONSOLE.info(
                            f"{'Parallel Devs':<{col1}}: {hes.get('numberOfParallelDevice', '---'):>3} {'':<{col2 - 4}} "
                            f"{'Battery count':<{col3}}: {hes.get('batCount', '---'):>3}"
                        )
                        CONSOLE.info(
                            f"{'Main SN':<{col1}}: {hes.get('main_sn', 'unknown'):<{col2}} "
                            f"{'System Code':<{col3}}: {hes.get('systemCode', 'unknown')}"
                        )
                        feat1 = hes.get("connected")
                        CONSOLE.info(
                            f"{'Connected':<{col1}}: {'YES' if feat1 else '---' if feat1 is None else ' NO':>3} {'':<{col2 - 4}} "
                            f"{'Repost time':<{col3}}: {hes.get('rePostTime', '---'):>3} min?"
                        )
                        CONSOLE.info(
                            f"{'Net status':<{col1}}: {hes.get('net', '---'):>3} {'':<{col2 - 4}} "
                            f"{'Real net':<{col3}}: {hes.get('realNet', '---'):>3}"
                        )
                        feat1 = hes.get("isAddHeatPump")
                        feat2 = hes.get("supportDiesel")
                        CONSOLE.info(
                            f"{'Has heat pump':<{col1}}: {'YES' if feat1 else '---' if feat1 is None else ' NO':>3} {'':<{col2 - 4}} "
                            f"{'Support diesel':<{col3}}: {'YES' if feat2 else '---' if feat2 is None else ' NO':>3}"
                        )
                    if ai_runtime := (site.get("site_details") or {}).get(
                        "ai_ems_runtime"
                    ):
                        runtime = (
                            timedelta(seconds=int(sec) * (-1))
                            if str(sec := ai_runtime.get("left_time"))
                            .replace("-", "")
                            .replace(".", "")
                            .isdigit()
                            else None
                        )
                        status = ai_runtime.get("status")
                        CONSOLE.info(
                            f"{'AI Collection':<{col1}}: {('-' if runtime.days < 0 else '') + str(abs(runtime)):<{col2}} "
                            f"{'Collect Status':<{col3}}: {str(ai_runtime.get('status_desc')).capitalize()} ({status})"
                        )
                    CONSOLE.info("-" * 80)
            else:
                CONSOLE.info("-" * 80)
            CONSOLE.info(
                f"{'Device [' + dev.get('device_pn', '') + ']':<{col1}}: {Color.MAG}{(dev.get('name', 'NoName')):<{col2}}{co} "
                f"{'Alias':<{col3}}: {Color.MAG}{dev.get('alias', 'Unknown')}{co}"
            )
            CONSOLE.info(
                f"{'Serialnumber':<{col1}}: {sn:<{col2}} "
                f"{'Admin':<{col3}}: {'YES' if admin else 'NO'}"
            )
            if m1 := cm and mqtt.get("local_timestamp", 0):
                m1 = datetime.fromtimestamp(m1).strftime("%Y-%m-%d %H:%M:%S")
                m2 = cm and datetime.fromtimestamp(
                    mqtt.get("utc_timestamp", 0)
                ).strftime("%Y-%m-%d %H:%M:%S")
                CONSOLE.info(
                    f"{'Local Time':<{col1}}: {m1 and (c or cm)}{m1:<{col2}}{co} "
                    f"{'UTC Time':<{col3}}: {m2 and (c or cm)}{m2}{co}"
                )
            if integrated := dev.get("intgr_device") or {}:
                CONSOLE.info(
                    f"{'Integrator':<{col1}}: {str(integrated.get('integrator')).capitalize():<{col2}} "
                    f"{'Access Group':<{col3}}: {integrated.get('access_group')!s}"
                )
            for fsn, fitting in (dev.get("fittings") or {}).items():
                CONSOLE.info(
                    f"{'Accessory':<{col1}}: {fitting.get('device_name', ''):<{col2}} "
                    f"{'Serialnumber':<{col3}}: {fsn}"
                )
            if not dev.get("is_passive"):
                wt = dev.get("wireless_type") or ""
                net = (
                    ((dev.get("relate_type") or [])[int(wt) : int(wt) + 1] or [""])[0]
                    if str(wt).isdigit()
                    else ""
                )
                CONSOLE.info(
                    f"{'Wireless Type':<{col1}}: {(dev.get('wireless_type') or '') + (' (' + (net.capitalize() or 'Unknown') + ')') if wt else '':<{col2}} "
                    f"{'Bluetooth MAC':<{col3}}: {dev.get('bt_ble_mac') or ''}"
                )
                CONSOLE.info(
                    f"{'Wifi SSID':<{col1}}: {dev.get('wifi_name', ''):<{col2}} "
                    f"{'Wifi MAC':<{col3}}: {dev.get('wifi_mac') or ''}"
                )
                online = dev.get("wifi_online")
                m2 = c and mqtt.get("wifi_signal", "")
                CONSOLE.info(
                    f"{'Wifi State':<{col1}}: {('Unknown' if online is None else 'Online' if online else 'Offline'):<{col2}} "
                    f"{'Signal':<{col3}}: {m2 and c}{m2 or dev.get('wifi_signal') or '---':>4} %{co} ({dev.get('rssi') or '---'} dBm)"
                )
                if support := dev.get("is_support_wired"):
                    online = dev.get("wired_connected")
                    CONSOLE.info(
                        f"{'Wired state':<{col1}}: {('Unknown' if online is None else 'Connected' if online else 'Disconnected'):<{col2}} "
                        f"{'Support Wired':<{col3}}: {('Unknown' if support is None else 'YES' if support else 'NO')}"
                    )
                upgrade = dev.get("auto_upgrade")
                ota = dev.get("is_ota_update")
                m1 = c and mqtt.get("sw_version", "")
                CONSOLE.info(
                    f"{'SW Version':<{col1}}: {m1 and c}{(m1 or (dev.get('sw_version', 'Unknown')) + ' (' + ('Unknown' if ota is None else 'Update' if ota else 'Latest') + ')'):<{col2}}{co} "
                    f"{'Auto-Upgrade':<{col3}}: {'Unknown' if upgrade is None else 'Enabled' if upgrade else 'Disabled'} (OTA {dev.get('ota_version') or 'Unknown'})"
                )
                for item in dev.get("ota_children") or []:
                    ota = item.get("need_update")
                    forced = item.get("force_upgrade")
                    CONSOLE.info(
                        f"{' -Component':<{col1}}: {item.get('device_type', 'Unknown') + ' (' + ('Unknown' if ota is None else 'Update' if ota else 'Latest') + ')':<{col2}} "
                        f"{' -Version':<{col3}}: {item.get('rom_version_name') or 'Unknown'}{' (Forced)' if forced else ''}"
                    )
                if mdev := self.mqtt_devices.get(sn):
                    CONSOLE.info(
                        f"{'MQTT Device':<{col1}}: {cm}{('Connected' if mdev.is_connected() else 'Disconnected'):<{col2}}{co} "
                        f"{'Subscription':<{col3}}: {cm}{('Active' if mdev.is_subscribed() else 'Inactive')}{co}"
                    )

            if devtype == SolixDeviceType.COMBINER_BOX.value:
                CONSOLE.info(
                    f"{'Cloud Status':<{col1}}: {str(dev.get('status_desc', '-------')).capitalize():<{col2}} "
                    f"{'Status Code':<{col3}}: {dev.get('status', '-')!s}"
                )
                CONSOLE.info(
                    f"{'Dock Status':<{col1}}: {str(dev.get('dock_status_desc', '-------')).capitalize():<{col2}} "
                    f"{'Status Code':<{col3}}: {dev.get('dock_status', '-')!s}"
                )
                unit = dev.get("power_unit", "W")
                # print station details
                CONSOLE.info(
                    f"{'Actual power':<{col1}}: {dev.get('current_power', '----'):>4} {unit:<{col2 - 5}} "
                    f"{'All AC In Limit':<{col3}}: {dev.get('all_ac_input_limit', '----'):>4} W"
                )
                CONSOLE.info(
                    f"{'All Pwr Limit':<{col1}}: {dev.get('all_power_limit', '----'):>4} {unit:<{col2 - 5}} "
                    f"{'Pwr Limit Opt':<{col3}}: {dev.get('power_limit_option') or '----'!s}"
                )
                feat1 = dev.get("allow_grid_export")
                CONSOLE.info(
                    f"{'Min SOC':<{col1}}: {(dev.get('power_cutoff') or dev.get('output_cutoff_data') or '--')!s:>4} {'%':<{col2 - 5}} "
                    f"{'Grid export':<{col3}}: {'ON' if feat1 else '---' if feat1 is None else 'OFF':>4}"
                )

            elif devtype == SolixDeviceType.SOLARBANK.value:
                unit = dev.get("power_unit", "W")
                CONSOLE.info(
                    f"{'Cloud Status':<{col1}}: {str(dev.get('status_desc', '-------')).capitalize():<{col2}} "
                    f"{'Status Code':<{col3}}: {dev.get('status', '-')!s}"
                )
                m2 = str(c and mqtt.get("charging_status", ""))
                CONSOLE.info(
                    f"{'Charge Status':<{col1}}: {str(dev.get('charging_status_desc', '-------')).capitalize():<{col2}} "
                    f"{'Status Code':<{col3}}: {m2 and c}{m2 or dev.get('charging_status', '-')!s}{co}"
                )
                if aiems := (dev.get("schedule") or {}).get("ai_ems") or {}:
                    status = aiems.get("status")
                    CONSOLE.info(
                        f"{'AI Status':<{col1}}: {str(SolarbankAiemsStatus(status).name if status in iter(SolarbankUsageMode) else '-----').capitalize() + ' (' + str(status) + ')':<{col2}} "
                        f"{'AI Enabled':<{col3}}: {'YES' if aiems.get('enable') else 'NO'}"
                    )
                m1 = c and mqtt.get("battery_soc", "")
                m2 = c and mqtt.get("power_cutoff", "")
                if m3 := cm and mqtt.get("battery_soh", ""):
                    m3 = f"{float(m3):6.2f}"
                soc = f"{m1 or dev.get('battery_soc', '---'):>4} %"
                CONSOLE.info(
                    f"{'Battery SOC/SOH':<{col1}}: {m1 and c}{soc} /{m3 and (c or cm)}{m3 if m3 else ' --.--':>4} {'%':<{col2 - 15}}{co} "
                    f"{'Min SOC':<{col3}}: {m2 and c}{m2 or (dev.get('power_cutoff') or dev.get('output_cutoff_data') or '--')!s:>4} %{co}"
                )
                energy = f"{dev.get('battery_energy', '----'):>4} Wh"
                CONSOLE.info(
                    f"{'Battery Energy':<{col1}}: {cc}{energy:<{col2}}{co} "
                    f"{'Capacity':<{col3}}: {cc}{customized.get('battery_capacity') or dev.get('battery_capacity', '----')!s:>4} Wh{co}"
                )
                unit = dev.get("power_unit", "W")
                if dev.get("generation", 0) > 1:
                    m1 = c and mqtt.get("expansion_packs", "")
                    CONSOLE.info(
                        f"{'Exp. Batteries':<{col1}}: {m1 and c}{m1 or dev.get('sub_package_num', '-'):>4} {'Pcs':<{col2 - 5}}{co} "
                        f"{'AC Socket':<{col3}}: {dev.get('ac_power', '---'):>4} {unit}"
                    )
                    for i in range(1, 6):
                        if m1 := cm and mqtt.get(f"exp_{i}_sn", ""):
                            m2 = cm and mqtt.get(f"exp_{i}_soc", "")
                            m3 = cm and mqtt.get(f"exp_{i}_temperature", "")
                            if m3 and mqtt.get("temp_unit_fahrenheit"):
                                m3 = f"{float(m3) * 9 / 5 + 32:>4} °F"
                            else:
                                m3 = f"{m3:>4} °C"
                            CONSOLE.info(
                                f"{'Exp. ' + str(i) + ' SN':<{col1}}: {m1 and (c or cm)}{m1:<{col2}}{co} "
                                f"{'Exp. ' + str(i) + ' SOC/Temp':<{col3}}: {m2 and (c or cm)}{m2:>3} %{co} / {m3 and (c or cm)}{m3}{co}"
                            )
                        else:
                            break
                # Solarbank power limits
                if "power_limit" in dev:
                    m1 = c and mqtt.get("max_load", "")
                    m2 = c and mqtt.get("ac_input_limit", "")
                    CONSOLE.info(
                        f"{'Power Limit':<{col1}}: {m1 and c}{m1 or dev.get('power_limit', '----'):>4} {unit:<{col2 - 5}}{co} "
                        f"{'AC Input Limit':<{col3}}: {m2 and c}{m2 or dev.get('ac_input_limit', '----'):>4} W{co}"
                    )
                    CONSOLE.info(
                        f"{'Pwr Limit Opt':<{col1}}: {(dev.get('power_limit_option') or '------')!s:<{col2}} "
                        f"{'Limit Opt Real':<{col3}}: {(dev.get('power_limit_option_real') or '------')!s}"
                    )
                if "pv_power_limit" in dev:
                    m1 = c and mqtt.get("pv_limit", "")
                    m2 = c and (
                        "OFF"
                        if mqtt.get("grid_export_disabled", "")
                        else "ON"
                        if "grid_export_disabled" in mqtt
                        else None
                    )
                    feat1 = dev.get("allow_grid_export")
                    CONSOLE.info(
                        f"{'Solar Limit':<{col1}}: {m1 and c}{m1 or dev.get('pv_power_limit', '----'):>4} {unit:<{col2 - 5}}{co} "
                        f"{'Grid export':<{col3}}: {m2 and c}{m2 or ('ON' if feat1 else '---' if feat1 is None else 'OFF'):>4}{co}"
                    )
                m1 = c and mqtt.get("photovoltaic_power", "")
                m2 = c and mqtt.get("output_power", "")
                m3 = cm and mqtt.get("pv_yield", "")
                m4 = cm and mqtt.get("output_energy", "")
                CONSOLE.info(
                    f"{'Solar Power':<{col1}}: {m1 and c}{m1 or dev.get('input_power', '---'):>4} {unit}{m3 and (c or cm)}{((' (' + m3 + ' kWh)') if m3 else ''):<{col2 - 6}}{co} "
                    f"{'Output Power':<{col3}}: {m2 and c}{m2 or dev.get('output_power', '---'):>4} {unit}{m4 and (c or cm)}{((' (' + m4 + ' kWh)') if m4 else '')}{co}"
                )
                # show PV and battery voltage if available
                if m1 := cm and mqtt.get("pv_1_voltage", ""):
                    m2 = cm and mqtt.get("pv_2_voltage", "")
                    m3 = cm and mqtt.get("battery_voltage", "")
                    CONSOLE.info(
                        f"{'Voltage Ch 1/2':<{col1}}: {m1 and (c or cm)}{m1 or '-.---':>6} / {m2 or '-.---':>6} {'V':<{col2 - 16}}{co} "
                        f"{'Voltage Battery':<{col3}}: {m3 and (c or cm)}{m3 or '-.---':>6} V{co}"
                    )
                # show each MPPT for Solarbank 2+
                names = dev.get("pv_name") or {}
                if "solar_power_1" in dev:
                    name1 = names.get("pv1_name") or ""
                    name2 = names.get("pv2_name") or ""
                    m1 = c and mqtt.get("pv_1_power", "")
                    m2 = c and mqtt.get("pv_2_power", "")
                    CONSOLE.info(
                        f"{'Solar Ch_1':<{col1}}: {m1 and c}{m1 or dev.get('solar_power_1', '---'):>4} {unit}{co}{(' (' + name1 + ')' if name1 else ''):<{col2 - 6}} "
                        f"{'Solar Ch_2':<{col3}}: {m2 and c}{m2 or dev.get('solar_power_2', '---'):>4} {unit}{co}{(' (' + name2 + ')' if name2 else '')}"
                    )
                    if "solar_power_3" in dev:
                        name1 = names.get("pv3_name") or ""
                        name2 = names.get("pv4_name") or ""
                        m1 = c and mqtt.get("pv_3_power", "")
                        m2 = c and mqtt.get("pv_4_power", "")
                        CONSOLE.info(
                            f"{'Solar Ch_3':<{col1}}: {m1 and c}{m1 or dev.get('solar_power_3', '---'):>4} {unit}{co}{(' (' + name1 + ')' if name1 else ''):<{col2 - 6}} "
                            f"{'Solar Ch_4':<{col3}}: {m2 and c}{m2 or dev.get('solar_power_4', '---'):>4} {unit}{co}{(' (' + name2 + ')' if name2 else '')}"
                        )
                if "micro_inverter_power" in dev:
                    name1 = names.get("micro_inverter_name") or ""
                    CONSOLE.info(
                        f"{'Inverter Power':<{col1}}: {dev.get('micro_inverter_power', '---'):>4} {unit + (' (' + name1 + ')' if name1 else ''):<{col2 - 5}} "
                        f"{'Heating Power':<{col3}}: {dev.get('pei_heating_power', '---'):>4} {unit}"
                    )
                if "micro_inverter_power_limit" in dev:
                    CONSOLE.info(
                        f"{'Inverter Limit':<{col1}}: {dev.get('micro_inverter_power_limit', '---'):>4} {unit:<{col2 - 5}} "
                        f"{'Low Limit':<{col3}}: {dev.get('micro_inverter_low_power_limit', '---'):>4} {unit}"
                    )
                if "grid_to_battery_power" in dev:
                    m1 = c and mqtt.get("grid_to_battery_power", "")
                    m2 = c and mqtt.get("ac_output_power_signed", "")
                    CONSOLE.info(
                        f"{'Grid to Battery':<{col1}}: {m1 and c}{m1 or dev.get('grid_to_battery_power', '---'):>4} {unit:<{col2 - 5}}{co} "
                        f"{'AC Input Power':<{col3}}: {m2 and c}{m2 or dev.get('other_input_power', '---'):>4} {unit}{co}"
                    )
                m1 = c and mqtt.get("charging_power", "")
                m2 = c and mqtt.get("discharging_power", "")
                m3 = cm and mqtt.get("charged_energy", "")
                m4 = cm and mqtt.get("discharged_energy", "")
                CONSOLE.info(
                    f"{'Battery Charge':<{col1}}: {m1 and c}{m1 or dev.get('bat_charge_power', '---'):>4} {unit}{m3 and (c or cm)}{(' (' + m3 + ' kWh)') if m3 else '':<{col2 - 6}}{co} "
                    f"{'Battery Dischrg':<{col3}}: {m2 and c}{m2 or dev.get('bat_discharge_power', '---'):>4} {unit}{m4 and (c or cm)}{(' (' + m4 + ' kWh)') if m4 else ''}{co}"
                )
                if m1 := cm and mqtt.get("system_efficiency", ""):
                    m1 = f"{float(m1):6.2f}"
                    if m2 := cm and mqtt.get("battery_efficiency", ""):
                        m2 = f"{float(m2):6.2f}"
                    CONSOLE.info(
                        f"{'System Eff.':<{col1}}: {cc}{m1 or '  --.--':>7} {'%':<{col2 - 8}}{co} "
                        f"{'Battery Eff.':<{col3}}: {cc}{m2 or '  --.--':>7} %{co}"
                    )
                preset = dev.get("set_output_power") or "---"
                site_preset = dev.get("set_system_output_power") or "---"
                m1 = c and mqtt.get("battery_power_signed", "")
                m2 = c and mqtt.get("home_load_preset", "")
                CONSOLE.info(
                    f"{'Battery Power':<{col1}}: {m1 and c}{m1 or dev.get('charging_power', '---'):>4} {unit:<{col2 - 5}}{co} "
                    f"{'Device Preset':<{col3}}: {m2 and c}{m2 or preset:>4} {unit}{co}"
                )
                if dev.get("generation", 0) > 1:
                    demand = site.get("home_load_power") or ""
                    load = (site.get("solarbank_info") or {}).get("to_home_load") or ""
                    diff = ""
                    if m1 := c and str(mqtt.get("home_demand", "")):
                        demand = m1
                    if m2 := c and str(
                        mqtt.get("ac_output_power_signed", "")
                        or mqtt.get("ac_output_power", "")
                    ):
                        load = m2
                    with contextlib.suppress(ValueError):
                        if float(demand) > float(load):
                            diff = "(-)"
                        elif float(demand) < float(load):
                            diff = "(+)"
                    CONSOLE.info(
                        f"{'Home Demand':<{col1}}: {str(m1) and c}{demand or '---':>4} {unit:<{col2 - 5}}{co} "
                        f"{'SB Home Load':<{col3}}: {str(m2) and c}{load or '---':>4} {unit}{co}  {diff}"
                    )
                    # Total smart plug power and other power?
                    CONSOLE.info(
                        f"{'Smart Plugs':<{col1}}: {(site.get('smart_plug_info') or {}).get('total_power') or '---':>4} {unit:<{col2 - 5}} "
                        f"{'Other (Plan)':<{col3}}: {site.get('other_loads_power') or '---':>4} {unit}"
                    )
                    if m3 := cm and str(mqtt.get("light_mode", "")):
                        m1 = cm and mqtt.get("light_off_switch", "")
                        m2 = cm and mqtt.get("ac_socket_switch", "")
                        mode = (
                            [
                                item.name
                                for item in SolarbankLightMode
                                if item.value == m3
                            ]
                            or [SolarbankLightMode.unknown.name]
                        )[0].capitalize()
                        CONSOLE.info(
                            f"{'Light':<{col1}}: {str(m1) and (c or cm)}{'OFF' if m1 else ' ON'} {'(Mode: ' + mode + ')':<{col2 - 4}}{co} "
                            f"{'AC Socket':<{col3}}: {str(m2) and (c or cm)}{' ON' if m2 else 'OFF'}{co}"
                        )
                    if m1 := cm and str(mqtt.get("device_timeout_minutes", "")):
                        m2 = cm and str(mqtt.get("max_load_legal", ""))
                        CONSOLE.info(
                            f"{'Device Timeout':<{col1}}: {m1 and (c or cm)}{m1 + ' Minutes':<{col2}}{co} "
                            f"{'Max load legal':<{col3}}: {m2 and (c or cm)}{m2 if m2 else '----':>4} W{co}"
                        )
                # update schedule with device details refresh and print it
                CONSOLE.info(
                    f"{'Schedule  (Now)':<{col1}}: {datetime.now().astimezone().strftime('%H:%M:%S UTC %z'):<{col2}} "
                    f"{'System Preset':<{col3}}: {str(site_preset).replace('W', ''):>4} W"
                )
                if admin:
                    # print schedule
                    common.print_schedule(dev.get("schedule") or {})

            elif devtype == SolixDeviceType.INVERTER.value:
                CONSOLE.info(
                    f"{'Cloud Status':<{col1}}: {str(dev.get('status_desc', '-------')).capitalize():<{col2}} "
                    f"{'Status Code':<{col3}}: {dev.get('status', '-')!s}"
                )
                unit = dev.get("power_unit", "W")
                CONSOLE.info(
                    f"{'AC Power':<{col1}}: {dev.get('generate_power', '----'):>4} {unit:<{col2 - 5}} "
                    f"{'Inverter Limit':<{col3}}: {dev.get('preset_inverter_limit', '---'):>4} {unit}"
                )

            elif devtype == SolixDeviceType.SMARTMETER.value:
                CONSOLE.info(
                    f"{'Cloud Status':<{col1}}: {str(dev.get('status_desc', '-------')).capitalize():<{col2}} "
                    f"{'Status Code':<{col3}}: {dev.get('status', '-')!s}"
                )
                CONSOLE.info(
                    f"{'Grid Status':<{col1}}: {str(dev.get('grid_status_desc', '-------')).capitalize():<{col2}} "
                    f"{'Status Code':<{col3}}: {dev.get('grid_status', '-')!s}"
                )
                unit = "W"
                m1 = cm and mqtt.get("grid_to_home_power", "")
                m2 = cm and mqtt.get("pv_to_grid_power", "")
                m3 = cm and mqtt.get("grid_import_energy", "")
                m4 = cm and mqtt.get("grid_export_energy", "")
                CONSOLE.info(
                    f"{'Grid Import':<{col1}}: {m1 and (c or cm)}{m1 or dev.get('grid_to_home_power', '----'):>4} {unit}{m3 and (c or cm)}{(' (' + m3 + ' kWh)' if m3 else ''):<{col2 - 6}}{co} "
                    f"{'Grid Export':<{col3}}: {m2 and (c or cm)}{m2 or dev.get('photovoltaic_to_grid_power', '----'):>4} {unit}{m4 and (c or cm)}{(' (' + m4 + ' kWh)' if m4 else '')}{co}"
                )

            elif devtype == SolixDeviceType.SMARTPLUG.value:
                CONSOLE.info(
                    f"{'Cloud Status':<{col1}}: {str(dev.get('status_desc', '-------')).capitalize():<{col2}} "
                    f"{'Status Code':<{col3}}: {dev.get('status', '-')!s}"
                )
                CONSOLE.info(
                    f"{'Device Error':<{col1}}: {'YES' if dev.get('err_code') else ' NO':<{col2}} "
                    f"{'Error Code':<{col3}}: {dev.get('err_code', '---')!s}"
                )
                feat1 = dev.get("auto_switch")
                feat2 = dev.get("priority")
                CONSOLE.info(
                    f"{'AI switched':<{col1}}: {'YES' if feat1 else '---' if feat1 is None else ' NO':>3} {'(Prio: ' + ('-' if feat2 is None else str(feat2)) + ')':<{col2 - 4}} "
                    f"{'Runtime':<{col3}}: {json.dumps(dev.get('running_time')).replace('null', '-------'):>3}"
                )
                unit = dev.get("power_unit", "W")
                CONSOLE.info(
                    f"{'Plug Power':<{col1}}: {dev.get('current_power', ''):>4} {unit:<{col2 - 5}} "
                    f"{'Tag':<{col3}}: {dev.get('tag', '')}"
                )
                if dev.get("energy_today"):
                    CONSOLE.info(
                        f"{'Energy Today':<{col1}}: {dev.get('energy_today') or '-.--':>4} {'kWh':<{col2 - 5}} "
                        f"{'Last Period':<{col3}}: {dev.get('energy_last_period') or '-.--':>4} kWh"
                    )

            elif devtype in [
                SolixDeviceType.POWERPANEL.value,
                SolixDeviceType.HES.value,
            ]:
                if hes := dev.get("hes_data") or {}:
                    CONSOLE.info(
                        f"{'Station ID':<{col1}}: {hes.get('station_id', '-------'):<{col2}}     (Type: {str(hes.get('type', '---')).upper()})"
                    )
                    CONSOLE.info(
                        f"{'Cloud Status':<{col1}}: {str(hes.get('status_desc', '-------')).capitalize():<{col2}} "
                        f"{'Status Code':<{col3}}: {hes.get('online_status', '-')!s}"
                    )
                    CONSOLE.info(
                        f"{'Network Status':<{col1}}: {str(hes.get('network_status_desc', '-------')).capitalize():<{col2}} "
                        f"{'Status Code':<{col3}}: {hes.get('network_status', '-')!s}"
                    )
                    CONSOLE.info(
                        f"{'Grid Status':<{col1}}: {str(hes.get('grid_status_desc', '-------')).capitalize():<{col2}} "
                        f"{'Status Code':<{col3}}: {hes.get('grid_status', '-')!s}"
                    )
                    CONSOLE.info(
                        f"{'Role Status':<{col1}}: {str(hes.get('role_status_desc', '-------')).capitalize():<{col2}} "
                        f"{'Status Code':<{col3}}: {hes.get('master_slave_status', '-')!s}"
                    )
                if "status_desc" in dev:
                    CONSOLE.info(
                        f"{'Cloud Status':<{col1}}: {str(dev.get('status_desc', '-------')).capitalize():<{col2}} "
                        f"{'Status Code':<{col3}}: {dev.get('status', '-')!s}"
                    )
                if "battery_capacity" in dev:
                    CONSOLE.info(
                        f"{'Capacity':<{col1}}: {cc}{customized.get('battery_capacity') or dev.get('battery_capacity', '-----')!s:>5} {'Wh':<{col2 - 6}}{co} "
                        f"{'Battery Count':<{col3}}: {dev.get('batCount') or '-'}"
                    )
                if avg := dev.get("average_power") or {}:
                    unit = str(avg.get("power_unit") or "").upper()
                    CONSOLE.info(
                        f"{'Valid ⌀ before':<{col1}}: {avg.get('valid_time', 'Unknown'):<{col2}} "
                        f"{'Last Check':<{col3}}: {avg.get('last_check', 'Unknown')!s}"
                    )
                    CONSOLE.info(
                        f"{'Battery SOC':<{col1}}: {avg.get('state_of_charge') or '---':>5} {'%':<{col2 - 6}} "
                        f"{'Battery Energy':<{col3}}: {cc}{dev.get('battery_energy', '-----'):>5} Wh{co}"
                    )
                    CONSOLE.info(
                        f"{'Solar Power ⌀':<{col1}}: {avg.get('solar_power_avg') or '-.--':>5} {unit:<{col2 - 6}} "
                        f"{'Home Usage ⌀':<{col3}}: {avg.get('home_usage_avg') or '-.--':>5} {unit}"
                    )
                    CONSOLE.info(
                        f"{'Charge Power ⌀':<{col1}}: {avg.get('charge_power_avg') or '-.--':>5} {unit:<{col2 - 6}} "
                        f"{'Discharge Pwr ⌀':<{col3}}: {avg.get('discharge_power_avg') or '-.--':>5} {unit}"
                    )
                    CONSOLE.info(
                        f"{'Grid Import ⌀':<{col1}}: {avg.get('grid_import_avg') or '-.--':>5} {unit:<{col2 - 6}} "
                        f"{'Grid Export ⌀':<{col3}}: {avg.get('grid_export_avg') or '-.--':>5} {unit}"
                    )
            elif devtype in [SolixDeviceType.EV_CHARGER.value]:
                CONSOLE.info(
                    f"{'Cloud Status':<{col1}}: {str(dev.get('status_desc', '-------')).capitalize():<{col2}} "
                    f"{'Status Code':<{col3}}: {dev.get('status', '-')!s}"
                )
                CONSOLE.info(
                    f"{'OCPP Status':<{col1}}: {str(dev.get('ocpp_status_desc', '-------')).capitalize():<{col2}} "
                    f"{'Status Code':<{col3}}: {dev.get('ocpp_connect_status', '-')!s}"
                )
                CONSOLE.info(
                    f"{'Device Error':<{col1}}: {'YES' if dev.get('err_code') else ' NO':<{col2}} "
                    f"{'Error Code':<{col3}}: {dev.get('err_code', '---')!s}"
                )
                CONSOLE.info(
                    f"{'Group':<{col1}}: {(dev.get('group_info') or '-------')!s:<{col2}} "
                    f"{'Access Group':<{col3}}: {integrated.get('access_group')!s}"
                )

            elif devtype == SolixDeviceType.PPS.value:
                if m1 := cm and str(mqtt.get("last_update", "")):
                    m2 = cm and str(mqtt.get("light_mode", ""))
                    CONSOLE.info(
                        f"{'Last Update':<{col1}}: {m1 and (c or cm)}{m1:<{col2}}{co} "
                        f"{'Light Mode':<{col1}}: {m2 and (c or cm)}"
                        f"{([item.name for item in SolixPpsDisplayMode if item.value == m2] or ['unknown'])[0].capitalize() + ' (' + m2 + ')':<{col2 - 6}}{co} "
                    )
                if m1 := cm and str(mqtt.get("display_switch", "")):
                    m2 = cm and str(mqtt.get("display_timeout_seconds", ""))
                    m3 = cm and str(mqtt.get("display_mode", ""))
                    CONSOLE.info(
                        f"{'Display Ctrl':<{col1}}: {m1 and (c or cm)}{' ON' if m1 == '1' else 'OFF' if m1 == '0' else '(' + m1 + ')'} / "
                        f"{([item.name for item in SolixPpsDisplayMode if item.value == m3] or ['unknown'])[0].capitalize() + ' (' + m3 + ')':<{col2 - 6}}{co} "
                        f"{'Display Timeout':<{col3}}: {m2 and (c or cm)}{(m2 or '---'):>4} Sec.{co}"
                    )
                if m1 := cm and str(mqtt.get("ac_output_power_switch", "")):
                    m2 = cm and str(mqtt.get("dc_output_power_switch", ""))
                    m3 = cm and str(mqtt.get("ac_output_mode", ""))
                    m4 = cm and str(mqtt.get("dc_12v_output_mode", ""))
                    CONSOLE.info(
                        f"{'AC Out Ctrl':<{col1}}: {m1 and (c or cm)}{' ON' if m1 == '1' else 'OFF' if m1 == '0' else '(' + m1 + ')'} / "
                        f"{([item.name for item in SolixPpsOutputMode if item.value == m3] or ['unknown'])[0].capitalize() + ' (' + m3 + ')':<{col2 - 6}}{co} "
                        f"{'DC Out Ctrl':<{col3}}: {m2 and (c or cm)}{' ON' if m2 == '1' else 'OFF' if m2 == '0' else '(' + m2 + ')'} / "
                        f"{([item.name for item in SolixPpsOutputMode if item.value == m4] or ['unknown'])[0].capitalize() + ' (' + m4 + ')'}{co}"
                    )

                if m1 := cm and mqtt.get("battery_soc", ""):
                    soc = f"{m1:>4} %"
                    m2 = cm and mqtt.get("temperature", "")
                    if m2 and mqtt.get("temp_unit_fahrenheit"):
                        m2 = f"{float(m2) * 9 / 5 + 32:>4} °F"
                    else:
                        m2 = f"{m2:>4} °C"
                    if m3 := cm and mqtt.get("battery_soh", ""):
                        m3 = f"{float(m3):6.2f}"
                    CONSOLE.info(
                        f"{'Battery SOC/SOH':<{col1}}: {m1 and (c or cm)}{soc} /{m3 if m3 else ' --.--':>7} {'%':<{col2 - 16}}{co} "
                        f"{'Batt. Temp.':<{col3}}: {m2 and (c or cm)}{m2 or '-- °C'!s:>7}{co}"
                    )
                if m1 := cm and mqtt.get("exp_1_soc", ""):
                    soc = f"{m1:>4} %"
                    m2 = cm and mqtt.get("exp_1_temperature", "")
                    if m2 and mqtt.get("temp_unit_fahrenheit"):
                        m2 = f"{float(m2) * 9 / 5 + 32:>4} °F"
                    else:
                        m2 = f"{m2:>4} °C"
                    if m3 := cm and mqtt.get("exp_1_soh", ""):
                        m3 = f"{float(m3):6.2f}"
                    CONSOLE.info(
                        f"{'Exp. 1 SOC/SOH':<{col1}}: {m1 and (c or cm)}{soc} /{m3 if m3 else ' --.--':>7} {'%':<{col2 - 16}}{co} "
                        f"{'Exp. 1 Temp.':<{col3}}: {m2 and (c or cm)}{m2 or '-- °C'!s:>7}{co}"
                    )
                m1 = cm and str(mqtt.get("backup_charge_switch", ""))
                m2 = cm and mqtt.get("exp_1_type", "")
                if m1 or m2:
                    CONSOLE.info(
                        f"{'Backup charge':<{col1}}: {m1 is not None and (c or cm)}{' ON' if m1 == '1' else 'OFF' if m1 == '0' else m1:<{col2}}{co} "
                        f"{'Exp. Type':<{col3}}: {m2 and (c or cm)}{m2 or 'Unknown'}{co}"
                    )
                energy = f"{dev.get('battery_energy', '----'):>4} Wh"
                CONSOLE.info(
                    f"{'Battery Energy':<{col1}}: {cc}{energy:<{col2}}{co} "
                    f"{'Capacity':<{col3}}: {cc}{customized.get('battery_capacity') or dev.get('battery_capacity', '----')!s:>4} Wh{co}"
                )
                unit = "W"
                if m1 := cm and mqtt.get("max_load", ""):
                    m2 = cm and mqtt.get("device_timeout_minutes", "")
                    CONSOLE.info(
                        f"{'Max. Load':<{col1}}: {m1 and (c or cm)}{m1:>4} {unit:<{col2 - 5}}{co} "
                        f"{'Device Timeout':<{col3}}: {m2 and (c or cm)}{m2 or '----':>4} Min.{co}"
                    )
                if m1 := cm and mqtt.get("grid_to_battery_power", ""):
                    m2 = cm and mqtt.get("dc_input_power", "")
                    CONSOLE.info(
                        f"{'AC Input Power':<{col1}}: {m1 and (c or cm)}{m1:>4} {unit:<{col2 - 5}}{co} "
                        f"{'DC Input Power':<{col3}}: {m2 and (c or cm)}{m2 or '----':>4} {unit}{co}"
                    )
                if m1 := cm and mqtt.get("ac_output_power_total", ""):
                    m2 = cm and mqtt.get("ac_output_power", "")
                    CONSOLE.info(
                        f"{'AC Output Tot.':<{col1}}: {m1 and (c or cm)}{m1:>4} {unit:<{col2 - 5}}{co} "
                        f"{'AC Output Power':<{col3}}: {m2 and (c or cm)}{m2 or '----':>4} {unit}{co}"
                    )
                if m1 := cm and mqtt.get("usbc_1_power", ""):
                    m2 = cm and mqtt.get("usbc_2_power", "")
                    CONSOLE.info(
                        f"{'USB-C 1 Power':<{col1}}: {m1 and (c or cm)}{m1:>4} {unit:<{col2 - 5}}{co} "
                        f"{'USB-C 2 Power':<{col3}}: {m2 and (c or cm)}{m2 or '----':>4} {unit}{co}"
                    )
                if m1 := cm and mqtt.get("usba_1_power", ""):
                    m2 = cm and mqtt.get("usba_2_power", "")
                    CONSOLE.info(
                        f"{'USB-A 1 Power':<{col1}}: {m1 and (c or cm)}{m1:>4} {unit:<{col2 - 5}}{co} "
                        f"{'USB-A 2 Power':<{col3}}: {m2 and (c or cm)}{m2 or '----':>4} {unit}{co}"
                    )

            else:
                if "battery_capacity" in dev:
                    CONSOLE.info(
                        f"{'Capacity':<{col1}}: {cc}{customized.get('battery_capacity') or dev.get('battery_capacity', '----')!s:>4} {'Wh':<{col2 - 5}}{co} "
                        f"{'Battery Count':<{col3}}: {dev.get('batCount') or 'Unknown'}"
                    )

                CONSOLE.warning(
                    "No Solarbank, Inverter, Smart Meter, Smart Plug, Power Panel or HES device, further device details will be skipped"
                )
        # print optional user vehicles
        if self.showVehicles and (vehicles := self.api.account.get("vehicles") or {}):
            CONSOLE.info("=" * 80)
            CONSOLE.info(
                f"{Color.BLUE}Electric vehicle details for user '{self.api.account.get('nickname') or 'Unknown'}':{co}"
            )
            keys = set(vehicles.keys())
            for vehicleId, vehicle in vehicles.items():
                CONSOLE.info(
                    f"{'EV Name':<{col1}}: {Color.BLUE}{vehicle.get('vehicle_name', 'Unknown')}{co}  (Vehicle ID: {vehicleId})"
                )
                ev = SolixVehicle(vehicle=vehicle)
                CONSOLE.info(
                    f"{'EV Brand':<{col1}}: {ev.brand or 'Unknown':<{col2}} "
                    f"{'EV model':<{col3}}: {ev.model or 'Unknown'}"
                )
                CONSOLE.info(
                    f"{'Consumption':<{col1}}: {(round(ev.energy_consumption_per_100km, 1) if ev.energy_consumption_per_100km else '--.-')!s:>4} {'kWh / 100 km':<{col2 - 5}} "
                    f"{'EV Year':<{col3}}: {(ev.productive_year or '----')!s}"
                )
                CONSOLE.info(
                    f"{'Charge Limit':<{col1}}: {(round(ev.ac_max_charging_power, 1) if ev.ac_max_charging_power else '--.-')!s:>4} {'kWh':<{col2 - 5}} "
                    f"{'Capacity':<{col3}}: {(round(ev.battery_capacity, 1) if ev.battery_capacity else '--.-')!s:>4} kW"
                )
                CONSOLE.info(
                    f"{'Is Charging':<{col1}}: {('YES' if vehicle.get('is_smart_charging') else 'NO'):<{col2}} "
                    f"{'Is Default EV':<{col3}}: {('YES' if vehicle.get('is_default_vehicle') else 'NO')}"
                )
                keys.discard(vehicleId)
                if keys:
                    CONSOLE.info("-" * 80)
        # print optional energy details
        if self.energy_stats and not self.device_filter:
            for site_id, site in [
                (s, d)
                for s, d in self.api.sites.items()
                if (not self.site_selected or s == self.site_selected)
            ]:
                details = site.get("site_details") or {}
                customized = site.get("customized") or {}
                CONSOLE.info("=" * 80)
                CONSOLE.info(
                    f"{Color.CYAN}Energy details for System {(site.get('site_info') or {}).get('site_name', 'Unknown')} (Site ID: {site_id}):{co}"
                )
                if len(totals := site.get("statistics") or []) >= 3:
                    CONSOLE.info(
                        f"{'Total Produced':<{col1}}: {totals[0].get('total', '---.--'):>6} {str(totals[0].get('unit', '')).upper():<{col2 - 8}}  "
                        f"{'Carbon Saved':<{col3}}: {totals[1].get('total', '---.--'):>6} {str(totals[1].get('unit', '')).upper()}"
                    )
                    if co2 := details.get("co2_ranking") or {}:
                        CONSOLE.info(
                            f"{'CO2 Ranking':<{col1}}: {co2.get('ranking') or '----':>6} {'(' + str(co2.get('tree') or '--.-') + ' Trees)':<{col2 - 8}}  "
                            f"{'Message':<{col3}}: {co2.get('content')}"
                        )
                    price = (
                        f"{float(price):.2f}"
                        if (price := str(details.get("price")))
                        .replace("-", "", 1)
                        .replace(".", "", 1)
                        .isdigit()
                        else "--.--"
                    )
                    unit = details.get("site_price_unit") or ""
                    CONSOLE.info(
                        f"{'Max Savings':<{col1}}: {totals[2].get('total', '---.--'):>6} {totals[2].get('unit', ''):<{col2 - 8}}  "
                        f"{'Price kWh':<{col3}}: {price:>6} {unit} (Fix)"
                    )
                if ai_profits := site.get("aiems_profit"):
                    unit = ai_profits.get("unit") or ""
                    CONSOLE.info(
                        f"{'AI Savings':<{col1}}: {ai_profits.get('aiems_profit_total', '---.--'):>6} {unit:<{col2 - 8}}  "
                        f"{'AI Advantage':<{col3}}: {ai_profits.get('aiems_self_use_diff', '---.--'):>6} {unit} ({ai_profits.get('percentage', '---.--')} %)"
                    )
                price_type = details.get("price_type") or ""
                dynamic = (
                    details.get("dynamic_price")
                    or customized.get("dynamic_price")
                    or {}
                )
                dyn_details = details.get("dynamic_price_details") or {}
                provider = SolixPriceProvider(provider=dynamic)
                if price_type or dynamic:
                    dyn_price = None
                    dyn_unit = None
                    if price_type in [SolixPriceTypes.DYNAMIC.value] or dynamic:
                        dyn_price = (
                            f"{float(price):.2f}"
                            if (price := dyn_details.get("dynamic_price_total") or "")
                            .replace("-", "", 1)
                            .replace(".", "", 1)
                            .isdigit()
                            else "--.--"
                        )
                        dyn_unit = dyn_details.get("spot_price_unit") or ""
                    elif price_type in [SolixPriceTypes.USE_TIME.value] and (
                        dev := self.api.devices.get(
                            (
                                next(
                                    iter(
                                        (site.get("solarbank_info") or {}).get(
                                            "solarbank_list"
                                        )
                                        or [{}]
                                    ),
                                    {},
                                )
                            ).get("device_sn")
                            or ""
                        )
                    ):
                        dyn_price = (
                            f"{float(price):.2f}"
                            if (price := dev.get("preset_tariff_price") or "")
                            .replace("-", "", 1)
                            .replace(".", "", 1)
                            .isdigit()
                            else "---.--"
                        )
                        dyn_unit = dev.get("preset_tariff_currency")
                    CONSOLE.info(
                        f"{'Active Price':<{col1}}: {dyn_price or price:>6} {(dyn_unit or unit) + ' (' + (price_type.capitalize() or '------') + ')':<{col2 - 7}} "
                        f"{'Price Provider':<{col3}}: {provider!s}"
                    )
                    if (spot := dyn_details.get("spot_price_mwh")) is not None:
                        spot = (
                            f"{float(price):.2f}"
                            if (price := spot)
                            .replace("-", "", 1)
                            .replace(".", "", 1)
                            .isdigit()
                            else "---.--"
                        )
                        today = (
                            f"{float(price):.2f}"
                            if (
                                price := dyn_details.get("spot_price_mwh_avg_today")
                                or ""
                            )
                            .replace("-", "", 1)
                            .replace(".", "", 1)
                            .isdigit()
                            else "---.--"
                        )
                        tomorrow = (
                            f"{float(price):.2f}"
                            if (
                                price := dyn_details.get("spot_price_mwh_avg_tomorrow")
                                or ""
                            )
                            .replace("-", "", 1)
                            .replace(".", "", 1)
                            .isdigit()
                            else "---.--"
                        )
                        unit = dyn_details.get("spot_price_unit") or ""
                        time = str(dyn_details.get("spot_price_time") or "")[-5:]
                        CONSOLE.info(
                            f"{'Spot Price':<{col1}}: {spot:>6} {unit + '/MWh (' + (time or '--:--') + ')':<{col2 - 7}} "
                            f"{'Avg today/tomor':<{col3}}: {today:>6} / {tomorrow:>6} {unit + '/MWh'}"
                        )

                        CONSOLE.info(
                            f"{'Price Fee':<{col1}}: {dyn_details.get('dynamic_price_fee') or '-.----':>8} {unit:<{col2 - 9}} "
                            f"{'Price VAT':<{col3}}: {dyn_details.get('dynamic_price_vat') or '--.--':>6} %"
                        )
                        CONSOLE.info(
                            f"{'Poll Time':<{col1}}: {dyn_details.get('dynamic_price_poll_time') or '':<{col2}} "
                            f"{'Calc Time':<{col3}}: {dyn_details.get('dynamic_price_calc_time') or ''}"
                        )
                if energy := site.get("energy_details") or {}:
                    today: dict = energy.get("today") or {}
                    yesterday: dict = energy.get("last_period") or {}
                    forecast: dict = energy.get("pv_forecast_details") or {}
                    unit = "kWh"
                    if value := forecast.get("forecast_24h"):
                        CONSOLE.info(
                            f"{'PV Trend 24h':<{col1}}: {value or '-.--':>6} {unit:<{col2 - 7}} "
                            f"{'Local Time':<{col3}}: {forecast.get('local_time') or ''}"
                        )
                        u = (forecast.get("trend_unit") or "").capitalize()
                        thishour = forecast.get("trend_this_hour") or ""
                        if "k" not in u.lower():
                            thishour = (
                                f"{float(thishour):.0f}"
                                if str(thishour)
                                .replace(".", "", 1)
                                .replace("-", "", 1)
                                .isdigit()
                                else ""
                            )
                        nexthour = forecast.get("trend_next_hour") or ""
                        if "k" not in u.lower():
                            nexthour = (
                                f"{float(nexthour):.0f}"
                                if str(nexthour)
                                .replace(".", "", 1)
                                .replace("-", "", 1)
                                .isdigit()
                                else ""
                            )
                        CONSOLE.info(
                            f"{'PV This/Next h':<{col1}}: {thishour or '-----':>6} / {nexthour or '-----':>5} {u:<{col2 - 15}} "
                            f"{'Trend Poll Time':<{col3}}: {forecast.get('poll_time') or ''}  {'(' + str(forecast.get('time_this_hour') or '--:--')[-5:] + ')'}"
                        )
                        CONSOLE.info(
                            f"{'PV Trend Today':<{col1}}: {forecast.get('forecast_today') or '-.--':>6} {unit:<{col2 - 7}} "
                            f"{'PV Trend Tomor.':<{col3}}: {forecast.get('forecast_tomorrow') or '-.--':>6} {unit}"
                        )
                        CONSOLE.info(
                            f"{'Produced Today':<{col1}}: {forecast.get('produced_today') or '-.--':>6} {unit:<{col2 - 7}} "
                            f"{'Remain Today':<{col3}}: {forecast.get('remaining_today') or '-.--':>6} {unit}"
                        )
                    CONSOLE.info("-" * 80)
                    CONSOLE.info(
                        f"{'Today':<{col1}}: {today.get('date', '----------'):<{col2}} "
                        f"{'Yesterday':<{col3}}: {yesterday.get('date', '----------')!s}"
                    )
                    CONSOLE.info(
                        f"{'Solar Energy':<{col1}}: {today.get('solar_production') or '-.--':>6} {unit:<{col2 - 7}} "
                        f"{'Solar Energy':<{col3}}: {yesterday.get('solar_production') or '-.--':>6} {unit}"
                    )
                    if value := today.get("solar_production_pv1"):
                        CONSOLE.info(
                            f"{'Solar Ch 1/2':<{col1}}: {value or '-.--':>6} / {today.get('solar_production_pv2') or '-.--':>5} {unit:<{col2 - 15}} "
                            f"{'Solar Ch 1/2':<{col3}}: {yesterday.get('solar_production_pv1') or '-.--':>6} / {yesterday.get('solar_production_pv2') or '-.--':>5} {unit}"
                        )
                    if value := today.get("solar_production_pv3"):
                        CONSOLE.info(
                            f"{'Solar Ch 3/4':<{col1}}: {value or '-.--':>6} / {today.get('solar_production_pv4') or '-.--':>5} {unit:<{col2 - 15}} "
                            f"{'Solar Ch 3/4':<{col3}}: {yesterday.get('solar_production_pv3') or '-.--':>6} / {yesterday.get('solar_production_pv4') or '-.--':>5} {unit}"
                        )
                    if value := today.get("solar_production_microinverter"):
                        CONSOLE.info(
                            f"{'Solar Ch AC':<{col1}}: {value or '-.--':>6} {unit:<{col2 - 7}} "
                            f"{'Solar Ch AC':<{col3}}: {yesterday.get('solar_production_microinverter') or '-.--':>6} {unit}"
                        )
                    if value := today.get("battery_charge"):
                        CONSOLE.info(
                            f"{'Charged':<{col1}}: {value or '-.--':>6} {unit:<{col2 - 7}} "
                            f"{'Charged':<{col3}}: {yesterday.get('battery_charge') or '-.--':>6} {unit}"
                        )
                    if value := today.get("solar_to_battery"):
                        CONSOLE.info(
                            f"{'Charged Solar':<{col1}}: {value or '-.--':>6} {unit:<{col2 - 7}} "
                            f"{'Charged Solar':<{col3}}: {yesterday.get('solar_to_battery') or '-.--':>6} {unit}"
                        )
                    if value := today.get("grid_to_battery"):
                        CONSOLE.info(
                            f"{'Charged Grid':<{col1}}: {value or '-.--':>6} {unit:<{col2 - 7}} "
                            f"{'Charged Grid':<{col3}}: {yesterday.get('grid_to_battery') or '-.--':>6} {unit}"
                        )
                    if value := today.get("3rd_party_pv_to_bat"):
                        CONSOLE.info(
                            f"{'Charged Ext PV':<{col1}}: {value or '-.--':>6} {unit:<{col2 - 7}} "
                            f"{'Charged Ext PV':<{col3}}: {yesterday.get('3rd_party_pv_to_bat') or '-.--':>6} {unit}"
                        )
                    if value := today.get("battery_discharge"):
                        CONSOLE.info(
                            f"{'Discharged':<{col1}}: {value or '-.--':>6} {unit:<{col2 - 7}} "
                            f"{'Discharged':<{col3}}: {yesterday.get('battery_discharge') or '-.--':>6} {unit}"
                        )
                    if value := today.get("home_usage"):
                        CONSOLE.info(
                            f"{'House Usage':<{col1}}: {value or '-.--':>6} {unit:<{col2 - 7}} "
                            f"{'House Usage':<{col3}}: {yesterday.get('home_usage') or '-.--':>6} {unit}"
                        )
                    if value := today.get("solar_to_home"):
                        CONSOLE.info(
                            f"{'Solar Usage':<{col1}}: {value or '-.--':>6} {unit:<{col2 - 7}} "
                            f"{'Solar Usage':<{col3}}: {yesterday.get('solar_to_home') or '-.--':>6} {unit}"
                        )
                    if value := today.get("battery_to_home"):
                        CONSOLE.info(
                            f"{'Battery Usage':<{col1}}: {value or '-.--':>6} {unit:<{col2 - 7}} "
                            f"{'Battery Usage':<{col3}}: {yesterday.get('battery_to_home') or '-.--':>6} {unit}"
                        )
                    if value := today.get("grid_to_home"):
                        CONSOLE.info(
                            f"{'Grid Usage':<{col1}}: {value or '-.--':>6} {unit:<{col2 - 7}} "
                            f"{'Grid Usage':<{col3}}: {yesterday.get('grid_to_home') or '-.--':>6} {unit}"
                        )
                    if value := today.get("grid_import"):
                        CONSOLE.info(
                            f"{'Grid Import':<{col1}}: {value or '-.--':>6} {unit:<{col2 - 7}} "
                            f"{'Grid Import':<{col3}}: {yesterday.get('grid_import') or '-.--':>6} {unit}"
                        )
                    if value := today.get("solar_to_grid"):
                        CONSOLE.info(
                            f"{'Grid Export':<{col1}}: {value or '-.--':>6} {unit:<{col2 - 7}} "
                            f"{'Grid Export':<{col3}}: {yesterday.get('solar_to_grid') or '-.--':>6} {unit}"
                        )
                    if value := today.get("3rd_party_pv_to_grid"):
                        CONSOLE.info(
                            f"{'Ext PV Export':<{col1}}: {value or '-.--':>6} {unit:<{col2 - 7}} "
                            f"{'Ext PV Export':<{col3}}: {yesterday.get('3rd_party_pv_to_grid') or '-.--':>6} {unit}"
                        )
                    if value := today.get("ac_socket"):
                        CONSOLE.info(
                            f"{'AC Socket':<{col1}}: {value or '-.--':>6} {unit:<{col2 - 7}} "
                            f"{'AC Socket':<{col3}}: {yesterday.get('ac_socket') or '-.--':>6} {unit}"
                        )
                    if value := today.get("smartplugs_total"):
                        CONSOLE.info(
                            f"{'Smartplugs':<{col1}}: {value or '-.--':>6} {unit:<{col2 - 7}} "
                            f"{'Smartplugs':<{col3}}: {yesterday.get('smartplugs_total') or '-.--':>6} {unit}"
                        )
                    for idx, plug_t in enumerate(today.get("smartplug_list") or []):
                        plug_y = (yesterday.get("smartplug_list") or [])[idx]
                        CONSOLE.info(
                            f"{'-' + plug_t.get('alias', 'Plug ' + str(idx + 1)):<{col1}}: {plug_t.get('energy') or '-.--':>6} {unit:<{col2 - 7}} "
                            f"{'-' + plug_y.get('alias', 'Plug ' + str(idx + 1)):<{col3}}: {plug_y.get('energy') or '-.--':>6} {unit}"
                        )
                    if value := today.get("solar_percentage"):
                        CONSOLE.info(
                            f"{'Sol/Bat/Gri %':<{col1}}: {float(value or '0') * 100:>3.0f}/{float(today.get('battery_percentage') or '0') * 100:>3.0f}/{float(today.get('other_percentage') or '0') * 100:>3.0f} {'%':<{col2 - 12}} "
                            f"{'Sol/Bat/Gri %':<{col3}}: {float(yesterday.get('solar_percentage') or '0') * 100:>3.0f}/{float(yesterday.get('battery_percentage') or '0') * 100:>3.0f}/{float(yesterday.get('other_percentage') or '0') * 100:>3.0f} %"
                        )
        CONSOLE.info("=" * 80)
        # Print MQTT stats if session active
        if self.api.mqttsession:
            if self.use_file:
                CONSOLE.info(
                    f"Active MQTT speed: {Color.CYAN}{self.folderdict.get('speed', 1):.2f}{co}, Message cycle duration: {Color.CYAN}"
                    f"{self.folderdict.get('duration', 0) / self.folderdict.get('speed', 1):.0f} sec ({self.folderdict.get('progress', 0):6.2f} %){co}"
                )
            else:
                trigger_sec = (
                    int((self.triggered - datetime.now()).total_seconds())
                    if self.triggered
                    else None
                )
                CONSOLE.info(
                    f"Active MQTT topics: {Color.GREEN}{str(self.api.mqttsession.subscriptions or ' None ')[1:-1]}{co}"
                )
                CONSOLE.info(
                    f"Realtime Triggered: {Color.GREEN + str(trigger_sec) + ' sec' if self.triggered is not None else Color.RED + 'OFF'}{co}, "
                    f"Devices: {Color.CYAN + str(self.api.mqttsession.triggered_devices or ' None ')[1:-1]}{co}"
                )
            CONSOLE.info(f"MQTT {self.api.mqttsession.mqtt_stats!s}")
        # clear any delayed refresh and print key options
        self.delayed_sn_refresh.clear()
        self.get_menu_options()

    async def main(self) -> None:  # noqa: C901
        """Run Main routine to start the monitor in a loop."""
        # pylint: disable=logging-fstring-interpolation
        CONSOLE.info("Anker Solix Monitor:")
        # get list of possible example and export folders to test the monitor against
        exampleslist: list = self.get_subfolders(
            Path(__file__).parent / "examples"
        ) + self.get_subfolders(Path(__file__).parent / "exports")
        # refresh interval in seconds, will be prompted or set from args
        refresh_interval: int = self.refresh_interval
        # interval count for details refresh
        details_refresh: int = 10
        if self.interactive:
            if exampleslist:
                exampleslist.sort()
                CONSOLE.info("\nSelect the input source for the monitor:")
                CONSOLE.info(f"({Color.CYAN}0{Color.OFF}) Real time from Anker cloud")
                for idx, filename in enumerate(exampleslist, start=1):
                    CONSOLE.info(f"({Color.YELLOW}{idx}{Color.OFF}) {filename}")
                CONSOLE.info(f"({Color.RED}Q{Color.OFF}) Quit")
            selection = input(
                f"Input Source number {Color.CYAN}0{Color.YELLOW}-{len(exampleslist)}{Color.OFF}) or [{Color.RED}Q{Color.OFF}]uit: "
            )
            if (
                selection.upper() in ["Q", "QUIT"]
                or not selection.isdigit()
                or int(selection) < 0
                or int(selection) > len(exampleslist)
            ):
                return False
            if (folderselection := int(selection)) == 0:
                self.use_file = False
            else:
                self.use_file = True
                self.folderdict["folder"] = exampleslist[folderselection - 1]
        else:
            self.use_file = False
        try:
            async with ClientSession() as websession:
                user = "" if self.use_file else common.user()
                if not self.use_file:
                    CONSOLE.info("Trying Api authentication for user %s...", user)

                # Create a logger for the API with appropriate level
                if self.debug_http:
                    api_logger = CONSOLE
                else:
                    # Create a logger that suppresses DEBUG messages
                    api_logger = logging.getLogger(f"{__name__}.api")
                    api_logger.setLevel(logging.INFO)
                    # Add the same handler as CONSOLE but with INFO level
                    handler = logging.StreamHandler()
                    handler.setLevel(logging.INFO)
                    handler.setFormatter(logging.Formatter("%(message)s"))
                    api_logger.addHandler(handler)
                    api_logger.propagate = False

                self.api = AnkerSolixApi(
                    user,
                    "" if self.use_file else common.password(),
                    "" if self.use_file else common.country(),
                    websession,
                    api_logger,
                )
                if self.use_file:
                    # set the correct test folder for Api
                    self.api.testDir(self.folderdict.get("folder"))
                elif await self.api.async_authenticate():
                    CONSOLE.info(
                        f"Anker Cloud authentication: {Color.GREEN}OK{Color.OFF}"
                    )
                else:
                    # Login validation will be done during first API call
                    CONSOLE.info(
                        f"Anker Cloud authentication: {Color.CYAN}CACHED{Color.OFF}"
                    )

                if self.interactive:
                    while True:
                        resp = input(
                            f"How many seconds refresh interval should be used? ({Color.YELLOW}5-600{Color.OFF}, default: {Color.CYAN}30{Color.OFF}): "
                        )
                        if not resp:
                            refresh_interval = 30
                            break
                        if resp.isdigit() and 5 <= int(resp) <= 600:
                            refresh_interval = int(resp)
                            break

                    # ask for including energy details
                    while True:
                        resp = input(
                            f"Do you want to include daily site energy statistics? ([{Color.YELLOW}Y{Color.OFF}]es / [{Color.CYAN}N{Color.OFF}]o = default): "
                        )
                        if not resp or resp.upper() in ["N", "NO"]:
                            break
                        if resp.upper() in ["Y", "YES"]:
                            self.energy_stats = True
                            break

                # Run loop to update Solarbank parameters
                self.next_refr = datetime.now().astimezone()
                self.next_dev_refr = 0
                site_names: list | None = None
                startup: bool = True
                deferred: bool = False
                # get running loop to run blocking code
                self.loop = asyncio.get_running_loop()
                mqtt_task: asyncio.Task | None = None
                while True:
                    now = datetime.now().astimezone()
                    if self.next_refr <= now:
                        # Ask whether monitor should be limited to selected site ID
                        if not (self.use_file or site_names):
                            CONSOLE.info("Getting site list...")
                            sites = (
                                await self.api.get_site_list(fromFile=self.use_file)
                            ).get("site_list") or []
                            site_names = ["All"] + [
                                (
                                    ", ".join(
                                        [
                                            str(s.get("site_id")),
                                            str(s.get("site_name")),
                                            "Type: "
                                            + str(
                                                s.get("power_site_type") or "unknown"
                                            ),
                                        ]
                                    )
                                )
                                for s in sites
                            ]
                            if self.interactive and len(site_names) > 2:
                                CONSOLE.info("Select which Site to be monitored:")
                                for idx, sitename in enumerate(site_names):
                                    CONSOLE.info(
                                        f"({Color.YELLOW}{idx}{Color.OFF}) {sitename}"
                                    )
                                selection = input(
                                    f"Enter site number ({Color.YELLOW}0-{len(site_names) - 1}{Color.OFF}) or nothing for {Color.CYAN}All{Color.OFF}: "
                                )
                                if selection.isdigit() and 1 <= int(selection) < len(
                                    site_names
                                ):
                                    self.site_selected = site_names[
                                        int(selection)
                                    ].split(",")[0]
                            # ask which endpoint limit should be applied or use command line arg
                            if self.interactive:
                                selection = input(
                                    f"Enter Api endpoint limit for request throttling ({Color.YELLOW}1-50, 0 = disabled{Color.OFF}) "
                                    f"[Default: {Color.CYAN}{self.api.apisession.endpointLimit()}{Color.OFF}]: "
                                )
                                if selection.isdigit() and 0 <= int(selection) <= 50:
                                    self.api.apisession.endpointLimit(int(selection))
                            else:
                                # Set endpoint limit from command line argument
                                self.api.apisession.endpointLimit(self.endpoint_limit)

                        CONSOLE.info("\nRunning site refresh...")
                        await self.api.update_sites(
                            fromFile=self.use_file, siteId=self.site_selected
                        )
                        self.next_dev_refr -= 1
                        if not self.use_file and self.energy_stats and deferred:
                            CONSOLE.info("Running energy details refresh...")
                            await self.api.update_device_energy(fromFile=self.use_file)
                            deferred = False
                        self.next_refr = datetime.now().astimezone() + timedelta(
                            seconds=refresh_interval
                        )
                    if self.next_dev_refr < 0:
                        CONSOLE.info(
                            "Running device and site details refresh%s...",
                            ", excluding " + str({SolixDeviceType.VEHICLE.value})
                            if self.site_selected or not self.showVehicles
                            else "",
                        )
                        # skip Vehicle data if dedicated site selected or vehicles disabled
                        await self.api.update_device_details(
                            fromFile=self.use_file,
                            exclude={SolixDeviceType.VEHICLE.value}
                            if self.site_selected or not self.showVehicles
                            else None,
                        )
                        await self.api.update_site_details(fromFile=self.use_file)
                        # run also energy refresh if requested
                        if self.energy_stats:
                            if startup and not self.use_file:
                                CONSOLE.info(
                                    "Deferring initial energy details refresh..."
                                )
                                startup = False
                                deferred = True
                            else:
                                CONSOLE.info("Running energy details refresh...")
                                await self.api.update_device_energy(
                                    fromFile=self.use_file
                                )
                                startup = False
                        self.next_refr = datetime.now().astimezone() + timedelta(
                            seconds=refresh_interval
                        )
                        self.next_dev_refr = details_refresh

                        # Generate device list for output filter toggle
                        if not self.device_names:
                            self.device_names = ["All"] + [
                                (
                                    ", ".join(
                                        [
                                            str(d.get("device_sn")),
                                            str(d.get("name")),
                                            f"Type: {d.get('device_pn')} - {d.get('type') or 'unknown'}",
                                        ]
                                    )
                                )
                                for d in self.api.devices.values()
                            ]
                        # Ask if output should be filtered to certain device
                        if (
                            self.interactive
                            and self.device_filter is None
                            and len(self.device_names) > 2
                        ):
                            CONSOLE.info(
                                "Select which device should be filtered in output:"
                            )
                            for idx, devicename in enumerate(self.device_names):
                                CONSOLE.info(
                                    f"({Color.YELLOW}{idx}{Color.OFF}) {devicename}"
                                )
                            selection = input(
                                f"Enter device number ({Color.YELLOW}0-{len(self.device_names) - 1}{Color.OFF}) or nothing for {Color.CYAN}All{Color.OFF}: "
                            )
                            if selection.isdigit() and 1 <= int(selection) < len(
                                self.device_names
                            ):
                                self.device_filter = self.device_names[
                                    int(selection)
                                ].split(",")[0]
                            else:
                                self.device_filter = ""

                        # Auto-start MQTT session if enabled via command line
                        if (
                            self.enable_mqtt
                            and not self.api.mqttsession
                            and not self.use_file
                        ):
                            CONSOLE.info("Auto-starting MQTT session...")
                            if mqttsession := await self.api.startMqttSession(
                                fromFile=self.use_file
                            ):
                                for dev in (
                                    devs := [
                                        dev
                                        for dev in self.api.devices.values()
                                        if dev.get("mqtt_described")
                                    ]
                                ):
                                    # generate MQTT device and track it
                                    sn = dev.get("device_sn")
                                    if mdev := SolixMqttDeviceFactory(
                                        self.api, sn
                                    ).create_device():
                                        self.mqtt_devices[sn] = mdev
                                if mqttsession.is_connected():
                                    CONSOLE.info(
                                        f"{Color.GREEN}MQTT session connected{Color.OFF}, subscribing eligible devices..."
                                    )
                                    for dev in devs:
                                        # subscribe device
                                        topic = f"{mqttsession.get_topic_prefix(deviceDict=dev)}#"
                                        resp = mqttsession.subscribe(topic)
                                        if resp and resp.is_failure:
                                            CONSOLE.info(
                                                f"{Color.RED}Failed subscription for topic: {topic}{Color.OFF}"
                                            )
                                    # set the value print as callback for mqtt value refreshes
                                    self.api.mqtt_update_callback(
                                        func=self.print_device_mqtt
                                    )
                                    # Auto-trigger realtime if enabled via command line
                                    if self.enable_realtime and self.mqtt_devices:
                                        CONSOLE.info(
                                            f"{Color.CYAN}Auto-triggering real time MQTT data for {self.rt_timeout} seconds... "
                                        )
                                        for mdev in self.mqtt_devices.values():
                                            if mdev.realtime_trigger(
                                                timeout=self.rt_timeout
                                            ):
                                                CONSOLE.info(
                                                    f"Triggered device: {Color.GREEN}{mdev.sn} ({mdev.pn}) - "
                                                    f"{mdev.device.get('name') or 'NoName'}{Color.OFF}"
                                                )
                                                mqttsession.triggered_devices.add(
                                                    mdev.sn
                                                )
                                            else:
                                                CONSOLE.info(
                                                    f"{Color.RED}Failed to publish Real Time trigger message for {mdev.sn}{Color.OFF}"
                                                )
                                                mqttsession.triggered_devices.discard(
                                                    mdev.sn
                                                )
                                        if mqttsession.triggered_devices:
                                            self.triggered = datetime.now() + timedelta(
                                                seconds=self.rt_timeout
                                            )
                                    if not devs:
                                        CONSOLE.info(
                                            f"{Color.YELLOW}No eligible MQTT devices found!{Color.OFF}"
                                        )
                                else:
                                    CONSOLE.info(
                                        f"{Color.YELLOW}MQTT client not fully connected yet, skipping subscription and real-time trigger{Color.OFF}"
                                    )
                            else:
                                CONSOLE.info(
                                    f"{Color.RED}Failed to start MQTT session!{Color.OFF}"
                                )
                    if self.showMqttDevice:
                        self.print_device_mqtt(deviceSn=None)
                    else:
                        common.clearscreen()
                        if self.use_file:
                            CONSOLE.info(
                                "Using input source folder: %s", self.api.testDir()
                            )
                        CONSOLE.info(
                            "Anker Solix Monitor (refresh %s s, details refresh countdown %s):",
                            refresh_interval,
                            self.next_dev_refr,
                        )
                        CONSOLE.info(
                            "Sites: %s, Devices: %s, Device Filter: %s",
                            len(self.api.sites),
                            len(self.api.devices),
                            f"{Color.MAG}{self.device_filter!s}{Color.OFF}",
                        )
                        # print the data with MQTT mixin if MQTT session is active
                        self.print_api_data(mqtt_mixin=bool(self.api.mqttsession))
                    CONSOLE.info("Api Requests: %s", self.api.request_count)
                    CONSOLE.log(
                        logging.INFO if self.showApiCalls else logging.DEBUG,
                        self.api.request_count.get_details(last_hour=True),
                    )
                    try:
                        # start task to print wait progress
                        wait_task = self.loop.create_task(
                            self.print_wait_progress(seconds=refresh_interval)
                        )
                        # key press loop
                        while True:
                            if wait_task.done():
                                break
                            break_refresh = False
                            # Check if realtime trigger is timed out
                            if self.triggered and self.triggered <= datetime.now():
                                self.triggered = None
                                if self.api.mqttsession:
                                    self.api.mqttsession.triggered_devices = set()
                            # Check if a key was pressed
                            if k := await self.loop.run_in_executor(
                                None, common.getkey
                            ):
                                k = k.lower()
                                if k == "k":
                                    # print key menu
                                    self.get_menu_options(details=True)
                                    break
                                if k == "o" and exampleslist and self.use_file:
                                    CONSOLE.info(
                                        "Select the input source for the monitor:"
                                    )
                                    for idx, filename in enumerate(
                                        exampleslist, start=1
                                    ):
                                        CONSOLE.info(
                                            f"({Color.YELLOW}{idx}{Color.OFF}) {filename}"
                                        )
                                    CONSOLE.info(f"({Color.RED}C{Color.OFF}) Cancel")
                                    while True:
                                        selection = input(
                                            f"Enter source file number ({Color.YELLOW}1-{len(exampleslist)}{Color.OFF}) or [{Color.RED}C{Color.OFF}]ancel: "
                                        )
                                        if selection.upper() in ["C", "CANCEL"]:
                                            selection = None
                                            break
                                        if selection.isdigit() and 1 <= int(
                                            selection
                                        ) <= len(exampleslist):
                                            folderselection = int(selection)
                                            break
                                    if selection:
                                        self.api.testDir(
                                            exampleslist[folderselection - 1]
                                        )
                                        self.api.clearCaches()
                                        self.api.request_count.recycle(
                                            last_time=datetime.now()
                                        )
                                        self.folderdict["folder"] = self.api.testDir()
                                        self.device_filter = ""
                                        self.device_names = []
                                        self.next_dev_refr = 0
                                        break_refresh = True
                                    else:
                                        break
                                elif k == "n" and exampleslist and self.use_file:
                                    self.device_filter = ""
                                    folderselection = (
                                        (folderselection + 1)
                                        if folderselection < len(exampleslist)
                                        else 1
                                    )
                                    self.api.testDir(exampleslist[folderselection - 1])
                                    self.api.clearCaches()
                                    self.api.request_count.recycle(
                                        last_time=datetime.now()
                                    )
                                    self.folderdict["folder"] = self.api.testDir()
                                    self.device_filter = ""
                                    self.device_names = []
                                    self.next_dev_refr = 0
                                    break_refresh = True
                                elif k == "p" and exampleslist and self.use_file:
                                    self.device_filter = ""
                                    folderselection = (
                                        (folderselection - 1)
                                        if folderselection > 1
                                        else len(exampleslist)
                                    )
                                    self.api.testDir(exampleslist[folderselection - 1])
                                    self.api.clearCaches()
                                    self.api.request_count.recycle(
                                        last_time=datetime.now()
                                    )
                                    self.folderdict["folder"] = self.api.testDir()
                                    self.device_filter = ""
                                    self.device_names = []
                                    self.next_dev_refr = 0
                                    break_refresh = True
                                elif k == "i" and self.use_file:
                                    CONSOLE.info(
                                        f"{Color.YELLOW}\nRefreshing sites...{Color.OFF}"
                                    )
                                    # set device details refresh to future to reload only site info
                                    self.next_dev_refr += 1
                                    break_refresh = True
                                elif k == "l" and self.use_file:
                                    CONSOLE.info(
                                        f"{Color.YELLOW}\nRefreshing all details...{Color.OFF}"
                                    )
                                    self.next_dev_refr = 0
                                    break_refresh = True
                                elif (
                                    k == "+" and self.use_file and self.api.mqttsession
                                ):
                                    if (speed := self.folderdict.get("speed", 1)) < 16:
                                        CONSOLE.info(
                                            f"{Color.GREEN}\nIncreasing MQTT message speed...{Color.OFF}"
                                        )
                                        self.folderdict["speed"] = round(
                                            min(16, 2 * speed), 2
                                        )
                                        break
                                    CONSOLE.info(
                                        f"{Color.RED}\nMax MQTT message speed reached!{Color.OFF}"
                                    )
                                elif (
                                    k == "-" and self.use_file and self.api.mqttsession
                                ):
                                    if (
                                        speed := self.folderdict.get("speed", 1)
                                    ) > 0.25:
                                        CONSOLE.info(
                                            f"{Color.CYAN}\nDecreasing MQTT message speed...{Color.OFF}"
                                        )
                                        self.folderdict["speed"] = round(
                                            max(0.25, speed / 2), 2
                                        )
                                        break
                                    CONSOLE.info(
                                        f"{Color.RED}\nMin MQTT message speed reached!{Color.OFF}"
                                    )
                                elif k == "e":
                                    # Toggle vehicle display
                                    if self.showVehicles:
                                        CONSOLE.info(
                                            f"{Color.RED}\nDisabling Electric Vehicle display...{Color.OFF}"
                                        )
                                        self.showVehicles = False
                                    else:
                                        CONSOLE.info(
                                            f"{Color.YELLOW}\nEnabling Electric Vehicle display...!{Color.OFF}"
                                        )
                                        self.showVehicles = True
                                    if self.use_file:
                                        break_refresh = True
                                elif k == "s":
                                    # Toggle MQTT session state
                                    if not self.api.mqttsession:
                                        CONSOLE.info(
                                            f"{Color.YELLOW}\nStarting MQTT session...{Color.OFF}"
                                        )
                                        if (
                                            mqttsession
                                            := await self.api.startMqttSession(
                                                fromFile=self.use_file
                                            )
                                        ):
                                            # generate MQTT devices and track them
                                            for dev in (
                                                devs := [
                                                    dev
                                                    for dev in self.api.devices.values()
                                                    if dev.get("mqtt_described")
                                                ]
                                            ):
                                                sn = dev.get("device_sn")
                                                if mdev := SolixMqttDeviceFactory(
                                                    self.api, sn
                                                ).create_device():
                                                    self.mqtt_devices[sn] = mdev
                                            if self.use_file:
                                                # set the value print as callback for mqtt value refreshes
                                                self.api.mqtt_update_callback(
                                                    func=self.print_device_mqtt
                                                )
                                                # Create task for polling mqtt messages from files for testing
                                                mqtt_task = self.loop.create_task(
                                                    mqttsession.file_poller(
                                                        folderdict=self.folderdict,
                                                        speed=1,
                                                    )
                                                )
                                                CONSOLE.info(
                                                    f"{Color.GREEN}MQTT file data poller task was started.{Color.OFF}"
                                                )
                                                await asyncio.sleep(1)
                                                break
                                            if mqttsession.is_connected():
                                                CONSOLE.info(
                                                    f"{Color.GREEN}MQTT session connected{Color.OFF}, subscribing eligible devices..."
                                                )
                                                for dev in devs:
                                                    topic = f"{mqttsession.get_topic_prefix(deviceDict=dev)}#"
                                                    resp = mqttsession.subscribe(topic)
                                                    if resp and resp.is_failure:
                                                        CONSOLE.info(
                                                            f"{Color.RED}Failed subscription for topic: {topic}{Color.OFF}"
                                                        )
                                                if devs:
                                                    # set the value print as callback for mqtt value refreshes
                                                    self.api.mqtt_update_callback(
                                                        func=self.print_device_mqtt
                                                    )
                                                else:
                                                    CONSOLE.info(
                                                        f"{Color.YELLOW}No eligible MQTT devices found!{Color.OFF}"
                                                    )
                                            else:
                                                CONSOLE.info(
                                                    f"{Color.RED}Failed to connect client of MQTT session!{Color.OFF}"
                                                )
                                        else:
                                            CONSOLE.info(
                                                f"{Color.RED}Failed to start MQTT session!{Color.OFF}"
                                            )
                                    else:
                                        CONSOLE.info(
                                            f"{Color.RED}\nStopping MQTT session...!{Color.OFF}"
                                        )
                                        if mqtt_task:
                                            mqtt_task.cancel()
                                            # Wait for the task to finish cancellation
                                            try:
                                                await mqtt_task
                                            except asyncio.CancelledError:
                                                CONSOLE.info(
                                                    "MQTT file data poller task was cancelled."
                                                )
                                        self.api.stopMqttSession()
                                        self.triggered = None
                                        self.mqtt_devices = {}
                                        if self.showMqttDevice:
                                            self.showMqttDevice = False
                                            CONSOLE.info(
                                                f"{Color.CYAN}Toggling back to Api device display for next refresh...{Color.OFF}"
                                            )
                                            if self.use_file:
                                                break_refresh = True
                                elif k == "a":
                                    # Toggle Api call display
                                    if self.showApiCalls:
                                        CONSOLE.info(
                                            f"{Color.RED}\nDisabling Api call display...{Color.OFF}"
                                        )
                                        self.showApiCalls = False
                                    else:
                                        CONSOLE.info(
                                            f"{Color.YELLOW}\nEnabling Api call display for next refresh...!{Color.OFF}"
                                        )
                                        self.showApiCalls = True
                                    if self.use_file:
                                        break_refresh = True
                                elif k == "m":
                                    # Toggle Mqtt device or Api device data display
                                    if self.api.mqttsession:
                                        if self.showMqttDevice:
                                            CONSOLE.info(
                                                f"{Color.CYAN}\nEnabling Api device display...{Color.OFF}"
                                            )
                                            self.showMqttDevice = False
                                        else:
                                            CONSOLE.info(
                                                f"{Color.YELLOW}\nEnabling MQTT device display...!{Color.OFF}"
                                            )
                                            self.showMqttDevice = True
                                        await asyncio.sleep(1)
                                        break
                                    CONSOLE.info(
                                        f"{Color.RED}\nNo MQTT session active to enable MQTT device display!{Color.OFF}"
                                    )
                                    self.showMqttDevice = False
                                elif k == "r" and not self.use_file:
                                    # Real time trigger
                                    if self.api.mqttsession:
                                        if not self.api.mqttsession.is_connected():
                                            CONSOLE.info(
                                                f"{Color.YELLOW}\nMQTT session not connected, trying reconnection...{Color.OFF}"
                                            )
                                            self.api.startMqttSession(
                                                fromFile=self.use_file
                                            )
                                        # Cycle through devices and publish trigger for each applicable device
                                        if self.api.mqttsession.is_connected():
                                            if self.mqtt_devices:
                                                CONSOLE.info(
                                                    f"{Color.CYAN}\nTriggering real time MQTT data for {self.rt_timeout} seconds...{Color.OFF}"
                                                )
                                                for mdev in self.mqtt_devices.values():
                                                    if mdev.realtime_trigger(
                                                        timeout=self.rt_timeout,
                                                        toFile=self.use_file,
                                                    ):
                                                        CONSOLE.info(
                                                            f"Triggered device: {Color.GREEN}{mdev.sn} ({mdev.pn}) - "
                                                            f"{mdev.device.get('name') or 'NoName'}{Color.OFF}"
                                                        )
                                                        self.api.mqttsession.triggered_devices.add(
                                                            mdev.sn
                                                        )
                                                    else:
                                                        CONSOLE.info(
                                                            f"{Color.RED}\nFailed to publish Real Time trigger message for {mdev.sn}{Color.OFF}"
                                                        )
                                                        self.api.mqttsession.triggered_devices.discard(
                                                            mdev.sn
                                                        )
                                                if self.api.mqttsession.triggered_devices:
                                                    self.triggered = (
                                                        datetime.now()
                                                        + timedelta(
                                                            seconds=self.rt_timeout
                                                        )
                                                    )
                                                else:
                                                    self.triggered = None
                                            else:
                                                CONSOLE.info(
                                                    f"{Color.YELLOW}\nNo eligible MQTT devices found!{Color.OFF}"
                                                )
                                        else:
                                            CONSOLE.info(
                                                f"{Color.RED}\nReal time MQTT data requires connected MQTT session...{Color.OFF}"
                                            )
                                    else:
                                        CONSOLE.info(
                                            f"{Color.RED}\nReal time MQTT data requires active MQTT session...{Color.OFF}"
                                        )
                                elif k == "d":
                                    # print the whole cache
                                    CONSOLE.info(
                                        "\nApi cache:\n%s",
                                        json.dumps(self.api.getCaches(), indent=2),
                                    )
                                    input(
                                        f"Hit [{Color.CYAN}Enter{Color.OFF}] to continue...\n"
                                    )
                                    break
                                elif k == "f":
                                    # toggle the filtered device sn
                                    if self.device_names:
                                        if not self.device_filter:
                                            self.device_filter = "All"
                                        sns = [d.split(",")[0] for d in self.device_names]
                                        index = (
                                            sns.index(self.device_filter)
                                            if self.device_filter in sns
                                            else -1
                                        )
                                        self.device_filter = self.device_names[
                                            index + 1
                                            if index + 1 < len(self.device_names)
                                            else 0
                                        ].split(",")[0]
                                        CONSOLE.info(
                                            f"\n{Color.MAG}Toggling device filter to {self.device_filter}...{Color.OFF}"
                                        )
                                        if self.device_filter == "All":
                                            self.device_filter = ""
                                        await asyncio.sleep(2)
                                        break
                                elif k == "v":
                                    # print all extracted MQTT values (MQTT session cache) and device data
                                    if self.api.mqttsession:
                                        CONSOLE.info(
                                            "\nMQTT value cache:\n%s",
                                            json.dumps(
                                                self.api.mqttsession.mqtt_data,
                                                indent=2,
                                            ),
                                        )
                                        for dev in [
                                            dev
                                            for dev in self.api.devices.values()
                                            if (
                                                not self.site_selected
                                                or dev.get("site_id")
                                                == self.site_selected
                                            )
                                            and dev.get("mqtt_data")
                                        ]:
                                            CONSOLE.info(
                                                f"Extracted MQTT device data: {Color.MAG}{dev.get('name') or 'NoName'} - "
                                                f"{dev.get('device_sn')} ({dev.get('device_pn')}){Color.OFF}\n"
                                                f"{json.dumps(dev.get('mqtt_data'), indent=2)}"
                                            )
                                        input(
                                            f"Hit [{Color.CYAN}Enter{Color.OFF}] to continue...\n"
                                        )
                                        break
                                    CONSOLE.info(
                                        f"{Color.RED}\nMQTT device data require active MQTT session...{Color.OFF}"
                                    )
                                elif k == "c":
                                    CONSOLE.info(
                                        f"\n{Color.YELLOW}Customizing Api cache entry...{Color.OFF}"
                                    )
                                    if self.customize_cache():
                                        break_refresh = True
                                    else:
                                        break
                                elif k in ["esc", "q"]:
                                    CONSOLE.info(
                                        f"{Color.RED}\nStopping monitor...{Color.OFF}"
                                    )
                                    raise asyncio.CancelledError
                                if break_refresh:
                                    self.next_refr = datetime.now().astimezone()
                                    wait_task.cancel()
                                await asyncio.sleep(0.5)
                    finally:
                        # Cancel the started tasks
                        wait_task.cancel()
                        # Wait for the tasks to finish cancellation
                        try:
                            await wait_task
                        except asyncio.CancelledError:
                            CONSOLE.info("\nData poller wait task was cancelled.")
        except (
            asyncio.CancelledError,
            KeyboardInterrupt,
            ClientError,
            AnkerSolixError,
        ) as err:
            if isinstance(err, ClientError | AnkerSolixError):
                CONSOLE.error("\n%s: %s", type(err), err)
                if self.api:
                    CONSOLE.info("Api Requests: %s", self.api.request_count)
                    CONSOLE.info(self.api.request_count.get_details(last_hour=True))
            return False
        finally:
            if self.api:
                if self.api.mqttsession:
                    CONSOLE.info("Disconnecting from MQTT server...")
                    self.api.mqttsession.cleanup()


# run async main
if __name__ == "__main__":
    try:
        # Parse command line arguments
        arg: argparse.Namespace = parse_arguments()

        # Print configuration when in non-interactive mode
        if arg.live_cloud:
            CONSOLE.info("Configuration:")
            CONSOLE.info(f"  Live cloud mode: {Color.GREEN}Enabled{Color.OFF}")
            CONSOLE.info(
                f"  MQTT session: {Color.GREEN if arg.enable_mqtt else Color.RED}{'Enabled' if arg.enable_mqtt else 'Disabled'}{Color.OFF}"
            )
            CONSOLE.info(
                f"  MQTT display mode: {Color.GREEN if arg.mqtt_display else Color.CYAN}{'Pure MQTT' if arg.mqtt_display else 'Mixed API+MQTT'}{Color.OFF}"
            )
            CONSOLE.info(
                f"  Real-time trigger: {Color.GREEN if arg.realtime else Color.RED}{'Enabled' if arg.realtime else 'Disabled'}{Color.OFF}"
            )
            CONSOLE.info(
                f"  Refresh interval: {Color.CYAN}{arg.interval}{Color.OFF} seconds"
            )
            CONSOLE.info(
                f"  Energy statistics: {Color.GREEN if arg.energy_stats else Color.RED}{'Enabled' if arg.energy_stats else 'Disabled'}{Color.OFF}"
            )
            if arg.site_id:
                CONSOLE.info(
                    f"  Monitoring site: {Color.YELLOW}{arg.site_id}{Color.OFF}"
                )
            if arg.device_id:
                CONSOLE.info(
                    f"  Device filter: {Color.YELLOW}{arg.device_id}{Color.OFF}"
                )
            CONSOLE.info(
                f"  Electric vehicles: {Color.GREEN if not arg.no_vehicles else Color.RED}{'Enabled' if not arg.no_vehicles else 'Disabled'}{Color.OFF}"
            )
            CONSOLE.info(
                f"  API call statistics: {Color.GREEN if arg.api_calls else Color.RED}{'Enabled' if arg.api_calls else 'Disabled'}{Color.OFF}"
            )
            CONSOLE.info(
                f"  HTTP debug logging: {Color.GREEN if arg.debug_http else Color.RED}{'Enabled' if arg.debug_http else 'Disabled'}{Color.OFF}"
            )
            CONSOLE.info(
                f"  Endpoint limit: {Color.CYAN}{arg.endpoint_limit if arg.endpoint_limit > 0 else 'Disabled'}{Color.OFF}"
            )
            CONSOLE.info("")

        if not asyncio.run(AnkerSolixApiMonitor(arg).main(), debug=False):
            CONSOLE.warning("\nAborted!")
    except KeyboardInterrupt:
        CONSOLE.warning("\nAborted!")
    except Exception as exception:  # pylint: disable=broad-exception-caught  # noqa: BLE001
        CONSOLE.exception("%s: %s", type(exception), exception)
