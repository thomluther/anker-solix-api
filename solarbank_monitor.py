#!/usr/bin/env python
"""Example exec module to use the Anker API for continuously querying and
displaying important solarbank parameters This module will prompt for the Anker
account details if not pre-set in the header.  Upon successful authentication,
you will see the solarbank parameters displayed and refreshed at regular
interval.

Note: When the system owning account is used, more details for the solarbank
can be queried and displayed.

Attention: During execution of this module, the used account cannot be used in
the Anker App since it will be kicked out on each refresh.

"""  # noqa: D205

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
import common

# use Console logger from common module
CONSOLE: logging.Logger = common.CONSOLE
# enable debug mode for the console handler
# CONSOLE.handlers[0].setLevel(logging.DEBUG)

REFRESH = 0  # default No refresh interval
INTERACTIVE = True


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
    """Run Main routine to start Solarbank monitor in a loop."""
    global REFRESH  # pylint: disable=global-statement  # noqa: PLW0603
    CONSOLE.info("Solarbank Monitor:")
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
            now = datetime.now().astimezone()
            next_refr = now
            next_dev_refr = now
            col1 = 15
            col2 = 23
            col3 = 15
            while True:
                clearscreen()
                now = datetime.now().astimezone()
                if next_refr <= now:
                    CONSOLE.info("Running site refresh...")
                    await myapi.update_sites(fromFile=use_file)
                    next_refr = now + timedelta(seconds=REFRESH)
                if next_dev_refr <= now:
                    CONSOLE.info("Running device details refresh...")
                    await myapi.update_device_details(fromFile=use_file)
                    # run also energy refresh if requested
                    if energy_stats:
                        CONSOLE.info("Running energy details refresh...")
                        await myapi.update_site_details(fromFile=use_file)
                        await myapi.update_device_energy(fromFile=use_file)
                    next_dev_refr = next_refr + timedelta(
                        seconds=max((not use_file) * 120, REFRESH * 9)
                    )
                    # schedules = {}
                if use_file:
                    CONSOLE.info("Using input source folder: %s", myapi.testDir())
                else:
                    CONSOLE.info(
                        "Solarbank Monitor (refresh %s s, details refresh %s s):",
                        REFRESH,
                        max(120, 10 * REFRESH),
                    )
                CONSOLE.info(
                    "Sites: %s, Devices: %s", len(myapi.sites), len(myapi.devices)
                )
                # pylint: disable=logging-fstring-interpolation
                shown_sites = set()
                for sn, dev in myapi.devices.items():
                    devtype = dev.get("type", "Unknown")
                    admin = dev.get("is_admin", False)
                    siteid = dev.get("site_id", "")
                    site = myapi.sites.get(siteid) or {}
                    if not (siteid and siteid in shown_sites):
                        CONSOLE.info("=" * 80)
                        if siteid:
                            shown_sites.add(siteid)
                            CONSOLE.info(
                                f"{'System':<{col1}}: {(site.get('site_info') or {}).get('site_name', 'Unknown')}  (Site ID: {siteid})"
                            )
                            site_type = str(site.get("site_type", ""))
                            CONSOLE.info(
                                f"{'Type ID':<{col1}}: {str((site.get('site_info') or {}).get('power_site_type', '--')) + (' (' + site_type.capitalize() + ')') if site_type else '':<{col2}} Device models  : {','.join((site.get('site_info') or {}).get('current_site_device_models', []))}"
                            )
                            if (sb := site.get("solarbank_info") or {}) and len(sb.get("solarbank_list",[])) > 0:
                                # print solarbank totals
                                soc = f"{int(float(sb.get('total_battery_power') or 0)*100)!s:>4} %"
                                unit = sb.get("power_unit") or "W"
                                update_time = sb.get("updated_time") or "Unknown"
                                CONSOLE.info(
                                    f"{'Cloud-Updated':<{col1}}: {update_time:<{col2}} {'Valid Data':<{col3}}: {'YES' if site.get('data_valid') else 'NO'} (Requeries: {site.get('requeries')})"
                                )
                                CONSOLE.info(
                                    f"{'SOC total':<{col1}}: {soc:<{col2}} {'Dischrg Pwr Tot':<{col3}}: {sb.get('battery_discharge_power', '---'):>4} {unit}"
                                )
                                CONSOLE.info(
                                    f"{'Solar  Pwr Tot':<{col1}}: {sb.get('total_photovoltaic_power', '---'):>4} {unit:<{col2 - 5}} {'Battery Pwr Tot':<{col3}}: {str(sb.get('total_charging_power')).split('.')[0]:>4} W"
                                )
                                CONSOLE.info(
                                    f"{'Output Pwr Tot':<{col1}}: {str(sb.get('total_output_power', '---')).split('.')[0]:>4} {unit:<{col2 - 5}} {'Home Load Tot':<{col3}}: {sb.get('to_home_load'):>4} W"
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
                            f"{'Cloud Status':<{col1}}: {dev.get('status_desc', 'Unknown'):<{col2}} {'Status code':<{col3}}: {dev.get('status', '-')!s}"
                        )
                        CONSOLE.info(
                            f"{'Charge Status':<{col1}}: {dev.get('charging_status_desc', 'Unknown'):<{col2}} {'Status code':<{col3}}: {dev.get('charging_status', '-')!s}"
                        )
                        soc = f"{dev.get('battery_soc', '---'):>4} %"
                        CONSOLE.info(
                            f"{'State Of Charge':<{col1}}: {soc:<{col2}} {'Min SOC':<{col3}}: {dev.get('power_cutoff', '--')!s:>4} %"
                        )
                        energy = f"{dev.get('battery_energy', '----'):>4} Wh"
                        CONSOLE.info(
                            f"{'Battery Energy':<{col1}}: {energy:<{col2}} {'Capacity':<{col3}}: {dev.get('battery_capacity', '----')!s:>4} Wh"
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
                        if "micro_inverter_power" in dev:
                            CONSOLE.info(
                                f"{'Inverter Power':<{col1}}: {dev.get('micro_inverter_power', '---'):>4} {unit:<{col2 - 5}} {'Grid to Battery':<{col3}}: {dev.get('grid_to_battery_power', '---'):>4} {unit}"
                            )
                        if "micro_inverter_power_limit" in dev:
                            CONSOLE.info(
                                f"{'Inverter Limit':<{col1}}: {dev.get('micro_inverter_power_limit', '---'):>4} {unit:<{col2 - 5}} {'Low Limit':<{col3}}: {dev.get('micro_inverter_low_power_limit', '---'):>4} {unit}"
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
                            f"{'Schedule  (Now)':<{col1}}: {now.strftime('%H:%M:%S UTC %z'):<{col2}} {'System Preset':<{col3}}: {str(site_preset).replace('W', ''):>4} W"
                        )
                        if admin:
                            # print schedule
                            common.print_schedule(dev.get("schedule") or {})
                    elif devtype == api.SolixDeviceType.INVERTER.value:
                        CONSOLE.info(
                            f"{'Cloud Status':<{col1}}: {dev.get('status_desc', 'Unknown'):<{col2}} {'Status code':<{col3}}: {dev.get('status', '-')!s}"
                        )
                        unit = dev.get("power_unit", "W")
                        CONSOLE.info(
                            f"{'AC Power':<{col1}}: {dev.get('generate_power', '----'):>3} {unit}"
                        )
                    elif devtype == api.SolixDeviceType.SMARTMETER.value:
                        CONSOLE.info(
                            f"{'Cloud Status':<{col1}}: {dev.get('status_desc', 'Unknown'):<{col2}} {'Status code':<{col3}}: {dev.get('status', '-')!s}"
                        )
                        CONSOLE.info(
                            f"{'Grid Status':<{col1}}: {dev.get('grid_status_desc', 'Unknown'):<{col2}} {'Status code':<{col3}}: {dev.get('grid_status', '-')!s}"
                        )
                        unit = "W"
                        CONSOLE.info(
                            f"{'Grid Import':<{col1}}: {dev.get('grid_to_home_power', '----'):>4} {unit:<{col2 - 5}} {'Grid Export':<{col3}}: {dev.get('photovoltaic_to_grid_power', '----'):>4} {unit}"
                        )
                    elif devtype == api.SolixDeviceType.SMARTPLUG.value:
                        CONSOLE.info(
                            f"{'Cloud Status':<{col1}}: {dev.get('status_desc', 'Unknown'):<{col2}} {'Status code':<{col3}}: {dev.get('status', '-')!s}"
                        )
                        unit = dev.get("power_unit", "W")
                        CONSOLE.info(
                            f"{'Plug Power':<{col1}}: {dev.get('current_power', ''):>4} {unit:<{col2 - 5}} {'Tag':<{col3}}: {dev.get('tag', '')}"
                        )
                        if dev.get("energy_today"):
                            CONSOLE.info(
                                f"{'Energy today':<{col1}}: {dev.get('energy_today', '-.--'):>4} {'kWh':<{col2 - 5}} {'Last Period':<{col3}}: {dev.get('energy_last_period', '-.--'):>4} kWh"
                            )
                    elif devtype in [api.SolixDeviceType.POWERPANEL.value]:
                        CONSOLE.info(
                            f"{'Cloud Status':<{col1}}: {dev.get('status_desc', 'Unknown'):<{col2}} {'Status code':<{col3}}: {dev.get('status', '-')!s}"
                        )
                        if avg := dev.get("average_power") or {}:
                            unit = avg.get("power_unit") or ""
                            CONSOLE.info(
                                f"{'Last Check ⌀':<{col1}}: {avg.get('last_check', 'Unknown'):<{col2}} {'Valid before':<{col3}}: {avg.get('valid_time', 'Unknown')!s}"
                            )
                            CONSOLE.info(
                                f"{'Solar Power ⌀':<{col1}}: {avg.get('solar_power_avg', '-.--'):>4} {unit:<{col2 - 5}} {'Battery SOC':<{col3}}: {avg.get('state_of_charge', '-.--'):>4} %"
                            )
                            CONSOLE.info(
                                f"{'Charge Power ⌀':<{col1}}: {avg.get('charge_power_avg', '-.--'):>4} {unit:<{col2 - 5}} {'Discharge ⌀':<{col3}}: {avg.get('discharge_power_avg', '-.--'):>4} {unit}"
                            )
                            CONSOLE.info(
                                f"{'Home Usage ⌀':<{col1}}: {avg.get('home_usage_avg', '-.--'):>4} {unit:<{col2 - 5}} {'Grid Import ⌀':<{col3}}: {avg.get('grid_import_avg', '-.--'):>4} {unit}"
                            )
                    elif devtype in [api.SolixDeviceType.HES.value]:
                        CONSOLE.info(
                            f"{'Cloud Status':<{col1}}: {dev.get('status_desc', 'Unknown'):<{col2}} {'Status code':<{col3}}: {dev.get('status', '-')!s}"
                        )

                    else:
                        CONSOLE.warning(
                            "No Solarbank, Inverter, Smart Meter, Smart Plug, Power Panel or HES device, further device details will be skipped"
                        )
                # print optional energy details
                if energy_stats:
                    for site_id, site in myapi.sites.items():
                        CONSOLE.info("=" * 80)
                        CONSOLE.info(
                            f"Energy details for System {(site.get('site_info') or {}).get('site_name', 'Unknown')} (Site ID: {site_id}):"
                        )
                        if len(totals := site.get("statistics") or []) >= 3:
                            CONSOLE.info(
                                f"{'Total Produced':<{col1}}: {totals[0].get('total', '---.--'):>7} {str(totals[0].get('unit', '')).upper():<{col2 - 9}}  {'Carbon saved':<{col3}}: {totals[1].get('total', '---.--'):>7} {str(totals[1].get('unit', '')).upper()}"
                            )
                            price = (site.get("site_details") or {}).get(
                                "price"
                            ) or "--.--"
                            unit = (site.get("site_details") or {}).get(
                                "site_price_unit"
                            ) or ""
                            CONSOLE.info(
                                f"{'Max savings':<{col1}}: {totals[2].get('total', '---.--'):>7} {totals[2].get('unit', ''):<{col2 - 9}}  {'Price kWh':<{col3}}: {price:>7} {unit}"
                            )
                        if energy := site.get("energy_details") or {}:
                            today: dict = energy.get("today")
                            yesterday: dict = energy.get("last_period")
                            unit = "kWh"
                            CONSOLE.info(
                                f"{'Today':<{col1}}: {today.get('date', '----------'):<{col2}} {'Yesterday':<{col3}}: {yesterday.get('date', '----------')!s}"
                            )
                            CONSOLE.info(
                                f"{'Solar Energy':<{col1}}: {today.get('solar_production', '-.--'):>6} {unit:<{col2 - 7}} {'Solar Energy':<{col3}}: {yesterday.get('solar_production', '-.--'):>6} {unit}"
                            )
                            if value := today.get("solar_production_pv1"):
                                CONSOLE.info(
                                    f"{'Solar Ch 1/2':<{col1}}: {today.get('solar_production_pv1', '-.--'):>6} / {today.get('solar_production_pv2', '-.--'):>5} {unit:<{col2 - 15}} {'Solar Ch 1/2':<{col3}}: {yesterday.get('solar_production_pv1', '-.--'):>6} / {yesterday.get('solar_production_pv2', '-.--'):>5} {unit}"
                                )
                            if value := today.get("solar_production_pv3"):
                                CONSOLE.info(
                                    f"{'Solar Ch 3/4':<{col1}}: {today.get('solar_production_pv3', '-.--'):>6} / {today.get('solar_production_pv4', '-.--'):>5} {unit:<{col2 - 15}} {'Solar Ch 3/4':<{col3}}: {yesterday.get('solar_production_pv3', '-.--'):>6} / {yesterday.get('solar_production_pv4', '-.--'):>5} {unit}"
                                )
                            CONSOLE.info(
                                f"{'Charged':<{col1}}: {today.get('battery_charge', '-.--'):>6} {unit:<{col2 - 7}} {'Charged':<{col3}}: {yesterday.get('battery_charge', '-.--'):>6} {unit}"
                            )
                            if value := today.get("solar_to_battery"):
                                CONSOLE.info(
                                    f"{'Charged Solar':<{col1}}: {value or '-.--':>6} {unit:<{col2 - 7}} {'Charged Solar':<{col3}}: {yesterday.get('solar_to_battery', '-.--'):>6} {unit}"
                                )
                            if value := today.get("grid_to_battery"):
                                CONSOLE.info(
                                    f"{'Charged Grid':<{col1}}: {value or '-.--':>6} {unit:<{col2 - 7}} {'Charged Grid':<{col3}}: {yesterday.get('grid_to_battery', '-.--'):>6} {unit}"
                                )
                            CONSOLE.info(
                                f"{'Discharged':<{col1}}: {today.get('battery_discharge', '-.--'):>6} {unit:<{col2 - 7}} {'Discharged':<{col3}}: {yesterday.get('battery_discharge', '-.--'):>6} {unit}"
                            )
                            if value := today.get("home_usage"):
                                CONSOLE.info(
                                    f"{'House Usage':<{col1}}: {value or '-.--':>6} {unit:<{col2 - 7}} {'House Usage':<{col3}}: {yesterday.get('home_usage', '-.--'):>6} {unit}"
                                )
                            if value := today.get("solar_to_home"):
                                CONSOLE.info(
                                    f"{'Solar Usage':<{col1}}: {value or '-.--':>6} {unit:<{col2 - 7}} {'Solar Usage':<{col3}}: {yesterday.get('solar_to_home', '-.--'):>6} {unit}"
                                )
                            if value := today.get("battery_to_home"):
                                CONSOLE.info(
                                    f"{'Battery Usage':<{col1}}: {value or '-.--':>6} {unit:<{col2 - 7}} {'Battery Usage':<{col3}}: {yesterday.get('battery_to_home', '-.--'):>6} {unit}"
                                )
                            if value := today.get("grid_to_home"):
                                CONSOLE.info(
                                    f"{'Grid Usage':<{col1}}: {value or '-.--':>6} {unit:<{col2 - 7}} {'Grid Usage':<{col3}}: {yesterday.get('grid_to_home', '-.--'):>6} {unit}"
                                )
                            if value := today.get("grid_import"):
                                CONSOLE.info(
                                    f"{'Grid Import':<{col1}}: {value or '-.--':>6} {unit:<{col2 - 7}} {'Grid Import':<{col3}}: {yesterday.get('grid_import', '-.--'):>6} {unit}"
                                )
                            if value := today.get("solar_to_grid"):
                                CONSOLE.info(
                                    f"{'Grid Export':<{col1}}: {value or '-.--':>6} {unit:<{col2 - 7}} {'Grid Export':<{col3}}: {yesterday.get('solar_to_grid', '-.--'):>6} {unit}"
                                )
                            if value := today.get("ac_socket"):
                                CONSOLE.info(
                                    f"{'AC Socket':<{col1}}: {value or '-.--':>6} {unit:<{col2 - 7}} {'AC Socket':<{col3}}: {yesterday.get('ac_socket', '-.--'):>6} {unit}"
                                )
                            if value := today.get("smartplugs_total"):
                                CONSOLE.info(
                                    f"{'Smartplugs':<{col1}}: {value or '-.--':>6} {unit:<{col2 - 7}} {'Smartplugs':<{col3}}: {yesterday.get('smartplugs_total', '-.--'):>6} {unit}"
                                )
                            for idx, plug_t in enumerate(
                                today.get("smartplug_list") or []
                            ):
                                plug_y = (yesterday.get("smartplug_list") or [])[idx]
                                CONSOLE.info(
                                    f"{'-' + plug_t.get('alias', 'Plug ' + str(idx + 1)):<{col1}}: {plug_t.get('energy') or '-.--':>6} {unit:<{col2 - 7}} {'-' + plug_y.get('alias', 'Plug ' + str(idx + 1)):<{col3}}: {plug_y.get('energy', '-.--'):>6} {unit}"
                                )
                            CONSOLE.info(
                                f"{'Sol/Bat/Gri %':<{col1}}: {float(today.get('solar_percentage') or '0') * 100:>3.0f}/{float(today.get('battery_percentage') or '0') * 100:>3.0f}/{float(today.get('other_percentage') or '0') * 100:>3.0f} {'%':<{col2 - 12}} {'Sol/Bat/Gri %':<{col3}}: {float(yesterday.get('solar_percentage') or '0') * 100:>3.0f}/{float(yesterday.get('battery_percentage') or '0') * 100:>3.0f}/{float(yesterday.get('other_percentage') or '0') * 100:>3.0f} %"
                            )

                # ask to reload or switch to next file or wait for refresh cycle of real time monitoring
                CONSOLE.info("=" * 80)
                if use_file:
                    while use_file:
                        CONSOLE.info("Api Requests: %s", myapi.request_count)
                        # CONSOLE.info(myapi.request_count.get_details(last_hour=True)))
                        myapi.request_count.recycle(last_time=datetime.now())
                        resp = input(
                            "[S]ite refresh, [A]ll refresh, select [O]ther file, toggle [N]ext/[P]revious file or [Q]uit: "
                        )
                        if resp.upper() in ["S", "SITE"]:
                            # set device details refresh to future to reload only site info
                            next_dev_refr = datetime.now().astimezone() + timedelta(
                                seconds=1
                            )
                            break
                        if resp.upper() in ["A", "ALL"]:
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
                            break
                        if resp.upper() in ["N", "NEXT"] and exampleslist:
                            selection = (
                                (selection + 1) if selection < len(exampleslist) else 1
                            )
                            testfolder = exampleslist[selection - 1]
                            myapi.testDir(testfolder)
                            break
                        if resp.upper() in ["P", "PREVIOUS"] and exampleslist:
                            selection = (
                                (selection - 1) if selection > 1 else len(exampleslist)
                            )
                            testfolder = exampleslist[selection - 1]
                            myapi.testDir(testfolder)
                            break
                        if resp.upper() in ["Q", "QUIT"]:
                            return True
                else:
                    CONSOLE.info("Api Requests: %s", myapi.request_count)
                    # CONSOLE.info(myapi.request_count.get_details(last_hour=True))
                    CONSOLE.debug(json.dumps(myapi.devices, indent=2))
                    for sec in range(REFRESH):
                        now = datetime.now().astimezone()
                        if sys.stdin is sys.__stdin__:
                            print(  # noqa: T201
                                f"Site refresh: {int((next_refr - now).total_seconds()):>3} sec,  Device details refresh: {int((next_dev_refr - now).total_seconds()):>3} sec  (CTRL-C to abort)",
                                end="\r",
                                flush=True,
                            )
                        elif sec == 0:
                            # IDLE may be used and does not support cursor placement, skip time progress display
                            print(  # noqa: T201
                                f"Site refresh: {int((next_refr - now).total_seconds()):>3} sec,  Device details refresh: {int((next_dev_refr - now).total_seconds()):>3} sec  (CTRL-C to abort)",
                                end="",
                                flush=True,
                            )
                        await asyncio.sleep(1)
            return False

    except (ClientError, errors.AnkerSolixError) as err:
        CONSOLE.error("%s: %s", type(err), err)
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
