"""Anker Power/Solix Cloud API class vehicle related methods."""

from datetime import datetime
from pathlib import Path
import random
import string

from .apitypes import API_ENDPOINTS, API_FILEPREFIXES, SolixDeviceType, SolixVehicle


async def get_vehicle_list(
    self,
    fromFile: bool = False,
) -> dict:
    """Get the vehicle list defined for the user.

    Example data:
    {"vehicle_list": [{
        "vehicle_id": "0734d28a-dd37-41fe-b2f4-f49d8e48e2b9","vehicle_name": "MyCar","brand": "Audi","model": "e-tron GT RS","productive_year": 2024,
        "is_default_vehicle": true,"is_smart_charging": false,"is_connected_to_enodeapi": false,"battery_capacity": 97,"update_time": 1753884935}]}
    """
    data = {}
    if fromFile:
        # For file data, verify first if there is a modified file to be used for testing
        if not (
            resp := await self.apisession.loadFromFile(
                Path(self.testDir())
                / f"{API_FILEPREFIXES['get_user_vehicles']}_modified.json"
            )
        ):
            resp = await self.apisession.loadFromFile(
                Path(self.testDir()) / f"{API_FILEPREFIXES['get_user_vehicles']}.json"
            )
    else:
        resp = await self.apisession.request(
            "post", API_ENDPOINTS["get_user_vehicles"], json=data
        )
    data = resp.get("data") or {}
    # update account details with curated list of vehicle details
    old_vehicles = self.account.get("vehicles") or {}
    vehicles = {}
    for vehicle in data.get("vehicle_list") or []:
        if vehicle_id := vehicle.get("vehicle_id"):
            vehicles[vehicle_id] = (
                (old_vehicles.get(vehicle_id) or {})
                | {"type": SolixDeviceType.VEHICLE.value}
                | vehicle
            )
    self._update_account({"vehicles": vehicles})
    # check if vehicles are registered, then used vehicle options should be loaded to cache
    if "vehicles_registered" in self.account:
        registered = self.account.get("vehicles_registered") or []
        for vid, vehicle in vehicles.items():
            if vid not in registered:
                await self.update_vehicle_options(vehicle=vehicle, fromFile=fromFile)
        self.account["vehicles_registered"] = list(vehicles.keys())
    return data


async def get_vehicle_details(
    self,
    vehicleId: str,
    fromFile: bool = False,
) -> dict:
    """Get the vehicle details for defined ID.

    Example data:
    {"vehicle_id": "0734d28a-dd37-41fe-b2f4-f49d8e48e2b9","vehicle_name": "MyCar","brand": "Audi","model": "e-tron GT RS","productive_year": 2024,"is_default_vehicle": true,
    "is_smart_charging": false,"is_connected_to_enodeapi": false,"update_time": 1753884935,"battery_capacity": 97,"ac_max_charging_power": 11,"energy_consumption_per_100km": 18.5}
    """
    vehicleId = str(vehicleId) or ""
    data = {"vehicle_id": vehicleId}
    if fromFile:
        # For file data, verify first if there is a modified file to be used for testing
        if not (
            resp := await self.apisession.loadFromFile(
                Path(self.testDir())
                / f"{API_FILEPREFIXES['get_user_vehicle_details']}_modified_{vehicleId}.json"
            )
        ):
            resp = await self.apisession.loadFromFile(
                Path(self.testDir())
                / f"{API_FILEPREFIXES['get_user_vehicle_details']}_{vehicleId}.json"
            )
    else:
        resp = await self.apisession.request(
            "post", API_ENDPOINTS["get_user_vehicle_details"], json=data
        )
    data = resp.get("data") or {}
    # update account details with vehicle details
    if vehicleId := data.get("vehicle_id"):
        vehicles = self.account.get("vehicles") or {}
        vehicle = vehicles.get(vehicleId) or {}
        # check if model id must be updated because other values have changed
        check_id = SolixVehicle(vehicle=vehicle | {"model_id": ""}) != SolixVehicle(
            vehicle=data
        )
        # update vehicle details
        vehicle = vehicle | {"type": SolixDeviceType.VEHICLE.value} | data
        # check if vehicle is registered
        if "vehicles_registered" in self.account:
            # used vehicle options should be loaded to cache
            if vehicleId not in (registered := self.account["vehicles_registered"]):
                await self.update_vehicle_options(vehicle=vehicle, fromFile=fromFile)
                registered.append(vehicleId)
            # try to find model id from loaded options in cache
            if check_id and (
                v := await self.get_vehicle_attributes(
                    vehicle=vehicle, fromFile=fromFile
                )
            ):
                vehicle["model_id"] = v.model_id
        # add updated vehicle data to cache
        self._update_account({"vehicles": vehicles | {vehicleId: vehicle}})
    return data


async def get_brand_list(
    self,
    fromFile: bool = False,
) -> dict:
    """Get the vehicle brand list.

    Example data:
    {"brand_list": ["Abarth","Aiways","Alfa Romeo","Alpine","Audi","BMW",...,"XPENG","Zeekr"]}
    """
    data = {}
    if fromFile:
        resp = await self.apisession.loadFromFile(
            Path(self.testDir()) / f"{API_FILEPREFIXES['get_vehicle_brands']}.json"
        )
    else:
        resp = await self.apisession.request(
            "post", API_ENDPOINTS["get_vehicle_brands"], json=data
        )
    data = resp.get("data") or {}
    # update account details with brand details
    old = self.account.get("vehicle_brands") or {}
    new = {}
    for item in data.get("brand_list") or []:
        new[item] = old.get(item) or {}
    self._update_account({"vehicle_brands": new | {"cached": True}})
    return data


async def get_brand_models(
    self,
    brand: str,
    fromFile: bool = False,
) -> dict:
    """Get the vehicle model list for give brand.

    Example data:
    {"model_list": ["i3 120 Ah","i3 60 Ah",...,"iX2 xDrive30","iX3"]}
    """
    brand = str(brand) or ""
    data = {"brand_name": brand}
    if fromFile:
        resp = await self.apisession.loadFromFile(
            Path(self.testDir())
            / f"{API_FILEPREFIXES['get_vehicle_brand_models']}_{brand.replace(' ', '_')}.json"
        )
    else:
        resp = await self.apisession.request(
            "post", API_ENDPOINTS["get_vehicle_brand_models"], json=data
        )
    data = resp.get("data") or {}
    # update account details with brand details
    if brand:
        oldroot = self.account.get("vehicle_brands") or {}
        old = oldroot.get(brand) or {}
        new = {}
        for item in data.get("model_list") or []:
            new[item] = old.get(item) or {}
        oldroot[brand] = new | {"cached": True}
        self._update_account({"vehicle_brands": oldroot})
    return data


async def get_model_years(
    self,
    brand: str,
    model: str,
    fromFile: bool = False,
) -> dict:
    """Get the vehicle model list for give brand.

    Example data:
    {"year_list": [2020,2021,2022,2023,2024]}
    """
    brand = str(brand) or ""
    model = str(model) or ""
    data = {"brand_name": brand, "model_name": model}
    if fromFile:
        resp = await self.apisession.loadFromFile(
            Path(self.testDir())
            / f"{API_FILEPREFIXES['get_vehicle_model_years']}_{brand.replace(' ', '_')}_{model.replace(' ', '_')}.json"
        )
    else:
        resp = await self.apisession.request(
            "post", API_ENDPOINTS["get_vehicle_model_years"], json=data
        )
    data = resp.get("data") or {}
    # update account details with model years
    if brand and model:
        oldroot = self.account.get("vehicle_brands") or {}
        old = (oldroot.get(brand) or {}).get(model) or {}
        new = {}
        for item in data.get("year_list") or []:
            new[str(item)] = old.get(str(item)) or {}
        oldroot[brand] = oldroot.get(brand) or {}
        oldroot[brand][model] = new | {"cached": True}
        self._update_account({"vehicle_brands": oldroot})
    return data


async def get_model_year_attributes(
    self,
    brand: str,
    model: str,
    year: str | int,
    fromFile: bool = False,
) -> dict:
    """Get the vehicle model list for give brand.

    Example data:
    {"car_model_list": [{"id": 100211,"brand_name": "BMW","model_name": "iX3","productive_year": 2023,"battery_capacity": 74,"ac_max_power": 11,"hundred_fuel_consumption": 19.2}]}
    """
    brand = str(brand) or ""
    model = str(model) or ""
    if not (year := int(year) if str(year).isdigit() else ""):
        return {}
    data = {"brand_name": brand, "model_name": model, "productive_year": year}
    if fromFile:
        resp = await self.apisession.loadFromFile(
            Path(self.testDir())
            / f"{API_FILEPREFIXES['get_vehicle_year_attributes']}_{brand.replace(' ', '_')}_{model.replace(' ', '_')}_{year!s}.json"
        )
    else:
        resp = await self.apisession.request(
            "post", API_ENDPOINTS["get_vehicle_year_attributes"], json=data
        )
    data = resp.get("data") or {}
    # update account details with model years
    if brand and model and year:
        oldroot = self.account.get("vehicle_brands") or {}
        old = ((oldroot.get(brand) or {}).get(model) or {}).get(str(year)) or {}
        new = {}
        for item in data.get("car_model_list") or []:
            mid = str(item.get("id") or "")
            new[mid] = (old.get(mid) or {}) | item
        oldroot[brand] = oldroot.get(brand) or {}
        oldroot[brand][model] = oldroot[brand].get(model) or {}
        oldroot[brand][model][str(year)] = new | {"cached": True}
        self._update_account({"vehicle_brands": oldroot})
    return data


async def update_vehicle_options(
    self,
    vehicle: SolixVehicle | str | dict | None = None,
    cacheChain: bool = True,
    fromFile: bool = False,
) -> list:
    """Optionally update and get the vehicle options for selection of parent option in the order brands -> brand models -> model years -> model IDs.

    Example data for brand model options:
    ["i3 120 Ah","i3 60 Ah",...,"iX2 xDrive30","iX3"]
    """
    options = []
    # validate parameters
    if not (
        vehicle := (
            vehicle
            if isinstance(vehicle, SolixVehicle)
            else SolixVehicle(vehicle=vehicle)
            if isinstance(vehicle, str | dict | None)
            else None
        )
    ):
        return options
    if (vehicle.productive_year and not vehicle.model) or (
        vehicle.model and not vehicle.brand
    ):
        return options
    if (cacheChain or not vehicle.brand) and "cached" not in (
        self.account.get("vehicle_brands") or {}
    ):
        # load brand options to cache
        await self.get_brand_list(fromFile=fromFile)
    if vehicle.brand and vehicle.brand in (
        brands := self.account.get("vehicle_brands") or {}
    ):
        if (cacheChain or not vehicle.model) and "cached" not in (
            brands.get(vehicle.brand) or {}
        ):
            # load model options to cache
            await self.get_brand_models(brand=vehicle.brand, fromFile=fromFile)
        if vehicle.model and vehicle.model in (
            models := brands.get(vehicle.brand) or {}
        ):
            if (cacheChain or not vehicle.productive_year) and "cached" not in (
                models.get(vehicle.model) or {}
            ):
                # get year options
                await self.get_model_years(
                    brand=vehicle.brand, model=vehicle.model, fromFile=fromFile
                )
            if vehicle.productive_year and str(vehicle.productive_year) in (
                years := models.get(vehicle.model) or {}
            ):
                # get year attribute options if not cached already
                if "cached" not in (years.get(str(vehicle.productive_year)) or {}):
                    await self.get_model_year_attributes(
                        brand=vehicle.brand,
                        model=vehicle.model,
                        year=vehicle.productive_year,
                        fromFile=fromFile,
                    )
    # get requested options from cache
    return self.get_vehicle_options(vehicle=vehicle)


def get_vehicle_options(
    self,
    vehicle: SolixVehicle | str | dict | None = None,
    extendAttributes: bool = False,
) -> list:
    """Get the vehicle options from cache for selection of parent options in the order brands -> brand models -> model years -> model IDs with attributes.

    If extendAttributes = True, the model IDs will be extended with some attributes
    Example data for brand model options:
    ["i3 120 Ah","i3 60 Ah",...,"iX2 xDrive30","iX3"]
    """
    options = set()
    # validate parameters
    if not (
        vehicle := (
            vehicle
            if isinstance(vehicle, SolixVehicle)
            else SolixVehicle(vehicle=vehicle)
            if isinstance(vehicle, str | dict | None)
            else None
        )
    ):
        return list(options)
    if (vehicle.productive_year and not vehicle.model) or (
        vehicle.model and not vehicle.brand
    ):
        return list(options)
    if vehicle.brand:
        if vehicle.model:
            if vehicle.productive_year:
                # get year attribute options
                model_ids = (
                    (
                        (self.account.get("vehicle_brands") or {}).get(vehicle.brand)
                        or {}
                    ).get(vehicle.model)
                    or {}
                ).get(str(vehicle.productive_year)) or {}
                if extendAttributes:
                    options = {
                        SolixVehicle(vehicle=value).idAttributes()
                        for key, value in model_ids.items()
                        if key != "cached"
                    }
                else:
                    options = set(model_ids.keys())
            else:
                # get year options
                options = set(
                    (
                        (
                            (self.account.get("vehicle_brands") or {}).get(
                                vehicle.brand
                            )
                            or {}
                        ).get(vehicle.model)
                        or {}
                    ).keys()
                )
        else:
            # get model options
            options = set(
                (
                    (self.account.get("vehicle_brands") or {}).get(vehicle.brand) or {}
                ).keys()
            )
    else:
        # get brand options
        options = set((self.account.get("vehicle_brands") or {}).keys())
    # Remove optional cache flag from list
    options.discard("cached")
    return list(options)


async def get_vehicle_attributes(
    self,
    vehicle: SolixVehicle | str | dict | None = None,
    fromFile: bool = False,
) -> SolixVehicle | None:
    """Get the vehicle model ID and attributes from cache or refresh for provided vehicle details."""
    # validate parameters
    if not (
        vehicle := (
            vehicle
            if isinstance(vehicle, SolixVehicle)
            else SolixVehicle(vehicle=vehicle)
            if isinstance(vehicle, str | dict | None)
            else None
        )
    ):
        return None
    # try lookup only if required details provided
    attributes = {}
    if vehicle.brand and vehicle.model and vehicle.productive_year:
        # get year options with optional cache update and filter best match
        for option in [
            self.account["vehicle_brands"][vehicle.brand][vehicle.model][
                str(vehicle.productive_year)
            ][str(o)]
            for o in await self.update_vehicle_options(
                vehicle=vehicle,
                fromFile=fromFile,
            )
        ]:
            if (
                not attributes
                or option.get("id") == vehicle.model_id
                or (
                    not vehicle.model_id
                    and (
                        option.get("battery_capacity") == vehicle.battery_capacity
                        or (
                            attributes.get("battery_capacity")
                            != vehicle.battery_capacity
                            and (
                                option.get("ac_max_power")
                                == vehicle.ac_max_charging_power
                                or (
                                    attributes.get("ac_max_power")
                                    != vehicle.ac_max_charging_power
                                    and option.get("hundred_fuel_consumption")
                                    == vehicle.energy_consumption_per_100km
                                )
                            )
                        )
                    )
                )
            ):
                attributes = option
    return SolixVehicle(vehicle=attributes) if attributes else None


async def create_vehicle(
    self,
    name: str,
    vehicle: SolixVehicle | str | dict | None,
    toFile: bool = False,
) -> bool | dict:
    """Create a new vehicle for the user account (max. 5 vehicles allowed).

    - name is the required user name for the vehicle (it must not exist yet)
    - vehicle is a SolixVehicle instance or a representation of it, including attributes like brand, model, productive_year, id of model,
      battery_capacity in kWh, ac_max_charging_power in kW and energy_consumption_per_100km in kWh
    - toFile will just create a vehicle file with random vehicle ID

    Example payloads for query:
    {"user_vehicle_info": [{"vehicle_name": "MyCar","brand": "Audi","model": "e-tron GT RS","productive_year": 2024}]}
    {"user_vehicle_info": [{"vehicle_name": "My 5th Car","brand": "Audi","model": "e-tron GT RS","productive_year": 2021, "battery_capacity": 10, "ac_max_charging_power": 11, "energy_consumption_per_100km": 17.5}]}
    """
    # validate parameters, all except name are optional
    if not (name := str(name) if name else None):
        return False
    # check if limit of 5 not exceeded and name does not exist yet
    if "vehicles" not in self.account:
        await self.get_vehicle_list(fromFile=toFile)
    if (vehicles := self.account.get("vehicles") or {}) and (
        len(vehicles) >= 5
        or [v for v in vehicles.values() if v.get("vehicle_name") == name]
    ):
        return False
    vehicle = (
        vehicle if isinstance(vehicle, SolixVehicle) else SolixVehicle(vehicle=vehicle)
    )
    # try lookup for missing attributes prior creation
    if (
        not vehicle.battery_capacity
        or not vehicle.ac_max_charging_power
        or not vehicle.energy_consumption_per_100km
    ):
        # get year options with optional cache update and filter best match
        if v := await self.get_vehicle_attributes(vehicle=vehicle, fromFile=toFile):
            vehicle = v
    if toFile:
        # generate random vehicle ID
        id_temp = "70d8e951-c4dc-53ea-f35b-0bbfeee44ddc"
        randomstr = ""
        for part in id_temp.split("-"):
            if randomstr:
                randomstr = "-".join(
                    [
                        randomstr,
                        "".join(random.choices(string.hexdigits.lower(), k=len(part))),
                    ]
                )
            else:
                randomstr = "".join(
                    random.choices(string.hexdigits.lower(), k=len(part))
                )
        # common data content for list and details with random attributes
        data = {
            "vehicle_id": randomstr,
            "vehicle_name": name,
            "brand": vehicle.brand,
            "model": vehicle.model,
            "productive_year": vehicle.productive_year
            or random.randrange(datetime.now().year - 4, datetime.now().year),
            "is_default_vehicle": not bool(self.account.get("vehicles")),
            "is_smart_charging": False,
            "is_connected_to_enodeapi": False,
            "update_time": int(datetime.now().timestamp()),
            "battery_capacity": random.randrange(60, 91),
        }
        # Write created vehicle details to file for testing purposes
        if not await self.apisession.saveToFile(
            Path(self.testDir())
            / f"{API_FILEPREFIXES['get_user_vehicle_details']}_modified_{randomstr}.json",
            data={
                "code": 0,
                "msg": "success!",
                "data": data
                | {
                    "ac_max_charging_power": 11,
                    "energy_consumption_per_100km": round(
                        random.randrange(175, 191) / 10, 1
                    ),
                },
            },
        ):
            return False
        # add vehicle also to list file
        if filedata := await self.get_vehicle_list(fromFile=toFile):
            # Write created vehicle details to file for testing purposes
            vehicles = filedata.get("vehicle_list") or []
            vehicles.append(data)
            if not await self.apisession.saveToFile(
                Path(self.testDir())
                / f"{API_FILEPREFIXES['get_user_vehicles']}_modified.json",
                data={
                    "code": 0,
                    "msg": "success!",
                    "data": {"vehicle_list": vehicles},
                },
            ):
                return False
    else:
        data = {
            "user_vehicle_info": [
                {
                    "vehicle_name": name,
                }
                | vehicle.asdict(skip_empty=True)
            ]
        }
        code = (
            await self.apisession.request(
                "post", API_ENDPOINTS["vehicle_add"], json=data
            )
        ).get("code")
        if not isinstance(code, int) or int(code) != 0:
            return False
    # update the data in api dict and return active data
    response = {}
    for v in [
        v
        for v in (
            (await self.get_vehicle_list(fromFile=toFile)).get("vehicle_list") or [{}]
        )
        if v.get("vehicle_name") == name
    ]:
        vehicleId = v.get("vehicle_id")
        response = await self.get_vehicle_details(vehicleId=vehicleId, fromFile=toFile)
        # check if vehicle is registered, then used vehicle options should be loaded to cache
        if (
            "vehicles_registered" in self.account
            and vehicleId
            and vehicleId not in (registered := self.account["vehicles_registered"])
        ):
            await self.update_vehicle_options(vehicle=vehicle, fromFile=toFile)
            registered.append(vehicleId)
    return response


async def manage_vehicle(  # noqa: C901
    self,
    vehicleId: str,
    action: str,
    vehicle: SolixVehicle | str | dict | None = None,
    chargeOrder: dict[str, str | int] | None = None,
    toFile: bool = False,
) -> bool | dict:
    """Manage an existing vehicle of the user account. Every vehicle attribute except the name can be updated.

    - vehicleId is the ID of the vehicle to manage
    - action is either update, restore, setdefault, setcharge, or delete
    - vehicle is a SolixVehicle instance or a representation of it, including attributes like brand, model, productive_year, id of model,
      battery_capacity in kWh, ac_max_charging_power in kW and energy_consumption_per_100km in kWh
    - chargeOrder({'device_sn': deviceSn, 'transaction_id': transactionId}) will set defined transactionId to deviceSn, which is the EV charger device
    - toFile will just work locally on files for test purpose
    """
    # validate parameters
    vehicleId = (
        str(vehicleId)
        if str(vehicleId) in (vehicles := self.account.get("vehicles") or {})
        else None
    )
    action = (
        action.lower()
        if action.lower() in ["setdefault", "setcharge", "update", "restore", "delete"]
        else None
    )
    vehicle = (
        vehicle if isinstance(vehicle, SolixVehicle) else SolixVehicle(vehicle=vehicle)
    )
    chargeOrder = (
        chargeOrder
        if isinstance(chargeOrder, dict)
        and chargeOrder.get("device_sn")
        and "transaction_id" in chargeOrder
        else None
    )
    if not (action and vehicleId) or (action == "setcharge" and not chargeOrder):
        return False
    old_vehicle = vehicles.pop(vehicleId, {})
    data = {"vehicle_id": vehicleId}
    filedata = {}
    if action == "delete":
        if toFile:
            # Delete modified vehicle file for testing purposes
            if not await self.apisession.deleteModifiedFile(
                Path(self.testDir())
                / f"{API_FILEPREFIXES['get_user_vehicle_details']}_modified_{vehicleId}.json"
            ):
                return False
            # prepare removal of vehicle also in modified list file
            if filedata := filedata or await self.get_vehicle_list(fromFile=toFile):
                new_list = [
                    v
                    for v in (filedata.get("vehicle_list") or [])
                    if v.get("vehicle_id") != vehicleId
                ]
                # set first vehicle default if deleted was default
                if old_vehicle.get("is_default_vehicle") and len(new_list) > 0:
                    new_list[0]["is_default_vehicle"] = True
                filedata["vehicle_list"] = new_list
        else:
            code = (
                await self.apisession.request(
                    "post", API_ENDPOINTS["vehicle_delete"], json=data
                )
            ).get("code")
            if not isinstance(code, int) or int(code) != 0:
                return False
        # check if vehicle is registered, then remove it from list
        if vehicleId in (registered := self.account.get("vehicles_registered") or []):
            self.account["vehicles_registered"] = [
                v for v in registered if v != vehicleId
            ]
    elif action == "setdefault":
        # set the vehicle as default
        if toFile:
            # Write updated vehicle to file for testing purposes
            if not await self.apisession.saveToFile(
                Path(self.testDir())
                / f"{API_FILEPREFIXES['get_user_vehicle_details']}_modified_{vehicleId}.json",
                data={
                    "code": 0,
                    "msg": "success!",
                    "data": old_vehicle
                    | {
                        "is_default_vehicle": True,
                        "update_time": int(datetime.now().timestamp()),
                    },
                },
            ):
                return False
            # prepare filedata to update vehicle also in modified list file
            if filedata := filedata or await self.get_vehicle_list(fromFile=toFile):
                # make sure only one vehicle is marked default in list file
                for v in filedata.get("vehicle_list") or []:
                    if (default := v.get("vehicle_id") == vehicleId) != v.get(
                        "is_default_vehicle"
                    ):
                        v.update(
                            {
                                "is_default_vehicle": default,
                                "update_time": int(datetime.now().timestamp()),
                            }
                        )
                        # update also other vehicle details file
                        if not default:
                            otherid = v.get("vehicle_id") or ""
                            await self.apisession.saveToFile(
                                Path(self.testDir())
                                / f"{API_FILEPREFIXES['get_user_vehicle_details']}_modified_{otherid}.json",
                                data={
                                    "code": 0,
                                    "msg": "success!",
                                    "data": (vehicles.get(otherid) or {})
                                    | {
                                        "is_default_vehicle": False,
                                        "update_time": int(datetime.now().timestamp()),
                                    },
                                },
                            )
        else:
            code = (
                await self.apisession.request(
                    "post", API_ENDPOINTS["vehicle_set_default"], json=data
                )
            ).get("code")
            if not isinstance(code, int) or int(code) != 0:
                return False
    elif action == "setcharge":
        # set the charge order for the vehicle
        data.update(chargeOrder)
        if toFile:
            # Write updated vehicle to file, for testing purposes indicate charging for transaction ID != 0
            if not await self.apisession.saveToFile(
                Path(self.testDir())
                / f"{API_FILEPREFIXES['get_user_vehicle_details']}_modified_{vehicleId}.json",
                data={
                    "code": 0,
                    "msg": "success!",
                    "data": old_vehicle
                    | {
                        "is_smart_charging": bool(chargeOrder.get("transaction_ id")),
                        "update_time": int(datetime.now().timestamp()),
                    },
                },
            ):
                return False
            # prepare filedata to update vehicle also in modified list file
            if filedata := filedata or await self.get_vehicle_list(fromFile=toFile):
                for v in [
                    veh
                    for veh in filedata.get("vehicle_list") or []
                    if veh.get("vehicle_id") == vehicleId
                ]:
                    v.update(
                        {
                            "is_smart_charging": bool(
                                chargeOrder.get("transaction_ id")
                            ),
                            "update_time": int(datetime.now().timestamp()),
                        }
                    )
        else:
            code = (
                await self.apisession.request(
                    "post", API_ENDPOINTS["vehicle_set_charging"], json=data
                )
            ).get("code")
            if not isinstance(code, int) or int(code) != 0:
                return False
    elif action in ["update", "restore"]:
        # For restore, try to get attributes from cache with optional lookup
        if action == "restore" and (
            not vehicle.battery_capacity
            or not vehicle.ac_max_charging_power
            or not vehicle.energy_consumption_per_100km
        ):
            # get year options with optional cache udate and filter best match
            if v := await self.get_vehicle_attributes(vehicle=vehicle, fromFile=toFile):
                vehicle = v
            else:
                return False
        if vehicle.brand:
            data["brand"] = vehicle.brand
        if vehicle.model:
            data["model"] = vehicle.model
        if vehicle.productive_year:
            data["productive_year"] = vehicle.productive_year
        if vehicle.battery_capacity:
            data["battery_capacity"] = vehicle.battery_capacity
        if vehicle.ac_max_charging_power:
            data["ac_max_charging_power"] = vehicle.ac_max_charging_power
        if vehicle.energy_consumption_per_100km:
            data["energy_consumption_per_100km"] = vehicle.energy_consumption_per_100km
        # update requested options
        if toFile:
            # Write updated vehicle to file for testing purposes
            data["update_time"] = int(datetime.now().timestamp())
            if not await self.apisession.saveToFile(
                Path(self.testDir())
                / f"{API_FILEPREFIXES['get_user_vehicle_details']}_modified_{vehicleId}.json",
                data={
                    "code": 0,
                    "msg": "success!",
                    "data": old_vehicle | data,
                },
            ):
                return False
            # prepare filedata to update vehicle also in modified list file
            if filedata := filedata or await self.get_vehicle_list(fromFile=toFile):
                data.pop("ac_max_charging_power", None)
                data.pop("energy_consumption_per_100km", None)
                for v in [
                    veh
                    for veh in filedata.get("vehicle_list") or []
                    if veh.get("vehicle_id") == vehicleId
                ]:
                    v.update(data)
        else:
            code = (
                await self.apisession.request(
                    "post", API_ENDPOINTS["vehicle_update"], json=data
                )
            ).get("code")
        # check if vehicle is registered, then updated options should be loaded to cache
        if vehicleId in (registered := self.account.get("vehicles_registered") or []):
            await self.update_vehicle_options(vehicle=vehicle, fromFile=toFile)
    # update list data file if required
    if filedata:
        if not await self.apisession.saveToFile(
            Path(self.testDir())
            / f"{API_FILEPREFIXES['get_user_vehicles']}_modified.json",
            data={"code": 0, "msg": "success!", "data": filedata},
        ):
            return False
    # update vehicle list in Api dict
    await self.get_vehicle_list(fromFile=toFile)
    # update vehicle details in api dict and return active details
    return (
        {}
        if action == "delete"
        else await self.get_vehicle_details(vehicleId, fromFile=toFile)
    )
