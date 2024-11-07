"""Class for interacting with the Anker Power / Solix API Power Panel related charging_service endpoints.

Required Python modules:
pip install cryptography
pip install aiohttp
pip install aiofiles
"""

from __future__ import annotations

from datetime import datetime, timedelta
import logging
from pathlib import Path

from aiohttp import ClientSession

from .apibase import AnkerSolixBaseApi
from .apitypes import API_CHARGING_ENDPOINTS, API_FILEPREFIXES, SolixDeviceType
from .helpers import convertToKwh
from .session import AnkerSolixClientSession

_LOGGER: logging.Logger = logging.getLogger(__name__)


class AnkerSolixPowerpanelApi(AnkerSolixBaseApi):
    """Define the API class to handle Anker server communication via AnkerSolixClientSession for Power Panel related queries.

    It will also build internal cache dictionaries with information collected through the Api.
    """

    def __init__(
        self,
        email: str | None = None,
        password: str | None = None,
        countryId: str | None = None,
        websession: ClientSession | None = None,
        logger: logging.Logger | None = None,
        apisession: AnkerSolixClientSession | None = None,
    ) -> None:
        """Initialize."""
        super().__init__(
            email=email,
            password=password,
            countryId=countryId,
            websession=websession,
            logger=logger,
            apisession=apisession,
        )

    def testDir(self, subfolder: str | None = None) -> str:
        """Get or set the subfolder for local API test files in the api session."""
        return self.apisession.testDir(subfolder)

    def logLevel(self, level: int | None = None) -> int:
        """Get or set the logger log level."""
        if level is not None and isinstance(level, int):
            self._logger.setLevel(level)
            self._logger.info("Set log level to: %s", level)
        return self._logger.getEffectiveLevel()

    def _update_site(  # noqa: C901
        self,
        siteId: str,
        details: dict,
    ) -> None:
        """Update the internal sites dictionary with data provided for the nested site details dictionary.

        This method is used to consolidate site details from various less frequent requests that are not covered with the update_sites poller method.
        """
        # lookup old site details if any
        if siteId in self.sites:
            site_details = (self.sites[siteId]).get("site_details") or {}
            site_details.update(details)
        else:
            site_details = details
            self.sites[siteId] = {}
        self.sites[siteId]["site_details"] = site_details

    def _update_dev(  # noqa: C901
        self,
        devData: dict,
        devType: str | None = None,
        siteId: str | None = None,
        isAdmin: bool | None = None,
    ) -> str | None:
        """Update the internal device details dictionary with the given data. The device_sn key must be set in the data dict for the update to be applied.

        This method should be implemented to consolidate various device related key values from various requests under a common set of device keys.
        The device SN should be returned if found in devData and an update was done
        """

        if sn := devData.get("device_sn"):
            device: dict = self.devices.get(sn, {})  # lookup old device info if any
            device.update({"device_sn": str(sn)})
            if devType:
                device.update({"type": devType.lower()})
            if siteId:
                device.update({"site_id": str(siteId)})
            if isAdmin:
                device.update({"is_admin": True})
            elif isAdmin is False and device.get("is_admin") is None:
                device.update({"is_admin": False})
            for key, value in devData.items():
                try:
                    #
                    # Implement device update code with key filtering, conversion, consolidation, calculation or dependency updates
                    #
                    if key in ["device_sw_version"] and value:
                        # Example for key name conversion when value is given
                        device.update({"sw_version": str(value)})
                    elif key in [
                        # Examples for boolean key values
                        "wifi_online",
                        "auto_upgrade",
                        "is_ota_update",
                    ]:
                        device.update({key: bool(value)})
                    elif key in [
                        # Example for key with string values
                        "wireless_type",
                        "ota_version",
                    ] or (
                        key
                        in [
                            # Example for key with string values that should only be updated if value returned
                            "wifi_name",
                        ]
                        and value
                    ):
                        device.update({key: str(value)})
                    else:
                        # Example for all other keys not filtered or converted
                        device.update({key: value})

                except Exception as err:  # pylint: disable=broad-exception-caught  # noqa: BLE001
                    self._logger.error(
                        "%s occurred when updating device details for key %s with value %s: %s",
                        type(err),
                        key,
                        value,
                        err,
                    )

            self.devices.update({str(sn): device})
        return sn

    async def update_sites(
        self,
        siteId: str | None = None,
        fromFile: bool = False,
        siteInfo: dict | None = None,
    ) -> dict:  # noqa: C901
        """Create/Update api sites cache structure.

        Implement this method to get the latest info for all power panel sites or only the provided siteId and update class cache dictionaries.
        """
        if siteId and (
            site_info := siteInfo
            or (self.sites.get(siteId) or {}).get("site_info")
            or {}
        ):
            # update only the provided site ID when siteInfo available/provided to avoid another site list query
            self._logger.debug("Updating Power Panel Sites data for site ID %s", siteId)
            new_sites = self.sites
            # prepare the site list dictionary for the update loop by copying the requested site from the cache
            sites: dict = {"site_list": [site_info]}
        else:
            # run normal query to get all power panel sites
            self._logger.debug("Updating Power Panel Sites data")
            new_sites = {}
            self._logger.debug("Getting site list")
            sites = await self.get_site_list(fromFile=fromFile)
            self._site_devices = set()
        for site in sites.get("site_list", []):
            if myid := site.get("site_id"):
                # Update site info
                mysite: dict = self.sites.get(myid, {})
                site_info: dict = mysite.get("site_info", {})
                site_info.update(site)
                # check if power panel site type 4
                if (site_info.get("power_site_type") or 0) in [4]:
                    mysite.update(
                        {"type": SolixDeviceType.SYSTEM.value, "site_info": site_info}
                    )
                    admin = (
                        site_info.get("ms_type", 0) in [0, 1]
                    )  # add boolean key to indicate whether user is site admin (ms_type 1 or not known) and can query device details
                    mysite.update({"site_admin": admin})
                    new_sites.update({myid: mysite})

        # Write back the updated sites
        self.sites = new_sites
        return self.sites

    async def update_site_details(
        self, fromFile: bool = False, exclude: set | None = None
    ) -> dict:
        """Get the latest updates for additional account or site related details updated less frequently.

        Implement this method for site related queries that should be used less frequently.
        Most of theses requests return data only when user has admin rights for sites owning the devices.
        To limit API requests, this update site details method should be called less frequently than update site method,
        and it updates just the nested site_details dictionary in the sites dictionary as well as the account dictionary
        """
        # define excluded categories to skip for queries
        if not exclude or not isinstance(exclude, set):
            exclude = set()
        self._logger.debug("Updating Power Panel Sites Details")
        for site_id, site in self.sites.items():
            # Fetch details that work for all account types
            if {SolixDeviceType.POWERPANEL.value} - exclude:
                self._logger.debug("Getting system running totals information")
                await self.get_system_running_info(siteId=site_id, fromFile=fromFile)
            # Fetch details that only work for site admins
            if site.get("site_admin", False):
                # Add extra power panel site polling that may make sense
                pass

        return self.sites

    async def update_device_energy(
        self, fromFile: bool = False, exclude: set | None = None
    ) -> dict:
        """Get the site energy statistics for given site.

        Implement this method for the required energy query methods to obtain energy data for today and yesterday.
        It was found that energy data is tracked only per site, but not individual devices even if a device SN parameter may be mandatory in the Api request.
        """
        # check exclusion list, default to all energy data
        if not exclude or not isinstance(exclude, set):
            exclude = set()
        query_types: set = {SolixDeviceType.POWERPANEL.value}
        for site_id, site in self.sites.items():
            self._logger.debug("Getting Power Panel energy details for site")
            # obtain previous energy details to check if yesterday must be queried as well
            energy = site.get("energy_details") or {}
            today = datetime.today().strftime("%Y-%m-%d")
            yesterday = (datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d")
            # Fetch energy from today or both days
            data: dict = {}
            if yesterday != (energy.get("last_period") or {}).get("date"):
                data.update(
                    await self.energy_daily(
                        siteId=site_id,
                        startDay=datetime.fromisoformat(yesterday),
                        numDays=1,
                        dayTotals=True,
                        devTypes=query_types,
                        fromFile=fromFile,
                    )
                )
            data.update(
                await self.energy_daily(
                    siteId=site_id,
                    startDay=datetime.fromisoformat(today),
                    numDays=1,
                    dayTotals=True,
                    devTypes=query_types,
                    fromFile=fromFile,
                )
            )
            if fromFile:
                # get last date entries from file and replace date with yesterday and today for testing
                days = len(data)
                if len(data) > 1:
                    entry: dict = list(data.values())[days - 2]
                    entry.update({"date": yesterday})
                    energy["last_period"] = entry
                if len(data) > 0:
                    entry: dict = list(data.values())[days - 1]
                    entry.update({"date": today})
                    energy["today"] = entry
            else:
                energy["today"] = data.get(today) or {}
                if data.get(yesterday):
                    energy["last_period"] = data.get(yesterday) or {}
            # save energy stats with sites dictionary
            site["energy_details"] = energy
            self.sites[site_id] = site
        return self.sites

    async def update_device_details(
        self, fromFile: bool = False, exclude: set | None = None
    ) -> dict:
        """Get the latest updates for additional device info updated less frequently.

        Implement this method for the required query methods to fetch device related data and update the device cache accordingly.
        To limit API requests, this update device details method should be called less frequently than update site method,
        which will also update most device details as found in the site data response.
        """
        # define excluded device types or categories to skip for queries
        if not exclude or not isinstance(exclude, set):
            exclude = set()
        self._logger.debug("Updating Device Details")
        #
        # Implement required queries according to exclusion set
        #

        return self.devices

    async def get_system_running_info(
        self, siteId: str, fromFile: bool = False
    ) -> dict:
        """Get the site running information with tracked total stats.

        Example data:
        {"connect_infos": {"9NKBPG283YESZL5Y": true},"connected": true,"total_system_savings": 310.5,"system_savings_price_unit": "$",
        "save_carbon_footprint": 2.53,"save_carbon_unit": "t","save_carbon_c": 0.997,"total_system_power_generation": 2.54,"system_power_generation_unit": "MWh"}
        """
        data = {"siteId": siteId}
        if fromFile:
            resp = await self.apisession.loadFromFile(
                Path(self.testDir())
                / f"{API_FILEPREFIXES['charging_get_system_running_info']}_{siteId}.json"
            )
        else:
            resp = await self.apisession.request(
                "post", API_CHARGING_ENDPOINTS["get_system_running_info"], json=data
            )
        data = resp.get("data") or {}
        # update sites dict with relevant info and with required structure
        stats = []
        if data and (mysite := self.sites.get(siteId)):
            # create statistics dictionary as used in scene_info for other sites to allow direct replacement
            # Total Energy
            stats.append(
                {
                    "type": "1",
                    "total": str(data.get("total_system_power_generation") or ""),
                    "unit": str(data.get("system_power_generation_unit") or "").lower(),
                }
            )
            # Total carbon
            stats.append(
                {
                    "type": "2",
                    "total": str(data.get("save_carbon_footprint") or ""),
                    "unit": str(data.get("save_carbon_unit") or "").lower(),
                }
            )
            # Total savings
            stats.append(
                {
                    "type": "3",
                    "total": str(data.get("total_system_savings") or ""),
                    "unit": str(data.get("system_savings_price_unit") or ""),
                }
            )
            # Add stats and connect infos to sites cache
            mysite.update(
                {
                    "statistics": stats,
                    "connect_infos": data.get("connect_infos") or {},
                },
            )
            self.sites[siteId] = mysite
        return data

    async def energy_statistics(
        self,
        siteId: str,
        rangeType: str | None = None,
        startDay: datetime | None = None,
        endDay: datetime | None = None,
        sourceType: str | None = None,
        isglobal: bool = False,
        productCode: str = "",
    ) -> dict:
        """Fetch Energy data for given device and optional time frame.

        siteId: site ID of device
        deviceSn: Device to fetch data # This does not really matter since system level data provided, but field is mandatory
        rangeType: "day" | "week" | "year"
        startTime: optional start Date and time
        endTime: optional end Date and time
        devType: "solar" | "hes" | "grid" | "home" | "pps"
        Example Data for solar_production:
        {"totalEnergy": "37.23","totalEnergyUnit": "KWh","totalImportedEnergy": "","totalImportedEnergyUnit": "","totalExportedEnergy": "37.23","totalExportedEnergyUnit": "KWh",
        "power": null,"powerUnit": "","chargeLevel": null,"energy": [
            {"value": "20.55","negValue": "0","rods": [
                {"from": "0.00","to": "20.55","sourceType": "solar"}]},
            {"value": "16.70","negValue": "0","rods": [
                {"from": "0.00","to": "16.70","sourceType": "solar"}]}],
        "energyUnit": "KWh","aggregates": [
            {"title": "Battery charging capacity","value": "26.00","unit": "KWh","type": "hes","percent": "69%","imported": false},
            {"title": "Load power consumption","value": "6.33","unit": "KWh","type": "home","percent": "17%","imported": false},
            {"title": "Sold power","value": "4.90","unit": "KWh","type": "grid","percent": "14%","imported": false}]}

        Responses for solar_production:
        Daily: Solar Energy, Extra Totals: charge, discharge, overall stats (Energy, CO2, Money), 3 x percentage share, solar_to_grid
        Responses for solar_production_pv*:
        Daily: Solar Energy
        Responses for solarbank:
        Daily: Discharge Energy, Extra Totals: charge, discharge, ac_socket, battery_to_home
        Responses for home_usage:
        Daily: Home Usage Energy, Extra Totals: discharge, grid_to_home, battery_to_home, smart_plugs
        Responses for grid:
        Daily: solar_to_grid, grid_to_home, Extra Totals:
        """
        data = {
            "siteId": siteId,
            "sourceType": sourceType
            if sourceType in ["solar", "hes", "home", "grid", "pps"]
            else "solar",
            "dateType": rangeType if rangeType in ["day", "week", "year"] else "day",
            "start": startDay.strftime("%Y-%m-%d")
            if startDay
            else datetime.today().strftime("%Y-%m-%d"),
            "end": endDay.strftime("%Y-%m-%d")
            if endDay
            else datetime.today().strftime("%Y-%m-%d"),
            "global": isglobal,
            "productCode": productCode,
        }
        resp = await self.apisession.request(
            "post", API_CHARGING_ENDPOINTS["energy_statistics"], json=data
        )
        return resp.get("data") or {}

    async def energy_daily(  # noqa: C901
        self,
        siteId: str,
        startDay: datetime = datetime.today(),
        numDays: int = 1,
        dayTotals: bool = False,
        devTypes: set | None = None,
        fromFile: bool = False,
    ) -> dict:
        """Fetch daily Energy data for given interval and provide it in a table format dictionary.

        Solar production data is always queried. Additional energy data will be queried for devtypes 'powerpanel'. The number of
        queries is optimized if dayTotals is True
        Example:
        {"2023-09-29": {"date": "2023-09-29", "solar_production": "1.21", "battery_discharge": "0.47", "battery_charge": "0.56"},
        "2023-09-30": {"date": "2023-09-30", "solar_production": "3.07", "battery_discharge": "1.06", "battery_charge": "1.39"}}
        """  # noqa: D413
        table = {}
        if not devTypes or not isinstance(devTypes, set):
            devTypes = set()
        today = datetime.today()
        # check daily range and limit to 1 year max and avoid future days
        if startDay > today:
            startDay = today
            numDays = 1
        elif (startDay + timedelta(days=numDays)) > today:
            numDays = (today - startDay).days + 1
        numDays = min(366, max(1, numDays))

        # first get HES export
        if SolixDeviceType.POWERPANEL.value in devTypes:
            if fromFile:
                resp = (
                    await self.apisession.loadFromFile(
                        Path(self.testDir())
                        / f"{API_FILEPREFIXES['charging_energy_hes']}_{siteId}.json"
                    )
                ).get("data", {})
            else:
                resp = await self.energy_statistics(
                    siteId=siteId,
                    rangeType="week",
                    startDay=startDay,
                    endDay=startDay + timedelta(days=numDays - 1),
                    sourceType="hes",
                )
            fileNumDays = 0
            fileStartDay = None
            unit = resp.get("energyUnit") or ""
            for item in resp.get("energy") or []:
                # No daystring in response, count the index for proper date
                # daystr = item.get("time", None)
                if daystr := (startDay + timedelta(days=fileNumDays)).strftime(
                    "%Y-%m-%d"
                ):
                    if fromFile and fileStartDay is None:
                        fileStartDay = daystr
                    fileNumDays += 1
                    entry = table.get(daystr, {"date": daystr})
                    entry.update(
                        {
                            "battery_discharge": convertToKwh(
                                val=item.get("value") or None, unit=unit
                            ),
                        }
                    )
                    table.update({daystr: entry})
            # Power Panel HES has total charge energy for given interval. If requested, make daily queries for given interval
            if dayTotals and table:
                if max(numDays, fileNumDays) == 1:
                    if fromFile:
                        daystr = fileStartDay
                    else:
                        daystr = startDay.strftime("%Y-%m-%d")
                    entry = table.get(daystr, {"date": daystr})
                    entry.update(
                        {
                            "battery_charge": convertToKwh(
                                val=resp.get("totalImportedEnergy") or None,
                                unit=resp.get("totalImportedEnergyUnit"),
                            ),
                        }
                    )
                    table.update({daystr: entry})
                else:
                    if fromFile:
                        daylist = [
                            datetime.strptime(fileStartDay, "%Y-%m-%d")
                            + timedelta(days=x)
                            for x in range(fileNumDays)
                        ]
                    else:
                        daylist = [startDay + timedelta(days=x) for x in range(numDays)]
                    for day in daylist:
                        daystr = day.strftime("%Y-%m-%d")
                        # update response only for real requests
                        if not fromFile:
                            resp = await self.energy_statistics(
                                siteId=siteId,
                                rangeType="week",
                                startDay=day,
                                endDay=day,
                                sourceType="hes",
                            )
                        entry = table.get(daystr, {"date": daystr})
                        entry.update(
                            {
                                "battery_charge": convertToKwh(
                                    val=resp.get("totalImportedEnergy") or None,
                                    unit=resp.get("totalImportedEnergyUnit"),
                                ),
                            }
                        )
                        table.update({daystr: entry})

        # Get home usage energy types
        if SolixDeviceType.POWERPANEL.value in devTypes:
            if fromFile:
                resp = (
                    await self.apisession.loadFromFile(
                        Path(self.testDir())
                        / f"{API_FILEPREFIXES['charging_energy_home']}_{siteId}.json"
                    )
                ).get("data", {})
            else:
                resp = await self.energy_statistics(
                    siteId=siteId,
                    rangeType="week",
                    startDay=startDay,
                    endDay=startDay + timedelta(days=numDays - 1),
                    sourceType="home",
                )
            fileNumDays = 0
            fileStartDay = None
            unit = resp.get("energyUnit") or ""
            for item in resp.get("energy") or []:
                # No daystring in response, count the index for proper date
                # daystr = item.get("time", None)
                if daystr := (startDay + timedelta(days=fileNumDays)).strftime(
                    "%Y-%m-%d"
                ):
                    if fromFile and fileStartDay is None:
                        fileStartDay = daystr
                    fileNumDays += 1
                    entry = table.get(daystr, {"date": daystr})
                    entry.update(
                        {
                            "home_usage": convertToKwh(
                                val=item.get("value") or None, unit=unit
                            ),
                        }
                    )
                    table.update({daystr: entry})
            # Home has consumption breakdown and shares for given interval. If requested, make daily queries for given interval
            if dayTotals and table:
                if max(numDays, fileNumDays) == 1:
                    if fromFile:
                        daystr = fileStartDay
                    else:
                        daystr = startDay.strftime("%Y-%m-%d")
                    entry = table.get(daystr, {"date": daystr})
                    for item in resp.get("aggregates") or []:
                        itemtype = str(item.get("type") or "").lower()
                        if itemtype == "hes":
                            if (
                                percent := str(item.get("percent") or "").replace(
                                    "%", ""
                                )
                            ) and percent.isdigit():
                                percent = str(float(percent) / 100)
                            entry.update(
                                {
                                    "battery_to_home": convertToKwh(
                                        val=item.get("value") or None,
                                        unit=item.get("unit"),
                                    ),
                                    "battery_percentage": percent,
                                }
                            )
                        elif itemtype == "solar":
                            if (
                                percent := str(item.get("percent") or "").replace(
                                    "%", ""
                                )
                            ) and percent.isdigit():
                                percent = str(float(percent) / 100)
                            entry.update(
                                {
                                    "solar_to_home": convertToKwh(
                                        val=item.get("value") or None,
                                        unit=item.get("unit"),
                                    ),
                                    "solar_percentage": percent,
                                }
                            )
                        elif itemtype == "grid":
                            if (
                                percent := str(item.get("percent") or "").replace(
                                    "%", ""
                                )
                            ) and percent.isdigit():
                                percent = str(float(percent) / 100)
                            entry.update(
                                {
                                    "grid_to_home": convertToKwh(
                                        val=item.get("value") or None,
                                        unit=item.get("unit"),
                                    ),
                                    "other_percentage": percent,
                                }
                            )
                    table.update({daystr: entry})
                else:
                    if fromFile:
                        daylist = [
                            datetime.strptime(fileStartDay, "%Y-%m-%d")
                            + timedelta(days=x)
                            for x in range(fileNumDays)
                        ]
                    else:
                        daylist = [startDay + timedelta(days=x) for x in range(numDays)]
                    for day in daylist:
                        daystr = day.strftime("%Y-%m-%d")
                        # update response only for real requests
                        if not fromFile:
                            resp = await self.energy_statistics(
                                siteId=siteId,
                                rangeType="week",
                                startDay=day,
                                endDay=day,
                                sourceType="home",
                            )
                        entry = table.get(daystr, {"date": daystr})
                        for item in resp.get("aggregates") or []:
                            itemtype = str(item.get("type") or "").lower()
                            if itemtype == "hes":
                                if (
                                    percent := str(item.get("percent") or "").replace(
                                        "%", ""
                                    )
                                ) and percent.isdigit():
                                    percent = str(float(percent) / 100)
                                entry.update(
                                    {
                                        "battery_to_home": convertToKwh(
                                            val=item.get("value") or None,
                                            unit=item.get("unit"),
                                        ),
                                        "battery_percentage": percent,
                                    }
                                )
                            elif itemtype == "solar":
                                if (
                                    percent := str(item.get("percent") or "").replace(
                                        "%", ""
                                    )
                                ) and percent.isdigit():
                                    percent = str(float(percent) / 100)
                                entry.update(
                                    {
                                        "solar_to_home": convertToKwh(
                                            val=item.get("value") or None,
                                            unit=item.get("unit"),
                                        ),
                                        "solar_percentage": percent,
                                    }
                                )
                            elif itemtype == "grid":
                                if (
                                    percent := str(item.get("percent") or "").replace(
                                        "%", ""
                                    )
                                ) and percent.isdigit():
                                    percent = str(float(percent) / 100)
                                entry.update(
                                    {
                                        "grid_to_home": convertToKwh(
                                            val=item.get("value") or None,
                                            unit=item.get("unit"),
                                        ),
                                        "other_percentage": percent,
                                    }
                                )
                        table.update({daystr: entry})

        # Add grid import, totals contain export and battery charging from grid for given interval
        if SolixDeviceType.POWERPANEL.value in devTypes:
            if fromFile:
                resp = (
                    await self.apisession.loadFromFile(
                        Path(self.testDir())
                        / f"{API_FILEPREFIXES['charging_energy_grid']}_{siteId}.json"
                    )
                ).get("data", {})
            else:
                resp = await self.energy_statistics(
                    siteId=siteId,
                    rangeType="week",
                    startDay=startDay,
                    endDay=startDay + timedelta(days=numDays - 1),
                    sourceType="grid",
                )
            fileNumDays = 0
            fileStartDay = None
            unit = resp.get("energyUnit") or ""
            for item in resp.get("energy") or []:
                # No daystring in response, count the index for proper date
                # daystr = item.get("time", None)
                if daystr := (startDay + timedelta(days=fileNumDays)).strftime(
                    "%Y-%m-%d"
                ):
                    if fromFile and fileStartDay is None:
                        fileStartDay = daystr
                    fileNumDays += 1
                    entry = table.get(daystr, {"date": daystr})
                    entry.update(
                        {
                            "grid_import": convertToKwh(
                                val=item.get("value") or None, unit=unit
                            ),
                        }
                    )
                    table.update({daystr: entry})
            # Grid import and battery charge from grid totals for given interval. If requested, make daily queries for given interval
            if dayTotals and table:
                if max(numDays, fileNumDays) == 1:
                    if fromFile:
                        daystr = fileStartDay
                    else:
                        daystr = startDay.strftime("%Y-%m-%d")
                    entry = table.get(daystr, {"date": daystr})
                    entry.update(
                        {
                            "solar_to_grid": convertToKwh(
                                val=resp.get("totalExportedEnergy") or None,
                                unit=resp.get("totalExportedEnergyUnit"),
                            ),
                        }
                    )
                    for item in resp.get("aggregates") or []:
                        itemtype = str(item.get("type") or "").lower()
                        if itemtype == "hes":
                            entry.update(
                                {
                                    "grid_to_battery": convertToKwh(
                                        val=item.get("value") or None,
                                        unit=item.get("unit"),
                                    ),
                                }
                            )
                    table.update({daystr: entry})
                else:
                    if fromFile:
                        daylist = [
                            datetime.strptime(fileStartDay, "%Y-%m-%d")
                            + timedelta(days=x)
                            for x in range(fileNumDays)
                        ]
                    else:
                        daylist = [startDay + timedelta(days=x) for x in range(numDays)]
                    for day in daylist:
                        daystr = day.strftime("%Y-%m-%d")
                        # update response only for real requests
                        if not fromFile:
                            resp = await self.energy_statistics(
                                siteId=siteId,
                                rangeType="week",
                                startDay=day,
                                endDay=day,
                                sourceType="home",
                            )
                        entry = table.get(daystr, {"date": daystr})
                        entry.update(
                            {
                                "solar_to_grid": convertToKwh(
                                    val=resp.get("totalExportedEnergy") or None,
                                    unit=resp.get("totalExportedEnergyUnit"),
                                ),
                            }
                        )
                        for item in resp.get("aggregates") or []:
                            itemtype = str(item.get("type") or "").lower()
                            if itemtype == "hes":
                                entry.update(
                                    {
                                        "grid_to_battery": convertToKwh(
                                            val=item.get("value") or None,
                                            unit=item.get("unit"),
                                        ),
                                    }
                                )
                        table.update({daystr: entry})

        # Always Add solar production which contains percentages
        if fromFile:
            resp = (
                await self.apisession.loadFromFile(
                    Path(self.testDir())
                    / f"{API_FILEPREFIXES['charging_energy_solar']}_{siteId}.json"
                )
            ).get("data", {})
        else:
            resp = await self.energy_statistics(
                siteId=siteId,
                rangeType="week",
                startDay=startDay,
                endDay=startDay + timedelta(days=numDays - 1),
                sourceType="solar",
            )
        fileNumDays = 0
        fileStartDay = None
        unit = resp.get("energyUnit") or ""
        for item in resp.get("energy") or []:
            # No daystring in response, count the index for proper date
            # daystr = item.get("time", None)
            if daystr := (startDay + timedelta(days=fileNumDays)).strftime("%Y-%m-%d"):
                if fromFile and fileStartDay is None:
                    fileStartDay = daystr
                fileNumDays += 1
                entry = table.get(daystr, {"date": daystr})
                entry.update(
                    {
                        "solar_production": convertToKwh(
                            val=item.get("value") or None, unit=unit
                        ),
                    }
                )
                table.update({daystr: entry})
        # Solar charge and is only received as total value for given interval. If requested, make daily queries for given interval
        if dayTotals and table:
            if max(numDays, fileNumDays) == 1:
                if fromFile:
                    daystr = fileStartDay
                else:
                    daystr = startDay.strftime("%Y-%m-%d")
                entry = table.get(daystr, {"date": daystr})
                for item in resp.get("aggregates") or []:
                    itemtype = str(item.get("type") or "").lower()
                    if itemtype == "hes":
                        entry.update(
                            {
                                "solar_to_battery": convertToKwh(
                                    val=item.get("value") or None,
                                    unit=item.get("unit"),
                                ),
                            }
                        )
                table.update({daystr: entry})
            else:
                if fromFile:
                    daylist = [
                        datetime.strptime(fileStartDay, "%Y-%m-%d") + timedelta(days=x)
                        for x in range(fileNumDays)
                    ]
                else:
                    daylist = [startDay + timedelta(days=x) for x in range(numDays)]
                for day in daylist:
                    daystr = day.strftime("%Y-%m-%d")
                    # update response only for real requests
                    if not fromFile:
                        resp = await self.energy_statistics(
                            siteId=siteId,
                            rangeType="week",
                            startDay=day,
                            endDay=day,
                            sourceType="solar",
                        )
                    entry = table.get(daystr, {"date": daystr})
                    for item in resp.get("aggregates") or []:
                        itemtype = str(item.get("type") or "").lower()
                        if itemtype == "hes":
                            entry.update(
                                {
                                    "solar_to_battery": convertToKwh(
                                        val=item.get("value") or None,
                                        unit=item.get("unit"),
                                    ),
                                }
                            )
                    table.update({daystr: entry})
        return table
