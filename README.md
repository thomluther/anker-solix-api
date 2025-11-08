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

This is an experimental Python library for Anker Solix Power devices (Solarbank, Inverter, Smart Meter, Portable Power Stations etc).

> [!WARNING]
> 🚨 This is by no means an official Anker Api. It can break at any time, or Api requests can be removed/added/changed and break some of the endpoint methods used in this Api.🚨

# Python Versions

The library is currently supported on

- Python 3.12
- Python 3.13

# Required libraries

The dependencies of this project are `cryptography`, `aiohttp`, `aiofiles`.
You can either install them manually (e.g. via a package manager) or use [`poetry`](https://github.com/python-poetry/poetry).

## Poetry

**Step 1:** Install `poetry` following the [official documentation](https://python-poetry.org/docs/#installation) or via your favorite package manager,
for example:
```shell
sudo pip install poetry
```
or
```shell
sudo pacman -S python-poetry
```

> [!IMPORTANT]
> [Poetry 2.0.0](https://github.com/python-poetry/poetry/releases/tag/2.0.0) or later is required for full support of the pyproject.toml file, see issue [#208](https://github.com/thomluther/anker-solix-api/issues/208).

**Step 2:** Install dependencies with `poetry`. In the root of this repository run:

```shell
poetry install
```

**Step 3:** Run programs in this repository with:

```shell
poetry run python [...].py
```

## Manually

To install the dependencies manually consult your favorite package manager, for example:

```shell
sudo pip install cryptography aiohttp aiofiles paho-mqtt
```
or
```shell
sudo pacman -S python-cryptography python-aiohttp python-aiofiles python-paho-mqtt
```

You should then be able to run programs with:

```shell
python [...].py
```

> [!IMPORTANT]
> The manual method can not check your python version so please make sure that yours is [supported](#python-versions).


# Anker Account Information

Because of the way the Anker Solix Cloud Api was working, one account with email/password could not be used for the Anker mobile app and this Api in parallel.
The Anker Solix Cloud allowed only one login token per account at any time. Each new login request by a client will create a new token and the previous token on the server was dropped. For that reason, it was not possible to use this Api client and your mobile app with the same account in parallel. Starting with Anker mobile app release 2.0, you could share your owned system(s) with 'family members'. Since then it was possible to create a second Anker account with a different email address and share your owned system(s) with one or more secondary accounts as member.

> [!NOTE]
> A shared account is only a member of the shared system, and as such currently has no permissions to access or query device details of the shared system.
Therefore an Api homepage query will neither display any data for a shared account. However, a shared account can receive Api scene/site details of shared systems (app system = Api site), which is equivalent to what is displayed in the mobile app on the home screen for the selected system.

> [!TIP]
> Starting end of July 2025 and with version 3.10 of the Anker mobile app, one account can now be used across multiple devices in parallel. That means active login tokens are no longer deleted upon login of another client and parallel account usage becomes possible. Actually there is **NO NEED ANYMORE** to create a second account and share the system with it, since the main account can now be used in parallel across multiple devices and clients.


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
CONSOLE: logging.Logger = common.CONSOLE


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
The AnkerSolixApi class provides also methods that utilize the `power_service` endpoints and it provides 4 main methods to query data and cache them into internal dictionaries (the Api cache):

- `AnkerSolixApi.update_sites()` to query overview data for all accessible sites and store data in dictionaries `AnkerSolixApi.sites`, `AnkerSolixApi.devices` and `AnkerSolixApi.account` for quick access.

  This method could be run in regular intervals (60 sec or more) to fetch new data of the systems. Note that the main system device updates the data in the cloud max. once every minute or even every 5 minutes. Therefore, less than 60 second intervals do not provide much benefit.

- `AnkerSolixApi.update_device_details()` to query further settings for the device serials as found in the sites query or for stand alone devices and store data in dictionary `AnkerSolixApi.devices`.

  This method should be run less frequently since this will mostly fetch various device configuration settings and needs multiple queries.
  It currently is developed for Solarbank and Inverter devices only. Further device types such as Power Panels or Home Energy Systems (X1) have a corresponding method in their api class, which will be used and merged accordingly. This method should be used first, before any of the 2 following methods is used, since it may create virtual sites for stand alone devices that track also energy statistics in the cloud, but are not reported by the update_sites() method.

- `AnkerSolixApi.update_site_details()` to query further settings for the defined site (power system) and store data in dictionary `AnkerSolixApi.sites` for quick access.

  This method should be run less frequently since this will mostly fetch various site configuration settings and needs multiple queries.

- `AnkerSolixApi.update_device_energy()` to query further energy statistics for the devices from each site and store data in dictionary `AnkerSolixApi.sites` for quick access.

  This method should be run less frequently since this will fetch 4-6 queries per site depending on found device types. With version 2.0.0, solarbank, inverter and smart meter devices are supported. However it was noticed, that the energy statistics endpoint (probably each endpoint) is limited to 25-30 queries per minute. As of Feb 2025, the endpoint limit for energy statistics was further reduced to 10-12 requests per minute.

The code of these 4 main methods has been separated into the [`poller.py`](api/poller.py) module. To reduce the size of the ever growing AnkerSolixApi class in the [`api.py`](api/api.py) module, a common base class AnkerSolixBaseApi was introduced with common attributes and methods that may be used by different Api client types. The AnkerSolixApi class enhances the base class for methods required to support balcony power systems. Due to the size of the required methods, they have been separated into various python modules and are simply imported into the main AnkerSolixApi class in the api module. The known Anker Cloud Api endpoints are all documented in the [`apitypes.py`](api/apitypes.py) module. However, parameter usage for many of them is unknown and still need to be explored for useful information.
If additional `charging_energy_service` endpoints (for Power Panels) and/or `charging_hes_svc` endpoints (for Home Energy Systems like X1) will be tested and documented by the community in future, a new AnkerSolixApi alike class based on AnkerSolixBaseApi class should be created for each endpoint type or power system category. Since Anker accounts may utilize different power system types in parallel, they should share the same instance of the created AnkerSolixApiSession for the user account. If any AnkerSolixApiSession instance was already created for the user account, the AnkerSolixApi class can be instanced with the AnkerSolixApiSession instance instead of the Anker Account credentials.

Check out the given example code and [`test_api.py`](./test_api.py) or other python executable tools that may help to leverage and explore the Api for your Anker power system.
The subfolder [`examples`](./examples) contains actual or older example exports with json files using anonymized responses of the [`export_system.py`](./export_system.py) module giving you an idea of how various Api responses look like. Those json files can also be used to develop/debug the Api for system constellations not available to the developer.

> [!IMPORTANT]
> The cloud api response structure may change over time without notice because additional fields will be added to support new devices or functionalities. Hopefully existing fields will not be modified to ensure backward compatibility.


# Api cache hierarchy generated by data poller methods

Cache entry type | Description
-- | --
`account` | Anker Solix user account used for the session. It collects all common fields belonging to the account or api connection. The account email address is used as cache identifier for the account structure.
`system` | Anker Solix 'Power System' as defined in the Anker app. It collects all fields belonging to the defined system and is referred as 'site' in the cloud api. The unique site id is used as cache identifier. A virtual site id is composed by `virtual-<device-sn>`.
`device` | Anker Solix end device as found in the Anker app. It collects all fields belonging to that device. The unique device SN is used as cache identifier. It contains a site_id field with the site id it belongs to if no stand alone device. There may be sub-devices that belong to a main device. They typically contain the `main_sn` field as reference and an `is_subdevice` flag in the cache.
`vehicle` | Electronic vehicle as it can be defined by an Anker Solix user account. They are used to manage EV charging orders with the new Solix V1 EV Charger device and can be seen as a virtual device that belongs to the user only. All vehicle information is managed under the account dictionary, but individual vehicles will be referred separately in the overall cache structure, using the vehicle ID as cache identifier.

For more details on the Anker Solix device hierarchy generated by the library, please refer to the discussion article [Integration device hierarchy and device attribute information](https://github.com/thomluther/ha-anker-solix/discussions/239) in the Home Assistant repo that is utilizing the data polling mechanism of this library.


# Supported devices

Following is an overview of supported Anker Solix device types with the data polling methods and api cache structure.

Device type | Description
-- | --
`account` | Anker Solix user account used for the configured hub entry. It collects all common entities belonging to the account or api connection.
`system` | Anker Solix 'Power System' as defined in the Anker app. It collects all entities belonging to the defined system and is referred as 'site' in the cloud api.
`solarbank` | Anker Solix Solarbank configured in the system:<br>- A17C0: Solarbank E1600 (Gen 1)<br>- A17C1: Solarbank 2 E1600 Pro<br>- A17C3: Solarbank 2 E1600 Plus<br>- A17C2: Solarbank 2 E1600 AC<br>- A17C5: Solarbank 3 E2700
`combiner_box` | Anker Solix (passive) combiner box configured in the system:<br>- AE100: Power Dock for Solarbank Multisystems
`inverter` | Anker Solix standalone inverter or configured in the system:<br>- A5140: MI60 Inverter (out of service)<br>- A5143: MI80 Inverter
`smartmeter` | Smart meter configured in the system:<br>- A17X7: Anker 3 Phase Wifi Smart Meter<br>- SHEM3: Shelly 3EM Smart Meter<br>- SHEMP3: Shelly 3EM Pro Smart Meter
`smartplug` | Anker Solix smart plugs configured in the system:<br>- A17X8: Smart Plug 2500 W **(No individual device setting supported)**
`pps` | Anker Solix Portable Power Stations stand alone devices:<br>- A1761: SOLIX C1000X Portable Power Station **(MQTT monitoring and control)**
`powerpanel` | Anker Solix Power Panels configured in the system **(only basic monitoring)**:<br>- A17B1: SOLIX Home Power Panel for SOLIX F3800 power stations (Non EU market)
`hes` | Anker Solix Home Energy Systems and their sub devices as configured in the system **(only basic monitoring)**:<br>- A5101: SOLIX X1 P6K US<br>- A5102 SOLIX X1 Energy module 1P H(3.68-6)K<br>- A5103: SOLIX X1 Energy module 3P H(5-12)K<br>- A5220: SOLIX X1 Battery module
`vehicle` | Electric vehicles as created/defined under the Anker Solix user account. Those vehicles are virtual devices that will be required to manage charging with the announced Anker Solix V1 EV Charger.


> [!IMPORTANT]
> While some api responses may show standalone devices that you can manage with your Anker account, the cloud api does **NOT** contain or receive power values or much other details from standalone devices which are not defined to a Power System. The realtime data that you see in the mobile app under device details are either provided through the local Bluetooth interface or through an MQTT cloud server, where all your devices report their actual values but only for the time they are prompted in the App. Therefore there may not be any endpoints that provide usage data or settings of such stand alone devices. If your device is tracking energy statistics, it it likely using the power api that seems to be the unique Anker service to record energy data over time.


# MQTT client

This is a rather new implementation in the library. It provides data classes to structure the byte data as received in MQTT or Bluetooth messages. The modules also contains a data mapping for the byte fields as known so far. This mapping description must be enhanced for each device model, constellation and message type that is provided, to allow MQTT data extraction and usage.

> [!IMPORTANT]
> At this point there is NO integration of MQTT data to the Api cache since the propriatary byte data must be described first for various devices.
This is where YOU can contribute as device owner, see discussion [MQTT data decoding guidelines](https://github.com/thomluther/anker-solix-api/discussions/222).

Following is a code snipped how you can utilize the library for easy byte data structuring and see decoding options of your received byte data packages from MQTT or BT clients. You can use this in the client example above.

```python
# required additional imports
from base64 import b64decode
from api import mqtttypes

      # hex byte data as received from MQTT or BT
      hexstr = "ff093b0003010f0407a10132xxxxxxxxxxxxxxxxxxxxxxxxxxxa502010128"
      # optional b64 encoded data as received
      b64str = "/wkOAAMBDwhXAKEBMjg="
      hexstr = b64decode(b64str).hex()
      # structure hex bytes in data class, specify your device model to get defined decoding descriptions for fields
      data = mqtttypes.DeviceHexData(model="A17C5",hexbytes=hexstr)
      # print data structure
      CONSOLE.info(str(data))
      # print bytes with decode options and defined field name description
      CONSOLE.info(data.decode())
```

The most convenient way to monitor and decode your device MQTT data however is the [mqtt_monitor.py](#mqtt_monitorpy) tool.


# AnkerSolixApi Tools

## test_api.py

```shell
poetry run python ./test_api.py
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

```shell
poetry run python ./export_system.py
```

Example exec module to use the Anker Api for export of defined system data and device details.
This module will prompt for the Anker account details if not pre-set in the header or defined in environment variables.
Upon successful authentication, you can specify which endpoint types you want to export and a subfolder for the exported JSON files received as Api query response, defaulting to your nick name. Optionally you can specify whether personalized information in the response data should be randomized in the files, like SNs, Site IDs, Trace IDs etc, and whether the output folder should be zipped to a file.
You can review the response files afterwards. They can be used as examples for dedicated data extraction from the devices.
Optionally the AnkerSolixApi class can use the json files for debugging and testing on various system outputs.

> [!NOTE]
> You should preferably run the `export_system.py` with the owner account of the power system. Otherwise only limited information can be exported by shared accounts due to access permissions.

## monitor.py

```shell
poetry run python ./monitor.py
```

Example exec module to use the Anker Api for continuously querying and displaying important Anker power device parameters.
This module can use real time data from your Anker account, or optionally use json files from your local examples or export folder.
When using the real time option, it will prompt for the Anker account details if not pre-set in the header or defined in environment variables.
Upon successful authentication, you will see relevant parameter of supported devices displayed and refreshed at regular interval.
When using monitoring from local json file folder, the values will not change. But this option is useful to validate the api parsing with various system constellations. You can navigate through the list of json folders to verify/debug various system exports with the tool.

<details>
<summary><b>Expand to see monitor tool usage overview</b><br><br></summary>

### Live Monitor key menu:

```console
----------------------------------------------------------------------------------------------------
[K]ey list to show this menu
[E]lectric Vehicle display toggle ON (default) or OFF
[D]ebug actual Api cache
[C]ustomize an Api cache entry
[V]iew actual MQTT data cache and extracted device data
[A]pi call display toggle OFF (default) or ON
Toggle MQTT [S]ession OFF (default) or ON
[R]eal time MQTT data trigger (Timeout 1 min). Only possible if MQTT session is ON
[M]qtt device or Api device (default) display toggle
[Q]uit, [ESC] or [CTRL-C] to stop monitor
----------------------------------------------------------------------------------------------------
```

### File usage Monitor key menu:

```console
----------------------------------------------------------------------------------------------------
[K]ey list to show this menu
[E]lectric Vehicle display toggle ON (default) or OFF
[D]ebug actual Api cache
[C]ustomize an Api cache entry
[V]iew actual MQTT data cache and extracted device data
[A]pi call display toggle OFF (default) or ON
Toggle MQTT [S]ession OFF (default) or ON
Change MQTT message speed [+] faster / [-] slower
Immediate s[I]te refresh
Immediate refresh for a[L]l
Select [N]next folder for monitoring
Select [P]previous folder for monitoring
Select [O]ther folder for monitoring
[M]qtt device or Api device (default) display toggle
[Q]uit, [ESC] or [CTRL-C] to stop monitor
----------------------------------------------------------------------------------------------------
```

### Command line options for monitor tool

Command line arguments allow making the monitor tool more suitable for automation and non-interactive usage.
Keep in mind that credential prompts are only avoided if they are defined as environment variables:
  - ANKERUSER=<username>
  - ANKERPASSWORD=<password>
  - ANKERCOUNTRY=<country_id>


#### Main usage options
- `--live-cloud` / `--live`: Skip interactive mode, use live cloud data directly
- `--site-id`: Monitor specific site ID only instead of all sites and devices for account
- `--enable-mqtt` / `--mqtt`: Auto-start MQTT session for real-time device data
- `--realtime` / `--rt`: Automatically trigger real-time MQTT data on startup
- `--mqtt-display`: Show pure MQTT data instead of mixed API+MQTT display

#### Configuration Options
- `--interval` / `-i`: Modify default refresh interval (5-600 seconds, default: 30)
- `--endpoint-limit`: Modify default API endpoint limit for request throttling (default: 10)
- `--energy-stats` / `--energy`: Include daily site energy statistics, only shown with API display
- `--no-vehicles` / `--no-ev`: Disable electric vehicle display for API display

#### Debug & Logging
- `--api-calls`: Show API call statistics and details
- `--debug-http`: Control HTTP request/response debug logging (separated from API stats)


#### Command line argument usage examples

```bash
# Quick monitoring with MQTT and real-time data
python monitor.py --live --mqtt --rt

# Energy monitoring with custom interval
python monitor.py --live --energy-stats --interval 60

# Monitor specific site with pure MQTT display
python monitor.py --live --mqtt --mqtt-display --site-id ABC123

# Debug mode with HTTP logging
python monitor.py --live --mqtt --debug-http
```
</details>

> [!TIP]
> If the system owning account is used, more details for the owning sites and devices can be queried and displayed. You can also compare the monitor data
with mobile App data.


## mqtt_monitor.py

```shell
poetry run python ./mqtt_monitor.py
```

Example exec module to use the Anker Api to establish a client connection to the MQTT cloud server and subscribe to MQTT topics for receiving
device messages. This module will prompt for the Anker account details if not pre-set in the header. Upon successful authentication,
you will see the owned devices of the user account and you can select a device you want to monitor. Optionally you
can dump the output to a file. The tool will display a usage menu before monitoring starts. While monitoring,
it reacts on key press for the menu options. The menu can be displayed again with 'm'.
The tool also utilizes the built in real time data trigger, which can trigger frequent data updates of your owned devices.

<details>
<summary><b>Expand to see monitor tool usage overview</b><br><br></summary>

### MQTT Monitor key menu:

```console
----------------------------------------------------------------------------------------------------
[M]enu to show this key list
[U]nsubscribe all topics. This will stop receiving MQTT messages
[S]ubscribe root topic. This will subscribe root only
[T]oggle subscribed topic. If only one topic identified from root topic, toggling is not possible
[R]eal time data trigger toggle OFF (Default) or ON
[V]iew value extraction refresh screen or MQTT message decoding
[Q]uit, [ESC] or [CTRL-C] to stop MQTT monitor
----------------------------------------------------------------------------------------------------
```
</details>

> [!TIP]
> For byte value decoding and possible field descriptions, you should monitor your app in parallel. See discussion [MQTT data decoding guidelines](https://github.com/thomluther/anker-solix-api/discussions/222) for MQTT details and general data decoding instructions.

## energy_csv.py

```shell
poetry run python ./energy_csv.py
```

Example exec module to use the Anker Api for export of daily Energy Data. This method will prompt for the Anker account details if not pre-set in the header.
Then you can specify a start day and the number of days for data extraction from the Anker Cloud. The received daily values will be exported into a csv file.

> [!NOTE]
> The solar production, Solarbank discharge, smart meter, smart plug and home usage can be queried across the full range each. The solarbank
charge as well as smart meter and smart plug totals however can be queried only as total for an interval (e.g. day). Therefore, once daily total
data is also selected for export, 2-4 additional Api queries per day are required.

> [!IMPORTANT]
> The api enforces a query limit per minute, per endpoint & IP address. The energy statistics endpoint is limited to 10-12 queries per minute. The Api library will apply a default throttling of 10 requests per minute once the first error is received for the endpoint that indicates exceeding the limit:
```
429: Too many requests
```
Therefore, large range queries of multiple weeks with daily totals may therefore have an unpredictable runtime of several minutes.


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
- [SolixBLE](https://github.com/flip-dots/SolixBLE)

# Showing Your Appreciation

[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/thomasluthe)

If you like this project, please give it a star on [GitHub](https://github.com/thomluther/anker-solix-api)
