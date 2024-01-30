"""
Example exec module to use the Anker API for export of defined system data and device details.
This module will prompt for the Anker account details if not pre-set in the header.
Upon successfull authentication, you can specify a subfolder for the exported JSON files received as API query response, defaulting to your nick name
Optionally you can specify whether personalized information in the response data should be randomized in the files, like SNs, Site IDs, Trace IDs etc.
You can review the response files afterwards. They can be used as examples for dedicated data extraction from the devices.
Optionally the API class can use the json files for debugging and testing on various system outputs.
"""

import asyncio
from aiohttp import ClientSession
from datetime import datetime
from getpass import getpass
from contextlib import suppress
import json, logging, sys, csv, os, time, string, random
from api import api

_LOGGER: logging.Logger = logging.getLogger(__name__)
_LOGGER.addHandler(logging.StreamHandler(sys.stdout))
#_LOGGER.setLevel(logging.DEBUG)    # enable for debug output

# Optional default Anker Account credentials to be used
USER = ""
PASSWORD = ""
COUNTRY = ""

RANDOMIZE = True    # Global flag to save randomize decission
RANDOMDATA = {}     # Global dict for randomized data, printed at the end


def randomize(val, key: str = "") -> str:
    """Randomize a given string while maintaining its format if format is known for given key name.
    Reuse same randomization if value was already randomized"""
    global RANDOMDATA
    if not RANDOMIZE:
        return str(val)
    randomstr = RANDOMDATA.get(val,"")
    if not randomstr:
        if "_sn" in key:
            randomstr = "".join(random.choices(string.ascii_uppercase+string.digits, k=len(val)))
        elif "bt_ble_" in key:
            """Handle values with and without : """
            temp = val.replace(":","")
            randomstr = RANDOMDATA.get(temp)    # retry existing randomized value without :
            if not randomstr:
                randomstr = "".join(random.choices(string.hexdigits.upper(), k=len(temp)))
            if ":" in val:
                RANDOMDATA.update({temp: randomstr})    # save also key value without :
                randomstr = ':'.join(a+b for a,b in zip(randomstr[::2], randomstr[1::2]))
        elif "_id" in key:
            for part in val.split("-"):
                if randomstr:
                    randomstr = "-".join([randomstr,"".join(random.choices(string.hexdigits.lower(), k=len(part)))])
                else:
                    randomstr = "".join(random.choices(string.hexdigits.lower(), k=len(part)))
        else:
            # default randomize format
            randomstr = "".join(random.choices(string.ascii_letters, k=len(val)))
        RANDOMDATA.update({val: randomstr})
    return randomstr

         
def check_keys(data):
    """Recursive traversal of complex nested objects to randomize value for certain keys"""
    if isinstance(data, str) or isinstance(data, int):
        return data
    for k, v in data.copy().items():
        if isinstance(v, dict):
            v = check_keys(v)
        if isinstance(v, list):
            v = [check_keys(i) for i in v]
        """Randomize value for certain keys"""
        if any(x in k for x in ["_sn","site_id","trace_id","bt_ble_"]):
            data[k] = randomize(v,k)
    return data


def export(filename: str, d: dict = {}) -> None:
    """Save dict data to given file"""
    time.sleep(1)   # central delay between multiple requests
    if len(d) == 0:
        print(f"WARNING: File {filename} not saved because JSON is empty")
        return
    elif RANDOMIZE:
        d = check_keys(d)
    try:
        with open(filename, 'w') as file:
            json.dump(d, file, indent=2)
            print(f"Saved JSON to file {filename}")
    except Exception as err:
        print(f"ERROR: Failed to save JSON to file {filename}")
    return


async def main() -> None:
    global USER, PASSWORD, COUNTRY, RANDOMIZE
    print("Exporting found Anker Solix system data for all assigned sites:")
    if USER == "":
        print("\nEnter Anker Account credentials:")
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
            print("\nTrying authentication...",end="")
            myapi = api.API(USER,PASSWORD,COUNTRY,websession, _LOGGER)
            if await myapi.async_authenticate():
                print("OK")
            else:
                print("CACHED")     # Login validation will be done during first API call
            
            random = input(f"\nDo you want to randomize unique IDs and SNs in exported files? (default: {'YES' if RANDOMIZE else 'NO'}) (Y/N): ")
            if random != "" or not isinstance(RANDOMIZE,bool):
                RANDOMIZE = random.upper() in ["Y","YES","TRUE",1]
            nickname = myapi.nickname.replace("*","#")  # avoid filesystem problems with * in user nicknames
            folder = input(f"Subfolder for export (default: {nickname}): ")
            if folder == "":
                if nickname == "":
                    return False
                else:
                    folder = nickname
            os.makedirs(folder, exist_ok=True) 
                
            # first update sites in API object
            print("\nQuerying site information...")
            await myapi.update_sites()
            print(f"Sites: {len(myapi.sites)}, Devices: {len(myapi.devices)}")
            _LOGGER.debug(json.dumps(myapi.devices, indent=2))
            
            # Query API using direct endpoints to save full response of each query in json files
            print("\nExporting homepage...")
            export(os.path.join(folder,f"homepage.json"), await myapi.request("post", api._API_ENDPOINTS["homepage"],json={}))
            print("Exporting site list...")
            export(os.path.join(folder,f"site_list.json"), await myapi.request("post", api._API_ENDPOINTS["site_list"],json={}))
            print("Exporting bind devices...")
            export(os.path.join(folder,f"bind_devices.json"), await myapi.request("post", api._API_ENDPOINTS["bind_devices"],json={}))          # shows only owner devices
            print("Exporting user devices...")
            export(os.path.join(folder,f"user_devices.json"), await myapi.request("post", api._API_ENDPOINTS["user_devices"],json={}))          # shows only owner devices
            print("Exporting charging devices...")
            export(os.path.join(folder,f"charging_devices.json"), await myapi.request("post", api._API_ENDPOINTS["charging_devices"],json={}))  # shows only owner devices
            print("Exporting auto upgrade settings...")
            export(os.path.join(folder,f"auto_upgrade.json"), await myapi.request("post", api._API_ENDPOINTS["get_auto_upgrade"],json={}))          # shows only owner devices
            for siteId, site in myapi.sites.items():
                print(f"\nExporting site specific data for site {siteId}...")
                print("Exporting scene info...")
                export(os.path.join(folder,f"scene_{randomize(siteId,'site_id')}.json"), await myapi.request("post", api._API_ENDPOINTS["scene_info"],json={"site_id": siteId}))
                print("Exporting solar info...")
                with suppress(Exception):
                    export(os.path.join(folder,f"solar_info_{randomize(siteId,'site_id')}.json"), await myapi.request("post", api._API_ENDPOINTS["solar_info"],json={"site_id": siteId}))    # PARAMETERS UNKNOWN, site id not sufficient
                print("Exporting site detail...")
                admin = site.get("site_admin")
                try:
                    export(os.path.join(folder,f"site_detail_{randomize(siteId,'site_id')}.json"), await myapi.request("post", api._API_ENDPOINTS["site_detail"],json={"site_id": siteId}))
                except Exception as err:
                    if not admin:
                        print("Query requires account of site owner!")
                print("Exporting wifi list...")
                try:
                    export(os.path.join(folder,f"wifi_list_{randomize(siteId,'site_id')}.json"), await myapi.request("post", api._API_ENDPOINTS["wifi_list"],json={"site_id": siteId}))      # works only for site owners
                except Exception as err:
                    if not admin:
                        print("Query requires account of site owner!")
                print("Exporting site price...")
                try:
                    export(os.path.join(folder,f"price_{randomize(siteId,'site_id')}.json"), await myapi.request("post", api._API_ENDPOINTS["get_site_price"],json={"site_id": siteId}))     # works only for site owners
                except Exception as err:
                    if not admin:
                        print("Query requires account of site owner!")
                print("Exporting device parameter settings...")
                try:
                    export(os.path.join(folder,f"device_parm_{randomize(siteId,'site_id')}.json"), await myapi.request("post", api._API_ENDPOINTS["get_device_parm"],json={"site_id": siteId, "param_type": "4"}))      # works only for site owners
                except Exception as err:
                    if not admin:
                        print("Query requires account of site owner!")
            for sn, device in myapi.devices.items():
                print(f"\nExporting device specific data for device {device.get('name','')} SN {sn}...")
                siteId = device.get('site_id','')
                admin = site.get('is_admin')
                print("Exporting power cutoff settings...")
                try:
                    export(os.path.join(folder,f"power_cutoff_{randomize(sn,'_sn')}.json"), await myapi.request("post", api._API_ENDPOINTS["get_cutoff"],json={"site_id": siteId, "device_sn": sn}))                 # works only for site owners
                except Exception as err:
                    if not admin:
                        print("Query requires account of site owner!")
                print("Exporting fittings...")
                try:
                    export(os.path.join(folder,f"device_fittings_{randomize(sn,'_sn')}.json"), await myapi.request("post", api._API_ENDPOINTS["get_device_fittings"],json={"site_id": siteId, "device_sn": sn}))     # works only for site owners
                except Exception as err:
                    if not admin:
                        print("Query requires account of site owner!")
                print("Exporting load...")
                try:
                    export(os.path.join(folder,f"device_load_{randomize(sn,'_sn')}.json"), await myapi.request("post", api._API_ENDPOINTS["get_device_load"],json={"site_id": siteId, "device_sn": sn}))             # works only for site owners
                except Exception as err:
                    if not admin:
                        print("Query requires account of site owner!")

            print(f"\nCompleted export of Anker Solix system data for user {USER}")
            if RANDOMIZE:
                print(f"Folder {os.path.abspath(folder)} contains the randomized JSON files. Pls check and update fields that may contain unrecognized personalized data.")
                print(f"Following trace or site IDs, SNs and MAC addresses have been randomized in files (from -> to):")
                print(json.dumps(RANDOMDATA, indent=2))
            else:
                print(f"Folder {os.path.abspath(folder)} contains the JSON files.")
            return True

    except Exception as err:
        print(f'{type(err)}: {err}')
        return False


"""run async main"""
if __name__ == '__main__':
    try:
        if not asyncio.run(main()):
            print("Aborted!")
    except KeyboardInterrupt:
        print("Aborted!")
    except Exception as err:
        print(f'{type(err)}: {err}')
