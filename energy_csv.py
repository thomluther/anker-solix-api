#!/usr/bin/env python
"""Example exec module to use the Anker API for export of daily Solarbank Energy Data.

This method will prompt for the Anker account details if not pre-set in the
header.  Then you can specify a start day and the number of days for data
extraction from the Anker Cloud.

Note: The Solar production and Solarbank discharge can be queried across the
full range. The solarbank charge however can be queried only as total for an
interval (e.g. day). Therefore when solarbank charge data is also selected for
export, an additional API query per day is required.  The received daily values
will be exported into a csv file.

"""

import asyncio
import csv
from datetime import datetime
import json
import logging
from pathlib import Path

from aiohttp import ClientSession
from aiohttp.client_exceptions import ClientError
from anker_solix_api.api import AnkerSolixApi
from anker_solix_api.apitypes import Color, SolixDefaults, SolixDeviceType
from anker_solix_api.errors import AnkerSolixError
import common

# use Console logger from common module
CONSOLE: logging.Logger = common.CONSOLE
# enable debug mode for the console handler
# CONSOLE.handlers[0].setLevel(logging.DEBUG)
# set a json folder to debug cache population from json files
JSONFOLDER = ""  # Path(__file__).parent / "examples" / "MI80_Standalone"


async def main() -> bool:
    """Run main to export energy history from cloud."""
    CONSOLE.info("Exporting daily Energy data for Anker Solarbank:")
    loop = asyncio.get_running_loop()
    input_task = False
    try:
        async with ClientSession() as websession:
            if JSONFOLDER:
                CONSOLE.info("\nStarting Api session from folder: %s", JSONFOLDER)
                myapi = AnkerSolixApi(
                    "",
                    "",
                    "",
                    websession,
                    CONSOLE,
                )
                myapi.testDir(JSONFOLDER)
                use_file = True
            else:
                CONSOLE.info("\nTrying authentication...")
                input_task = True
                myapi = AnkerSolixApi(
                    common.user(),
                    common.password(),
                    common.country(),
                    websession,
                    CONSOLE,
                )
                input_task = False
                if await myapi.async_authenticate():
                    CONSOLE.info("OK")
                else:
                    CONSOLE.info(
                        "CACHED"
                    )  # Login validation will be done during first API call
                use_file = False
            # Refresh the site and admin device info of the API
            CONSOLE.info("\nUpdating site info...")
            await myapi.update_sites(fromFile=use_file)
            CONSOLE.info("Updating device details info...")
            await myapi.update_device_details(fromFile=use_file)
            if not myapi.sites:
                CONSOLE.info("NO INFO")
                return False
            CONSOLE.info("OK")
            energy_devices = {
                sn: dev
                for sn, dev in myapi.devices.items()
                if not dev.get("site_id")
                and dev.get("device_pn") in SolixDefaults.DEVICE_ENERGY
            }
            repeat_date = ""
            CONSOLE.info(
                "Found sites: %s,  Found standalone devices with energy statistics: %s",
                len(myapi.sites),
                len(energy_devices),
            )

            for site_id, site in myapi.sites.items():
                site_name = (site.get("site_info") or {}).get("site_name") or ""
                site_type = site.get("site_type", "")
                powerpanel = bool(
                    myapi.powerpanelApi and site_id in myapi.powerpanelApi.sites
                )
                hes = bool(myapi.hesApi and site_id in myapi.hesApi.sites)
                inverter = bool(
                    str(site_id).startswith(SolixDeviceType.VIRTUAL.value)
                    and site.get("solar_list")
                )
                CONSOLE.info("\nFound site '%s' ID: %s", site_name, site_id)
                CONSOLE.info(
                    "Site type %s: %s",
                    (site.get("site_info") or {}).get("power_site_type", "??"),
                    "Power Panel"
                    if powerpanel
                    else "Home Energy System"
                    if hes
                    else "Standalone Inverter"
                    if inverter
                    else "Balcony Power",
                )
                try:
                    input_task = True
                    daystr = await loop.run_in_executor(
                        None,
                        input,
                        f"Enter start day for daily energy data ({Color.YELLOW}yyyy-mm-dd{Color.OFF})"
                        f"{' (or [' + Color.YELLOW + 'r' + Color.OFF + ']epeat for previous date (' + Color.YELLOW + repeat_date + Color.OFF + '))' if repeat_date else ''}"
                        f" or [{Color.YELLOW}ENTER{Color.OFF}] to skip site: ",
                    )
                    if daystr == "":
                        CONSOLE.info(
                            "Skipped site '%s', checking for next site...", site_name
                        )
                        continue
                    if daystr.lower() == "r" and repeat_date:
                        daystr = repeat_date
                    else:
                        repeat_date = daystr
                    startday = datetime.fromisoformat(daystr)
                    numdays = int(
                        await loop.run_in_executor(
                            None,
                            input,
                            f"How many days to query ({Color.YELLOW}1-366{Color.OFF}): ",
                        )
                    )
                    if inverter:
                        daytotals = False
                    else:
                        daytotals = await loop.run_in_executor(
                            None,
                            input,
                            f"Do you want to include daily total data (e.g. battery charge, grid import/export) which may require several API queries per day? ({Color.YELLOW}Y/N{Color.OFF}): ",
                        )
                    daytotals = str(daytotals).upper() in ["Y", "YES", "TRUE", 1]
                    prefix = await loop.run_in_executor(
                        None,
                        input,
                        f"CSV filename prefix for export ({Color.YELLOW}{site_name.replace(' ', '_')}_daily_energy_{daystr}{Color.OFF}): ",
                    )
                    if prefix == "":
                        prefix = f"{site_name.replace(' ', '_')}_daily_energy"
                    filename = f"{prefix}_{daystr}.csv"
                    input_task = False
                except ValueError:
                    input_task = False
                    return False
                # delay requests, endpoint limit appears to be around 25 per minute
                # As of Feb 2025, endpoint limit appears to be reduced to 10-12 per minute
                if numdays > 3:
                    CONSOLE.info(
                        "Queries may take several minutes depending on system configuration and throttling ...please wait..."
                    )
                else:
                    CONSOLE.info(
                        "Queries may take up to %s seconds with %.1f seconds delay ...please wait...",
                        round(
                            (
                                numdays
                                if inverter
                                else (4 * (numdays - 1) * daytotals + 4)
                                if powerpanel or hes
                                else (2 * numdays * daytotals + 5)
                            )
                            * myapi.apisession.requestDelay()
                        ),
                        myapi.apisession.requestDelay(),
                    )
                if powerpanel:
                    data = await myapi.powerpanelApi.energy_daily(
                        siteId=site_id,
                        startDay=startday,
                        numDays=numdays,
                        dayTotals=daytotals,
                        devTypes={
                            SolixDeviceType.POWERPANEL.value,
                        },
                        showProgress=True,
                        fromFile=use_file,
                    )
                elif hes:
                    data = await myapi.hesApi.energy_daily(
                        siteId=site_id,
                        startDay=startday,
                        numDays=numdays,
                        dayTotals=daytotals,
                        devTypes={
                            SolixDeviceType.HES.value,
                        },
                        showProgress=True,
                        fromFile=use_file,
                    )
                elif inverter:
                    data = await myapi.device_pv_energy_daily(
                        deviceSn=site_id.split("-")[1],
                        startDay=startday,
                        numDays=numdays,
                        showProgress=True,
                        fromFile=use_file,
                    )
                else:
                    data = await myapi.energy_daily(
                        siteId=site_id,
                        deviceSn="",  # mandatory parameter but can be empty (= total for all same devices in system)
                        startDay=startday,
                        numDays=numdays,
                        dayTotals=daytotals,
                        # include all possible energy stats per site, Solarbank_pps only if site type, otherwise Solar not queried
                        devTypes={
                            SolixDeviceType.INVERTER.value,
                            SolixDeviceType.SOLARBANK.value,
                            SolixDeviceType.SMARTMETER.value,
                            SolixDeviceType.SMARTPLUG.value,
                            SolixDeviceType.EV_CHARGER.value,
                        }
                        | (
                            {SolixDeviceType.SOLARBANK_PPS.value}
                            if site_type == SolixDeviceType.SOLARBANK_PPS.value
                            else set()
                        ),
                        showProgress=True,
                        fromFile=use_file,
                    )
                CONSOLE.debug(json.dumps(data, indent=2))
                # remove statistics to match csv headers
                data.pop("statistics", None)
                # Write csv file
                if len(data) > 0:
                    with Path.open(
                        Path(filename), "w", newline="", encoding="utf-8"
                    ) as csvfile:
                        fieldnames = (next(iter(data.values()))).keys()
                        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                        writer.writeheader()
                        writer.writerows(data.values())
                        CONSOLE.info(
                            "\nCompleted: Successfully exported data to %s",
                            Path.resolve(Path(filename)),
                        )
                else:
                    CONSOLE.info(
                        "No data received for site %s ID %s", site_name, site_id
                    )
                    return False
            # Export supported standalone devices
            for sn, device in energy_devices.items():
                name = device.get("name", "")
                CONSOLE.info("\nFound device '%s' ID: %s", device.get("alias", ""), sn)
                CONSOLE.info(
                    "Device type %s: %s",
                    device.get("device_pn", "Unknown"),
                    name,
                )
                try:
                    input_task = True
                    daystr = await loop.run_in_executor(
                        None,
                        input,
                        f"Enter start day for daily energy data ({Color.YELLOW}yyyy-mm-dd{Color.OFF})"
                        f"{', or [' + Color.YELLOW + 'r' + Color.OFF + ']epeat for previous date (' + Color.YELLOW + repeat_date + Color.OFF + ')' if repeat_date else ''}"
                        f" or [{Color.YELLOW}ENTER{Color.OFF}] to skip device: ",
                    )
                    if daystr == "":
                        CONSOLE.info(
                            "Skipped device '%s', checking for next device...", sn
                        )
                        continue
                    if daystr.lower() == "r" and repeat_date:
                        daystr = repeat_date
                    else:
                        repeat_date = daystr
                    startday = datetime.fromisoformat(daystr)
                    numdays = int(
                        await loop.run_in_executor(
                            None,
                            input,
                            f"How many days to query ({Color.YELLOW}1-366{Color.OFF}): ",
                        )
                    )
                    prefix = await loop.run_in_executor(
                        None,
                        input,
                        f"CSV filename prefix for export ({Color.YELLOW}{site_name.replace(' ', '_')}_{sn}_daily_energy_{daystr}{Color.OFF}): ",
                    )
                    if prefix == "":
                        prefix = f"{name.replace(' ', '_')}_{sn}_daily_energy"
                    filename = f"{prefix}_{daystr}.csv"
                    input_task = False
                except ValueError:
                    input_task = False
                    return False
                # delay requests, endpoint limit appears to be around 25 per minute
                # As of Feb 2025, endpoint limit appears to be reduced to 10-12 per minute
                CONSOLE.info(
                    "Queries may take up to %s seconds with %.1f seconds delay ...please wait...",
                    round((numdays / 30 + 1) * myapi.apisession.requestDelay()),
                    myapi.apisession.requestDelay(),
                )
                data = await myapi.device_energy_daily(
                    deviceSn=sn,
                    startDay=startday,
                    numDays=numdays,
                    showProgress=True,
                    fromFile=use_file,
                )
                CONSOLE.debug(json.dumps(data, indent=2))
                # Write csv file
                if len(data) > 0:
                    with Path.open(
                        Path(filename), "w", newline="", encoding="utf-8"
                    ) as csvfile:
                        fieldnames = (next(iter(data.values()))).keys()
                        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                        writer.writeheader()
                        writer.writerows(data.values())
                        CONSOLE.info(
                            "\nCompleted: Successfully exported data to %s",
                            Path.resolve(Path(filename)),
                        )
                else:
                    CONSOLE.info("No data received for device %s SN %s", name, sn)
                    return False

            # CONSOLE.info(myapi.apisession.request_count.get_details())
            CONSOLE.info(f"\nApi Requests: {myapi.request_count}")
            return True

    except (
        asyncio.CancelledError,
        KeyboardInterrupt,
        ClientError,
        AnkerSolixError,
    ) as err:
        if isinstance(err, ClientError | AnkerSolixError):
            CONSOLE.error("%s: %s", type(err), err)
            CONSOLE.info("Api Requests: %s", myapi.request_count)
            CONSOLE.info(myapi.request_count.get_details(last_hour=True))
        elif isinstance(err, asyncio.CancelledError):
            if input_task:
                CONSOLE.warning(f"\n{Color.RED}[Input cancelled, hit ENTER]{Color.OFF}")
            else:
                CONSOLE.info(f"{Color.YELLOW}Export process was cancelled.{Color.OFF}")
        return False


# run async main
if __name__ == "__main__":
    try:
        if not asyncio.run(main(), debug=False):
            CONSOLE.warning("Aborted!")
    except KeyboardInterrupt:
        CONSOLE.warning("Aborted!")
    except Exception as exception:  # pylint: disable=broad-exception-caught  # noqa: BLE001
        CONSOLE.exception("%s: %s", type(exception), exception)
