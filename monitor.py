#!/usr/bin/env python
"""Example exec module to use the Anker API for continuously querying and displaying important parameters of Anker Solix sites and devices.

This module will prompt for the Anker account details if not pre-set in the header.  Upon successful authentication,
you will see the solarbank parameters displayed and refreshed at regular interval.

Note: When the system owning account is used, more details for the systems and devices can be queried and displayed.

Attention: During execution of this module, the used account cannot be used in
the Anker App since it will be kicked out on each refresh.
"""

import asyncio
import contextlib
from datetime import datetime, timedelta
import json
import logging
import os
from pathlib import Path
import sys

from aiohttp import ClientSession
from aiohttp.client_exceptions import ClientError
from api import api, errors  # pylint: disable=no-name-in-module
from api.apitypes import (  # pylint: disable=no-name-in-module
    SolarbankAiemsStatus,
    SolarbankUsageMode,
    SolixPriceTypes,
)
import common

# use Console logger from common module
CONSOLE: logging.Logger = common.CONSOLE
# enable debug mode for the console handler
# CONSOLE.handlers[0].setLevel(logging.DEBUG)

REFRESH = 0  # default No refresh interval
DETAILSREFRESH = 10  # Multiplier for device details refresh
INTERACTIVE = True  # Interactive allows to select examples and exports as input for tests and debug
SHOWAPICALLS = (
    False  # Enable to show Api calls and cache details for additional debugging
)


def clearscreen():
    """Clear the terminal screen."""
    if sys.stdin is sys.__stdin__:  # check if not in IDLE shell
        if os.name == "nt":
            os.system("cls")
        else:
            os.system("clear")
        # CONSOLE.info("\033[H\033[2J", end="")  # ESC characters to clear terminal screen, system independent?


def get_subfolders(folder: str | Path) -> list:
    """Get the full pathname of all subfolder for given folder as list."""
    if isinstance(folder, str):
        folder: Path = Path(folder)
    if folder.is_dir():
        return [f.resolve() for f in folder.iterdir() if f.is_dir()]
    return []


async def main() -> (  # noqa: C901 # pylint: disable=too-many-locals,too-many-branches,too-many-statements
    None
):
    """Run Main routine to start the monitor in a loop."""
    global REFRESH  # pylint: disable=global-statement  # noqa: PLW0603
    CONSOLE.info("Anker Solix Monitor:")
    # get list of possible example and export folders to test the monitor against
    exampleslist: list = get_subfolders(
        Path(__file__).parent / "examples"
    ) + get_subfolders(Path(__file__).parent / "exports")
    energy_stats: bool = False
    testfolder: str | None = None
    if INTERACTIVE:
        if exampleslist:
            exampleslist.sort()
            CONSOLE.info("\nSelect the input source for the monitor:")
            CONSOLE.info("(0) Real time from Anker cloud")
            for idx, filename in enumerate(exampleslist, start=1):
                CONSOLE.info("(%s) %s", idx, filename)
            CONSOLE.info("(q) Quit")
        selection = input(f"Input Source number (0-{len(exampleslist)}) or [q]uit: ")
        if (
            selection.upper() in ["Q", "QUIT"]
            or not selection.isdigit()
            or int(selection) < 0
            or int(selection) > len(exampleslist)
        ):
            return False
        if (selection := int(selection)) == 0:
            use_file = False
        else:
            use_file = True
            testfolder = exampleslist[selection - 1]
    else:
        use_file = False
    try:
        async with ClientSession() as websession:
            user = "" if use_file else common.user()
            if not use_file:
                CONSOLE.info("Trying Api authentication for user %s...", user)
            myapi = api.AnkerSolixApi(
                user,
                "" if use_file else common.password(),
                "" if use_file else common.country(),
                websession,
                CONSOLE,
            )
            if use_file:
                # set the correct test folder for Api
                myapi.testDir(testfolder)
            elif await myapi.async_authenticate():
                CONSOLE.info("Anker Cloud authentication: OK")
            else:
                # Login validation will be done during first API call
                CONSOLE.info("Anker Cloud authentication: CACHED")

            while not use_file:
                resp = input(
                    "How many seconds refresh interval should be used? (5-600, default: 30): "
                )
                if not resp:
                    REFRESH = 30
                    break
                if resp.isdigit() and 5 <= int(resp) <= 600:
                    REFRESH = int(resp)
                    break

            # ask for including energy details
            while True:
                resp = input(
                    "Do you want to include daily site energy statistics? ([Y]es / [N]o = default): "
                )
                if not resp or resp.upper() in ["N", "NO"]:
                    break
                if resp.upper() in ["Y", "YES"]:
                    energy_stats = True
                    break

            # Run loop to update Solarbank parameters
            next_refr: datetime = datetime.now().astimezone()
            next_dev_refr: int = 0
            col1 = 15
            col2 = 23
            col3 = 15
            site_names: list | None = None
            site_selected: str = None
            startup: bool = True
            deferred: bool = False
            while True:
                clearscreen()
                now = datetime.now().astimezone()
                if next_refr <= now:
                    # Ask whether monitor should be limited to selected site ID
                    if not (use_file or site_names):
                        CONSOLE.info("Getting site list...")
                        sites = (await myapi.get_site_list(fromFile=use_file)).get(
                            "site_list"
                        ) or []
                        site_names = ["All"] + [
                            (
                                ", ".join(
                                    [
                                        str(s.get("site_id")),
                                        str(s.get("site_name")),
                                        "Type: "
                                        + str(s.get("power_site_type") or "unknown"),
                                    ]
                                )
                            )
                            for s in sites
                        ]
                        if len(site_names) > 2:
                            CONSOLE.info("Select which Site to be monitored:")
                            for idx, sitename in enumerate(site_names):
                                CONSOLE.info("(%s) %s", idx, sitename)
                            selection = input(
                                f"Enter site number (0-{len(site_names) - 1}) or nothing for All: "
                            )
                            if selection.isdigit() and 1 <= int(selection) < len(
                                site_names
                            ):
                                site_selected = site_names[int(selection)].split(",")[0]
                        # ask which endpoint limit should be applied
                        selection = input(
                            f"Enter Api endpoint limit for request throttling (1-50, 0 = disabled) [Default: {myapi.apisession.endpointLimit()}]: "
                        )
                        if selection.isdigit() and 0 <= int(selection) <= 50:
                            myapi.apisession.endpointLimit(int(selection))
                    CONSOLE.info("Running site refresh...")
                    await myapi.update_sites(fromFile=use_file, siteId=site_selected)
                    next_dev_refr -= 1
                    if not use_file and energy_stats and deferred:
                        CONSOLE.info("Running energy details refresh...")
                        await myapi.update_device_energy(fromFile=use_file)
                        deferred = False
                    next_refr = datetime.now().astimezone() + timedelta(seconds=REFRESH)
                if next_dev_refr < 0:
                    CONSOLE.info("Running device and site details refresh...")
                    await myapi.update_device_details(fromFile=use_file)
                    await myapi.update_site_details(fromFile=use_file)
                    # run also energy refresh if requested
                    if energy_stats:
                        if startup and not use_file:
                            CONSOLE.info("Deferring initial energy details refresh...")
                            startup = False
                            deferred = True
                        else:
                            CONSOLE.info("Running energy details refresh...")
                            await myapi.update_device_energy(fromFile=use_file)
                            startup = False
                    next_refr = datetime.now().astimezone() + timedelta(seconds=REFRESH)
                    next_dev_refr = DETAILSREFRESH
                if use_file:
                    CONSOLE.info("Using input source folder: %s", myapi.testDir())
                else:
                    CONSOLE.info(
                        "Anker Solix Monitor (refresh %s s, details refresh countdown %s):",
                        REFRESH,
                        next_dev_refr,
                    )
                CONSOLE.info(
                    "Sites: %s, Devices: %s", len(myapi.sites), len(myapi.devices)
                )

                # pylint: disable=logging-fstring-interpolation
                shown_sites = set()
                for sn, dev in [
                    (s, d)
                    for s, d in myapi.devices.items()
                    if (not site_selected or d.get("site_id") == site_selected)
                ]:
                    devtype = dev.get("type", "Unknown")
                    admin = dev.get("is_admin", False)
                    siteid = dev.get("site_id", "")
                    site = myapi.sites.get(siteid) or {}
                    customized = dev.get("customized") or {}
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
                                f"{'System (' + shift + ')':<{col1}}: {(site.get('site_info') or {}).get('site_name', 'Unknown')}  (Site ID: {siteid})"
                            )
                            site_type = str(site.get("site_type", ""))
                            CONSOLE.info(
                                f"{'Type ID':<{col1}}: {str((site.get('site_info') or {}).get('power_site_type', '--')) + (' (' + site_type.capitalize() + ')') if site_type else '':<{col2}} Device models  : {','.join((site.get('site_info') or {}).get('current_site_device_models', []))}"
                            )
                            offset = site.get("energy_offset_seconds")
                            CONSOLE.info(
                                f"{'Energy Time':<{col1}}: {'----.--.-- --:--:--' if offset is None else (datetime.now() + timedelta(seconds=offset)).strftime('%Y-%m-%d %H:%M:%S'):<{col2}} {'Last Check':<{col3}}: {site.get('energy_offset_check') or '----.--.-- --:--:--'}"
                            )
                            if (sb := site.get("solarbank_info") or {}) and len(
                                sb.get("solarbank_list", [])
                            ) > 0:
                                # print solarbank totals
                                soc = f"{int(float(sb.get('total_battery_power') or 0) * 100)!s:>4} %"
                                unit = sb.get("power_unit") or "W"
                                update_time = sb.get("updated_time") or "Unknown"
                                CONSOLE.info(
                                    f"{'Cloud-Updated':<{col1}}: {update_time:<{col2}} {'Valid Data':<{col3}}: {'YES' if site.get('data_valid') else 'NO'} (Requeries: {site.get('requeries')})"
                                )
                                CONSOLE.info(
                                    f"{'SOC total':<{col1}}: {soc:<{col2}} {'Dischrg Pwr Tot':<{col3}}: {sb.get('battery_discharge_power', '---'):>4} {unit}"
                                )
                                CONSOLE.info(
                                    f"{'Solar  Pwr Tot':<{col1}}: {sb.get('total_photovoltaic_power', '---'):>4} {unit:<{col2 - 5}} {'Battery Pwr Tot':<{col3}}: {str(sb.get('total_charging_power')).split('.', maxsplit=1)[0]:>4} W"
                                )
                                CONSOLE.info(
                                    f"{'Output Pwr Tot':<{col1}}: {str(sb.get('total_output_power', '---')).split('.', maxsplit=1)[0]:>4} {unit:<{col2 - 5}} {'Home Load Tot':<{col3}}: {sb.get('to_home_load') or '----':>4} W"
                                )
                                features = site.get("feature_switch") or {}
                                if mode := site.get("scene_mode"):
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
                                        f"{'Active Mode':<{col1}}: {str(mode_name).capitalize() + ' (' + str(mode) + ')' if mode_name else '---------':<{col2}} {'Heating':<{col3}}: {'ON' if feat1 else '---' if feat1 is None else 'OFF'}"
                                    )
                                if "offgrid_with_micro_inverter_alert" in features:
                                    feat1 = features.get(
                                        "offgrid_with_micro_inverter_alert"
                                    )
                                    feat2 = features.get("micro_inverter_power_exceed")
                                    CONSOLE.info(
                                        f"{'Offgrid Alert':<{col1}}: {'ON' if feat1 else '---' if feat1 is None else 'OFF':<{col2}} {'Inv. Pwr Exceed':<{col3}}: {'ON' if feat2 else '---' if feat2 is None else 'OFF'}"
                                    )
                            if (hes := site.get("hes_info") or {}) and len(
                                hes.get("hes_list", [])
                            ) > 0:
                                # print hes totals
                                CONSOLE.info(
                                    f"{'Parallel Devs':<{col1}}: {hes.get('numberOfParallelDevice', '---'):>3} {'':<{col2 - 4}} {'Battery count':<{col3}}: {hes.get('batCount', '---'):>3}"
                                )
                                CONSOLE.info(
                                    f"{'Main SN':<{col1}}: {hes.get('main_sn', 'unknown'):<{col2}} {'System Code':<{col3}}: {hes.get('systemCode', 'unknown')}"
                                )
                                feat1 = hes.get("connected")
                                CONSOLE.info(
                                    f"{'Connected':<{col1}}: {'YES' if feat1 else '---' if feat1 is None else ' NO':>3} {'':<{col2 - 4}} {'Repost time':<{col3}}: {hes.get('rePostTime', '---'):>3} min?"
                                )
                                CONSOLE.info(
                                    f"{'Net status':<{col1}}: {hes.get('net', '---'):>3} {'':<{col2 - 4}} {'Real net':<{col3}}: {hes.get('realNet', '---'):>3}"
                                )
                                feat1 = hes.get("isAddHeatPump")
                                feat2 = hes.get("supportDiesel")
                                CONSOLE.info(
                                    f"{'Has heat pump':<{col1}}: {'YES' if feat1 else '---' if feat1 is None else ' NO':>3} {'':<{col2 - 4}} {'Support diesel':<{col3}}: {'YES' if feat2 else '---' if feat2 is None else ' NO':>3}"
                                )
                            CONSOLE.info("-" * 80)
                    else:
                        CONSOLE.info("-" * 80)
                    CONSOLE.info(
                        f"{'Device [' + dev.get('device_pn', '') + ']':<{col1}}: {(dev.get('name', 'NoName')):<{col2}} {'Alias':<{col3}}: {dev.get('alias', 'Unknown')}"
                    )
                    CONSOLE.info(
                        f"{'Serialnumber':<{col1}}: {sn:<{col2}} {'Admin':<{col3}}: {'YES' if admin else 'NO'}"
                    )
                    for fsn, fitting in (dev.get("fittings") or {}).items():
                        CONSOLE.info(
                            f"{'Accessory':<{col1}}: {fitting.get('device_name', ''):<{col2}} {'Serialnumber':<{col3}}: {fsn}"
                        )
                    CONSOLE.info(
                        f"{'Wifi SSID':<{col1}}: {dev.get('wifi_name', ''):<{col2}}"
                    )
                    online = dev.get("wifi_online")
                    CONSOLE.info(
                        f"{'Wifi state':<{col1}}: {('Unknown' if online is None else 'Online' if online else 'Offline'):<{col2}} {'Signal':<{col3}}: {dev.get('wifi_signal') or '---':>4} % ({dev.get('rssi') or '---'} dBm)"
                    )
                    if support := dev.get("is_support_wired"):
                        online = dev.get("wired_connected")
                        CONSOLE.info(
                            f"{'Wired state':<{col1}}: {('Unknown' if online is None else 'Connected' if online else 'Disconnected'):<{col2}} {'Support Wired':<{col3}}: {('Unknown' if support is None else 'YES' if support else 'NO')}"
                        )
                    upgrade = dev.get("auto_upgrade")
                    ota = dev.get("is_ota_update")
                    CONSOLE.info(
                        f"{'SW Version':<{col1}}: {dev.get('sw_version', 'Unknown') + ' (' + ('Unknown' if ota is None else 'Update' if ota else 'Latest') + ')':<{col2}} {'Auto-Upgrade':<{col3}}: {'Unknown' if upgrade is None else 'Enabled' if upgrade else 'Disabled'} (OTA {dev.get('ota_version') or 'Unknown'})"
                    )
                    for item in dev.get("ota_children") or []:
                        ota = item.get("need_update")
                        forced = item.get("force_upgrade")
                        CONSOLE.info(
                            f"{' -Component':<{col1}}: {item.get('device_type', 'Unknown') + ' (' + ('Unknown' if ota is None else 'Update' if ota else 'Latest') + ')':<{col2}} {' -Version':<{col3}}: {item.get('rom_version_name') or 'Unknown'}{' (Forced)' if forced else ''}"
                        )

                    if devtype == api.SolixDeviceType.SOLARBANK.value:
                        CONSOLE.info(
                            f"{'Cloud Status':<{col1}}: {str(dev.get('status_desc', '-------')).capitalize():<{col2}} {'Status code':<{col3}}: {dev.get('status', '-')!s}"
                        )
                        CONSOLE.info(
                            f"{'Charge Status':<{col1}}: {str(dev.get('charging_status_desc', '-------')).capitalize():<{col2}} {'Status code':<{col3}}: {dev.get('charging_status', '-')!s}"
                        )
                        if aiems := (dev.get("schedule") or {}).get("ai_ems") or {}:
                            status = aiems.get("status")
                            CONSOLE.info(
                                f"{'AI Status':<{col1}}: {str(SolarbankAiemsStatus(status).name if status in iter(SolarbankUsageMode) else '-----').capitalize() + ' (' + str(status) + ')':<{col2}} {'AI Enabled':<{col3}}: {'YES' if aiems.get('enable') else 'NO'}"
                            )
                        soc = f"{dev.get('battery_soc', '---'):>4} %"
                        CONSOLE.info(
                            f"{'State Of Charge':<{col1}}: {soc:<{col2}} {'Min SOC':<{col3}}: {dev.get('power_cutoff', '--')!s:>4} %"
                        )
                        energy = f"{dev.get('battery_energy', '----'):>4} Wh"
                        CONSOLE.info(
                            f"{'Battery Energy':<{col1}}: {energy:<{col2}} {'Capacity':<{col3}}: {customized.get('battery_capacity') or dev.get('battery_capacity', '----')!s:>4} Wh"
                        )
                        unit = dev.get("power_unit", "W")
                        if dev.get("generation", 0) > 1:
                            CONSOLE.info(
                                f"{'Exp. Batteries':<{col1}}: {dev.get('sub_package_num', '-'):>4} {'Pcs':<{col2 - 5}} {'AC socket':<{col3}}: {dev.get('ac_power', '---'):>4} {unit}"
                            )
                        CONSOLE.info(
                            f"{'Solar Power':<{col1}}: {dev.get('input_power', '---'):>4} {unit:<{col2 - 5}} {'Output Power':<{col3}}: {dev.get('output_power', '---'):>4} {unit}"
                        )
                        # show each MPPT for Solarbank 2
                        if "solar_power_1" in dev:
                            CONSOLE.info(
                                f"{'Solar Ch_1':<{col1}}: {dev.get('solar_power_1', '---'):>4} {unit:<{col2 - 5}} {'Solar Ch_2':<{col3}}: {dev.get('solar_power_2', '---'):>4} {unit}"
                            )
                            if "solar_power_3" in dev:
                                CONSOLE.info(
                                    f"{'Solar Ch_3':<{col1}}: {dev.get('solar_power_3', '---'):>4} {unit:<{col2 - 5}} {'Solar Ch_4':<{col3}}: {dev.get('solar_power_4', '---'):>4} {unit}"
                                )
                        if "pei_heating_power" in dev:
                            CONSOLE.info(
                                f"{'Other Input':<{col1}}: {dev.get('other_input_power', '---'):>4} {unit:<{col2 - 5}} {'Heating Power':<{col3}}: {dev.get('pei_heating_power', '---'):>4} {unit}"
                            )
                        if "grid_to_battery_power" in dev:
                            CONSOLE.info(
                                f"{'Grid to Battery':<{col1}}: {dev.get('grid_to_battery_power', '---'):>4} {unit:<{col2 - 5}} {'Inverter Power':<{col3}}: {dev.get('micro_inverter_power', '---'):>4} {unit}"
                            )
                        if "micro_inverter_power_limit" in dev:
                            CONSOLE.info(
                                f"{'Inverter Limit':<{col1}}: {dev.get('micro_inverter_power_limit', '---'):>4} {unit:<{col2 - 5}} {'Low Limit':<{col3}}: {dev.get('micro_inverter_low_power_limit', '---'):>4} {unit}"
                            )

                        CONSOLE.info(
                            f"{'Battery charge':<{col1}}: {dev.get('bat_charge_power', '---'):>4} {unit:<{col2 - 5}}"
                        )
                        preset = dev.get("set_output_power") or "---"
                        site_preset = dev.get("set_system_output_power") or "---"
                        CONSOLE.info(
                            f"{'Battery Power':<{col1}}: {dev.get('charging_power', '---'):>4} {unit:<{col2 - 5}} {'Device Preset':<{col3}}: {preset:>4} {unit}"
                        )
                        if dev.get("generation", 0) > 1:
                            demand = site.get("home_load_power") or ""
                            load = (site.get("solarbank_info") or {}).get(
                                "to_home_load"
                            ) or ""
                            diff = ""
                            with contextlib.suppress(ValueError):
                                if float(demand) > float(load):
                                    diff = "(-)"
                                elif float(demand) < float(load):
                                    diff = "(+)"
                            CONSOLE.info(
                                f"{'Home Demand':<{col1}}: {demand or '---':>4} {unit:<{col2 - 5}} {'SB Home Load':<{col3}}: {load or '---':>4} {unit}  {diff}"
                            )
                            # Total smart plug power and other power?
                            CONSOLE.info(
                                f"{'Smart Plugs':<{col1}}: {(site.get('smart_plug_info') or {}).get('total_power') or '---':>4} {unit:<{col2 - 5}} {'Other (Plan)':<{col3}}: {site.get('other_loads_power') or '---':>4} {unit}"
                            )
                        # update schedule with device details refresh and print it
                        CONSOLE.info(
                            f"{'Schedule  (Now)':<{col1}}: {datetime.now().astimezone().strftime('%H:%M:%S UTC %z'):<{col2}} {'System Preset':<{col3}}: {str(site_preset).replace('W', ''):>4} W"
                        )
                        if admin:
                            # print schedule
                            common.print_schedule(dev.get("schedule") or {})
                    elif devtype == api.SolixDeviceType.INVERTER.value:
                        CONSOLE.info(
                            f"{'Cloud Status':<{col1}}: {str(dev.get('status_desc', '-------')).capitalize():<{col2}} {'Status code':<{col3}}: {dev.get('status', '-')!s}"
                        )
                        unit = dev.get("power_unit", "W")
                        CONSOLE.info(
                            f"{'AC Power':<{col1}}: {dev.get('generate_power', '----'):>4} {unit:<{col2 - 5}} {'Inverter Limit':<{col3}}: {dev.get('preset_inverter_limit', '---'):>4} {unit}"
                        )
                    elif devtype == api.SolixDeviceType.SMARTMETER.value:
                        CONSOLE.info(
                            f"{'Cloud Status':<{col1}}: {str(dev.get('status_desc', '-------')).capitalize():<{col2}} {'Status code':<{col3}}: {dev.get('status', '-')!s}"
                        )
                        CONSOLE.info(
                            f"{'Grid Status':<{col1}}: {str(dev.get('grid_status_desc', '-------')).capitalize():<{col2}} {'Status code':<{col3}}: {dev.get('grid_status', '-')!s}"
                        )
                        unit = "W"
                        CONSOLE.info(
                            f"{'Grid Import':<{col1}}: {dev.get('grid_to_home_power', '----'):>4} {unit:<{col2 - 5}} {'Grid Export':<{col3}}: {dev.get('photovoltaic_to_grid_power', '----'):>4} {unit}"
                        )
                    elif devtype == api.SolixDeviceType.SMARTPLUG.value:
                        CONSOLE.info(
                            f"{'Cloud Status':<{col1}}: {str(dev.get('status_desc', '-------')).capitalize():<{col2}} {'Status code':<{col3}}: {dev.get('status', '-')!s}"
                        )
                        unit = dev.get("power_unit", "W")
                        CONSOLE.info(
                            f"{'Plug Power':<{col1}}: {dev.get('current_power', ''):>4} {unit:<{col2 - 5}} {'Tag':<{col3}}: {dev.get('tag', '')}"
                        )
                        if dev.get("energy_today"):
                            CONSOLE.info(
                                f"{'Energy today':<{col1}}: {dev.get('energy_today') or '-.--':>4} {'kWh':<{col2 - 5}} {'Last Period':<{col3}}: {dev.get('energy_last_period') or '-.--':>4} kWh"
                            )
                    elif devtype in [
                        api.SolixDeviceType.POWERPANEL.value,
                        api.SolixDeviceType.HES.value,
                    ]:
                        if hes := dev.get("hes_data") or {}:
                            CONSOLE.info(
                                f"{'Station ID':<{col1}}: {hes.get('station_id', '-------'):<{col2}}     (Type: {str(hes.get('type', '---')).upper()})"
                            )
                            CONSOLE.info(
                                f"{'Cloud Status':<{col1}}: {str(hes.get('status_desc', '-------')).capitalize():<{col2}} {'Status code':<{col3}}: {hes.get('online_status', '-')!s}"
                            )
                            CONSOLE.info(
                                f"{'Network Status':<{col1}}: {str(hes.get('network_status_desc', '-------')).capitalize():<{col2}} {'Status code':<{col3}}: {hes.get('network_status', '-')!s}"
                            )
                            CONSOLE.info(
                                f"{'Grid Status':<{col1}}: {str(hes.get('grid_status_desc', '-------')).capitalize():<{col2}} {'Status code':<{col3}}: {hes.get('grid_status', '-')!s}"
                            )
                            CONSOLE.info(
                                f"{'Role Status':<{col1}}: {str(hes.get('role_status_desc', '-------')).capitalize():<{col2}} {'Status code':<{col3}}: {hes.get('master_slave_status', '-')!s}"
                            )
                        if "status_desc" in dev:
                            CONSOLE.info(
                                f"{'Cloud Status':<{col1}}: {str(dev.get('status_desc', '-------')).capitalize():<{col2}} {'Status code':<{col3}}: {dev.get('status', '-')!s}"
                            )
                        if avg := dev.get("average_power") or {}:
                            unit = str(avg.get("power_unit") or "").upper()
                            CONSOLE.info(
                                f"{'Valid ⌀ before':<{col1}}: {avg.get('valid_time', 'Unknown'):<{col2}} {'Last Check':<{col3}}: {avg.get('last_check', 'Unknown')!s}"
                            )
                            CONSOLE.info(
                                f"{'Battery SOC':<{col1}}: {avg.get('state_of_charge') or '---':>4} %"
                            )
                            CONSOLE.info(
                                f"{'Solar Power ⌀':<{col1}}: {avg.get('solar_power_avg') or '-.--':>4} {unit:<{col2 - 5}} {'Home Usage ⌀':<{col3}}: {avg.get('home_usage_avg') or '-.--':>4} {unit}"
                            )
                            CONSOLE.info(
                                f"{'Charge Power ⌀':<{col1}}: {avg.get('charge_power_avg') or '-.--':>4} {unit:<{col2 - 5}} {'Discharge Pwr ⌀':<{col3}}: {avg.get('discharge_power_avg') or '-.--':>4} {unit}"
                            )
                            CONSOLE.info(
                                f"{'Grid Import ⌀':<{col1}}: {avg.get('grid_import_avg') or '-.--':>4} {unit:<{col2 - 5}} {'Grid Export ⌀':<{col3}}: {avg.get('grid_export_avg') or '-.--':>4} {unit}"
                            )

                    else:
                        CONSOLE.warning(
                            "No Solarbank, Inverter, Smart Meter, Smart Plug, Power Panel or HES device, further device details will be skipped"
                        )
                # print optional energy details
                if energy_stats:
                    for site_id, site in [
                        (s, d)
                        for s, d in myapi.sites.items()
                        if (not site_selected or s == site_selected)
                    ]:
                        details = site.get("site_details") or {}
                        customized = site.get("customized") or {}
                        CONSOLE.info("=" * 80)
                        CONSOLE.info(
                            f"Energy details for System {(site.get('site_info') or {}).get('site_name', 'Unknown')} (Site ID: {site_id}):"
                        )
                        if len(totals := site.get("statistics") or []) >= 3:
                            CONSOLE.info(
                                f"{'Total Produced':<{col1}}: {totals[0].get('total', '---.--'):>6} {str(totals[0].get('unit', '')).upper():<{col2 - 8}}  {'Carbon saved':<{col3}}: {totals[1].get('total', '---.--'):>6} {str(totals[1].get('unit', '')).upper()}"
                            )
                            if co2 := details.get("co2_ranking") or {}:
                                CONSOLE.info(
                                    f"{'CO2 Ranking':<{col1}}: {co2.get('ranking') or '----':>6} {'(' + str(co2.get('tree') or '--.-') + ' Trees)':<{col2 - 8}}  {'Message':<{col3}}: {co2.get('content')}"
                                )
                            price = (
                                f"{float(price):.2f}"
                                if (price := str(details.get("price") or ""))
                                .replace("-", "", 1)
                                .replace(".", "", 1)
                                .isdigit()
                                else "--.--"
                            )
                            unit = details.get("site_price_unit") or ""
                            CONSOLE.info(
                                f"{'Max savings':<{col1}}: {totals[2].get('total', '---.--'):>6} {totals[2].get('unit', ''):<{col2 - 8}}  {'Price kWh':<{col3}}: {price:>6} {unit} (Fix)"
                            )
                        if ai_profits := site.get("aiems_profit"):
                            unit = ai_profits.get("unit") or ""
                            CONSOLE.info(
                                f"{'AI savings':<{col1}}: {ai_profits.get('aiems_profit_total', '---.--'):>6} {unit:<{col2 - 8}}  {'AI Advantage':<{col3}}: {ai_profits.get('aiems_self_use_diff', '---.--'):>6} {unit} ({ai_profits.get('percentage', '---.--')} %)"
                            )
                        price_type = details.get("price_type") or ""
                        dynamic = details.get("dynamic_price") or {}
                        if price_type or dynamic:
                            dyn_price = None
                            dyn_unit = None
                            if price_type in [SolixPriceTypes.DYNAMIC.value]:
                                dyn_price = (
                                    f"{float(price):.2f}"
                                    if (
                                        price := details.get("dynamic_price_total")
                                        or ""
                                    )
                                    .replace("-", "", 1)
                                    .replace(".", "", 1)
                                    .isdigit()
                                    else "--.--"
                                )
                                dyn_unit = details.get("spot_price_unit") or ""
                            elif price_type in [SolixPriceTypes.USE_TIME.value] and (
                                dev := myapi.devices.get(
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
                            if provider := dynamic.get("company") or "":
                                provider = f"{provider} ({dynamic.get('country') or '--'}/{dynamic.get('area') or '---'})"
                            CONSOLE.info(
                                f"{'Active Price':<{col1}}: {dyn_price or price:>6} {(dyn_unit or unit) + ' (' + (price_type.capitalize() or '------') + ')':<{col2 - 7}} {'Price Provider':<{col3}}: {provider or '----------'}"
                            )
                            if (spot := details.get("spot_price_mwh")) is not None:
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
                                        price := details.get("spot_price_mwh_avg_today")
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
                                        price := details.get(
                                            "spot_price_mwh_avg_tomorrow"
                                        )
                                        or ""
                                    )
                                    .replace("-", "", 1)
                                    .replace(".", "", 1)
                                    .isdigit()
                                    else "---.--"
                                )
                                unit = details.get("spot_price_unit") or ""
                                time = str(details.get('spot_price_time') or "")[-5:]
                                CONSOLE.info(
                                    f"{'Spot Price':<{col1}}: {spot:>6} {unit + '/MWh (' + (time or '--:--') + ')':<{col2 - 7}} {'Avg today/tomor':<{col3}}: {today:>6} / {tomorrow:>6} {unit + '/MWh'}"
                                )

                                CONSOLE.info(
                                    f"{'Price Fee':<{col1}}: {details.get('dynamic_price_fee') or '-.----':>8} {unit:<{col2 - 9}} {'Price VAT':<{col3}}: {details.get('dynamic_price_vat') or '--.--':>6} %"
                                )
                        if energy := site.get("energy_details") or {}:
                            CONSOLE.info("-" * 80)
                            today: dict = energy.get("today") or {}
                            yesterday: dict = energy.get("last_period") or {}
                            unit = "kWh"
                            CONSOLE.info(
                                f"{'Today':<{col1}}: {today.get('date', '----------'):<{col2}} {'Yesterday':<{col3}}: {yesterday.get('date', '----------')!s}"
                            )
                            CONSOLE.info(
                                f"{'Solar Energy':<{col1}}: {today.get('solar_production') or '-.--':>6} {unit:<{col2 - 7}} {'Solar Energy':<{col3}}: {yesterday.get('solar_production') or '-.--':>6} {unit}"
                            )
                            if value := today.get("solar_production_pv1"):
                                CONSOLE.info(
                                    f"{'Solar Ch 1/2':<{col1}}: {today.get('solar_production_pv1') or '-.--':>6} / {today.get('solar_production_pv2') or '-.--':>5} {unit:<{col2 - 15}} {'Solar Ch 1/2':<{col3}}: {yesterday.get('solar_production_pv1') or '-.--':>6} / {yesterday.get('solar_production_pv2') or '-.--':>5} {unit}"
                                )
                            if value := today.get("solar_production_pv3"):
                                CONSOLE.info(
                                    f"{'Solar Ch 3/4':<{col1}}: {today.get('solar_production_pv3') or '-.--':>6} / {today.get('solar_production_pv4') or '-.--':>5} {unit:<{col2 - 15}} {'Solar Ch 3/4':<{col3}}: {yesterday.get('solar_production_pv3') or '-.--':>6} / {yesterday.get('solar_production_pv4') or '-.--':>5} {unit}"
                                )
                            if value := today.get("solar_production_microinverter"):
                                CONSOLE.info(
                                    f"{'Solar Ch AC':<{col1}}: {today.get('solar_production_microinverter') or '-.--':>6} {unit:<{col2 - 7}} {'Solar Ch AC':<{col3}}: {yesterday.get('solar_production_microinverter') or '-.--':>6} {unit}"
                                )
                            if value := today.get("battery_charge"):
                                CONSOLE.info(
                                    f"{'Charged':<{col1}}: {value or '-.--':>6} {unit:<{col2 - 7}} {'Charged':<{col3}}: {yesterday.get('battery_charge') or '-.--':>6} {unit}"
                                )
                            if value := today.get("solar_to_battery"):
                                CONSOLE.info(
                                    f"{'Charged Solar':<{col1}}: {value or '-.--':>6} {unit:<{col2 - 7}} {'Charged Solar':<{col3}}: {yesterday.get('solar_to_battery') or '-.--':>6} {unit}"
                                )
                            if value := today.get("grid_to_battery"):
                                CONSOLE.info(
                                    f"{'Charged Grid':<{col1}}: {value or '-.--':>6} {unit:<{col2 - 7}} {'Charged Grid':<{col3}}: {yesterday.get('grid_to_battery') or '-.--':>6} {unit}"
                                )
                            if value := today.get("battery_discharge"):
                                CONSOLE.info(
                                    f"{'Discharged':<{col1}}: {value or '-.--':>6} {unit:<{col2 - 7}} {'Discharged':<{col3}}: {yesterday.get('battery_discharge') or '-.--':>6} {unit}"
                                )
                            if value := today.get("home_usage"):
                                CONSOLE.info(
                                    f"{'House Usage':<{col1}}: {value or '-.--':>6} {unit:<{col2 - 7}} {'House Usage':<{col3}}: {yesterday.get('home_usage') or '-.--':>6} {unit}"
                                )
                            if value := today.get("solar_to_home"):
                                CONSOLE.info(
                                    f"{'Solar Usage':<{col1}}: {value or '-.--':>6} {unit:<{col2 - 7}} {'Solar Usage':<{col3}}: {yesterday.get('solar_to_home') or '-.--':>6} {unit}"
                                )
                            if value := today.get("battery_to_home"):
                                CONSOLE.info(
                                    f"{'Battery Usage':<{col1}}: {value or '-.--':>6} {unit:<{col2 - 7}} {'Battery Usage':<{col3}}: {yesterday.get('battery_to_home') or '-.--':>6} {unit}"
                                )
                            if value := today.get("grid_to_home"):
                                CONSOLE.info(
                                    f"{'Grid Usage':<{col1}}: {value or '-.--':>6} {unit:<{col2 - 7}} {'Grid Usage':<{col3}}: {yesterday.get('grid_to_home') or '-.--':>6} {unit}"
                                )
                            if value := today.get("grid_import"):
                                CONSOLE.info(
                                    f"{'Grid Import':<{col1}}: {value or '-.--':>6} {unit:<{col2 - 7}} {'Grid Import':<{col3}}: {yesterday.get('grid_import') or '-.--':>6} {unit}"
                                )
                            if value := today.get("solar_to_grid"):
                                CONSOLE.info(
                                    f"{'Grid Export':<{col1}}: {value or '-.--':>6} {unit:<{col2 - 7}} {'Grid Export':<{col3}}: {yesterday.get('solar_to_grid') or '-.--':>6} {unit}"
                                )
                            if value := today.get("ac_socket"):
                                CONSOLE.info(
                                    f"{'AC Socket':<{col1}}: {value or '-.--':>6} {unit:<{col2 - 7}} {'AC Socket':<{col3}}: {yesterday.get('ac_socket') or '-.--':>6} {unit}"
                                )
                            if value := today.get("smartplugs_total"):
                                CONSOLE.info(
                                    f"{'Smartplugs':<{col1}}: {value or '-.--':>6} {unit:<{col2 - 7}} {'Smartplugs':<{col3}}: {yesterday.get('smartplugs_total') or '-.--':>6} {unit}"
                                )
                            for idx, plug_t in enumerate(
                                today.get("smartplug_list") or []
                            ):
                                plug_y = (yesterday.get("smartplug_list") or [])[idx]
                                CONSOLE.info(
                                    f"{'-' + plug_t.get('alias', 'Plug ' + str(idx + 1)):<{col1}}: {plug_t.get('energy') or '-.--':>6} {unit:<{col2 - 7}} {'-' + plug_y.get('alias', 'Plug ' + str(idx + 1)):<{col3}}: {plug_y.get('energy') or '-.--':>6} {unit}"
                                )
                            if value := today.get("solar_percentage"):
                                CONSOLE.info(
                                    f"{'Sol/Bat/Gri %':<{col1}}: {float(value or '0') * 100:>3.0f}/{float(today.get('battery_percentage') or '0') * 100:>3.0f}/{float(today.get('other_percentage') or '0') * 100:>3.0f} {'%':<{col2 - 12}} {'Sol/Bat/Gri %':<{col3}}: {float(yesterday.get('solar_percentage') or '0') * 100:>3.0f}/{float(yesterday.get('battery_percentage') or '0') * 100:>3.0f}/{float(yesterday.get('other_percentage') or '0') * 100:>3.0f} %"
                                )

                # ask to reload or switch to next file or wait for refresh cycle of real time monitoring
                CONSOLE.info("=" * 80)
                if use_file:
                    while use_file:
                        CONSOLE.info("Api Requests: %s", myapi.request_count)
                        CONSOLE.log(
                            logging.INFO if SHOWAPICALLS else logging.DEBUG,
                            myapi.request_count.get_details(last_hour=True),
                        )
                        CONSOLE.log(
                            logging.INFO if SHOWAPICALLS else logging.DEBUG,
                            json.dumps(myapi.sites, indent=2),
                        )
                        CONSOLE.log(
                            logging.INFO if SHOWAPICALLS else logging.DEBUG,
                            json.dumps(myapi.devices, indent=2),
                        )
                        myapi.request_count.recycle(last_time=datetime.now())
                        resp = input(
                            "[S]ite refresh, [A]ll refresh, select [O]ther file, toggle [N]ext/[P]revious file, [C]ustomize or [Q]uit: "
                        )
                        if resp.upper() in ["S", "SITE"]:
                            # set device details refresh to future to reload only site info
                            next_dev_refr += 1
                            break
                        if resp.upper() in ["A", "ALL"]:
                            next_dev_refr = 0
                            break
                        if resp.upper() in ["C", "USTOMIZE"]:
                            CONSOLE.info("Site IDs and Device SNs for customization:")
                            cache: dict = myapi.sites | myapi.devices
                            for idx, item in enumerate(
                                itemlist := list(cache.keys()),
                                start=1,
                            ):
                                CONSOLE.info(
                                    "(%s) %s - %s",
                                    idx,
                                    item,
                                    cache.get(item).get("name")
                                    or (cache.get(item).get("site_info") or {}).get(
                                        "site_name"
                                    ),
                                )
                            CONSOLE.info("(q) Quit")
                            while use_file:
                                select = input(
                                    f"Select ID (1-{len(itemlist)}) or [c]ancel: "
                                )
                                if select.upper() in ["C", "CANCEL"]:
                                    break
                                if select.isdigit() and 1 <= (
                                    select := int(select)
                                ) <= len(itemlist):
                                    break
                            if isinstance(select, int):
                                item = itemlist[select - 1]
                                key = input(f"Enter key to be customized in '{item}': ")
                                value = json.loads(f'{input(f"Enter '{key}' value in JSON format: ").replace("'",'"')}')
                                myapi.customizeCacheId(id=item, key=key, value=value)
                                CONSOLE.info(
                                    "Customized part of %s:\n%s",
                                    item,
                                    json.dumps(
                                        myapi.getCaches().get(item).get("customized")
                                        or {},
                                        indent=2,
                                    ),
                                )
                                input("Hit enter to refresh all data...")
                                next_dev_refr = 0
                            break
                        if resp.upper() in ["O", "OTHER"] and exampleslist:
                            CONSOLE.info("Select the input source for the monitor:")
                            for idx, filename in enumerate(exampleslist, start=1):
                                CONSOLE.info("(%s) %s", idx, filename)
                            CONSOLE.info("(q) Quit")
                            while use_file:
                                selection = input(
                                    f"Enter source file number (1-{len(exampleslist)}) or [q]uit: "
                                )
                                if selection.upper() in ["Q", "QUIT"]:
                                    return True
                                if selection.isdigit() and 1 <= (
                                    selection := int(selection)
                                ) <= len(exampleslist):
                                    break
                            testfolder = exampleslist[selection - 1]
                            myapi.testDir(testfolder)
                            myapi.clearCaches()
                            next_dev_refr = 0
                            break
                        if resp.upper() in ["N", "NEXT"] and exampleslist:
                            selection = (
                                (selection + 1) if selection < len(exampleslist) else 1
                            )
                            testfolder = exampleslist[selection - 1]
                            myapi.testDir(testfolder)
                            myapi.clearCaches()
                            next_dev_refr = 0
                            break
                        if resp.upper() in ["P", "PREVIOUS"] and exampleslist:
                            selection = (
                                (selection - 1) if selection > 1 else len(exampleslist)
                            )
                            testfolder = exampleslist[selection - 1]
                            myapi.testDir(testfolder)
                            myapi.clearCaches()
                            next_dev_refr = 0
                            break
                        if resp.upper() in ["Q", "QUIT"]:
                            return True
                else:
                    CONSOLE.info(
                        "Api Requests: %s",
                        myapi.request_count,
                    )
                    CONSOLE.log(
                        logging.INFO if SHOWAPICALLS else logging.DEBUG,
                        myapi.request_count.get_details(last_hour=True),
                    )
                    CONSOLE.log(
                        logging.INFO if SHOWAPICALLS else logging.DEBUG,
                        json.dumps(myapi.sites, indent=2),
                    )
                    CONSOLE.log(
                        logging.INFO if SHOWAPICALLS else logging.DEBUG,
                        json.dumps(myapi.devices, indent=2),
                    )
                    for sec in range(REFRESH):
                        now = datetime.now().astimezone()
                        if sys.stdin is sys.__stdin__:
                            print(  # noqa: T201
                                f"Site refresh: {int((next_refr - now).total_seconds()):>3} sec,  Device details countdown: {int(next_dev_refr):>2}  (CTRL-C to abort)",
                                end="\r",
                                flush=True,
                            )
                            if next_refr < now:
                                break
                        elif sec == 0 or next_refr < now:
                            # IDLE may be used and does not support cursor placement, skip time progress display
                            print(  # noqa: T201
                                f"Site refresh: {int((next_refr - now).total_seconds()):>3} sec,  Device details countdown: {int(next_dev_refr):>2}  (CTRL-C to abort)",
                                end="",
                                flush=True,
                            )
                            if next_refr < now:
                                break
                        await asyncio.sleep(1)
                    await asyncio.sleep(1)
            return False

    except (ClientError, errors.AnkerSolixError) as err:
        CONSOLE.error("%s: %s", type(err), err)
        CONSOLE.info("Api Requests: %s", myapi.request_count)
        CONSOLE.info(myapi.request_count.get_details(last_hour=True))
        return False


# run async main
if __name__ == "__main__":
    try:
        if not asyncio.run(main(), debug=False):
            CONSOLE.warning("\nAborted!")
    except KeyboardInterrupt:
        CONSOLE.warning("\nAborted!")
    except Exception as exception:  # pylint: disable=broad-exception-caught  # noqa: BLE001
        CONSOLE.exception("%s: %s", type(exception), exception)
