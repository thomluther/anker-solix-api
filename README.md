<img src="https://public-aiot-fra-prod.s3.dualstack.eu-central-1.amazonaws.com/anker-power/public/product/anker-power/e9478c2d-e665-4d84-95d7-dd4844f82055/20230719-144818.png" alt="Solarbank E1600 Logo" title="Anker Solix API" align="right" height="60" />

# Anker Solix API

[![github licence](https://img.shields.io/badge/Licence-MIT-orange)](https://github.com/thomluther/anker-solix-api/blob/main/LICENSE)
![python badge](https://img.shields.io/badge/Made%20with-Python-orange)

This is an experimental Python library for Anker Solix Power devices (Solarbank, Inverter etc).

🚨 This is by no means an official Anker API. 🚨
🚨 It can break at any time, or API request can be removed/added/changed and break some of the endpoint methods used in this API.🚨

# Python Versions

The library is currently supported on

* Python 3.11
* Python 3.12

# Required libraries

```bash
pip install cryptography
pip install aiohttp
```

# Anker Account Information

Because of the way the Anker Solix API works, one account with email/password combo cannot be used for the Anker mobile App work and this API in parallel.
The Anker Cloud allows only one account token at a time, each new authentication request will create a new token and drop a previous token.
It is recommended to create a second Anker account and share your Power System(s) with the second account.
Attention: A shared account is only a member of the shared site, and as such currently has no permissions to access or query device details. However, a shared account 
can receive the data as provided in the scene/site details, which is equivalent to what is displayed in the mobile App on the Home screen for the selected system.

# Usage

Everything starts with an:
[aiohttp](https://aiohttp.readthedocs.io/en/stable/) `ClientSession`:

```python
import asyncio
from aiohttp import ClientSession
import logging, json

_LOGGER: logging.Logger = logging.getLogger(__name__)

async def main() -> None:
    """Create the aiohttp session and run the example."""
    async with ClientSession() as websession:
        """put your code here, example"""
        myapi = api.API("username@domain.com","password","de",websession, _LOGGER)
        await myapi.update_sites()
        await myapi.update_device_details()
        print("System Overview:")
        print(json.dumps(myapi.sites, indent=2))
        print("Device Overview:")
        print(json.dumps(myapi.devices, indent=2))

"""run async main"""
if __name__ == '__main__':
    try:
        asyncio.run(main())
    except Exception as err:
        print(f'{type(err)}: {err}')
```

Check out `test_api.py` and other python executable tools that may help to leverage and explore the API.
The subfolder examples contains json files with anonymized responses of the export_system.py module giving you an idea of how various API responses look like.
Those json files can also be used to develop/debug the API for system constellations not available to the developper.

# API Tools

## test_api.py

Example exec module that can be used to explore and test API methods or direct enpoint requests with parameters.

## export_system.py

Example exec module to use the Anker API for export of defined system data and device details.
This module will prompt for the Anker account details if not pre-set in the header.
Upon successfull authentication, you can specify a subfolder for the exported JSON files received as API query response, defaulting to your nick name
Optionally you can specify whether personalized information in the response data should be randomized in the files, like SNs, Site IDs, Trace IDs etc.
You can review the response files afterwards. They can be used as examples for dedicated data extraction from the devices.
Optionally the API class can use the json files for debugging and testing on various system outputs.

## solarbank_monitor.py

Example exec module to use the Anker API for continously querying and displaying important solarbank parameters
This module will prompt for the Anker account details if not pre-set in the header.
Upon successfull authentication, you will see the solarbank parameters displayed and refreshed at reqular interval.
Note: When the system owning account is used, more details for the solarbank can be queried and displayed.
Attention: During executiion of this module, the used account cannot be used in the Anker App since it will be kicked out on each refresh.

## energy_csv.py

Example exec module to use the Anker API for export of daily Solarbank Energy Data.
This method will prompt for the Anker account details if not pre-set in the header.
Then you can specify a start day and the number of days for data extraction from the Anker Cloud.
Note: The Solar production and Solarbank discharge can be queried across the full range. The solarbank
charge however can be queried only as total for an interval (e.g. day). Therefore when solarbank charge
data is also selected for export, an additional API query per day is required.
The received daily values will be exported into a csv file.


# Contributing

![github contributors](https://img.shields.io/github/contributors/thomluther/anker-solix-api?color=orange)
![last commit](https://img.shields.io/github/last-commit/thomluther/anker-solix-api?color=orange)
[![Community Discussion](https://img.shields.io/badge/Home%20Assistant%20Community-Discussion-orange)](https://community.home-assistant.io/t/feature-request-integration-or-addon-for-anker-solix-e1600-solarbank/641086)

1. [Check for open features/bugs](https://github.com/thomluther/anker-solix-api/issues)
  or [initiate a discussion on one](https://github.com/thomluther/anker-solix-api/issues/new).
2. [Fork the repository](https://github.com/thomluther/anker-solix-api/fork).
3. Install the dev environment: `make init`.
4. Enter the virtual environment: `source ./venv/bin/activate`
5. Code your new feature or bug fix.
6. Write a test that covers your new functionality.
7. Update `README.md` with any new documentation.
8. Run tests and ensure 100% code coverage: `make coverage`
9. Ensure you have no linting errors: `make lint`
10. Ensure you have typed your code correctly: `make typing`
11. Submit a pull request!


# Acknowledgements / Credits

[python-eufy-security](https://github.com/FuzzyMistborn/python-eufy-security)
[solix2mqtt](https://github.com/tomquist/solix2mqtt)


# Showing Your Appreciation

If you like this project, please give it a star on [GitHub](https://github.com/thomluther/anker-solix-api) 