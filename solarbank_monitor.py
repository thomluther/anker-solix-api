"""Example exec module to use the Anker API for continously querying and displaying important solarbank parameters
This module will prompt for the Anker account details if not pre-set in the header.
Upon successfull authentication, you will see the solarbank parameters displayed and refreshed at reqular interval.
Note: When the system owning account is used, more details for the solarbank can be queried and displayed.
Attention: During executiion of this module, the used account cannot be used in the Anker App since it will be kicked out on each refresh.
"""  # noqa: D205

import asyncio
from datetime import datetime, timedelta
from getpass import getpass
import json
import logging
import os
import sys
import time

from aiohttp import ClientSession
from api import api

_LOGGER: logging.Logger = logging.getLogger(__name__)
_LOGGER.addHandler(logging.StreamHandler(sys.stdout))
#_LOGGER.setLevel(logging.DEBUG)    # enable for debug output
CONSOLE: logging.Logger = logging.getLogger("console")
CONSOLE.addHandler(logging.StreamHandler(sys.stdout))
CONSOLE.setLevel(logging.INFO)

# Optional default Anker Account credentials to be used
USER = ""
PASSWORD = ""
COUNTRY = ""
REFRESH = 30    # default refresh interval in seconds


def clearscreen():
    """Clear the terminal screen."""
    if sys.stdin is sys.__stdin__:  # check if not in IDLE shell
        if os.name == "nt":
            os.system("cls")
        else:
            os.system("clear")
        #CONSOLE.info("\033[H\033[2J", end="")  # ESC characters to clear terminal screen, system independent?


async def main() -> None:
    """Run Main routine to start Solarbank monitor in a loop."""
    global USER, PASSWORD, COUNTRY, REFRESH  # noqa: PLW0603
    CONSOLE.info("Solarbank Monitor:")
    if USER == "":
        CONSOLE.info("\nEnter Anker Account credentials:")
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
            CONSOLE.info("\nTrying authentication...")
            myapi = api.AnkerSolixApi(USER,PASSWORD,COUNTRY,websession, _LOGGER)
            if await myapi.async_authenticate():
                CONSOLE.info("OK")
            else:
                # Login validation will be done during first API call
                CONSOLE.info("CACHED")

            while True:
                resp = input(f"\nHow many seconds refresh interval should be used? (10-600, default: {REFRESH}): ")
                if not resp:
                    break
                elif resp.isdigit() and 10 <= int(resp) <= 600:
                    REFRESH = int(resp)
                    break

            # Run loop to update Solarbank parameters
            now = datetime.now().astimezone()
            next_refr = now
            next_dev_refr = now
            col1 = 15
            col2 = 20
            t1 = 2
            t2 = 5
            t3 = 5
            t4 = 9
            t5 = 6
            t6 = 10
            while True:
                CONSOLE.info("\n")
                now = datetime.now().astimezone()
                if next_refr <= now:
                    CONSOLE.info("Running site refresh...")
                    await myapi.update_sites()
                    next_refr = now + timedelta(seconds=REFRESH)
                if next_dev_refr <= now:
                    CONSOLE.info("Running device details refresh...")
                    await myapi.update_device_details()
                    next_dev_refr = next_refr + timedelta(seconds=REFRESH*9)
                    schedules = {}
                clearscreen()
                CONSOLE.info(f"Solarbank Monitor (refresh {REFRESH} s, details refresh {10*REFRESH} s):")
                CONSOLE.info(f"Sites: {len(myapi.sites)}, Devices: {len(myapi.devices)}")
                for sn, dev in myapi.devices.items():
                    devtype = dev.get('type','unknown')
                    admin = dev.get('is_admin',False)
                    CONSOLE.info(f"{'Device':<{col1}}: {(dev.get('name','NoName')):<{col2}} (Admin: {'YES' if admin else 'NO'})")
                    CONSOLE.info(f"{'SN':<{col1}}: {sn}")
                    CONSOLE.info(f"{'PN':<{col1}}: {dev.get('pn','')}")
                    CONSOLE.info(f"{'Type':<{col1}}: {devtype.capitalize()}")
                    if devtype == "solarbank":
                        siteid = dev.get('site_id','')
                        CONSOLE.info(f"{'Site ID':<{col1}}: {siteid}")
                        online = dev.get('wifi_online')
                        CONSOLE.info(f"{'Wifi state':<{col1}}: {('Unknown' if online is None else 'Online' if online else 'Offline'):<{col2}} (Charging Status: {dev.get('charging_status','')})")
                        upgrade = dev.get('auto_upgrade')
                        CONSOLE.info(f"{'SW Version':<{col1}}: {dev.get('sw_version','Unknown'):<{col2}} (Auto-Upgrade: {'Unknown' if upgrade is None else 'Enabled' if upgrade else 'Disabled'})")
                        soc = f"{dev.get('battery_soc','---'):>3} %"
                        CONSOLE.info(f"{'Status':<{col1}}: {dev.get('status_description','Unknown'):<{col2}} (Status code: {str(dev.get('charging_status','-'))})")
                        CONSOLE.info(f"{'State Of Charge':<{col1}}: {soc:<{col2}} (Min SOC: {str(dev.get('power_cutoff','--'))+' %'})")
                        unit = dev.get('power_unit','W')
                        CONSOLE.info(f"{'Input Power':<{col1}}: {dev.get('input_power',''):>3} {unit}")
                        CONSOLE.info(f"{'Charge Power':<{col1}}: {dev.get('charging_power',''):>3} {unit}")
                        CONSOLE.info(f"{'Output Power':<{col1}}: {dev.get('output_power',''):>3} {unit}")
                        preset = dev.get('set_output_power')
                        if not preset:
                            preset = '---'
                        CONSOLE.info(f"{'Output Preset':<{col1}}: {preset:>3} {unit}")
                        # update schedule with device details refresh and print it
                        if admin:
                            if not schedules.get(sn) and siteid:
                                schedules.update({sn: await myapi.get_device_load(siteId=siteid,deviceSn=sn)})
                            data = schedules.get(sn,{})
                            CONSOLE.info(f"{'Schedule':<{col1}}: {now.strftime('%H:%M UTC %z'):<{col2}} (Current Preset: {data.get('current_home_load','')})")
                            CONSOLE.info(f"{'ID':<{t1}} {'Start':<{t2}} {'End':<{t3}} {'Discharge':<{t4}} {'Output':<{t5}} {'ChargePrio':<{t6}}")
                            for slot in (data.get("home_load_data",{})).get("ranges",[]):
                                enabled = slot.get('turn_on')
                                load = slot.get('appliance_loads',[])
                                load = load[0] if len(load) > 0 else {}
                                CONSOLE.info(f"{str(slot.get('id','')):>{t1}} {slot.get('start_time',''):<{t2}} {slot.get('end_time',''):<{t3}} {('---' if enabled is None else 'YES' if enabled else 'NO'):^{t4}} {str(load.get('power',''))+' W':>{t5}} {str(slot.get('charge_priority',''))+' %':>{t6}}")
                    else:
                        sys.stdoutf("Not a Solarbank device, further details skipped")
                    CONSOLE.info("")
                    CONSOLE.debug(json.dumps(myapi.devices, indent=2))
                for sec in range(0,REFRESH):
                    now = datetime.now().astimezone()
                    if sys.stdin is sys.__stdin__:
                        print(f"Site refresh: {int((next_refr-now).total_seconds()):>3} sec,  Device details refresh: {int((next_dev_refr-now).total_seconds()):>3} sec  (CTRL-C to abort)", end = "\r", flush=True)  # noqa: T201
                    elif sec == 0:
                        # IDLE may be used and does not support cursor placement, skip time progress display
                        print(f"Site refresh: {int((next_refr-now).total_seconds()):>3} sec,  Device details refresh: {int((next_dev_refr-now).total_seconds()):>3} sec  (CTRL-C to abort)", end = "", flush=True)  # noqa: T201
                    time.sleep(1)
            return False

    except Exception as exception:
        CONSOLE.info(f'{type(exception)}: {exception}')
        return False


# run async main
if __name__ == '__main__':
    try:
        if not asyncio.run(main()):
            CONSOLE.info("\nAborted!")
    except KeyboardInterrupt:
        CONSOLE.info("\nAborted!")
    except Exception as err:
        CONSOLE.info(f'{type(err)}: {err}')
