#!/usr/bin/env python
"""Example exec module to test the Anker API for various methods or direct endpoint requests with various parameters."""  # noqa: D205
# pylint: disable=duplicate-code

import asyncio
from datetime import datetime
import json
import logging
import os
import sys

from aiohttp import ClientSession
from api import api
import common

_LOGGER: logging.Logger = logging.getLogger(__name__)
_LOGGER.addHandler(logging.StreamHandler(sys.stdout))
# _LOGGER.setLevel(logging.DEBUG)    # enable for detailed API output
CONSOLE: logging.Logger = logging.getLogger("console")
CONSOLE.addHandler(logging.StreamHandler(sys.stdout))
CONSOLE.setLevel(logging.INFO)

TESTAUTHENTICATE = False
TESTAPIMETHODS = False
TESTAPIENDPOINTS = False
TESTAPIFROMJSON = False


def _out(jsondata):
    CONSOLE.info(json.dumps(jsondata, indent=2))


async def test_api_methods(myapi: api.AnkerSolixApi) -> None:  # noqa: D103
    _system = list(myapi.sites.values())[0]
    siteid = _system["site_info"]["site_id"]
    devicesn = _system["solarbank_info"]["solarbank_list"][0]["device_sn"]
    _out(await myapi.get_site_list())
    _out(await myapi.get_homepage())
    _out(await myapi.get_bind_devices())
    _out(await myapi.get_user_devices())
    _out(await myapi.get_charging_devices())
    _out(await myapi.get_auto_upgrade())
    _out(await myapi.get_upgrade_record())
    _out(await myapi.get_ota_update(deviceSn=devicesn))
    _out(await myapi.get_ota_info(solarbankSn=devicesn))
    _out(await myapi.get_scene_info(siteId=siteid))
    _out(await myapi.get_wifi_list(siteId=siteid))
    _out(await myapi.get_solar_info(solarbankSn=devicesn))
    _out(await myapi.get_device_parm(siteId=siteid))

    _out(
        await myapi.get_power_cutoff(
            siteId=siteid,
            deviceSn=devicesn,
        )
    )
    _out(
        await myapi.get_device_load(
            siteId=siteid,
            deviceSn=devicesn,
        )
    )

    _out(
        await myapi.energy_analysis(
            siteId=siteid,
            deviceSn=devicesn,
            rangeType="week",
            startDay=datetime.fromisoformat("2023-10-10"),
            endDay=datetime.fromisoformat("2023-10-10"),
            devType="solar_production",
        )
    )
    _out(
        await myapi.energy_analysis(
            siteId=siteid,
            deviceSn=devicesn,
            rangeType="week",
            startDay=datetime.fromisoformat("2023-10-10"),
            endDay=datetime.fromisoformat("2023-10-10"),
            devType="solarbank",
        )
    )
    _out(
        await myapi.energy_daily(
            siteId=siteid,
            deviceSn=devicesn,
            startDay=datetime.fromisoformat("2024-01-10"),
            numDays=10,
        )
    )
    _out(await myapi.home_load_chart(siteId=siteid))
    _out(await myapi.get_site_price(siteId=siteid))
    _out(await myapi.get_message_unread())
    _out(await myapi.get_site_rules())


async def test_api_endpoints(myapi: api.AnkerSolixApi) -> None:  # noqa: D103
    _system = list(myapi.sites.values())[0]
    siteid = _system["site_info"]["site_id"]
    devicesn = _system["solarbank_info"]["solarbank_list"][0]["device_sn"]
    _out(await myapi.request("post", api._API_ENDPOINTS["homepage"], json={}))  # pylint: disable=protected-access
    _out(await myapi.request("post", api._API_ENDPOINTS["site_list"], json={}))  # pylint: disable=protected-access
    _out(await myapi.request("post", api._API_ENDPOINTS["bind_devices"], json={}))  # pylint: disable=protected-access
    _out(await myapi.request("post", api._API_ENDPOINTS["user_devices"], json={}))  # pylint: disable=protected-access
    _out(await myapi.request("post", api._API_ENDPOINTS["charging_devices"], json={}))  # pylint: disable=protected-access
    _out(await myapi.request("post", api._API_ENDPOINTS["get_auto_upgrade"], json={}))  # pylint: disable=protected-access
    _out(
        await myapi.request(
            "post",
            api._API_ENDPOINTS["site_detail"],  # pylint: disable=protected-access
            json={"site_id": siteid},
        )
    )
    _out(
        await myapi.request(
            "post",
            api._API_ENDPOINTS["wifi_list"],  # pylint: disable=protected-access
            json={"site_id": siteid},
        )
    )
    _out(
        await myapi.request(
            "post",
            api._API_ENDPOINTS["get_site_price"],  # pylint: disable=protected-access
            json={"site_id": siteid},
        )
    )
    _out(
        await myapi.request(
            "post",
            api._API_ENDPOINTS["solar_info"],  # pylint: disable=protected-access
            json={
                "site_id": siteid,
                "solarbank_sn": devicesn,
            },
        )
    )
    _out(
        await myapi.request(
            "post",
            api._API_ENDPOINTS["get_cutoff"],  # pylint: disable=protected-access
            json={
                "site_id": siteid,
                "device_sn": devicesn,
            },
        )
    )
    _out(
        await myapi.request(
            "post",
            api._API_ENDPOINTS["get_device_fittings"],  # pylint: disable=protected-access
            json={
                "site_id": siteid,
                "device_sn": devicesn,
            },
        )
    )
    _out(
        await myapi.request(
            "post",
            api._API_ENDPOINTS["get_device_load"],  # pylint: disable=protected-access
            json={
                "site_id": siteid,
                "device_sn": devicesn,
            },
        )
    )
    _out(
        await myapi.request(
            "post",
            api._API_ENDPOINTS["get_device_parm"],  # pylint: disable=protected-access
            json={
                "site_id": siteid,
                "param_type": "4",
            },
        )
    )
    _out(
        await myapi.request(
            "post",
            api._API_ENDPOINTS["compatible_process"],  # pylint: disable=protected-access
            json={"solarbank_sn": devicesn},
        )
    )
    _out(
        await myapi.request(
            "post",
            api._API_ENDPOINTS["home_load_chart"],  # pylint: disable=protected-access
            json={"site_id": siteid},
        )
    )


async def test_api_from_json_files(myapi: api.AnkerSolixApi) -> None:  # noqa: D103
    myapi.testDir(os.path.join(os.path.dirname(__file__), "examples", "example1"))
    await myapi.update_sites(fromFile=True)
    await myapi.update_site_details(fromFile=True)
    await myapi.update_device_details(fromFile=True)
    _out(myapi.sites)
    _out(myapi.devices)


async def main() -> None:
    """Create the aiohttp session and run the example."""
    CONSOLE.info("Testing Solix API:")
    async with ClientSession() as websession:
        myapi = api.AnkerSolixApi(
            common.user(),
            common.password(),
            common.country(),
            websession,
            _LOGGER,
        )

        if TESTAUTHENTICATE:
            # show login response
            new = await myapi.async_authenticate(
                restart=True
            )  # enforce new login data from server
            new = (
                await myapi.async_authenticate()
            )  # receive new or load cached login data
            if new:
                CONSOLE.info("Received Login response:")
            else:
                CONSOLE.info("Cached Login response:")
            _out(
                myapi._login_response  # pylint: disable=protected-access
            )  # show used login response for API reqests

        # test site api methods
        await myapi.update_sites()
        await myapi.update_site_details()
        await myapi.update_device_details()
        await myapi.update_device_energy(devtypes={api.SolixDeviceType.SOLARBANK.value})
        CONSOLE.info("System Overview:")
        _out(myapi.sites)
        CONSOLE.info("Device Overview:")
        _out(myapi.devices)

        if TESTAPIMETHODS:
            await test_api_methods(myapi)

        if TESTAPIENDPOINTS:
            await test_api_endpoints(myapi)

        if TESTAPIFROMJSON:
            await test_api_from_json_files(myapi)


# run async main
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as err:  # pylint: disable=broad-exception-caught
        CONSOLE.exception("%s: %s", type(err), err)
