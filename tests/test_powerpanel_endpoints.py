#!/usr/bin/env python
"""Example exec module to test the Anker Power Panel read-only endpoint methods.

By default it replays the responses captured in the example export folder via the
fromFile mechanism, so it runs without contacting the cloud. Set TESTFROMFILE = False
to run the methods live against your own Power Panel account instead.
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
# Example export folder and identifiers contained in it
JSONFOLDER = "PowerPanel_ReadEndpoints"
SITE_ID = "492cbe8c-e2a9-b6c4-c7ee-45b3ef4260e0"
HPP_SN = "UUBABYAH2ONIAPD4"
PPS_MACS = ["FFB7B7D7A1D6"]


def _out(jsondata) -> None:
    """Print json or dictionary data to console logger."""
    CONSOLE.info(json.dumps(jsondata, indent=2, ensure_ascii=False))


async def test_read_methods(myapi: AnkerSolixPowerpanelApi) -> None:
    """Exercise the Power Panel read-only methods."""
    if TESTFROMFILE:
        myapi.testDir(Path(Path(__file__).parent) / "examples" / JSONFOLDER)

    ff = TESTFROMFILE
    CONSOLE.info("Utility rate plan (TOU):")
    _out(
        await myapi.get_utility_rate_plan(siteId=SITE_ID, deviceSn=HPP_SN, fromFile=ff)
    )
    CONSOLE.info("Monetary units:")
    _out(await myapi.get_monetary_units(deviceSn=HPP_SN, fromFile=ff))
    CONSOLE.info("Device info:")
    _out(await myapi.get_device_info(deviceSns=[HPP_SN], fromFile=ff))
    CONSOLE.info("Wi-Fi info:")
    _out(await myapi.get_wifi_info(deviceSn=HPP_SN, fromFile=ff))
    CONSOLE.info("Installation inspection:")
    _out(
        await myapi.get_installation_inspection(
            siteId=SITE_ID, deviceSn=HPP_SN, fromFile=ff
        )
    )
    CONSOLE.info("Device SNs (mac -> sn):")
    _out(await myapi.get_device_sns(mainSn=HPP_SN, macs=PPS_MACS, fromFile=ff))


async def main() -> None:
    """Create the aiohttp session and run the example."""
    CONSOLE.info("Testing Solix Power Panel read-only endpoint methods:")
    async with ClientSession() as websession:
        myapi = AnkerSolixPowerpanelApi(
            common.user(),
            common.password(),
            common.country(),
            websession,
            _LOGGER,
        )
        await test_read_methods(myapi)


# run async main
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        CONSOLE.warning("\nAborted!")
    except Exception as err:  # pylint: disable=broad-exception-caught  # noqa: BLE001
        CONSOLE.exception("%s: %s", type(err), err)
