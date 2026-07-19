#!/usr/bin/env python
"""Example exec module to use the Anker API export module to extract Api responses for the given account.

This module will prompt for the Anker account details if not pre-set in the header.

Upon successful authentication, you can specify a subfolder for the exported
JSON files received as API query response, defaulting to your nick name.

Optionally you can specify whether personalized information in the response
data should be randomized in the files, like SNs, Site IDs, Trace IDs etc.  You
can review the response files afterwards. They can be used as examples for
dedicated data extraction from the devices.

Optionally you can export MQTT messages from eligible devices. They can also be
randomized for the known Api device SNs, but not for complete data that may exist in
unknown binary data of the MQTT message. Upon MQTT export, the duration will be > 5 min
to include most standard messages of the device, including a 60 second real time data period.

The API class can use the json files for debugging and testing on
various system outputs. MQTT classes also use the exported MQTT messages for debugging and
proper decoding of the messages can be validated as well once decoding has been described.

All prompts can be pre-answered via command line arguments for unattended runs
(e.g. cron, CI). Any option not supplied on the command line is still prompted
interactively, unless --non-interactive is set, in which case the default is used.

"""

import argparse
import asyncio
from dataclasses import asdict
import json
import logging

from aiohttp import ClientSession
from aiohttp.client_exceptions import ClientError
from anker_solix_api.api import AnkerSolixApi
from anker_solix_api.apitypes import ApiEndpointServices, Color
from anker_solix_api.errors import AnkerSolixError
from anker_solix_api.export import AnkerSolixApiExport
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


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments.

    Every interactive prompt has a matching option. Supplying it skips that
    prompt; omitting it still prompts, unless --non-interactive uses the default.
    """
    parser = argparse.ArgumentParser(
        description="Anker Solix System Export - Export Api responses and optional MQTT device data for an account"
    )
    parser.add_argument(
        "--services",
        "-s",
        type=str,
        choices=["all", "power", "charging", "hes", "mqtt", "discover"],
        help="Api endpoint services to export (default: discover)",
    )
    parser.add_argument(
        "--endpoint-limit",
        "-l",
        type=int,
        metavar="N",
        help="Api endpoint request limit for throttling, 0 = disabled (default: keep api default)",
    )
    parser.add_argument(
        "--randomize",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Randomize unique IDs and SNs in exported files (default: yes)",
    )
    parser.add_argument(
        "--mqtt-data",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Export optional MQTT device data, adds > 5 minutes (default: yes)",
    )
    parser.add_argument(
        "--folder",
        "-f",
        type=str,
        help="Subfolder for the export (default: account nickname)",
    )
    parser.add_argument(
        "--zip",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Zip the output folder (default: yes)",
    )
    parser.add_argument(
        "--non-interactive",
        "-n",
        action="store_true",
        help="Never prompt; use defaults for any option not supplied via arguments",
    )
    return parser.parse_args()


async def main(args: argparse.Namespace) -> bool:  # noqa: C901
    """Run main function to export config after querying some options from user."""

    CONSOLE.info("Exporting found Anker Solix system data for all assigned sites.")
    randomize: bool = True
    mqttdata: bool = True
    services: set = set()
    loop = asyncio.get_running_loop()
    input_task = True
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
            # Which Api endpoint services to export
            services_map = {
                "all": set(asdict(ApiEndpointServices()).values()),
                "power": {ApiEndpointServices.power},
                "charging": {ApiEndpointServices.charging},
                "hes": {ApiEndpointServices.hes_svc},
                "mqtt": {"mqtt_only"},
                "discover": set(),
            }
            if args.services is not None:
                services = services_map[args.services]
            elif not args.non_interactive:
                resp = await loop.run_in_executor(
                    None,
                    input,
                    f"INPUT: Which Api endpoint services do you want to export? [{Color.CYAN}A{Color.OFF}]ll / "
                    f"[{Color.CYAN}P{Color.OFF}]ower / [{Color.CYAN}C{Color.OFF}]harging / [{Color.CYAN}H{Color.OFF}]es / "
                    f"[{Color.CYAN}M{Color.OFF}]qtt only / [{Color.YELLOW}D{Color.OFF}]iscover (default): ",
                )
                if resp != "" or not isinstance(services, set):
                    if resp.upper() in ["A", "LL"]:
                        services = services_map["all"]
                    elif resp.upper() in ["P", "POWER"]:
                        services = services_map["power"]
                    elif resp.upper() in ["C", "CHARGING"]:
                        services = services_map["charging"]
                    elif resp.upper() in ["H", "HES"]:
                        services = services_map["hes"]
                    elif resp.upper() in ["M", "MQTT"]:
                        services = services_map["mqtt"]
                    else:
                        # default to discover required services
                        services = set()
            CONSOLE.info(
                f"Exporting following services: {Color.YELLOW}{services or 'Discover automatically'}{Color.OFF}"
            )
            # Api endpoint request limit
            if args.endpoint_limit is not None:
                if args.endpoint_limit >= 0:
                    myapi.endpointLimit(limit=args.endpoint_limit)
            elif not args.non_interactive:
                resp = await loop.run_in_executor(
                    None,
                    input,
                    f"INPUT: Do you want to change Api endpoint request limit for proper throttling of same endpoint requests? "
                    f"[{Color.CYAN}0{Color.OFF}] = disabled / [{Color.YELLOW}{myapi.endpointLimit()!s}{Color.OFF}] = default: ",
                )
                if resp.isdigit() and int(resp) >= 0:
                    myapi.endpointLimit(limit=int(resp))
            CONSOLE.info(
                f"Api endpoint limit: {Color.YELLOW}{myapi.endpointLimit()!s}{Color.OFF}"
            )
            # Randomize unique IDs and SNs
            if args.randomize is not None:
                randomize = args.randomize
            elif not args.non_interactive:
                resp = await loop.run_in_executor(
                    None,
                    input,
                    f"INPUT: Do you want to randomize unique IDs and SNs in exported files? "
                    f"[{Color.YELLOW if randomize else Color.CYAN}Y{Color.OFF}]es{' (default)' if randomize else ''} / "
                    f"[{Color.YELLOW if not randomize else Color.CYAN}N{Color.OFF}]o{' (default)' if not randomize else ''}: ",
                )
                if resp != "" or not isinstance(randomize, bool):
                    randomize = resp.upper() in ["Y", "YES", "TRUE", 1]
            CONSOLE.info(
                f"Randomization of data: {Color.YELLOW}{randomize!s}{Color.OFF}",
            )
            # Optional MQTT device data export
            if "mqtt_only" in services:
                mqttdata = True
            elif args.mqtt_data is not None:
                mqttdata = args.mqtt_data
            elif not args.non_interactive:
                resp = await loop.run_in_executor(
                    None,
                    input,
                    f"INPUT: Do you want to export optional MQTT device data? These may not be completely randomized and export will take > 5 minutes. "
                    f"[{Color.YELLOW if mqttdata else Color.CYAN}Y{Color.OFF}]es{' (default)' if mqttdata else ''} / "
                    f"[{Color.YELLOW if not mqttdata else Color.CYAN}N{Color.OFF}]o{' (default)' if not mqttdata else ''}: ",
                )
                if resp != "" or not isinstance(mqttdata, bool):
                    mqttdata = resp.upper() in ["Y", "YES", "TRUE", 1]
            CONSOLE.info(
                f"MQTT device data export: {Color.YELLOW}{mqttdata!s}{Color.OFF}",
            )
            nickname = myapi.apisession.nickname.replace(
                "*", "x"
            )  # avoid filesystem problems with * in user nicknames
            # Subfolder for export
            if args.folder is not None:
                folder = args.folder
            elif args.non_interactive:
                folder = nickname
            else:
                folder = await loop.run_in_executor(
                    None,
                    input,
                    f"INPUT: Subfolder for export (default: {Color.YELLOW}{nickname}{Color.OFF}): ",
                )
            if folder == "":
                if nickname == "":
                    return False
                folder = nickname
            CONSOLE.info(f"Subfolder for export: {Color.YELLOW}{folder!s}{Color.OFF}")

            # Zip the output folder
            zipped: bool = True
            if args.zip is not None:
                zipped = args.zip
            elif not args.non_interactive:
                resp = await loop.run_in_executor(
                    None,
                    input,
                    f"INPUT: Do you want to zip the output folder? "
                    f"[{Color.YELLOW}Y{Color.OFF}]es (default) / [{Color.CYAN}N{Color.OFF}]o: ",
                )
                if resp != "":
                    zipped = resp.upper() not in ["N", "NO", "FALSE", 0]
            CONSOLE.info(f"Zip output folder: {Color.YELLOW}{zipped!s}{Color.OFF}")
            input_task = False
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
        elif isinstance(err, asyncio.CancelledError):
            if input_task:
                CONSOLE.warning(f"\n{Color.RED}[Input cancelled, hit ENTER]{Color.OFF}")
            else:
                CONSOLE.info("Export process was cancelled.")
        return False


# run async main
if __name__ == "__main__":
    try:
        if not asyncio.run(main(parse_arguments()), debug=False):
            CONSOLE.warning("Aborted!")
    except KeyboardInterrupt:
        CONSOLE.warning("Aborted!")
    except Exception as exception:  # pylint: disable=broad-exception-caught  # noqa: BLE001
        CONSOLE.exception("%s: %s", type(exception), exception)
