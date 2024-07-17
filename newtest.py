import asyncio
import json
import logging

from aiohttp import ClientSession
from api import api
import common

_LOGGER: logging.Logger = logging.getLogger(__name__)
_LOGGER.setLevel(logging.DEBUG)    # enable for detailed Api output

async def main() -> None:
    """Create the aiohttp session and run the example."""
    async with ClientSession() as websession:
        # put your code here, example
        myapi = api.AnkerSolixApi(
            common.user(), common.password(), common.country(), websession, _LOGGER
        )
        #await myapi.update_sites()
        #await myapi.update_site_details()
        #await myapi.update_device_details()
        #await myapi.update_device_energy()

        scheduleSB2 = {
                "mode_type": 3,
                "custom_rate_plan": None,
                "blend_plan": None,
            }

        siteId="REDACTED"
        deviceSn="REDACTED"
        print(json.dumps((await myapi.set_device_parm(siteId=siteId, paramData=scheduleSB2, paramType="6", deviceSn=deviceSn)), indent=2))
        print(json.dumps(myapi.devices,indent=2))
        print(f"Api Requests: {myapi.request_count}")


# run async main
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as err:
        print(f"{type(err)}: {err}")
