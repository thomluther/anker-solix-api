<div class="container">
  <div class="image"> <img src="https://public-aiot-fra-prod.s3.dualstack.eu-central-1.amazonaws.com/anker-power/public/product/2024/07/23/iot-admin/jvwLiu0cOHjYMCwV/picl_A17X8_normal.png" alt="Smart Plug" title="Smart Plug" align="right" height="65px"/> </div>
  <div class="image"> <img src="https://public-aiot-fra-prod.s3.dualstack.eu-central-1.amazonaws.com/anker-power/public/product/anker-power/0f8e0ca7-dda9-4e70-940d-fe08e1fc89ea/picl_A5143_normal.png" alt="Anker MI80 Logo" title="Anker MI80" align="right" height="65px"/> </div>
  <div class="image"> <img src="https://public-aiot-fra-prod.s3.dualstack.eu-central-1.amazonaws.com/anker-power/public/product/anker-power/e9478c2d-e665-4d84-95d7-dd4844f82055/20230719-144818.png" alt="Solarbank E1600 Logo" title="Anker Solarbank E1600" align="right" height="80px"/> </div>
  <div class="image"> <img src="https://public-aiot-fra-prod.s3.dualstack.eu-central-1.amazonaws.com/anker-power/public/product/2024/05/24/iot-admin/opwTD5izbjD9DjKB/picl_A17X7_normal.png" alt="Smart Meter Logo" title="Anker Smart Meter" align="right" height="65px"/> </div>
  <img src="https://public-aiot-fra-prod.s3.dualstack.eu-central-1.amazonaws.com/anker-power/public/product/2024/05/24/iot-admin/5iJoq1dk63i47HuR/picl_A17C1_normal%281%29.png" alt="Solarbank 2 E1600 Logo" title="Anker Solarbank 2 E1600"  align="right" height="80px"/> </div>
</div>

# Anker Solix Api library

[![github license](https://img.shields.io/badge/License-MIT-orange)](https://github.com/thomluther/anker-solix-api/blob/main/LICENSE)
![python badge](https://img.shields.io/badge/Made%20with-Python-orange)
[![GitHub repo Good Issues for newbies](https://img.shields.io/github/issues/thomluther/anker-solix-api/good%20first%20issue?style=flat&logo=github&logoColor=green&label=Good%20First%20issues)](https://github.com/thomluther/anker-solix-api/issues?q=is%3Aopen+is%3Aissue+label%3A%22good+first+issue%22) [![GitHub Help Wanted issues](https://img.shields.io/github/issues/thomluther/anker-solix-api/help%20wanted?style=flat&logo=github&logoColor=b545d1&label=%22Help%20Wanted%22%20issues)](https://github.com/thomluther/anker-solix-api/issues?q=is%3Aopen+is%3Aissue+label%3A%22help+wanted%22) [![GitHub Help Wanted PRs](https://img.shields.io/github/issues-pr/thomluther/anker-solix-api/help%20wanted?style=flat&logo=github&logoColor=b545d1&label=%22Help%20Wanted%22%20PRs)](https://github.com/thomluther/anker-solix-api/pulls?q=is%3Aopen+is%3Aissue+label%3A%22help+wanted%22) [![GitHub repo Issues](https://img.shields.io/github/issues/thomluther/anker-solix-api?style=flat&logo=github&logoColor=red&label=Issues)](https://github.com/thomluther/anker-solix-api/issues?q=is%3Aopen)

This is an experimental Python library for Anker Solix Power devices (Solarbank, Inverter, Smart Meter etc).

🚨 This is by no means an official Anker Api.
It can break at any time, or Api requests can be removed/added/changed and break some of the endpoint methods used in this Api.🚨

# Python Versions

The library is currently supported on

- Python 3.12
- Python 3.13

# Required libraries

This project uses `pipenv` for Python dependency management

```bash
pip install pipenv
pipenv sync -d
pipenv run python [...]
```

If you get path errors during `pipenv synd -d`, delete your local `Pipenv.lock` file and re-run the lock and sync process.
```bash
rm Pipfile.lock
pipenv lock
pipenv sync -d
```

# Anker Account Information

Because of the way the Anker Solix Cloud Api works, one account with email/password cannot be used for the Anker mobile app and this Api in parallel.
The Anker Solix Cloud allows only one request token per account at any time. Each new authentication request by a client will create a new token and drop a previous token.
Therefore usage of this Api may kick out your account login in the mobile app. However, starting with Anker mobile app release 2.0, you can share your defined system(s) with 'family members'. Therefore it is recommended to create a second Anker account with a different email address and share your defined system(s) with the second account.

> [!IMPORTANT]
> A shared account is only a member of the shared system, and as such currently has no permissions to access or query device details of the shared system.
Therefore an Api homepage query will neither display any data for a shared account. However, a shared account can receive Api scene/site details of shared systems (app system = Api site), which is equivalent to what is displayed in the mobile app on the home screen for the selected system.


# Usage

Everything starts with an:

[aiohttp](https://aiohttp.readthedocs.io/en/stable/) `ClientSession`:

```python
"""Example module to test the api methods."""

import asyncio
import json
import logging

from aiohttp import ClientSession
from api import api, apitypes
import common

_LOGGER: logging.Logger = logging.getLogger(__name__)
# _LOGGER.setLevel(logging.DEBUG)    # enable for detailed Api output


def _out(jsondata):
    """Print json string in readable format."""
    CONSOLE.info(json.dumps(jsondata, indent=2))

async def main() -> None:
    """Create the aiohttp session and run the example."""
    async with ClientSession() as websession:
        # put your code here, example
        myapi = api.AnkerSolixApi(
            common.user(), common.password(), common.country(), websession, _LOGGER
        )
        await myapi.update_sites()
        await myapi.update_device_details()
        await myapi.update_site_details()
        await myapi.update_device_energy()
        CONSOLE.info("Account Overview:")
        _out(myapi.account)
        CONSOLE.info("System Overview:")
        _out(myapi.sites)
        CONSOLE.info("Device Overview:")
        _out(myapi.devices)

        # Test a defined endpoint from apitypes module
        #_out(await myapi.apisession.request("post", apitypes.API_ENDPOINTS["bind_devices"],json={}))

        # Test an undefined endpoint directly (available endpoints documented in apitypes module)
        #mysite = "<your_site_id>"
        #_out(await myapi.apisession.request("post", "power_service/v1/app/compatible/get_installation",json={"site_id": mysite}))

        # Note: Error response msg from api request may list missing field names or wrong field types from what the endpoint is expecting in the json payload

# run async main
if __name__ == "__main__":
    try:
        asyncio.run(main(), debug=False)
    except Exception as err:
        CONSOLE.info(f"{type(err)}: {err}")
```

# Data polling

The AnkerSolixApi class starts an AnkerSolixApiSession to handle the Api connection for the provided Anker user account.
The AnkerSolixApi class provides also methods that utilize the `power_service` endpoints and it provides 4 main methods to query data and cache them into internal dictionaries:

- `AnkerSolixApi.update_sites()` to query overview data for all accessible sites and store data in dictionaries `AnkerSolixApi.sites` and `AnkerSolixApi.devices` for quick access.

  This method could be run in regular intervals (60sec or more) to fetch new data of the systems. Note that the system devices update the cloud data only once per minute, therefore less than 60 second intervals do not provide much benefit

- `AnkerSolixApi.update_device_details()` to query further settings for the device serials as found in the sites query or for stand alone devices and store data in dictionary `AnkerSolixApi.devices`

  This method should be run less frequently since this will mostly fetch various device configuration settings and needs multiple queries.
  It currently is developed for Solarbank and Inverter devices only. Further device types such as Power Panels or Home Energy Systems have a corresponding method in their api class and will be used and merged accordingly. This method should be used first before the any of the 2 following methods is used, since it may create virtual sites for stand alone devices that track also energy statistics in the cloud, but are not reported by the update_sites() method.

- `AnkerSolixApi.update_site_details()` to query further settings for the defined site (power system) and store data in dictionary `AnkerSolixApi.sites` for quick access.

  This method should be run less frequently since this will mostly fetch various site configuration settings and needs multiple queries.

- `AnkerSolixApi.update_device_energy()` to query further energy statistics for the devices from each site and store data in dictionary `AnkerSolixApi.sites` for quick access.

  This method should be run less frequently since this will fetch 4-6 queries per site depending on found device types. With version 2.0.0, solarbank, inverter and smart meter devices are supported. However it was noticed, that the energy statistics endpoint (probably each endpoint) is limited to 25-30 queries per minute. As of Feb 2025, the endpoint limit was further reduced to 10-12 requests per endpoint per minute for certain endpoints.

The code of these 4 main methods has been separated into the [`poller.py`](api/poller.py) module. To reduce the size of the ever growing AnkerSolixApi class in the [`api.py`](api/api.py) module, a common base class AnkerSolixBaseApi was introduced with common attributes and methods that may be used by different Api client types. The AnkerSolixApi class enhances the base class for methods required to support balcony power systems. Due to the size of the required methods, they have been separated into various python modules and are simply imported into the main AnkerSolixApi class in the api module. The known Anker Cloud Api endpoints are all documented in the [`apitypes.py`](api/apitypes.py) module. However, parameter usage for many of them is unknown and still need to be explored for useful information.
If additional `charging_energy_service` endpoints (for Power Panels / Power Stations ?) and/or `charging_hes_svc` endpoints (for Home Energy Systems like X1 ?) will be tested and documented by the community in future, a new AnkerSolixApi alike class based on AnkerSolixBaseApi class should be created for each endpoint type or power system category. Since Anker accounts may utilize different power system types in parallel, they should share the same instance of the created AnkerSolixApiSession for the user account. If any AnkerSolixApiSession instance was already created for the user account, the AnkerSolixApi class can be instanced with the AnkerSolixApiSession instance instead of the Anker Account credentials.

Check out the given example code and [`test_api.py`](./test_api.py) or other python executable tools that may help to leverage and explore the Api for your Anker power system.
The subfolder [`examples`](./examples) contains actual or older example exports with json files using anonymized responses of the [`export_system.py`](./export_system.py) module giving you an idea of how various Api responses look like. Those json files can also be used to develop/debug the Api for system constellations not available to the developer.

> [!IMPORTANT]
> The cloud api response structure may change over time without notice because additional fields have been added to support new functionalities. Hopefully existing fields will not be modified to ensure backward compatibility.


# Api cache hierarchy generated by data poller methods

Cache entry type | Description
-- | --
`account` | Anker Solix user account used for the session. It collects all common fields belonging to the account or api connection. `account` is used as cache identifier.
`system` | Anker Solix 'Power System' as defined in the Anker app. It collects all fields belonging to the defined system and is referred as 'site' in the cloud api. The unique site id is used as cache identifier. A virtual site id is composed by `virtual-<device-sn>`.
`device` | Anker Solix end device as found in the Anker app. It collects all fields belonging to that device. The unique device SN is used as cache identifier. It contains a site_id field with the site id it belongs to if no stand alone device. There may be sub-devices that belong to a main device. They typically contain the `main_sn` field as reference and an `is_subdevice` flag in the cache.

For more details on the Anker Solix device hierarchy generated by the library, please refer to the discussion article [Integration device hierarchy and device attribute information](https://github.com/thomluther/ha-anker-solix/discussions/239) in the Home Assistant repo that is utilizing the data polling mechanism of this library.


# Supported devices

Following is an overview of supported Anker Solix device types with the data polling methods and api cache structure.

Device type | Description
-- | --
`solarbank` | Anker Solix Solarbank configured in the system:<br>- A17C0: Solarbank E1600 (Gen 1)<br>- A17C1: Solarbank 2 E1600 Pro<br>- A17C3: Solarbank 2 E1600 Plus<br>- A17C2: Solarbank 2 E1600 AC
`inverter` | Anker Solix standalone inverter or configured in the system:<br>- A5140: MI60 Inverter (out of service)<br>- A5143: MI80 Inverter
`smartmeter` | Smart meter configured in the system:<br>- A17X7: Anker 3 Phase Wifi Smart Meter<br>- SHEM3: Shelly 3EM Smart Meter<br>- SHEMP3: Shelly 3EM Pro Smart Meter
`smartplug` | Anker Solix smart plugs configured in the system:<br>- A17X8: Smart Plug 2500 W **(No individual device setting supported)**
`powerpanel` | Anker Solix Power Panels configured in the system **(only basic monitoring)**:<br>- A17B1: SOLIX Home Power Panel for SOLIX F3800 power stations (Non EU market)
`hes` | Anker Solix Home Energy Systems and their sub devices as configured in the system **(only basic monitoring)**:<br>- A5101: SOLIX X1 P6K US<br>- A5102 SOLIX X1 Energy module 1P H(3.68-6)K<br>- A5103: SOLIX X1 Energy module 3P H(5-12)K<br>- A5220: SOLIX X1 Battery module

> [!IMPORTANT]
> While some api responses may show standalone devices that you can manage with your Anker account, the cloud api does **NOT** contain or receive power values or much other details from standalone devices which are not defined to a Power System. The realtime data that you see in the mobile app under device details are either provided through the local Bluetooth interface or through an MQTT cloud server, where all your devices report their actual values but only for the time they are prompted in the App. Therefore there may not be any endpoints that provide usage data or settings of such stand alone devices. If your device is tracking energy statistics, it it likely using the power api that seems to be the unique Anker service to record energy data over time.


# AnkerSolixApi Tools

## test_api.py

```
> pipenv run ./test_api.py
```

Example exec module that can be used to explore and test AnkerSolixApi methods or direct endpoint requests with parameters. You can modify this module as required. Optionally you can create your own test file called `client.py` starting with the usage example above. This file is not indexed and added to gitignore, so your local changes are not tracked for git updates/commits.
This allows you to code your credentials in the local file if you do not want to utilize the environment variables:
```python
_CREDENTIALS = {
    "USER": os.getenv("ANKERUSER"),
    "PASSWORD": os.getenv("ANKERPASSWORD"),
    "COUNTRY": os.getenv("ANKERCOUNTRY"),
}
```

## export_system.py

```
> pipenv run ./export_system.py
```

Example exec module to use the Anker Api for export of defined system data and device details.
This module will prompt for the Anker account details if not pre-set in the header or defined in environment variables.
Upon successful authentication, you can specify which endpoint types you want to export and a subfolder for the exported JSON files received as Api query response, defaulting to your nick name. Optionally you can specify whether personalized information in the response data should be randomized in the files, like SNs, Site IDs, Trace IDs etc, and whether the output folder should be zipped to a file.
You can review the response files afterwards. They can be used as examples for dedicated data extraction from the devices.
Optionally the AnkerSolixApi class can use the json files for debugging and testing on various system outputs.

> [!NOTE]
> You should preferably run the export_system.py with the owner account of the power system. Otherwise only limited information can be exported by shared accounts due to access permissions.

## monitor.py

```
> pipenv run ./monitor.py
```

Example exec module to use the Anker Api for continuously querying and displaying important Anker power device parameters.
This module can use real time data from your Anker account, or optionally use json files from your local examples or export folder.
When using the real time option, it will prompt for the Anker account details if not pre-set in the header or defined in environment variables.
Upon successful authentication, you will see relevant parameter of supported devices displayed and refreshed at regular interval.
When using monitoring from local json file folder, the values will not change. But this option is useful to validate the api parsing with various system constellations. You can navigate through the list of json folders to verify/debug various system exports with the tool.

> [!NOTE]
> When the system owning account is used, more details for the owning sites and devices can be queried and displayed.

> [!IMPORTANT]
> **When executing this module with real time data from your Anker account, the used account cannot be used in the Anker App since it will be kicked out on each refresh.**

## energy_csv.py

```
> pipenv run ./energy_csv.py
```

Example exec module to use the Anker Api for export of daily Energy Data. This method will prompt for the Anker account details if not pre-set in the header.
Then you can specify a start day and the number of days for data extraction from the Anker Cloud. The received daily values will be exported into a csv file.

> [!NOTE]
> The solar production, Solarbank discharge, smart meter, smart plug and home usage can be queried across the full range each. The solarbank
charge as well as smart meter and smart plug totals however can be queried only as total for an interval (e.g. day). Therefore, when daily total
data is also selected for export, 2-4 additional Api queries per day are required.


# Contributing

![github contributors](https://img.shields.io/github/contributors/thomluther/anker-solix-api?color=orange)
![last commit](https://img.shields.io/github/last-commit/thomluther/anker-solix-api?color=orange)
[![Community Discussion](https://img.shields.io/badge/Home%20Assistant%20Community-Discussion-orange)](https://community.home-assistant.io/t/feature-request-integration-or-addon-for-anker-solix-e1600-solarbank/641086)

[![GitHub repo Good Issues for newbies](https://img.shields.io/github/issues/thomluther/anker-solix-api/good%20first%20issue?style=flat&logo=github&logoColor=green&label=Good%20First%20issues)](https://github.com/thomluther/anker-solix-api/issues?q=is%3Aopen+is%3Aissue+label%3A%22good+first+issue%22) [![GitHub Help Wanted issues](https://img.shields.io/github/issues/thomluther/anker-solix-api/help%20wanted?style=flat&logo=github&logoColor=b545d1&label=%22Help%20Wanted%22%20issues)](https://github.com/thomluther/anker-solix-api/issues?q=is%3Aopen+is%3Aissue+label%3A%22help+wanted%22) [![GitHub Help Wanted PRs](https://img.shields.io/github/issues-pr/thomluther/anker-solix-api/help%20wanted?style=flat&logo=github&logoColor=b545d1&label=%22Help%20Wanted%22%20PRs)](https://github.com/thomluther/anker-solix-api/pulls?q=is%3Aopen+is%3Aissue+label%3A%22help+wanted%22) [![GitHub repo Issues](https://img.shields.io/github/issues/thomluther/anker-solix-api?style=flat&logo=github&logoColor=red&label=Issues)](https://github.com/thomluther/anker-solix-api/issues?q=is%3Aopen)

Github is used to host code, to track issues and feature requests, as well as accept pull requests.

Pull requests are the best way to propose changes to the codebase.

1. [Check for open features/bugs](https://github.com/thomluther/anker-solix-api/issues)
   or [initiate a discussion on one](https://github.com/thomluther/anker-solix-api/issues/new).
1. [Fork the repository](https://github.com/thomluther/anker-solix-api/fork).
1. Fork the repo and create your branch from `main`.
1. If you've changed something, update the documentation.
1. Test your contribution.
1. Issue that pull request!

# Acknowledgements / Credits

- [python-eufy-security](https://github.com/FuzzyMistborn/python-eufy-security)
- [solix2mqtt](https://github.com/tomquist/solix2mqtt)

# Showing Your Appreciation

[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/thomasluthe)

If you like this project, please give it a star on [GitHub](https://github.com/thomluther/anker-solix-api)
