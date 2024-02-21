#!/usr/bin/env python
"""Example exec module to use the Anker API for export of daily Solarbank Energy Data.

This method will prompt for the Anker account details if not pre-set in the header.
Then you can specify a start day and the number of days for data extraction from the Anker Cloud.
Note: The Solar production and Solarbank discharge can be queried across the full range. The solarbank
charge however can be queried only as total for an interval (e.g. day). Therefore when solarbank charge
data is also selected for export, an additional API query per day is required.
The received daily values will be exported into a csv file.
"""

import asyncio
import csv
import json
import logging
import sys
from datetime import datetime
from getpass import getpass

from aiohttp import ClientSession

from api import api

_LOGGER: logging.Logger = logging.getLogger(__name__)
_LOGGER.addHandler(logging.StreamHandler(sys.stdout))
# _LOGGER.setLevel(logging.DEBUG)    # enable for debug output
CONSOLE: logging.Logger = logging.getLogger("console")
CONSOLE.addHandler(logging.StreamHandler(sys.stdout))
CONSOLE.setLevel(logging.INFO)

# Optional default Anker Account credentials to be used
USER = ""
PASSWORD = ""
COUNTRY = ""


async def main() -> None:
    """Run main to export energy history from cloud."""
    global USER, PASSWORD, COUNTRY  # noqa: PLW0603
    CONSOLE.info("Exporting daily Energy data for Anker Solarbank:")
    if USER == "":
        CONSOLE.info("\nEnter Anker Account credentials:")
        USER = input("Username (email): ")
        if USER == "":
            return False
        PASSWORD = getpass("Password: ")
        if PASSWORD == "":
            return False
        COUNTRY = input("Country ID (e.g. DE): ")
        if COUNTRY == "":
            return False
    try:
        async with ClientSession() as websession:
            CONSOLE.info("\nTrying authentication...")
            myapi = api.AnkerSolixApi(USER, PASSWORD, COUNTRY, websession, _LOGGER)
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
            CONSOLE.info(f"\nDevices: {len(myapi.devices)}")
            _LOGGER.debug(json.dumps(myapi.devices, indent=2))

            for sn, device in myapi.devices.items():
                if device.get("type") == "solarbank":
                    CONSOLE.info(f"Found {device.get('name')} SN: {sn}")
                    try:
                        daystr = input(
                            "\nEnter start day for daily energy data (yyyy-mm-dd) or enter to skip: "
                        )
                        if daystr == "":
                            CONSOLE.info(
                                f"Skipped SN: {sn}, checking for next Solarbank..."
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
                    CONSOLE.info(
                        f"Queries may take up to {numdays*daytotals + 2} seconds...please wait..."
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
                                f"\nCompleted: Successfully exported data to {filename}"
                            )
                        return True

                    CONSOLE.info("No data received for device")
                    return False
            CONSOLE.info("No accepted Solarbank device found.")
            return False

    except Exception as err:
        CONSOLE.info(f"{type(err)}: {err}")
        return False


# run async main
if __name__ == "__main__":
    try:
        if not asyncio.run(main()):
            CONSOLE.info("Aborted!")
    except Exception as exception:
        CONSOLE.info(f"{type(exception)}: {exception}")
