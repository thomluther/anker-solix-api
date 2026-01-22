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

The dependencies of this project are `cryptography`, `aiohttp`, `aiofiles` and `paho-mqtt` for the Api library modules.
The tools utilizing the common.py module optionally require `python-dotenv` to support definition of credentials via local `.env` file that can be utilized for loading environment variables at runtime only.
You can either install the requirements manually (e.g. via a package manager) or use [`poetry`](https://github.com/python-poetry/poetry).

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
sudo pip install cryptography aiohttp aiofiles paho-mqtt python-dotenv
```
or
```shell
sudo pacman -S python-cryptography python-aiohttp python-aiofiles python-paho-mqtt python-python-dotenv
```

You should then be able to run programs with:

```shell
python [...].py
```

> [!IMPORTANT]
> The manual method can not check your python version so please make sure that yours is [supported](#python-versions).


# Anker Account Information

Originally, one account with email/password could not be used for the Anker mobile app and this Api in parallel. In the past, the Anker Solix Cloud allowed only one login token per account at any time. Each new login request by a client will create a new token and the previous token on the server was dropped. For that reason, it was not possible to use this Api client and your mobile app with the same account in parallel. Starting with Anker mobile app release 2.0, you could share your owned system(s) with 'family members'. Since then it was possible to create a second Anker account with a different email address and share your owned system(s) with one or more secondary accounts as member.

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
The AnkerSolixApi class provides also methods which utilize the `power_service` endpoints and it provides 4 main methods to query data and cache them into internal dictionaries (the Api cache):

- `AnkerSolixApi.update_sites()` to query overview data for all accessible sites and store data in dictionaries `AnkerSolixApi.sites`, `AnkerSolixApi.devices` and `AnkerSolixApi.account` for quick access.

  This method could be run in regular intervals (60 sec or more) to fetch new data of the systems. Note that the main system device updates the data in the cloud max. once every minute or even every 5 minutes. Therefore, less than 60 second intervals do not provide much benefit.

- `AnkerSolixApi.update_device_details()` to query further settings for the device serials as found in the sites query or for stand alone devices and store data in dictionary `AnkerSolixApi.devices`.

  This method should be run less frequently since this will mostly fetch various device configuration settings and needs multiple queries.
  It currently is developed for Solarbank and Inverter devices only. Further device types such as Power Panels or Home Energy Systems (X1) have a corresponding method in their Api class, which will be used and merged accordingly. This method should be used first, before any of the 2 following methods is used, since it may create virtual sites for stand alone devices that track also energy statistics in the cloud, but are not reported by the update_sites() method.

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
`solarbank` | Anker Solix Solarbank configured in the system:<br>- A17C0: Solarbank E1600 (Gen 1) **(with MQTT monitoring & control)**<br>- A17C1: Solarbank 2 E1600 Pro **(with MQTT monitoring & control)**<br>- A17C3: Solarbank 2 E1600 Plus **(with MQTT monitoring & control)**<br>- A17C2: Solarbank 2 E1600 AC **(with MQTT monitoring & control)**<br>- A17C5: Solarbank 3 E2700 **(with MQTT monitoring & control)**
`combiner_box` | Anker Solix (passive) combiner box configured in the system:<br>- AE100: Power Dock for Solarbank Multisystems **(with MQTT monitoring & control)**
`inverter` | Anker Solix standalone inverter or configured in the system:<br>- A5140: MI60 Inverter (out of service)<br>- A5143: MI80 Inverter
`smartmeter` | Smart meter configured in the system:<br>- A17X7: Anker 3 Phase Wifi Smart Meter **(with MQTT monitoring)**<br>- SHEM3: Shelly 3EM Smart Meter<br>- SHEMP3: Shelly 3EM Pro Smart Meter **(with MQTT monitoring)**
`smartplug` | Anker Solix smart plugs configured in the system:<br>- A17X8: Smart Plug 2500 W **(with MQTT monitoring & control)**
`pps` | Anker Solix Portable Power Stations stand alone devices (only minimal Api data):<br>- A1722/A1723: C300(X) AC Portable Power Station **(MQTT monitoring & control)**<br>- A1726/A1728: C300(X) DC Portable Power Station **(MQTT monitoring & control)**<br>- A1761: C1000(X) Portable Power Station **(MQTT monitoring & control)**<br>- A1763: C1000 Gen 2 Portable Power Station **(MQTT monitoring & control)**<br>- A1780(P): F2000(P) Portable Power Station **(MQTT monitoring & control)**<br>- A1790(P): F3800(P) Portable Power Station **(MQTT monitoring & control)**
`powerpanel` | Anker Solix Power Panels configured in the system **(basic Api monitoring)**:<br>- A17B1: SOLIX Home Power Panel for SOLIX F3800 power stations (Non EU market)
`hes` | Anker Solix Home Energy Systems and their sub devices as configured in the system **(basic Api monitoring)**:<br>- A5101: SOLIX X1 P6K US<br>- A5102 SOLIX X1 Energy module 1P H(3.68-6)K<br>- A5103: SOLIX X1 Energy module 3P H(5-12)K<br>- A5220: SOLIX X1 Battery module
`vehicle` | Electric vehicles as created/defined under the Anker Solix user account. Those vehicles are virtual devices that will be required to manage charging with the announced Anker Solix V1 EV Charger.


> [!IMPORTANT]
> While some api responses may show standalone devices that you can manage with your Anker account, the cloud api does **NOT** contain or receive power values or much other details from standalone devices which are not defined to a Power System. The realtime data that you see in the mobile app under device details are either provided through the local Bluetooth interface or through an MQTT cloud server, where all your devices report their actual values. MQTT data may be published at regular, less frequent intervals, or may be triggered for real time data publish as prompted by the mobile App. Therefore, there are no Api endpoints that provide usage data or settings of such stand alone devices. If your device is tracking energy statistics, it it likely using the power Api that seems to be the unique Anker service to record energy data over time.


# MQTT client

This is a rather new implementation in the library. It provides data classes to structure the byte data as received in MQTT messages. The modules also contain a data mapping for the byte fields as known so far. This mapping descriptions in `mqttmap.py` and `mqttcmdmap.py` must be enhanced for each device model, constellation and message type that is provided, to allow MQTT data decoding, extraction and usage.
Devices publish 3 different type of messages typically:
- Message 0405 and optional other 04xx messages while triggered for real time data (typically in 3-5 second intervals)
  - These messages may also be published once upon a status request command if supported by the device
- Message 08xx at regular intervals of 60-500 seconds (typically as long as device is awake)
- Other messages like 07xx at irregular intervals, probably upon changes like message for Wifi signal strength

Once you decode and describe messages, you need to document their interval as well. All message types with meaningful data fields should be described, messages that do not contain relevant data should be skipped in the description. If only the triggered/requested message types for a device are described, no data can be extracted by the MQTT client if the real time trigger is not active. Therefore, standard/regular message types should be described as well if available and their interval should be known.

MQTT command messages have various message types, but they may be similar across various devices and only use different message number. There are simple commands that contain only 1 variable field with a value beside the common header and command message fields. Other commands may be very complex and contain many variable fields.

> [!IMPORTANT]
> At this point there is limited integration of MQTT data to the Api cache since the propriatary byte data must be described first for various devices.
This is where YOU can contribute as device owner, see discussion [MQTT data decoding guidelines](https://github.com/thomluther/anker-solix-api/discussions/222).

Following is a code snipped how you can utilize the library for easy byte data structuring and to see decoding options of your received byte data packages from MQTT clients. You can use this in the client example above.

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
      data = mqtttypes.DeviceHexData(model="A17C5", hexbytes=hexstr)
      # print data structure
      CONSOLE.info(str(data))
      # print bytes with decode options and defined field name description
      CONSOLE.info(data.decode())
```

The most convenient way to monitor and decode MQTT messages or commands of your device is the [mqtt_monitor.py](#mqtt_monitorpy) tool. It also allows you to dump all the monitor output to a file for later review and interpretation in case the live view is too fast, especially while the real time trigger is active. You can use the dumped messages also for comparing the status messages field changes before and after an MQTT command to identify the state field for the command.
In order to decode MQTT commands, you need to execute them in the App while the mqtt_monitor is active. Then you can easily find the command messages and how the settings/values are encoded into bytes. For each command, the valid and supported options, ranges or value steps must be documented in the mapping description before the controls for a particular device can be implemented into the library. It will be required to document full hex message examples per command, since they must be fully described to use the description for command composition and generic device control.
All MQTT commands must be defined and described in `mqttcmdmap.py`. The device message descriptions in `mqttmap.py` can then reuse (and optionally update) the defined commands for the correct message type as being observed. The device mapping also need to describe the 'STATE_NAME' field of the command in status messages were the command state is reported. Described commands without described state fields cannot be utilized for device control tools.
Please follow the [guidelines in this comment](https://github.com/thomluther/anker-solix-api/discussions/222#discussioncomment-14660599) to analyze and describe command messages and their corresponding state fields.


# AnkerSolixApi Tools

## test_api.py

```shell
poetry run python ./test_api.py
```

Example exec module that can be used to explore and test AnkerSolixApi methods or direct endpoint requests with parameters. You can modify this module as required. Optionally you can create your own test file called `client.py` starting with the usage example above. The `client.py` file is not indexed and added to gitignore, so your local changes are not tracked for git updates/commits.
This allows you to code your credentials in the local file if you do not want to utilize the environment variables:
```python
_CREDENTIALS = {
    "USER": os.getenv("ANKERUSER"),
    "PASSWORD": os.getenv("ANKERPASSWORD"),
    "COUNTRY": os.getenv("ANKERCOUNTRY"),
}
```
Those environment variables can optionally be defined in a local `.env` file in your repo root folder which is excluded from repo updates as well.
```console
ANKERUSER="username"
ANKERPASSWORD="password"
ANKERCOUNTRY="2_char_country_id"
```
Those variables will only be loaded at runtime when importing the common module.


## export_system.py

```shell
poetry run python ./export_system.py
```

Example exec module to use the Anker Api for export of defined system data and device details.
This module will prompt for the Anker account details if not pre-set in the header or defined in environment variables or an `.env` file.
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
When using the real time option, it will prompt for the Anker account details if not pre-set in the header or defined in environment variables or an `.env` file.
Upon successful authentication, you will see relevant parameter of supported devices displayed and refreshed at regular interval.
When using monitoring from local json file folder, the values will not change typically, with the exception of mixed in MQTT data from MQTT file poller. The file option is useful to validate the Api parsing with various system constellations, as well as validating MQTT data extraction. You can navigate through the list of json folders to verify/debug various system exports with the tool.

> [!NOTE]
> MQTT data in File mode can only be extracted if the export files contain MQTT messages (optional), the MQTT session is enabled in the monitor tool and an MQTT data description is defined in the `mqttmap.py` for the device PN.

The monitor uses following value highlighting with enabled MQTT session to distinguish their data source:
- Yellow: Device MQTT values with any new extracted data for the device
- Cyan: Last known device MQTT values if no device data was updated
- No color: Api data

Beside value highlighting, systems, devices, vehicles etc have their own highlighting to recognize corresponding sections quickly in the Api display.

You can also issue MQTT device controls with the monitor, if the MQTT session is enabled. You need to select or filter the device, select the control and confirm customizable control parameters and then the composed MQTT command will be published. The monitor should show whether the state was changed accordingly, which you can also verify in the mobile App in parallel.

> [!NOTE]
> If any MQTT control is used in file mode, the composed MQTT command will only be printed in decoded format for debugging purpose.

> [!IMPORTANT]
> Some Solarbank MQTT controls may need to be coordinated with Api commands to work and display properly in the mobile App and the monitor. Only using the MQTT control may change the settings on the solarbank itself, but not reflect the full change to the cloud, the App and within dependent system or station controls. Use them with care.


<details>
<summary><b>Expand to see monitor tool usage overview</b><br><br></summary>

### Live Monitor key menu:

```console
----------------------------------------------------------------------------------------------------
[K]ey list to show this menu
[E]lectric Vehicle display toggle ON (default) or OFF
[F]ilter toggle for device display
[D]ebug actual Api cache
Customi[Z]e an Api cache entry
[V]iew actual MQTT data cache and extracted device data
[A]pi call display toggle OFF (default) or ON
Toggle MQTT [S]ession OFF (default) or ON
[R]eal time MQTT data trigger (Timeout 1 min). Only possible if MQTT session is ON
[I]mmediate status request. Only possible if MQTT session is ON
[C]ontrol MQTT device. Only possible if MQTT session is ON
[M]qtt device or Api device (default) display toggle
[Q]uit, [ESC] or [CTRL-C] to stop monitor
----------------------------------------------------------------------------------------------------
```

### File usage Monitor key menu:

```console
----------------------------------------------------------------------------------------------------
[K]ey list to show this menu
[E]lectric Vehicle display toggle ON (default) or OFF
[F]ilter toggle for device display
[D]ebug actual Api cache
Customi[Z]e an Api cache entry
[V]iew actual MQTT data cache and extracted device data
[A]pi call display toggle OFF (default) or ON
Toggle MQTT [S]ession OFF (default) or ON
Change MQTT message speed [+] faster / [-] slower
Immediate s[I]te refresh
Immediate refresh for a[L]l
Select [N]next folder for monitoring
Select [P]previous folder for monitoring
Select [O]ther folder for monitoring
[C]ontrol MQTT device. Only possible if MQTT session is ON
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

Optionally you can define those variables in an `.env` file, which is defining them at runtime, see [test_api.py](#test_apipy).

#### Main usage options
- `--help` / `-h`: Get usage information
- `--live-cloud` / `-live`: Skip interactive mode, use live cloud data directly
- `--site-id`: Monitor specific site ID only instead of all sites and devices for account
- `--device-id`, `-dev`: Filter output for specific device ID only
- `--enable-mqtt` / `-mqtt`: Enable MQTT session after startup for real-time device data
- `--realtime-trigger` / `-rt`: Enable real-time MQTT trigger after startup (requires --enable-mqtt)
- `--mqtt-display`: Initially show pure MQTT data display instead of mixed API + MQTT display (requires --enable-mqtt)

#### Configuration Options
- `--interval` / `-i`: Modify default refresh interval (5-600 seconds, default: 30)
- `--endpoint-limit`: Modify default API endpoint limit for request throttling (default: 10)
- `--energy-stats` / `-energy`: Include daily site energy statistics, only shown with API display
- `--no-vehicles` / `-no-ev`: Disable electric vehicle display for API display

#### Debug & Logging
- `--api-calls`: Show API call statistics and details
- `--debug-http`: Control HTTP request/response debug logging (separated from API stats)


#### Command line argument usage examples

```bash
# Quick monitoring with MQTT and real-time data
python monitor.py -live -mqtt -rt

# Energy monitoring with custom interval
python monitor.py -live --energy-stats --interval 60

# Monitor specific site with pure MQTT display
python monitor.py -live -mqtt --mqtt-display --site-id ABC123

# Debug mode with HTTP logging
python monitor.py -live -mqtt --debug-http
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
it reacts on key press for the menu options. The menu can be displayed again with 'k' or 'm'.
The tool also utilizes the built in real time data trigger, which can trigger frequent data updates of your owned devices.

You can also issue described and supported MQTT device controls with the mqtt_monitor. You need to select the control and confirm customizable control parameters and then the composed MQTT command will be published. The monitor should show the decoded published command if subscribed to the command topics. To verify the MQTT control was correctly executed, you should verify the device settings in the mobile App in parallel. Some device controls require to re-enter the device details panel to get updates visualized in the mobile App. If the device control does not work, the command message description is most likely wrong or incomplete. You need to dump MQTT command message examples while doing the same control changes via the App and compare them with the composed commands from the message descriptions of your device PN.

> [!NOTE]
> - Device firmware changes may introduce additional fields in the control, that are not described yet.
> - Certain device controls may trigger more than one MQTT command through the App or Cloud. Multiple commands per control are not implemented (yet) in the MQTT control framework of this library. Subsequent commands for controls will have to be described and understood entirely before such multi command controls can be supported.
> - Some MQTT device controls are just a partial control if the control is also manageable via the cloud Api. If only the device command is published, the cloud Api may not be aware of the control change. One example is the Solarbank min SOC setting (SOC Reserve), which must be triggered through the cloud Api instead of the MQTT control for full functionality. Other examples are settings through the station in a solarbank system, especially if the station control needs to modify multiple devices in the system (Multisystems with or without power dock)


<details>
<summary><b>Expand to see monitor tool usage overview</b><br><br></summary>

### MQTT Monitor key menu:

```console
----------------------------------------------------------------------------------------------------
[K]ey list to show this [M]enu
[U]nsubscribe all topics. This will stop receiving MQTT messages
[S]ubscribe root topic. This will subscribe root only
[T]oggle subscribed topic. If only one topic identified from root topic, toggling is not possible
[R]eal time data trigger loop OFF (Default) or ON for continuous status messages
[O]ne real time trigger for device (timeout 60 seconds)
[I]mmediate status request for device
[C]ontrol MQTT device, select described command and parameter values to be published
[V]iew value extraction refresh screen or MQTT message decoding
[D]isplay snapshot of extracted values
[Q]uit, [ESC] or [CTRL-C] to stop MQTT monitor
----------------------------------------------------------------------------------------------------
```

### Command line options for mqtt_monitor tool

Command line arguments allow making the mqtt_monitor tool more suitable for automation and non-interactive usage.
For example you can use it for automated start with dump file and realtime trigger enabled, if you want to track
a certain control change via the mobile app. The dump file can then later be grepped for corresponding command
messages and differences in the status messages before and after the command.
To analyze the dump files, you can modify and use the `grep_mqtt_cmd.py`utility.

Keep in mind that credential prompts are only avoided if they are defined as environment variables:
  - ANKERUSER=<username>
  - ANKERPASSWORD=<password>
  - ANKERCOUNTRY=<country_id>

Optionally you can define those variables in an `.env` file, which is defining them at runtime, see [test_api.py](#test_apipy).

#### Main usage options
- `--help` / `-h`: Get usage information
- `--device-sn`, `-dev` DEVICE_SN: Define device SN to be monitored (required to use monitor without prompting)
- `--filedump` / `-fd`: Enable console dump into file
- `--dump-prefix` / `-dp` DUMP_PREFIX: Define dump filename prefix
- `--runtime` / `-r` MINUTES: Optional runtime in minutes [1-60] (default: Until cancelled)

#### Configuration Options
- `--realtime-trigger` / `-rt`: Enable MQTT real-time data trigger at startup
- `--status-request` / `-sr`: Issue immediate MQTT status request after startup
- `--value-display` / `-vd`: Initially show MQTT value display instead of MQTT messages display

#### Command line argument usage examples

```bash
# start MQTT monitoring for 10 minutes with dump into file while running realtime trigger
python mqtt_monitor.py -dev 1234567890123456 -rt 10 -fd

# start MQTT monitoring with dump into file using customer prefex and initial status request
python mqtt_monitor.py -dev 1234567890123456 -fd -dp cmd.device_timeout -sr
```
</details>

> [!TIP]
> For byte value decoding and possible field descriptions, you should monitor your app in parallel. See discussion [MQTT data decoding guidelines](https://github.com/thomluther/anker-solix-api/discussions/222) for MQTT details and general data decoding instructions.

> [!NOTE]
> The mobile app will always trigger realtime data from your device with a default timeout of 5 minutes. So you don't have to enable real time trigger in the monitor as well in case you use the app in parallel, e.g. to dump control messages for the changes you apply through the app.


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

> [!TIP]
> This tool becomes obsolete with the Energy Export capability that was built into the mobile App. Use the official export function preferably, which will also contain a daily breakdown per tracked energy type in your system.


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
