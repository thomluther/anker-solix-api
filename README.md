<img src="https://public-aiot-fra-prod.s3.dualstack.eu-central-1.amazonaws.com/anker-power/public/product/anker-power/e9478c2d-e665-4d84-95d7-dd4844f82055/20230719-144818.png" alt="Solarbank E1600 Logo" title="Anker Solix Api" align="right" height="100" />

# Anker Solix Api

[![github licence](https://img.shields.io/badge/Licence-MIT-orange)](https://github.com/thomluther/anker-solix-api/blob/main/LICENSE)
![python badge](https://img.shields.io/badge/Made%20with-Python-orange)

This is an experimental Python library for Anker Solix Power devices (Solarbank, Inverter etc).

🚨 This is by no means an official Anker Api. 🚨

🚨 It can break at any time, or Api request can be removed/added/changed and break some of the endpoint methods used in this Api.🚨

# Python Versions

The library is currently supported on

- Python 3.11
- Python 3.12

# Required libraries

This project uses `pipenv` for Python dependency management

```bash
pip install pipenv
pipenv sync -d
pipenv run python [...]
```

# Anker Account Information

Because of the way the Anker Solix Api works, one account with email/password cannot be used for the Anker mobile App and this Api in parallel.
The Anker Cloud allows only one request token per account at any time. Each new authentication request by a client will create a new token and drop a previous token.
Therefore usage of this Api may kick out your account login in the mobile app.
However, starting with Anker mobile app release 2.0, you can share your defined system(s) with 'family members'.
Therefore it is recommended to create a second Anker account with a different email address and share your defined system(s) with the second account.
Attention: A shared account is only a member of the shared system, and as such currently has no permissions to access or query device details of the shared system.
Therefore an Api homepage query will neither display any data for a shared account. However, a shared account can receive Api scene/site details of shared systems (App system = Api site),
which is equivalent to what is displayed in the mobile app on the home screen for the selected system.

# Usage

Everything starts with an:
[aiohttp](https://aiohttp.readthedocs.io/en/stable/) `ClientSession`:

```python
import logging, json
import asyncio
from aiohttp import ClientSession
from api import api, errors
import common

_LOGGER: logging.Logger = logging.getLogger(__name__)
# _LOGGER.setLevel(logging.DEBUG)    # enable for detailed Api output


async def main() -> None:
    """Create the aiohttp session and run the example."""
    async with ClientSession() as websession:
        """put your code here, example"""
        myapi = api.AnkerSolixApi(
            common.user(), common.password(), common.country(), websession, _LOGGER
        )
        await myapi.update_sites()
        await myapi.update_site_details()
        await myapi.update_device_details()
        await myapi.update_device_energy()
        print("System Overview:")
        print(json.dumps(myapi.sites, indent=2))
        print("Device Overview:")
        print(json.dumps(myapi.devices, indent=2))


# run async main
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as err:
        print(f"{type(err)}: {err}")
```

The AnkerSolixApi class provides 4 main methods to query data and cache them into internal dictionaries:

- `AnkerSolixApi.update_sites()` to query overview data for all accessible sites and store data in dictionaries `AnkerSolixApi.sites` and `AnkerSolixApi.devices` for quick access.
  This method could be run in regular intervals (60sec or more) to fetch new data of the systems. Note that the system devices update the cloud data only once per minute, therefore less than 60 second intervals do not provide much benefit
- `AnkerSolixApi.update_device_details()` to query further settings for the device serials as found in the sites query or for stand alone devices and store data in dictionary `AnkerSolixApi.devices`
  This method should be run less frequently since this will mostly fetch various device configuration settings and needs multiple queries.
  It currently is developped for Solarbank and Inverter devices only, further device types such as Portable Power Stations or Power Panels
  could be added once example data is available.
- `AnkerSolixApi.update_site_details()` to query further settings for the defined site (power system) and store data in dictionary `AnkerSolixApi.sites` for quick access.
  This method should be run less frequently since this will mostly fetch various site configuration settings and needs multiple queries.
- `AnkerSolixApi.update_device_energy()` to query further energy statistics for the devices and store data in dictionary `AnkerSolixApi.devices` for quick access.
  This method should be run less frequently since this will fetch 2-4 queries per device. Currently only solarbank devices are supported, but it was noticed, that the energy statistics endpoint (maybe each endpoint) is limited to 25-30 queries per minute.

Check out `test_api.py` and other python executable tools that may help to leverage and explore the Api for your Anker power system.
The subfolder [`examples`](https://github.com/thomluther/anker-solix-api/tree/main/examples) contains actual example exports with json files using anonymized responses of the `export_system.py` module giving you an idea of how various Api responses look like.
Those json files can also be used to develop/debug the Api for system constellations not available to the developper.

# AnkerSolixApi Tools

## test_api.py

```
> pipenv run ./test_api.py
```

Example exec module that can be used to explore and test AnkerSolixApi methods or direct enpoint requests with parameters. You can modify this module as required. Optionally you can create your own test file called `client.py` which is not indexed and added to gitignore, so your local changes are not tracked for git updates/commits.
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
Upon successfull authentication, you can specify a subfolder for the exported JSON files received as Api query response, defaulting to your nick name
Optionally you can specify whether personalized information in the response data should be randomized in the files, like SNs, Site IDs, Trace IDs etc.
You can review the response files afterwards. They can be used as examples for dedicated data extraction from the devices.
Optionally the AnkerSolixApi class can use the json files for debugging and testing on various system outputs.

**Note**:

You should preferrably run the export_system with the owner account of the site. Otherwise only limited information can be exported by shared accounts due to access permissions.

## solarbank_monitor.py

```
> pipenv run ./solarbank_monitor.py
```

Example exec module to use the Anker Api for continously querying and displaying important solarbank parameters.
This module will can use real time data from your Anker account, or optionally use json files from your local examples or export folder.
When using the real time option, it will prompt for the Anker account details if not pre-set in the header or defined in environment variables.
Upon successfull authentication, you will see the solarbank parameters displayed and refreshed at reqular interval.
When using monitoring from local json file folder, they values will not change. But this option is useful to validate the api parsing with various system constellations.

Note: When the system owning account is used, more details for the solarbank can be queried and displayed.

**Attention: When executing this module with real time data from your Anker account, the used account cannot be used in the Anker App since it will be kicked out on each refresh.**

## energy_csv.py

```
> pipenv run ./energy_csv.py
```

Example exec module to use the Anker Api for export of daily Solarbank Energy Data.
This method will prompt for the Anker account details if not pre-set in the header.
Then you can specify a start day and the number of days for data extraction from the Anker Cloud.
Note: The Solar production and Solarbank discharge can be queried across the full range. The solarbank
charge however can be queried only as total for an interval (e.g. day). Therefore when solarbank charge
data is also selected for export, an additional Api query per day is required.
The received daily values will be exported into a csv file.

# Contributing

![github contributors](https://img.shields.io/github/contributors/thomluther/anker-solix-api?color=orange)
![last commit](https://img.shields.io/github/last-commit/thomluther/anker-solix-api?color=orange)
[![Community Discussion](https://img.shields.io/badge/Home%20Assistant%20Community-Discussion-orange)](https://community.home-assistant.io/t/feature-request-integration-or-addon-for-anker-solix-e1600-solarbank/641086)

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
