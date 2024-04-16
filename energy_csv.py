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
import sys

from aiohttp import ClientSession
from api import api
import common

_LOGGER: logging.Logger = logging.getLogger(__name__)
_LOGGER.addHandler(logging.StreamHandler(sys.stdout))
# _LOGGER.setLevel(logging.DEBUG)    # enable for debug output
CONSOLE: logging.Logger = logging.getLogger("console")
CONSOLE.addHandler(logging.StreamHandler(sys.stdout))
CONSOLE.setLevel(logging.INFO)


async def main() -> None:
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
            CONSOLE.info("\nDevices: %s", len(myapi.devices))
            _LOGGER.debug(json.dumps(myapi.devices, indent=2))

            for sn, device in myapi.devices.items():
                if device.get("type") == "solarbank":
                    CONSOLE.info("Found %s SN: %s", device.get("name"), sn)
                    try:
                        daystr = input(
                            "\nEnter start day for daily energy data (yyyy-mm-dd) or enter to skip: "
                        )
                        if daystr == "":
                            CONSOLE.info(
                                "Skipped SN: %s, checking for next Solarbank...", sn
                            )
                            continue
                        startday = datetime.fromisoformat(daystr)
                        numdays = int(input("How many days to query (1-366): "))
                        daytotals = input(
                            "Do you want to include daily total data (e.g. solarbank charge) which require API query per day? (Y/N): "
                        )
                        daytotals = daytotals.upper() in ["Y", "YES", "TRUE", 1]
                        filename = input(
                            f"CSV filename for export (daily_energy_{daystr}.csv): "
                        )
                        if filename == "":
                            filename = f"daily_energy_{daystr}.csv"
                    except ValueError:
                        return False
                    # delay requests, limit appears to be around 25 per minute
                    if numdays > 25:
                        myapi.requestDelay(2.5)
                    else:
                        myapi.requestDelay(.3)
                    CONSOLE.info(
                        "Queries may take up to %s seconds with %.3f seconds delay...please wait...",
                        round((numdays * daytotals + 1) * myapi.requestDelay()),myapi.requestDelay()
                    )
                    data = await myapi.energy_daily(
                        siteId=device.get("site_id"),
                        deviceSn=sn,
                        startDay=startday,
                        numDays=numdays,
                        dayTotals=daytotals,
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
                                filename,
                            )
                        return True

                    CONSOLE.info("No data received for device")
                    return False
            CONSOLE.info("No accepted Solarbank device found.")
            return False

    except Exception as err:  # pylint: disable=broad-exception-caught
        CONSOLE.error("%s: %s", type(err), err)
        return False


# run async main
if __name__ == "__main__":
    try:
        if not asyncio.run(main()):
            CONSOLE.warning("Aborted!")
    except Exception as exception:  # pylint: disable=broad-exception-caught
        CONSOLE.exception("%s: %s", type(exception), exception)
