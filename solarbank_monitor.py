"""
Example exec module to use the Anker API for continously querying and displaying important solarbank parameters
This module will prompt for the Anker account details if not pre-set in the header.
Upon successfull authentication, you will see the solarbank parameters displayed and refreshed at reqular interval.
Note: When the system owning account is used, more details for the solarbank can be queried and displayed.
Attention: During executiion of this module, the used account cannot be used in the Anker App since it will be kicked out on each refresh.
"""

import asyncio
from aiohttp import ClientSession
from datetime import datetime, timedelta
from getpass import getpass
import json, logging, sys, time, os
from api import api

_LOGGER: logging.Logger = logging.getLogger(__name__)
_LOGGER.addHandler(logging.StreamHandler(sys.stdout))
#_LOGGER.setLevel(logging.DEBUG)    # enable for debug output

# Optional default Anker Account credentials to be used
USER = ""
PASSWORD = ""
COUNTRY = ""
REFRESH = 30    # refresh interval in seconds


def clearscreen():
    if sys.stdin is sys.__stdin__:  # check if not in IDLE shell
        os.system("cls") if os.name == "nt" else os.system("clear")
        #print("\033[H\033[2J", end="")  # ESC characters to clear screen, system independent?


async def main() -> None:
    global USER, PASSWORD, COUNTRY, REFRESH
    print("Solarbank Monitor:")
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
                print("\n")
                now = datetime.now().astimezone()
                if next_refr <= now:
                    print("Running site refresh...")
                    await myapi.update_sites()
                    next_refr = now + timedelta(seconds=REFRESH)
                if next_dev_refr <= now:
                    print("Running device details refresh...")
                    await myapi.update_device_details()
                    next_dev_refr = next_refr + timedelta(seconds=REFRESH*9)
                    schedules = {}
                clearscreen()
                print(f"Solarbank Monitor (refresh {REFRESH} s, details refresh {10*REFRESH} s):")
                print(f"Sites: {len(myapi.sites)}, Devices: {len(myapi.devices)}")
                for sn, dev in myapi.devices.items():
                    devtype = dev.get('type','unknown')
                    admin = dev.get('is_admin',False)
                    print(f"{'Device':<{col1}}: {(dev.get('name','NoName')):<{col2}} (Admin: {'YES' if admin else 'NO'})")
                    print(f"{'SN':<{col1}}: {sn}")
                    print(f"{'PN':<{col1}}: {dev.get('pn','')}")
                    print(f"{'Type':<{col1}}: {devtype.capitalize()}")
                    if devtype == "solarbank":
                        siteid = dev.get('site_id','')
                        print(f"{'Site ID':<{col1}}: {siteid}")
                        online = dev.get('wifi_online')
                        print(f"{'Wifi state':<{col1}}: {('Unknown' if online == None else 'Online' if online else 'Offline'):<{col2}} (Charging Status: {dev.get('charging_status','')})")
                        upgrade = dev.get('auto_upgrade')
                        print(f"{'SW Version':<{col1}}: {dev.get('sw_version','Unknown'):<{col2}} (Auto-Upgrade: {'Unknown' if upgrade == None else 'Enabled' if upgrade else 'Disabled'})")
                        soc = f"{dev.get('battery_soc','---'):>3} %"
                        print(f"{'State Of Charge':<{col1}}: {soc:<{col2}} (Min SOC: {str(dev.get('power_cutoff','--'))+' %'})")
                        unit = dev.get('power_unit','W')
                        print(f"{'Input Power':<{col1}}: {dev.get('input_power',''):>3} {unit}")
                        print(f"{'Charge Power':<{col1}}: {dev.get('charging_power',''):>3} {unit}")
                        print(f"{'Output Power':<{col1}}: {dev.get('output_power',''):>3} {unit}")
                        preset = dev.get('set_output_power')
                        if not preset:
                            preset = '---'
                        print(f"{'Output Preset':<{col1}}: {preset:>3} {unit}")
                        """update schedule with device details refresh and print it"""
                        if admin:
                            if not schedules.get(sn) and siteid:
                                schedules.update({sn: await myapi.get_device_load(siteId=siteid,deviceSn=sn)})
                            data = schedules.get(sn,{})
                            print(f"{'Schedule':<{col1}}: {now.strftime('%H:%M UTC %z'):<{col2}} (Current Preset: {data.get('current_home_load','')})")
                            print(f"{'ID':<{t1}} {'Start':<{t2}} {'End':<{t3}} {'Discharge':<{t4}} {'Output':<{t5}} {'ChargePrio':<{t6}}")
                            for slot in (data.get("home_load_data",{})).get("ranges",[]):
                                enabled = slot.get('turn_on')
                                load = slot.get('appliance_loads',[])
                                load = load[0] if len(load) > 0 else {}
                                print(f"{str(slot.get('id','')):>{t1}} {slot.get('start_time',''):<{t2}} {slot.get('end_time',''):<{t3}} {('---' if enabled == None else 'YES' if enabled else 'NO'):^{t4}} {str(load.get('power',''))+' W':>{t5}} {str(slot.get('charge_priority',''))+' %':>{t6}}")
                    else:
                        print(f"Not a Solarbank device, further details skipped")
                    print("")
                    #print(json.dumps(myapi.devices, indent=2))
                for sec in range(0,REFRESH):
                    now = datetime.now().astimezone()
                    if sys.stdin is sys.__stdin__:
                        print(f"Site refresh: {int((next_refr-now).total_seconds()):>3} sec,  Device details refresh: {int((next_dev_refr-now).total_seconds()):>3} sec  (CTRL-C to abort)", end = "\r", flush=True)
                    elif sec == 0:
                        # IDLE may be used and does not support cursor placement, skip time progress display
                        print(f"Site refresh: {int((next_refr-now).total_seconds()):>3} sec,  Device details refresh: {int((next_dev_refr-now).total_seconds()):>3} sec  (CTRL-C to abort)", end = "", flush=True)
                    time.sleep(1)
            return False

    except Exception as err:
        print(f'{type(err)}: {err}')
        return False


"""run async main"""
if __name__ == '__main__':
    try:
        if not asyncio.run(main()):
            print("\nAborted!")
    except KeyboardInterrupt:
        print("\nAborted!")
    except Exception as err:
        print(f'{type(err)}: {err}')
