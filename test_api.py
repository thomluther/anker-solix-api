#!/usr/bin/env python
"""Example exec module to test the Anker API for various methods or direct endpoint requests with various parameters related to solarbank devices."""

import asyncio
from datetime import datetime
import json
import logging
from pathlib import Path

from aiohttp import ClientSession
from api import api  # pylint: disable=no-name-in-module
from api.apitypes import SolixParmType  # pylint: disable=no-name-in-module
import common

_LOGGER: logging.Logger = logging.getLogger(__name__)
_LOGGER.addHandler(logging.StreamHandler())
# _LOGGER.setLevel(logging.DEBUG)    # enable for detailed API output
CONSOLE: logging.Logger = common.CONSOLE

TESTAUTHENTICATE = False
TESTAPIMETHODS = False
TESTAPIENDPOINTS = False
TESTAPIFROMJSON = True
JSONFOLDER = "SB2_SM_ManMode_Schedule"


def _out(jsondata):
    CONSOLE.info(json.dumps(jsondata, indent=2))


async def test_api_methods(myapi: api.AnkerSolixApi) -> None:
    """Test Api methods of the library."""

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
    _out(await myapi.get_ota_batch())
    _out(await myapi.get_scene_info(siteId=siteid))
    _out(await myapi.get_wifi_list(siteId=siteid))
    _out(await myapi.get_solar_info(solarbankSn=devicesn))
    _out(
        await myapi.get_device_parm(
            siteId=siteid, paramType=SolixParmType.SOLARBANK_SCHEDULE.value
        )
    )
    _out(
        await myapi.get_device_parm(
            siteId=siteid, paramType=SolixParmType.SOLARBANK_2_SCHEDULE.value
        )
    )
    _out(await myapi.get_power_cutoff(siteId=siteid, deviceSn=devicesn))
    _out(await myapi.get_device_load(siteId=siteid, deviceSn=devicesn))
    _out(
        await myapi.energy_analysis(
            siteId=siteid,
            deviceSn=devicesn,
            rangeType="week",
            startDay=datetime.fromisoformat("2024-10-10"),
            endDay=datetime.fromisoformat("2024-10-10"),
            devType="solar_production",
        )
    )
    _out(
        await myapi.energy_analysis(
            siteId=siteid,
            deviceSn=devicesn,
            rangeType="week",
            startDay=datetime.fromisoformat("2024-10-10"),
            endDay=datetime.fromisoformat("2024-10-10"),
            devType="solarbank",
        )
    )
    _out(
        await myapi.energy_daily(
            siteId=siteid,
            deviceSn=devicesn,
            startDay=datetime.fromisoformat("2024-10-10"),
            numDays=10,
        )
    )
    _out(await myapi.home_load_chart(siteId=siteid))
    _out(await myapi.get_site_price(siteId=siteid))
    _out(await myapi.get_message_unread())
    _out(await myapi.get_site_rules())


async def testAPI_ENDPOINTS(myapi: api.AnkerSolixApi) -> None:
    """Test Api endpoints for solarbanks."""

    _system = list(myapi.sites.values())[0]
    siteid = _system["site_info"]["site_id"]
    devicesn = _system["solarbank_info"]["solarbank_list"][0]["device_sn"]
    _out(await myapi.apisession.request("post", api.API_ENDPOINTS["homepage"], json={}))
    _out(
        await myapi.apisession.request("post", api.API_ENDPOINTS["site_list"], json={})
    )
    _out(
        await myapi.apisession.request(
            "post", api.API_ENDPOINTS["bind_devices"], json={}
        )
    )
    _out(
        await myapi.apisession.request(
            "post", api.API_ENDPOINTS["user_devices"], json={}
        )
    )
    _out(
        await myapi.apisession.request(
            "post", api.API_ENDPOINTS["charging_devices"], json={}
        )
    )
    _out(
        await myapi.apisession.request(
            "post", api.API_ENDPOINTS["get_auto_upgrade"], json={}
        )
    )
    _out(
        await myapi.apisession.request(
            "post",
            api.API_ENDPOINTS["site_detail"],
            json={"site_id": siteid},
        )
    )
    _out(
        await myapi.apisession.request(
            "post",
            api.API_ENDPOINTS["wifi_list"],
            json={"site_id": siteid},
        )
    )
    _out(
        await myapi.apisession.request(
            "post",
            api.API_ENDPOINTS["get_site_price"],
            json={"site_id": siteid},
        )
    )
    _out(
        await myapi.apisession.request(
            "post",
            api.API_ENDPOINTS["solar_info"],
            json={
                "site_id": siteid,
                "solarbank_sn": devicesn,
            },
        )
    )
    _out(
        await myapi.apisession.request(
            "post",
            api.API_ENDPOINTS["get_cutoff"],
            json={
                "site_id": siteid,
                "device_sn": devicesn,
            },
        )
    )
    _out(
        await myapi.apisession.request(
            "post",
            api.API_ENDPOINTS["get_device_fittings"],
            json={
                "site_id": siteid,
                "device_sn": devicesn,
            },
        )
    )
    _out(
        await myapi.apisession.request(
            "post",
            api.API_ENDPOINTS["get_device_load"],
            json={
                "site_id": siteid,
                "device_sn": devicesn,
            },
        )
    )
    _out(
        await myapi.apisession.request(
            "post",
            api.API_ENDPOINTS["get_device_parm"],
            json={
                "site_id": siteid,
                "param_type": "4",
            },
        )
    )
    _out(
        await myapi.apisession.request(
            "post",
            api.API_ENDPOINTS["compatible_process"],
            json={"solarbank_sn": devicesn},
        )
    )
    _out(
        await myapi.apisession.request(
            "post",
            api.API_ENDPOINTS["home_load_chart"],
            json={"site_id": siteid},
        )
    )


async def test_api_from_json_files(myapi: api.AnkerSolixApi) -> None:
    """Test Api library from json files."""

    myapi.testDir(Path(Path(__file__).parent) / "examples" / JSONFOLDER)
    await myapi.update_sites(fromFile=True)
    await myapi.update_device_details(fromFile=True)
    await myapi.update_site_details(fromFile=True)
    await myapi.update_device_energy(fromFile=True)
    _out(myapi.account)
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
                myapi.apisession._login_response  # noqa: SLF001
            )  # show used login response for API requests

        # test site api methods
        if TESTAPIFROMJSON:
            await test_api_from_json_files(myapi)
        else:
            await myapi.update_sites()
            await myapi.update_device_details()
            await myapi.update_site_details()
            await myapi.update_device_energy()
            CONSOLE.info("Account Overview:")
            _out(myapi.account)
            CONSOLE.info("System Overview:")
            _out(myapi.sites)
            CONSOLE.info("Device Overview:")
            _out(myapi.devices)
            CONSOLE.info("Anker Solix Product Overview:")
            common.print_products(await myapi.get_products)

            if TESTAPIMETHODS:
                await test_api_methods(myapi)

            if TESTAPIENDPOINTS:
                await testAPI_ENDPOINTS(myapi)


# run async main
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        CONSOLE.warning("\nAborted!")
    except Exception as err:  # pylint: disable=broad-exception-caught  # noqa: BLE001
        CONSOLE.exception("%s: %s", type(err), err)
