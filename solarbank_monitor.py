#!/usr/bin/env python
"""Example exec module to use the Anker API for continously querying and
displaying important solarbank parameters This module will prompt for the Anker
account details if not pre-set in the header.  Upon successfull authentication,
you will see the solarbank parameters displayed and refreshed at reqular
interval.

Note: When the system owning account is used, more details for the solarbank
can be queried and displayed.

Attention: During executiion of this module, the used account cannot be used in
the Anker App since it will be kicked out on each refresh.

"""  # noqa: D205

import asyncio
from datetime import datetime, timedelta
import json
import logging
import os
import sys
import time

from aiohttp import ClientSession
from aiohttp.client_exceptions import ClientError
from api import api, errors  # type: ignore  # noqa: PGH003
import common  # type: ignore  # noqa: PGH003

_LOGGER: logging.Logger = logging.getLogger(__name__)
_LOGGER.addHandler(logging.StreamHandler(sys.stdout))
# _LOGGER.setLevel(logging.DEBUG)    # enable for debug output
CONSOLE: logging.Logger = common.CONSOLE

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


def get_subfolders(folder: str) -> list:
    """Get the full pathnames of all subfolders for given folder as list."""
    if os.path.isdir(folder):
        return [os.path.abspath(f) for f in os.scandir(folder) if f.is_dir()]
    return []


async def main() -> (  # noqa: C901 # pylint: disable=too-many-locals,too-many-branches,too-many-statements
    None
):
    """Run Main routine to start Solarbank monitor in a loop."""
    global REFRESH  # pylint: disable=global-statement  # noqa: PLW0603
    CONSOLE.info("Solarbank Monitor:")
    # get list of possible example and export folders to test the monitor against
    exampleslist: list = get_subfolders(
        os.path.join(os.path.dirname(__file__), "examples")
    ) + get_subfolders(os.path.join(os.path.dirname(__file__), "exports"))
    energy_stats: bool = False

    if INTERACTIVE:
        if exampleslist:
            exampleslist.sort()
            CONSOLE.info("\nSelect the input source for the monitor:")
            CONSOLE.info("(0) Real time from Anker cloud")
            for idx, filename in enumerate(exampleslist, start=1):
                CONSOLE.info("(%s) %s", idx, filename)
        selection = input(f"Input Source number (0-{len(exampleslist)}): ")
        if (
            not selection.isdigit()
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
            myapi = api.AnkerSolixApi(
                "" if use_file else common.user(),
                "" if use_file else common.password(),
                "" if use_file else common.country(),
                websession,
                _LOGGER,
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
                elif resp.upper() in ["Y","YES"]:
                    energy_stats = True
                    break

            # Run loop to update Solarbank parameters
            now = datetime.now().astimezone()
            next_refr = now
            next_dev_refr = now
            col1 = 15
            col2 = 23
            col3 = 14
            t1 = 2
            t2 = 5
            t3 = 5
            t4 = 6
            t5 = 6
            t6 = 10
            t7 = 6
            t8 = 6
            t9 = 5
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
                        await myapi.update_device_energy(fromFile=use_file)
                    next_dev_refr = next_refr + timedelta(seconds=max((not use_file) * 120, REFRESH * 9))
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
                    f"Sites: {len(myapi.sites)},  Devices: {len(myapi.devices)}"
                )
                CONSOLE.info("-" * 80)
                # pylint: disable=logging-fstring-interpolation
                for sn, dev in myapi.devices.items():
                    devtype = dev.get("type", "Unknown")
                    admin = dev.get("is_admin", False)
                    site = myapi.sites.get(dev.get("site_id", "")) or {}
                    update_time = (site.get("solarbank_info") or {}).get(
                        "updated_time"
                    ) or "Unknown"
                    CONSOLE.info(
                        f"{'Device':<{col1}}: {(dev.get('name','NoName')):<{col2}} {'Alias':<{col3}}: {dev.get('alias','Unknown')}"
                    )
                    CONSOLE.info(
                        f"{'Serialnumber':<{col1}}: {sn:<{col2}} {'Admin':<{col3}}: {'YES' if admin else 'NO'}"
                    )
                    siteid = dev.get("site_id", "")
                    CONSOLE.info(f"{'System':<{col1}}: {(site.get('site_info') or {}).get('site_name','Unknown')}  (Site ID: {siteid})")
                    for fsn, fitting in (dev.get("fittings") or {}).items():
                        CONSOLE.info(
                            f"{'Accessory':<{col1}}: {fitting.get('device_name',''):<{col2}} {'Serialnumber':<{col3}}: {fsn}"
                        )
                    CONSOLE.info(
                        f"{'Wifi SSID':<{col1}}: {dev.get('wifi_name',''):<{col2}}"
                    )
                    online = dev.get("wifi_online")
                    CONSOLE.info(
                        f"{'Wifi state':<{col1}}: {('Unknown' if online is None else 'Online' if online else 'Offline'):<{col2}} {'Signal':<{col3}}: {dev.get('wifi_signal','---'):>4} %"
                    )
                    if devtype == api.SolixDeviceType.SOLARBANK.value:
                        upgrade = dev.get("auto_upgrade")
                        CONSOLE.info(
                            f"{'SW Version':<{col1}}: {dev.get('sw_version','Unknown'):<{col2}} {'Auto-Upgrade':<{col3}}: {'Unknown' if upgrade is None else 'Enabled' if upgrade else 'Disabled'}"
                        )
                        CONSOLE.info(
                            f"{'Cloud-Updated':<{col1}}: {update_time:<{col2}} {'Valid Data':<{col3}}: {'YES' if dev.get('data_valid') else 'NO'} (Requeries: {site.get('requeries')})"
                        )
                        CONSOLE.info(
                            f"{'Cloud Status':<{col1}}: {dev.get('status_desc','Unknown'):<{col2}} {'Status code':<{col3}}: {dev.get('status','-')!s}"
                        )
                        CONSOLE.info(
                            f"{'Charge Status':<{col1}}: {dev.get('charging_status_desc','Unknown'):<{col2}} {'Status code':<{col3}}: {dev.get('charging_status','-')!s}"
                        )
                        soc = f"{dev.get('battery_soc','---'):>4} %"
                        CONSOLE.info(
                            f"{'State Of Charge':<{col1}}: {soc:<{col2}} {'Min SOC':<{col3}}: {dev.get('power_cutoff','--')!s:>4} %"
                        )
                        energy = f"{dev.get('battery_energy','----'):>4} Wh"
                        CONSOLE.info(
                            f"{'Battery Energy':<{col1}}: {energy:<{col2}} {'Capacity':<{col3}}: {dev.get('battery_capacity','----')!s:>4} Wh"
                        )
                        unit = dev.get("power_unit", "W")
                        if dev.get("generation", 0) > 1:
                            CONSOLE.info(
                                f"{'Exp. Batteries':<{col1}}: {dev.get('sub_package_num',''):>4} {'Pcs':<{col2-5}} {'AC socket':<{col3}}: {dev.get('ac_power','---'):>4} {unit}"
                            )
                        CONSOLE.info(
                            f"{'Solar Power':<{col1}}: {dev.get('input_power',''):>4} {unit:<{col2-5}} {'Output Power':<{col3}}: {dev.get('output_power',''):>4} {unit}"
                        )
                        # show each MPPT for Solarbank 2
                        if "solar_power_1" in dev:
                            CONSOLE.info(
                                f"{'Solar Ch_1':<{col1}}: {dev.get('solar_power_1',''):>4} {unit:<{col2-5}} {'Solar Ch_2':<{col3}}: {dev.get('solar_power_2',''):>4} {unit}"
                            )
                            if "solar_power_3" in dev:
                                CONSOLE.info(
                                    f"{'Solar Ch_3':<{col1}}: {dev.get('solar_power_3',''):>4} {unit:<{col2-5}} {'Solar Ch_4':<{col3}}: {dev.get('solar_power_4',''):>4} {unit}"
                                )
                        preset = dev.get("set_output_power") or "---"
                        site_preset = dev.get("set_system_output_power") or "---"
                        CONSOLE.info(
                            f"{'Charge Power':<{col1}}: {dev.get('charging_power',''):>4} {unit:<{col2-5}} {'Device Preset':<{col3}}: {preset:>4} {unit}"
                        )
                        # update schedule with device details refresh and print it
                        if admin:
                            data = dev.get("schedule") or {}
                            CONSOLE.info(
                                f"{'Schedule  (Now)':<{col1}}: {now.strftime('%H:%M:%S UTC %z'):<{col2}} {'System Preset':<{col3}}: {str(site_preset).replace('W',''):>4} W"
                            )
                            CONSOLE.info(
                                f"{'ID':<{t1}} {'Start':<{t2}} {'End':<{t3}} {'Export':<{t4}} {'Output':<{t5}} {'ChargePrio':<{t6}} {'SB1':>{t7}} {'SB2':>{t8}} {'Mode':>{t9}} Name"
                            )
                            for slot in data.get("ranges") or []:
                                enabled = slot.get("turn_on")
                                load = slot.get("appliance_loads") or []
                                load = load[0] if len(load) > 0 else {}
                                solarbanks = slot.get("device_power_loads") or []
                                sb1 = str(
                                    solarbanks[0].get("power")
                                    if len(solarbanks) > 0
                                    else "---"
                                )
                                sb2 = str(
                                    solarbanks[1].get("power")
                                    if len(solarbanks) > 1
                                    else "---"
                                )
                                CONSOLE.info(
                                    f"{slot.get('id','')!s:>{t1}} {slot.get('start_time',''):<{t2}} {slot.get('end_time',''):<{t3}} {('---' if enabled is None else 'YES' if enabled else 'NO'):^{t4}} {str(load.get('power',''))+' W':>{t5}} {str(slot.get('charge_priority',''))+' %':>{t6}} {sb1+' W':>{t7}} {sb2+' W':>{t8}} {slot.get('power_setting_mode') or '-'!s:^{t9}} {load.get('name','')!s}"
                                )
                    elif devtype == api.SolixDeviceType.INVERTER.value:
                        upgrade = dev.get("auto_upgrade")
                        CONSOLE.info(
                            f"{'SW Version':<{col1}}: {dev.get('sw_version','Unknown'):<{col2}} {'Auto-Upgrade':<{col3}}: {'Unknown' if upgrade is None else 'Enabled' if upgrade else 'Disabled'}"
                        )
                        CONSOLE.info(
                            f"{'Cloud Status':<{col1}}: {dev.get('status_desc','Unknown'):<{col2}} {'Status code':<{col3}}: {dev.get('status','-')!s}"
                        )
                        unit = dev.get("power_unit", "W")
                        CONSOLE.info(
                            f"{'AC Power':<{col1}}: {dev.get('generate_power',''):>3} {unit}"
                        )
                    elif devtype == api.SolixDeviceType.SMARTMETER.value:
                        upgrade = dev.get("auto_upgrade")
                        CONSOLE.info(
                            f"{'SW Version':<{col1}}: {dev.get('sw_version','Unknown'):<{col2}} {'Auto-Upgrade':<{col3}}: {'Unknown' if upgrade is None else 'Enabled' if upgrade else 'Disabled'}"
                        )
                        CONSOLE.info(
                            f"{'Cloud Status':<{col1}}: {dev.get('status_desc','Unknown'):<{col2}} {'Status code':<{col3}}: {dev.get('status','-')!s}"
                        )
                        CONSOLE.info(
                            f"{'Grid Status':<{col1}}: {dev.get('grid_status_desc','Unknown'):<{col2}} {'Status code':<{col3}}: {dev.get('grid_status','-')!s}"
                        )
                        unit = "W"
                        CONSOLE.info(
                            f"{'Grid Import':<{col1}}: {dev.get('grid_to_home_power',''):>4} {unit:<{col2-5}} {'Grid Export':<{col3}}: {dev.get('photovoltaic_to_grid_power',''):>4} {unit}"
                        )
                    else:
                        CONSOLE.warning(
                            "No Solarbank, Inverter or Smartreader device, further device details will be skipped"
                        )
                    CONSOLE.info("-" * 80)
                # print optional energy details
                if energy_stats:
                    unit = "kWh"
                    for site_id, site in myapi.sites.items():
                        if (energy:=site.get("energy_details") or {}):
                            today :dict = energy.get("today")
                            yesterday :dict = energy.get("last_period")
                            CONSOLE.info(f"Energy details for System {(site.get('site_info') or {}).get('site_name','Unknown')} (Site ID: {site_id}):")
                            CONSOLE.info(
                                f"{'Today':<{col1}}: {today.get('date','----------'):<{col2}} {'Yesterday':<{col3}}: {yesterday.get('date','----------')!s}"
                            )
                            CONSOLE.info(
                                f"{'Solar Energy':<{col1}}: {today.get('solar_production',''):>6} {unit:<{col2-7}} {'Solar Energy':<{col3}}: {yesterday.get('solar_production',''):>6} {unit}"
                            )
                            CONSOLE.info(
                                f"{'SB Charged':<{col1}}: {today.get('solarbank_charge',''):>6} {unit:<{col2-7}} {'SB Charged':<{col3}}: {yesterday.get('solarbank_charge',''):>6} {unit}"
                            )
                            CONSOLE.info(
                                f"{'SB Discharged':<{col1}}: {today.get('solarbank_discharge',''):>6} {unit:<{col2-7}} {'SB Discharged':<{col3}}: {yesterday.get('solarbank_discharge',''):>6} {unit}"
                            )
                            CONSOLE.info(
                                f"{'House Feed':<{col1}}: {today.get('battery_to_home',''):>6} {unit:<{col2-7}} {'House Feed':<{col3}}: {yesterday.get('battery_to_home',''):>6} {unit}"
                            )
                            CONSOLE.info(
                                f"{'House Usage':<{col1}}: {today.get('home_usage',''):>6} {unit:<{col2-7}} {'House Usage':<{col3}}: {yesterday.get('home_usage',''):>6} {unit}"
                            )
                            CONSOLE.info(
                                f"{'Sol/Bat/Oth %':<{col1}}: {float(today.get('solar_percentage',''))*100:>3.0f}/{float(today.get('battery_percentage',''))*100:>3.0f}/{float(today.get('other_percentage',''))*100:>3.0f} {'%':<{col2-12}} {'Sol/Bat/Oth %':<{col3}}: {float(today.get('solar_percentage',''))*100:>3.0f}/{float(today.get('battery_percentage',''))*100:>3.0f}/{float(today.get('other_percentage',''))*100:>3.0f} %"
                            )
                            CONSOLE.info("-" * 80)

                # ask to reload or switch to next file or wait for refresh cycle of real time monitoring
                if use_file:
                    while use_file:
                        resp = input("[S]ite refresh, [A]ll refresh, select [O]ther file, toggle [N]ext file or [Q]uit: ")
                        if resp.upper() in ["S", "SITE"]:
                            # set device details refresh to future to reload only site info
                            next_dev_refr = datetime.now().astimezone() + timedelta(seconds=1)
                            break
                        elif resp.upper() in ["A", "ALL"]:
                            break
                        elif resp.upper() in ["O", "OTHER"] and exampleslist:
                            CONSOLE.info("Select the input source for the monitor:")
                            for idx, filename in enumerate(exampleslist, start=1):
                                CONSOLE.info("(%s) %s", idx, filename)
                            while use_file:
                                selection = input(f"Enter source file number (1-{len(exampleslist)}): ")
                                if (
                                    selection.isdigit()
                                    and 1 <= (selection := int(selection)) <= len(exampleslist)
                                ):
                                    break
                            testfolder = exampleslist[selection - 1]
                            myapi.testDir(testfolder)
                            break
                        elif resp.upper() in ["N", "NEXT"] and exampleslist:
                            selection = (selection + 1) if selection < len(exampleslist) else 1
                            testfolder = exampleslist[selection - 1]
                            myapi.testDir(testfolder)
                            break
                        elif resp.upper() in ["Q", "QUIT"]:
                            return True
                else:
                    CONSOLE.info("Api Requests: %s", myapi.request_count)
                    CONSOLE.debug(json.dumps(myapi.devices, indent=2))
                    for sec in range(REFRESH):
                        now = datetime.now().astimezone()
                        if sys.stdin is sys.__stdin__:
                            print(  # noqa: T201
                                f"Site refresh: {int((next_refr-now).total_seconds()):>3} sec,  Device details refresh: {int((next_dev_refr-now).total_seconds()):>3} sec  (CTRL-C to abort)",
                                end="\r",
                                flush=True,
                            )
                        elif sec == 0:
                            # IDLE may be used and does not support cursor placement, skip time progress display
                            print(  # noqa: T201
                                f"Site refresh: {int((next_refr-now).total_seconds()):>3} sec,  Device details refresh: {int((next_dev_refr-now).total_seconds()):>3} sec  (CTRL-C to abort)",
                                end="",
                                flush=True,
                            )
                        time.sleep(1)
            return False

    except (ClientError, errors.AnkerSolixError) as err:
        CONSOLE.error("%s: %s", type(err), err)
        return False


# run async main
if __name__ == "__main__":
    try:
        if not asyncio.run(main()):
            CONSOLE.warning("\nAborted!")
    except KeyboardInterrupt:
        CONSOLE.warning("\nAborted!")
    except Exception as exception:  # pylint: disable=broad-exception-caught  # noqa: BLE001
        CONSOLE.exception("%s: %s", type(exception), exception)
