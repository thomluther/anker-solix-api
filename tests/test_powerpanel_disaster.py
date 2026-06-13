#!/usr/bin/env python
"""Example exec module to test the Anker Power Panel manual backup (disaster preparedness) methods.

By default it replays the responses captured in the example export folder via the
fromFile mechanism, so it runs without contacting the cloud. Set TESTFROMFILE = False
to run the read methods live against your own Power Panel account instead.
"""

import asyncio
import json
import logging
from pathlib import Path

from aiohttp import ClientSession
from anker_solix_api.powerpanel import AnkerSolixPowerpanelApi
from context import common

_LOGGER: logging.Logger = logging.getLogger(__name__)
_LOGGER.addHandler(logging.StreamHandler())
# _LOGGER.setLevel(logging.DEBUG)    # enable for detailed API output
CONSOLE: logging.Logger = common.CONSOLE

TESTFROMFILE = True
# Example export folder and the Power Panel site id contained in it
JSONFOLDER = "PowerPanel_ManualBackup"
SITE_ID = "f6a1b2c3-d4e5-6789-abcd-ef0123456789"


def _out(jsondata) -> None:
    """Print json or dictionary data to console logger."""
    CONSOLE.info(json.dumps(jsondata, indent=2))


async def test_disaster_methods(myapi: AnkerSolixPowerpanelApi) -> None:
    """Exercise the Power Panel manual backup read methods."""
    if TESTFROMFILE:
        myapi.testDir(Path(Path(__file__).parent) / "examples" / JSONFOLDER)

    CONSOLE.info("Backup configuration (get_device_disaster):")
    _out(await myapi.get_device_disaster(siteId=SITE_ID, fromFile=TESTFROMFILE))

    CONSOLE.info("Backup status (get_device_disaster_status):")
    _out(await myapi.get_device_disaster_status(siteId=SITE_ID, fromFile=TESTFROMFILE))

    CONSOLE.info("Backup support info (get_disaster_support):")
    _out(await myapi.get_disaster_support(siteId=SITE_ID, fromFile=TESTFROMFILE))


async def main() -> None:
    """Create the aiohttp session and run the example."""
    CONSOLE.info("Testing Solix Power Panel manual backup methods:")
    async with ClientSession() as websession:
        myapi = AnkerSolixPowerpanelApi(
            common.user(),
            common.password(),
            common.country(),
            websession,
            _LOGGER,
        )
        await test_disaster_methods(myapi)


# run async main
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        CONSOLE.warning("\nAborted!")
    except Exception as err:  # pylint: disable=broad-exception-caught  # noqa: BLE001
        CONSOLE.exception("%s: %s", type(err), err)
