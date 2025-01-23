"""A collection of helper functions for pyscripts."""  # noqa: INP001

import datetime
import getpass
import logging
import os

from api.apitypes import (  # pylint: disable=no-name-in-module
    SolarbankRatePlan,
    SolarbankUsageMode,
)

# create logger
CONSOLE: logging.Logger = logging.getLogger(__name__)
# Set parent to lowest level to allow messages passed to all handlers using their own level
CONSOLE.setLevel(logging.DEBUG)

# create console handler and set level to info
ch = logging.StreamHandler()
# This can be changed to DEBUG if more messages should be printed to console
ch.setLevel(logging.INFO)
CONSOLE.addHandler(ch)

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

    t2 = 2
    t5 = 5
    t6 = 6
    t9 = 9
    t10 = 10
    plan = schedule or {}
    if plan.get("mode_type", 0):
        # SB2 schedule
        usage_mode = plan.get("mode_type") or 0
        CONSOLE.info(
            f"{'Usage Mode':<{t2}}: {str(SolarbankUsageMode(usage_mode).name if usage_mode in iter(SolarbankUsageMode) else 'Unknown').capitalize()+' ('+str(usage_mode)+')':<{t5+t5+t6}} {'Def. Preset':<{t5}}: {plan.get('default_home_load','----'):>4} W"
        )
        week = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
        for rate_plan_name in {
            getattr(SolarbankRatePlan, attr)
            for attr in ['smartmeter', 'smartplugs']
        }:
            for idx in plan.get(rate_plan_name) or [{}]:
                index = idx.get("index", "--")
                weekdays = [week[day] for day in idx.get("week") or []]
                if ranges := idx.get("ranges") or []:
                    CONSOLE.info(
                        f"{'ID':<{t2}} {'Start':<{t5}} {'End':<{t5}} {'Output':<{t6}} {'Weekdays':<{t6}}   <== {rate_plan_name}{' (Smart plugs)' if rate_plan_name == SolarbankRatePlan.smartplugs else ''}"
                    )
                for slot in ranges:
                    CONSOLE.info(
                        f"{index!s:>{t2}} {slot.get('start_time','')!s:<{t5}} {slot.get('end_time','')!s:<{t5}} {str(slot.get('power',''))+' W':>{t6}} {','.join(weekdays):<{t6}}"
                    )
        # AC specific plans
        if (rate_plan := plan.get('manual_backup') or {}) and (ranges := rate_plan.get("ranges") or []):
            CONSOLE.info(
                f"{'Backup Start':<{t10+t10}} {'Backup End':<{t10+t10}}  <== manual_backup (Switch {'ON' if rate_plan.get('switch') else 'OFF'})"
            )
            for slot in ranges:
                CONSOLE.info(
                    f"{datetime.datetime.fromtimestamp(slot.get('start_time',0),datetime.UTC).astimezone().strftime("%Y-%m-%d %H:%M:%S"):<{t10+t10}} {datetime.datetime.fromtimestamp(slot.get('end_time',0),datetime.UTC).astimezone().strftime("%Y-%m-%d %H:%M:%S"):<{t10+t10}}"
                )
    else:
        # SB1 schedule
        if ranges := plan.get("ranges") or []:
            CONSOLE.info(
                f"{'ID':<{t2}} {'Start':<{t5}} {'End':<{t5}} {'Export':<{t6}} {'Output':<{t6}} {'ChargePrio':<{t10}} {'DisChPrio':<{t9}} {'SB1':>{t6}} {'SB2':>{t6}} {'Mode':>{t5}} Name"
            )
        for slot in ranges:
            enabled = slot.get("turn_on")
            discharge = slot.get("priority_discharge_switch") if plan.get("is_show_priority_discharge") else None
            load = slot.get("appliance_loads", [])
            load = load[0] if len(load) > 0 else {}
            solarbanks = slot.get("device_power_loads") or []
            sb1 = str(solarbanks[0].get("power") if len(solarbanks) > 0 else "---")
            sb2 = str(solarbanks[1].get("power") if len(solarbanks) > 1 else "---")
            CONSOLE.info(
                f"{slot.get('id','')!s:>{t2}} {slot.get('start_time','')!s:<{t5}} {slot.get('end_time','')!s:<{t5}} {('---' if enabled is None else 'YES' if enabled else 'NO'):^{t6}} {str(load.get('power',''))+' W':>{t6}} {str(slot.get('charge_priority',''))+' %':>{t10}} {('---' if discharge is None else 'YES' if discharge else 'NO'):>{t9}} {sb1+' W':>{t6}} {sb2+' W':>{t6}} {slot.get('power_setting_mode','-')!s:^{t5}} {load.get('name','')!s}"
            )
