"""A collection of helper functions for pyscripts."""  # noqa: INP001

import getpass
import logging
import os
import sys

from api.types import SolarbankUsageMode

CONSOLE: logging.Logger = logging.getLogger("console")
CONSOLE.addHandler(logging.StreamHandler(sys.stdout))
CONSOLE.setLevel(logging.INFO)

# Optional default Anker Account credentials to be used
_CREDENTIALS = {
    "USER": os.getenv("ANKERUSER"),
    "PASSWORD": os.getenv("ANKERPASSWORD"),
    "COUNTRY": os.getenv("ANKERCOUNTRY"),
}


def user() -> str:
    """Get anker account user."""
    if _CREDENTIALS.get("USER"):
        return _CREDENTIALS["USER"]
    CONSOLE.info("\nEnter Anker Account credentials:")
    username = input("Username (email): ")
    while not username:
        username = input("Username (email): ")
    return username


def password() -> str:
    """Get anker account password."""
    if _CREDENTIALS.get("PASSWORD"):
        return _CREDENTIALS["PASSWORD"]
    pwd = getpass.getpass("Password: ")
    while not pwd:
        pwd = getpass.getpass("Password: ")
    return pwd


def country() -> str:
    """Get anker account country."""
    if _CREDENTIALS.get("COUNTRY"):
        return _CREDENTIALS["COUNTRY"]
    countrycode = input("Country ID (e.g. DE): ")
    while not countrycode:
        countrycode = input("Country ID (e.g. DE): ")
    return countrycode


def print_schedule(schedule: dict) -> None:
    """Print the schedule ranges as table."""

    plan = schedule or {}
    t1 = 2
    t2 = 5
    t3 = 5
    t4 = 6
    t5 = 6
    t6 = 10
    t7 = 6
    t8 = 6
    t9 = 5
    if plan.get("mode_type", 0):
        # SB2 schedule
        usage_mode = plan.get("mode_type") or 0
        week = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
        CONSOLE.info(
            f"{'Usage Mode':<{t1}}: {str(SolarbankUsageMode(usage_mode).name if usage_mode in iter(SolarbankUsageMode) else 'Unknown').capitalize()+' ('+str(usage_mode)+')':<{t2+t3+t4}} {'Def. Preset':<{t3}}: {plan.get('default_home_load','----'):>4} W"
        )
        CONSOLE.info(
            f"{'ID':<{t1}} {'Start':<{t2}} {'End':<{t3}} {'Output':<{t4}} {'Weekdays':<{t5}}"
        )
        for idx in plan.get("custom_rate_plan") or [{}]:
            index = idx.get("index", "--")
            weekdays = [week[day] for day in idx.get("week") or []]
            for slot in idx.get("ranges") or []:
                CONSOLE.info(
                    f"{index!s:>{t1}} {slot.get('start_time','')!s:<{t2}} {slot.get('end_time','')!s:<{t3}} {str(slot.get('power',''))+' W':>{t4}} {','.join(weekdays):<{t5}}"
                )
    else:
        # SB1 schedule
        CONSOLE.info(
            f"{'ID':<{t1}} {'Start':<{t2}} {'End':<{t3}} {'Export':<{t4}} {'Output':<{t5}} {'ChargePrio':<{t6}} {'SB1':>{t7}} {'SB2':>{t8}} {'Mode':>{t9}} Name"
        )
        for slot in (schedule or {}).get("ranges", []):
            enabled = slot.get("turn_on")
            load = slot.get("appliance_loads", [])
            load = load[0] if len(load) > 0 else {}
            solarbanks = slot.get("device_power_loads", [])
            sb1 = str(solarbanks[0].get("power") if len(solarbanks) > 0 else "---")
            sb2 = str(solarbanks[1].get("power") if len(solarbanks) > 1 else "---")
            CONSOLE.info(
                f"{slot.get('id','')!s:>{t1}} {slot.get('start_time','')!s:<{t2}} {slot.get('end_time','')!s:<{t3}} {('---' if enabled is None else 'YES' if enabled else 'NO'):^{t4}} {str(load.get('power',''))+' W':>{t5}} {str(slot.get('charge_priority',''))+' %':>{t6}} {sb1+' W':>{t7}} {sb2+' W':>{t8}} {slot.get('power_setting_mode','-')!s:^{t9}} {load.get('name','')!s}"
            )
