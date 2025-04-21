#!/usr/bin/env python
"""Example exec module to test standalone inverter Api."""

import asyncio
from datetime import datetime, timedelta
import logging
from pathlib import Path

from aiohttp import ClientSession
from aiohttp.client_exceptions import ClientError
from api import api, errors  # pylint: disable=no-name-in-module
import common

# use Console logger from common module
CONSOLE: logging.Logger = common.CONSOLE


def get_subfolders(folder: str | Path) -> list:
    """Get the full pathname of all subfolder for given folder as list."""
    if isinstance(folder, str):
        folder: Path = Path(folder)
    if folder.is_dir():
        return [f.resolve() for f in folder.iterdir() if f.is_dir()]
    return []


async def main() -> bool:
    CONSOLE.info("Inverter Monitor:")

    # get list of possible example and export folders to test the monitor against
    example_list: list = get_subfolders(
        Path(__file__).parent / "examples"
    ) + get_subfolders(Path(__file__).parent / "exports")

    # let user select to use example or live data
    CONSOLE.info("\nSelect the input source for the monitor:")
    CONSOLE.info("(0) Real time from Anker cloud")
    for idx, filename in enumerate(example_list, start=1):
        CONSOLE.info("(%s) %s", idx, filename)
    CONSOLE.info("(q) Quit")

    selection = input(f"Input Source number (0-{len(example_list)}) or [q]uit: ")
    if (
        selection.upper() in ["Q", "QUIT"]
        or not selection.isdigit()
        or int(selection) < 0
        or int(selection) > len(example_list)
    ):
        return False

    if (selection := int(selection)) == 0:
        use_file = False
        test_folder = None
    else:
        use_file = True
        test_folder = example_list[selection - 1]

    try:
        async with ClientSession() as websession:
            user = "" if use_file else common.user()
            if not use_file:
                CONSOLE.info("Trying Api authentication for user %s...", user)
            myapi = api.AnkerSolixApi(
                user,
                "" if use_file else common.password(),
                "" if use_file else common.country(),
                websession,
                CONSOLE,
            )
            if use_file:
                # set the correct test folder for Api
                myapi.testDir(test_folder)
            elif await myapi.async_authenticate():
                CONSOLE.info("Anker Cloud authentication: OK")
            else:
                # Login validation will be done during first API call
                CONSOLE.info("Anker Cloud authentication: CACHED")

            # query user for device to be monitored
            CONSOLE.info("Getting device list...")
            devices = (await myapi.get_user_devices(fromFile=use_file)).get(
                "solar_list"
            ) or []
            CONSOLE.info("Select which device to monitor:")
            devices_names = [
                (
                    ", ".join(
                        [
                            str(d.get("device_name")),
                            str(d.get("device_sn")),
                        ]
                    )
                )
                for d in devices
            ]
            if devices_names > 1:
                for idx, sitename in enumerate(devices_names):
                    CONSOLE.info("(%s) %s", idx, sitename)
                selection = input(f"Enter device number (0-{len(devices_names) - 1}): ")
                if not selection.isdigit() or 0 < int(selection) >= len(devices_names):
                    CONSOLE.error("Invalid selection")
                    return False
                device_sn = devices[int(selection)].get("device_sn")

            # query user for refresh rate
            refresh = 30
            if not (
                resp := input(
                    "How many seconds refresh interval should be used? (5-600, default: 30): "
                )
            ):
                resp = 30
            if resp.isdigit() and 5 >= int(resp) <= 600:
                refresh = int(resp)
            else:
                CONSOLE.error("Invalid selection")
                return False

            # ask which endpoint limit should be applied
            selection = input(
                f"Enter Api endpoint limit for request throttling (1-50, 0 = disabled) [Default: {myapi.apisession.endpointLimit()}]: "
            )
            if selection.isdigit() and 0 <= int(selection) <= 50:
                myapi.apisession.endpointLimit(int(selection))

            # Monitor device
            next_refresh: datetime = datetime.now().astimezone()

            while True:
                now = datetime.now().astimezone()
                if next_refresh > now:
                    await asyncio.sleep(1)
                    continue

                next_refresh = now + timedelta(seconds=refresh)

                device_status = await myapi.get_device_pv_status(
                    deviceSn=device_sn,
                    fromFile=use_file,
                )

                device_total_statistics = await myapi.get_device_pv_total_statistics(
                    deviceSn=device_sn,
                    fromFile=use_file,
                )

                CONSOLE.info(device_status | device_total_statistics)

                if refresh == 0:
                    break
    except (ClientError, errors.AnkerSolixError) as err:
        CONSOLE.error("%s: %s", type(err), err)
        CONSOLE.info("Api Requests: %s", myapi.request_count)
        CONSOLE.info(myapi.request_count.get_details(last_hour=True))
        return False

    return True


# run async main
if __name__ == "__main__":
    try:
        if not asyncio.run(main(), debug=False):
            CONSOLE.warning("\nAborted!")
    except KeyboardInterrupt:
        CONSOLE.warning("\nAborted!")
    except Exception as exception:
        CONSOLE.exception("%s: %s", type(exception), exception)
