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
# pylint: disable=duplicate-code

import asyncio
import csv
from datetime import datetime
import json
import logging
import os
import sys

from aiohttp import ClientSession
from api import api  # type: ignore  # noqa: PGH003
import common  # type: ignore  # noqa: PGH003

_LOGGER: logging.Logger = logging.getLogger(__name__)
_LOGGER.addHandler(logging.StreamHandler(sys.stdout))
# _LOGGER.setLevel(logging.DEBUG)    # enable for debug output
CONSOLE: logging.Logger = common.CONSOLE


async def main() -> bool:
    """Run main to export energy history from cloud."""
    CONSOLE.info("Exporting daily Energy data for Anker Solarbank:")
    try:
        async with ClientSession() as websession:
            CONSOLE.info("\nTrying authentication...")
            myapi = api.AnkerSolixApi(
                common.user(), common.password(), common.country(), websession, _LOGGER
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
            _LOGGER.debug(json.dumps(myapi.sites, indent=2))

            for site_id, site in myapi.sites.items():
                site_name = (site.get("site_info") or {}).get("site_name") or ""
                CONSOLE.info("Found site %s ID %s", site_name, site_id)
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
                        "Do you want to include daily total data (e.g. solarbank charge) which require API query per day? (Y/N): "
                    )
                    daytotals = daytotals.upper() in ["Y", "YES", "TRUE", 1]
                    prefix = input(
                        f"CSV filename prefix for export (daily_energy_{daystr}): "
                    )
                    if prefix == "":
                        prefix = f"daily_energy_{daystr}"
                    filename = f"{prefix}_{site_name}.csv"
                except ValueError:
                    return False
                # delay requests, limit appears to be around 25 per minute
                if numdays > 10:
                    myapi.requestDelay(2.5)
                else:
                    myapi.requestDelay(.3)
                CONSOLE.info(
                    "Queries may take up to %s seconds with %.1f seconds delay...please wait...",
                    round((2 * numdays * daytotals + 1) * myapi.requestDelay()),myapi.requestDelay()
                )
                data = await myapi.energy_daily(
                    siteId=site_id,
                    deviceSn="",    # mandatory parameter but can be empty since not distinguished for site energy stats
                    startDay=startday,
                    numDays=numdays,
                    dayTotals=daytotals,
                    # TODO(#SMARTPLUG): Add Smartplug type once supported
                    devTypes={api.SolixDeviceType.SOLARBANK.value,api.SolixDeviceType.SMARTMETER.value}    # include all possible energy stats per site
                )
                _LOGGER.debug(json.dumps(data, indent=2))
                # Write csv file
                if len(data) > 0:
                    with open(
                        filename, "w", newline="", encoding="utf-8"
                    ) as csvfile:
                        fieldnames = (next(iter(data.values()))).keys()
                        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                        writer.writeheader()
                        writer.writerows(data.values())
                        CONSOLE.info(
                            "\nCompleted: Successfully exported data to %s",
                            os.path.abspath(filename),
                        )
                else:
                    CONSOLE.info("No data received for site %s ID %s", site_name, site_id)
                    return False
            return True

    except Exception as err:  # pylint: disable=broad-exception-caught  # noqa: BLE001
        CONSOLE.error("%s: %s", type(err), err)
        return False


# run async main
if __name__ == "__main__":
    try:
        if not asyncio.run(main()):
            CONSOLE.warning("Aborted!")
    except Exception as exception:  # pylint: disable=broad-exception-caught  # noqa: BLE001
        CONSOLE.exception("%s: %s", type(exception), exception)
