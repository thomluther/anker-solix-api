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
from api.api import AnkerSolixApi  # pylint: disable=no-name-in-module
from api.apitypes import SolixDeviceType  # pylint: disable=no-name-in-module
import common

# use Console logger from common module
CONSOLE: logging.Logger = common.CONSOLE
# enable debug mode for the console handler
# CONSOLE.handlers[0].setLevel(logging.DEBUG)


async def main() -> bool:
    """Run main to export energy history from cloud."""
    CONSOLE.info("Exporting daily Energy data for Anker Solarbank:")
    try:
        async with ClientSession() as websession:
            CONSOLE.info("\nTrying authentication...")
            myapi = AnkerSolixApi(
                common.user(), common.password(), common.country(), websession, CONSOLE
            )
            if await myapi.async_authenticate():
                CONSOLE.info("OK")
            else:
                CONSOLE.info(
                    "CACHED"
                )  # Login validation will be done during first API call
            # Refresh the site and device info of the API
            CONSOLE.info("\nUpdating Site Info...")
            if (await myapi.update_sites()) == {}:
                CONSOLE.info("NO INFO")
                return False
            CONSOLE.info("OK")
            CONSOLE.info("\nSites: %s", len(myapi.sites))
            CONSOLE.debug(json.dumps(myapi.sites, indent=2))

            for site_id, site in myapi.sites.items():
                site_name = (site.get("site_info") or {}).get("site_name") or ""
                powerpanel = bool(
                    myapi.powerpanelApi and site_id in myapi.powerpanelApi.sites
                )
                hes = bool(myapi.hesApi and site_id in myapi.hesApi.sites)
                CONSOLE.info("Found site %s ID %s", site_name, site_id)
                CONSOLE.info(
                    "Site Type %s: %s",
                    (site.get("site_info") or {}).get("power_site_type") or "??",
                    "Power Panel"
                    if powerpanel
                    else "Home Energy System"
                    if hes
                    else "Balcony Power",
                )
                try:
                    daystr = input(
                        "\nEnter start day for daily energy data (yyyy-mm-dd) or enter to skip site: "
                    )
                    if daystr == "":
                        CONSOLE.info(
                            "Skipped site %s, checking for next site...", site_name
                        )
                        continue
                    startday = datetime.fromisoformat(daystr)
                    numdays = int(input("How many days to query (1-366): "))
                    daytotals = input(
                        "Do you want to include daily total data (e.g. battery charge, grid import/export) which may require several API queries per day? (Y/N): "
                    )
                    daytotals = daytotals.upper() in ["Y", "YES", "TRUE", 1]
                    prefix = input(
                        f"CSV filename prefix for export ({site_name.replace(' ','_')}_daily_energy_{daystr}): "
                    )
                    if prefix == "":
                        prefix = f"{site_name.replace(' ','_')}_daily_energy_{daystr}"
                    filename = f"{prefix}_{site_name}.csv"
                except ValueError:
                    return False
                # delay requests, limit appears to be around 25 per minute
                # As of Feb 2025, limit appears to be reduced to 12 per minute
                if numdays > 3:
                    # myapi.apisession.requestDelay(5.1)
                    CONSOLE.info(
                        "Queries may take several minutes depending on system configuration and throttling ...please wait..."
                    )
                else:
                    # myapi.apisession.requestDelay(0.3)
                    CONSOLE.info(
                        "Queries may take up to %s seconds with %.1f seconds delay ...please wait...",
                        round(
                            (
                                (4 * (numdays - 1) * daytotals + 4)
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
                    )
                else:
                    data = await myapi.energy_daily(
                        siteId=site_id,
                        deviceSn=next(iter((site.get("solarbank_info") or {}).get("solarbank_list") or []),{}).get("device_sn"),  # mandatory parameter but can be empty since not distinguished for site energy stats
                        startDay=startday,
                        numDays=numdays,
                        dayTotals=daytotals,
                        # include all possible energy stats per site
                        devTypes={
                            SolixDeviceType.INVERTER.value,
                            SolixDeviceType.SOLARBANK.value,
                            SolixDeviceType.SMARTMETER.value,
                            SolixDeviceType.SMARTPLUG.value,
                        },
                        showProgress=True,
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
                    CONSOLE.info(
                        "No data received for site %s ID %s", site_name, site_id
                    )
                    return False
                # CONSOLE.info(myapi.apisession.request_count.get_details())
                CONSOLE.info(f"Api Requests: {myapi.request_count}")
            return True

    except Exception as err:  # pylint: disable=broad-exception-caught  # noqa: BLE001
        CONSOLE.error("%s: %s", type(err), err)
        return False


# run async main
if __name__ == "__main__":
    try:
        if not asyncio.run(main(), debug=False):
            CONSOLE.warning("Aborted!")
    except Exception as exception:  # pylint: disable=broad-exception-caught  # noqa: BLE001
        CONSOLE.exception("%s: %s", type(exception), exception)
