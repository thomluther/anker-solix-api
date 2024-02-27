#!/usr/bin/env python
"""Example exec module to use the Anker API for export of defined system data
and device details.

This module will prompt for the Anker account details if not pre-set in the header.

Upon successfull authentication, you can specify a subfolder for the exported
JSON files received as API query response, defaulting to your nick name.

Optionally you can specify whether personalized information in the response
data should be randomized in the files, like SNs, Site IDs, Trace IDs etc.  You
can review the response files afterwards. They can be used as examples for
dedicated data extraction from the devices.

Optionally the API class can use the json files for debugging and testing on
various system outputs.

"""  # noqa: D205
# pylint: disable=duplicate-code

import asyncio
import json
import logging
import os
import random
import string
import sys
import time

from aiohttp import ClientSession
from aiohttp.client_exceptions import ClientError
from api import api, errors
import common

_LOGGER: logging.Logger = logging.getLogger(__name__)
_LOGGER.addHandler(logging.StreamHandler(sys.stdout))
# _LOGGER.setLevel(logging.DEBUG)    # enable for debug output
CONSOLE: logging.Logger = logging.getLogger("console")
CONSOLE.addHandler(logging.StreamHandler(sys.stdout))
CONSOLE.setLevel(logging.INFO)

RANDOMIZE = True  # Global flag to save randomize decission
RANDOMDATA = {}  # Global dict for randomized data, printed at the end


def randomize(val, key: str = "") -> str:
    """Randomize a given string while maintaining its format if format is known for given key name.

    Reuse same randomization if value was already randomized
    """
    if not RANDOMIZE:
        return str(val)
    randomstr = RANDOMDATA.get(val, "")
    if not randomstr and val:
        if "_sn" in key or key in ["sn"]:
            randomstr = "".join(
                random.choices(string.ascii_uppercase + string.digits, k=len(val))
            )
        elif "bt_ble_" in key:
            # Handle values with and without ':'
            temp = val.replace(":", "")
            randomstr = RANDOMDATA.get(
                temp
            )  # retry existing randomized value without :
            if not randomstr:
                randomstr = "".join(
                    random.choices(string.hexdigits.upper(), k=len(temp))
                )
            if ":" in val:
                RANDOMDATA.update({temp: randomstr})  # save also key value without :
                randomstr = ":".join(
                    a + b for a, b in zip(randomstr[::2], randomstr[1::2])
                )
        elif "_id" in key:
            for part in val.split("-"):
                if randomstr:
                    randomstr = "-".join(
                        [
                            randomstr,
                            "".join(
                                random.choices(string.hexdigits.lower(), k=len(part))
                            ),
                        ]
                    )
                else:
                    randomstr = "".join(
                        random.choices(string.hexdigits.lower(), k=len(part))
                    )
        elif "wifi_name" in key:
            idx = sum(1 for s in RANDOMDATA.values() if "wifi-network-" in s)
            randomstr = f"wifi-network-{idx+1}"
        elif key in ["home_load_data", "param_data"]:
            # these keys may contain schedule dict encoded as string, ensure contained serials are replaced in string
            # replace all mappings from randomdata, but skip trace ids
            randomstr = val
            for k, v in ((old,new) for old,new in RANDOMDATA.items() if len(old) != 32):
                randomstr = randomstr.replace(k,v)
            # leave without saving randomized string in RANDOMDATA
            return randomstr
        else:
            # default randomize format
            randomstr = "".join(random.choices(string.ascii_letters, k=len(val)))
        RANDOMDATA.update({val: randomstr})
    return randomstr


def check_keys(data):
    """Recursive traversal of complex nested objects to randomize value for certain keys."""
    if isinstance(data, int | str):
        return data
    for k, v in data.copy().items():
        if isinstance(v, dict):
            v = check_keys(v)
        if isinstance(v, list):
            v = [check_keys(i) for i in v]
        # Randomize value for certain keys
        if any(
            x in k for x in ["_sn", "site_id", "trace_id", "bt_ble_", "wifi_name", "home_load_data", "param_data"]
        ) or k in ["sn"]:
            data[k] = randomize(v, k)
    return data


def export(filename: str, d: dict = None, skip_randomize: bool = False, randomkeys: bool = False) -> None:
    """Save dict data to given file."""
    if not d:
        d = {}
    time.sleep(1)  # central delay between multiple requests
    if len(d) == 0:
        CONSOLE.info("WARNING: File %s not saved because JSON is empty", filename)
        return
    if RANDOMIZE and not skip_randomize:
        d = check_keys(d)
        # Randomize also the (nested) keys for dictionary export if required
        if randomkeys:
            d_copy = d.copy()
            for key, val in d.items():
                # check first nested keys in dict values
                for nested_key, nested_val in dict(val).items():
                    if isinstance(nested_val, dict):
                        for k in [text for text in nested_val if isinstance(text,str)]:
                            # check nested dict keys
                            if k in RANDOMDATA:
                                d_copy[key][nested_key][RANDOMDATA[k]] = d_copy[key][
                                    nested_key
                                ].pop(k)
                # check root keys
                if key in RANDOMDATA:
                    d_copy[RANDOMDATA[key]] = d_copy.pop(key)
            d = d_copy

    try:
        with open(filename, "w", encoding="utf-8") as file:
            json.dump(d, file, indent=2)
            CONSOLE.info("Saved JSON to file %s", filename)
    except OSError as err:
        CONSOLE.error("ERROR: Failed to save JSON to file %s: %s", filename, err)
    return


async def main() -> bool:  # noqa: C901 # pylint: disable=too-many-branches,too-many-statements
    """Run main function to export config."""
    global RANDOMIZE  # noqa: PLW0603, W0603 # pylint: disable=global-statement
    CONSOLE.info("Exporting found Anker Solix system data for all assigned sites:")
    try:
        user = common.user()
        async with ClientSession() as websession:
            CONSOLE.info("\nTrying authentication...")
            myapi = api.AnkerSolixApi(
                user, common.password(), common.country(), websession, _LOGGER
            )
            if await myapi.async_authenticate():
                CONSOLE.info("OK")
            else:
                CONSOLE.info(
                    "CACHED"
                )  # Login validation will be done during first API call

            resp = input(
                f"\nDo you want to randomize unique IDs and SNs in exported files? (default: {'YES' if RANDOMIZE else 'NO'}) (Y/N): "
            )
            if resp != "" or not isinstance(RANDOMIZE, bool):
                RANDOMIZE = resp.upper() in ["Y", "YES", "TRUE", 1]
            nickname = myapi.nickname.replace(
                "*", "#"
            )  # avoid filesystem problems with * in user nicknames
            folder = input(f"Subfolder for export (default: {nickname}): ")
            if folder == "":
                if nickname == "":
                    return False
                folder = nickname
            # Ensure to use local subfolder
            folder = os.path.join(os.path.dirname(__file__), "exports", folder)
            os.makedirs(folder, exist_ok=True)

            # first update sites and devices in API object
            CONSOLE.info("\nQuerying site information...")
            await myapi.update_sites()
            # Skip device detail queries, the defined serials are provided with the sites update
            #await myapi.update_device_details()
            CONSOLE.info("Sites: %s, Devices: %s", len(myapi.sites), len(myapi.devices))
            _LOGGER.debug(json.dumps(myapi.devices, indent=2))

            # pylint: disable=protected-access
            # Query API using direct endpoints to save full response of each query in json files
            CONSOLE.info("\nExporting homepage...")
            export(
                os.path.join(folder, "homepage.json"),
                await myapi.request("post", api._API_ENDPOINTS["homepage"], json={}),
            )
            CONSOLE.info("Exporting site list...")
            export(
                os.path.join(folder, "site_list.json"),
                await myapi.request("post", api._API_ENDPOINTS["site_list"], json={}),
            )
            CONSOLE.info("Exporting bind devices...")
            export(
                os.path.join(folder, "bind_devices.json"),
                await myapi.request(
                    "post", api._API_ENDPOINTS["bind_devices"], json={}
                ),
            )  # shows only owner devices
            CONSOLE.info("Exporting user devices...")
            export(
                os.path.join(folder, "user_devices.json"),
                await myapi.request(
                    "post", api._API_ENDPOINTS["user_devices"], json={}
                ),
            )  # shows only owner devices
            CONSOLE.info("Exporting charging devices...")
            export(
                os.path.join(folder, "charging_devices.json"),
                await myapi.request(
                    "post", api._API_ENDPOINTS["charging_devices"], json={}
                ),
            )  # shows only owner devices
            CONSOLE.info("Exporting auto upgrade settings...")
            export(
                os.path.join(folder, "auto_upgrade.json"),
                await myapi.request(
                    "post", api._API_ENDPOINTS["get_auto_upgrade"], json={}
                ),
            )  # shows only owner devices
            for siteId, site in myapi.sites.items():
                CONSOLE.info("\nExporting site specific data for site %s...", siteId)
                CONSOLE.info("Exporting scene info...")
                export(
                    os.path.join(folder, f"scene_{randomize(siteId,'site_id')}.json"),
                    await myapi.request(
                        "post",
                        api._API_ENDPOINTS["scene_info"],
                        json={"site_id": siteId},
                    ),
                )
                CONSOLE.info("Exporting site detail...")
                admin = site.get("site_admin")
                try:
                    export(
                        os.path.join(
                            folder, f"site_detail_{randomize(siteId,'site_id')}.json"
                        ),
                        await myapi.request(
                            "post",
                            api._API_ENDPOINTS["site_detail"],
                            json={"site_id": siteId},
                        ),
                    )
                except (ClientError, errors.AnkerSolixError):
                    if not admin:
                        CONSOLE.warning("Query requires account of site owner!")
                CONSOLE.info("Exporting wifi list...")
                try:
                    export(
                        os.path.join(
                            folder, f"wifi_list_{randomize(siteId,'site_id')}.json"
                        ),
                        await myapi.request(
                            "post",
                            api._API_ENDPOINTS["wifi_list"],
                            json={"site_id": siteId},
                        ),
                    )  # works only for site owners
                except (ClientError, errors.AnkerSolixError):
                    if not admin:
                        CONSOLE.warning("Query requires account of site owner!")
                CONSOLE.info("Exporting site price...")
                try:
                    export(
                        os.path.join(
                            folder, f"price_{randomize(siteId,'site_id')}.json"
                        ),
                        await myapi.request(
                            "post",
                            api._API_ENDPOINTS["get_site_price"],
                            json={"site_id": siteId},
                        ),
                    )  # works only for site owners
                except (ClientError, errors.AnkerSolixError):
                    if not admin:
                        CONSOLE.warning("Query requires account of site owner!")
                CONSOLE.info("Exporting device parameter settings...")
                try:
                    export(
                        os.path.join(
                            folder, f"device_parm_{randomize(siteId,'site_id')}.json"
                        ),
                        await myapi.request(
                            "post",
                            api._API_ENDPOINTS["get_device_parm"],
                            json={"site_id": siteId, "param_type": "4"},
                        ),
                    )  # works only for site owners
                except (ClientError, errors.AnkerSolixError):
                    if not admin:
                        CONSOLE.warning("Query requires account of site owner!")
            for sn, device in myapi.devices.items():
                CONSOLE.info(
                    "\nExporting device specific data for device %s SN %s...",
                    device.get("name", ""),
                    sn,
                )
                siteId = device.get("site_id", "")
                admin = device.get("is_admin")

                if device.get("type") == "solarbank":
                    CONSOLE.info("Exporting solar info settings for solarbank...")
                    try:
                        export(
                            os.path.join(
                                folder, f"solar_info_{randomize(sn,'_sn')}.json"
                            ),
                            await myapi.request(
                                "post",
                                api._API_ENDPOINTS["solar_info"],
                                json={"solarbank_sn": sn},
                            ),
                        )
                    except (ClientError, errors.AnkerSolixError):
                        if not admin:
                            CONSOLE.warning("Query requires account of site owner!")

                    CONSOLE.info("Exporting compatible process info for solarbank...")
                    try:
                        export(
                            os.path.join(
                                folder, f"compatible_process_{randomize(sn,'_sn')}.json"
                            ),
                            await myapi.request(
                                "post",
                                api._API_ENDPOINTS["compatible_process"],
                                json={"solarbank_sn": sn},
                            ),
                        )
                    except (ClientError, errors.AnkerSolixError):
                        if not admin:
                            CONSOLE.warning("Query requires account of site owner!")

                CONSOLE.info("Exporting power cutoff settings...")
                try:
                    export(
                        os.path.join(
                            folder, f"power_cutoff_{randomize(sn,'_sn')}.json"
                        ),
                        await myapi.request(
                            "post",
                            api._API_ENDPOINTS["get_cutoff"],
                            json={"site_id": siteId, "device_sn": sn},
                        ),
                    )  # works only for site owners
                except (ClientError, errors.AnkerSolixError):
                    if not admin:
                        CONSOLE.warning("Query requires account of site owner!")
                CONSOLE.info("Exporting fittings...")
                try:
                    export(
                        os.path.join(
                            folder, f"device_fittings_{randomize(sn,'_sn')}.json"
                        ),
                        await myapi.request(
                            "post",
                            api._API_ENDPOINTS["get_device_fittings"],
                            json={"site_id": siteId, "device_sn": sn},
                        ),
                    )  # works only for site owners
                except (ClientError, errors.AnkerSolixError):
                    if not admin:
                        CONSOLE.warning("Query requires account of site owner!")
                CONSOLE.info("Exporting load...")
                try:
                    export(
                        os.path.join(folder, f"device_load_{randomize(sn,'_sn')}.json"),
                        await myapi.request(
                            "post",
                            api._API_ENDPOINTS["get_device_load"],
                            json={"site_id": siteId, "device_sn": sn},
                        ),
                    )  # works only for site owners
                except (ClientError, errors.AnkerSolixError):
                    if not admin:
                        CONSOLE.warning("Query requires account of site owner!")

            # update the api dictionaries from exported files to use randomized input data
            # this is more efficient and allows validation of randomized data in export files
            myapi.testDir(folder)
            await myapi.update_sites(fromFile=True)
            await myapi.update_device_details(fromFile=True)
            # avoid randomizing dictionary export twice when imported from randomized files already
            CONSOLE.info("\nExporting Api Sites overview...")
            export(
                os.path.join(folder, "api_sites.json"),
                myapi.sites,
                skip_randomize=True,
            )
            CONSOLE.info("Exporting Api Devices overview...")
            export(
                os.path.join(folder, "api_devices.json"),
                myapi.devices,
                skip_randomize=True,
            )

            CONSOLE.info(
                "\nCompleted export of Anker Solix system data for user %s", user
            )
            if RANDOMIZE:
                CONSOLE.info(
                    "Folder %s contains the randomized JSON files. Pls check and update fields that may contain unrecognized personalized data.",
                    os.path.abspath(folder),
                )
                CONSOLE.info(
                    "Following trace or site IDs, SNs and MAC addresses have been randomized in files (from -> to):"
                )
                CONSOLE.info(json.dumps(RANDOMDATA, indent=2))
            else:
                CONSOLE.info(
                    "Folder %s contains the JSON files.", os.path.abspath(folder)
                )
            return True

    except (ClientError, errors.AnkerSolixError) as err:
        CONSOLE.error("%s: %s", type(err), err)
        return False


# run async main
if __name__ == "__main__":
    try:
        if not asyncio.run(main()):
            CONSOLE.info("Aborted!")
    except KeyboardInterrupt:
        CONSOLE.warning("Aborted!")
    except Exception as exception:  # pylint: disable=broad-exception-caught
        CONSOLE.exception("%s: %s", type(exception), exception)
