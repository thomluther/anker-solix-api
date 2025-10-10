#!/usr/bin/env python
"""Example exec module to use the Anker API export module to extract Api responses for the given account.

This module will prompt for the Anker account details if not pre-set in the header.

Upon successful authentication, you can specify a subfolder for the exported
JSON files received as API query response, defaulting to your nick name.

Optionally you can specify whether personalized information in the response
data should be randomized in the files, like SNs, Site IDs, Trace IDs etc.  You
can review the response files afterwards. They can be used as examples for
dedicated data extraction from the devices.

Optionally the API class can use the json files for debugging and testing on
various system outputs.

"""

import asyncio
from dataclasses import asdict
import json
import logging

from aiohttp import ClientSession
from aiohttp.client_exceptions import ClientError
from api.api import AnkerSolixApi  # pylint: disable=no-name-in-module
from api.apitypes import ApiEndpointServices  # pylint: disable=no-name-in-module
from api.errors import AnkerSolixError  # pylint: disable=no-name-in-module
from api.export import AnkerSolixApiExport  # pylint: disable=no-name-in-module
import common

# use Console logger from common module
CONSOLE: logging.Logger = common.CONSOLE
CONSOLE.name = "ExportSystem"
# enable debug mode for the console handler
# CONSOLE.handlers[0].setLevel(logging.DEBUG)
CONSOLE.handlers[0].setFormatter(
    logging.Formatter(
        fmt="%(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )
)
# Use separate Logger for Api session to avoid printing debug data
SESSION: logging.Logger = logging.getLogger(__name__)
SESSION.name = "ExportSystem"
# create console handler and set level to info
ch = logging.StreamHandler()
# This can be changed to DEBUG if more session messages should be printed to console
ch.setLevel(logging.INFO)
ch.setFormatter(
    logging.Formatter(
        fmt="%(levelname)s: %(message)s",
    )
)
SESSION.addHandler(ch)


async def main() -> bool:
    """Run main function to export config after querying some options from user."""

    CONSOLE.info("Exporting found Anker Solix system data for all assigned sites.")
    randomize: bool = True
    mqttdata: bool = False
    services: set = set()
    try:
        user = common.user()
        async with ClientSession() as websession:
            CONSOLE.info("Trying Api authentication for user %s...", user)
            myapi = AnkerSolixApi(
                user, common.password(), common.country(), websession, SESSION
            )
            if await myapi.async_authenticate():
                CONSOLE.info("Authentication: OK")
            else:
                CONSOLE.info(
                    "Authentication: CACHED"
                )  # Login validation will be done during first API call

            resp = input(
                "INPUT: Which Api endpoint services do you want to export? [A]ll / [P]ower / [C]harging / [H]es / [M]qtt only / [D]iscover (default): "
            )
            if resp != "" or not isinstance(services, set):
                if resp.upper() in ["A", "LL"]:
                    services = set(asdict(ApiEndpointServices()).values())
                elif resp.upper() in ["P", "POWER"]:
                    services = {ApiEndpointServices.power}
                elif resp.upper() in ["C", "CHARGING"]:
                    services = {ApiEndpointServices.charging}
                elif resp.upper() in ["H", "HES"]:
                    services = {ApiEndpointServices.hes_svc}
                elif resp.upper() in ["M", "MQTT"]:
                    services = {"mqtt_only"}
                else:
                    # default to discover required services
                    services = set()
            CONSOLE.info(
                "Exporting following services: %s",
                services if services else "Discover automatically",
            )
            resp = input(
                f"INPUT: Do you want to change Api endpoint request limit for proper throttling of same endpoint requests? [0] = disabled / [{myapi.endpointLimit()!s}] = default: "
            )
            if resp.isdigit() and int(resp) >= 0:
                myapi.endpointLimit(limit=int(resp))
            CONSOLE.info("Api endpoint limit: %s", myapi.endpointLimit())
            resp = input(
                f"INPUT: Do you want to randomize unique IDs and SNs in exported files? [Y]es{' (default)' if randomize else ''} / [N]o{' (default)' if not randomize else ''}: "
            )
            if resp != "" or not isinstance(randomize, bool):
                randomize = resp.upper() in ["Y", "YES", "TRUE", 1]
            CONSOLE.info("Randomization of data: %s", randomize)
            if "mqtt_only" in services:
                mqttdata = True
            else:
                resp = input(
                    f"INPUT: Do you want to export optional MQTT device data? These may not be completely randomized and export will take > 5 minutes. [Y]es{' (default)' if mqttdata else ''} / [N]o{' (default)' if not mqttdata else ''}: "
                )
                if resp != "" or not isinstance(mqttdata, bool):
                    mqttdata = resp.upper() in ["Y", "YES", "TRUE", 1]
            CONSOLE.info("MQTT device data export: %s", mqttdata)
            nickname = myapi.apisession.nickname.replace(
                "*", "x"
            )  # avoid filesystem problems with * in user nicknames
            folder = input(f"INPUT: Subfolder for export (default: {nickname}): ")
            if folder == "":
                if nickname == "":
                    return False
                folder = nickname
            CONSOLE.info("Subfolder for export: %s", folder)

            zipped: bool = True
            resp = input(
                "INPUT: Do you want to zip the output folder? [Y]es (default) / [N]o: "
            )
            if resp != "":
                zipped = resp.upper() not in ["N", "NO", "FALSE", 0]
            CONSOLE.info("Zip output folder: %s", zipped)

            myexport = AnkerSolixApiExport(
                client=myapi,
                logger=CONSOLE,
            )
            result = await myexport.export_data(
                export_folder=folder,
                export_services=services,
                randomized=randomize,
                mqttdata=mqttdata,
                zipped=zipped,
            )
            if result and randomize:
                CONSOLE.info(
                    "\nFollowing trace or site IDs, Tokens, SNs, MAC or eMail addresses have been randomized in files (from -> to):\n%s",
                    json.dumps(myexport.get_random_mapping(), indent=2),
                )
            return result

    except (
        asyncio.CancelledError,
        KeyboardInterrupt,
        ClientError,
        AnkerSolixError,
    ) as err:
        if isinstance(err, ClientError | AnkerSolixError):
            CONSOLE.error("%s: %s", type(err), err)
        return False


# run async main
if __name__ == "__main__":
    try:
        if not asyncio.run(main(), debug=False):
            CONSOLE.warning("Aborted!")
    except KeyboardInterrupt:
        CONSOLE.warning("Aborted!")
    except Exception as exception:  # pylint: disable=broad-exception-caught  # noqa: BLE001
        CONSOLE.exception("%s: %s", type(exception), exception)
