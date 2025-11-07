#!/usr/bin/env python3
"""Example: Basic A1790P device control via MQTT."""

from dotenv import load_dotenv
load_dotenv()

import asyncio
import logging
from aiohttp import ClientSession
import contextlib

from api.api import AnkerSolixApi
from api.mqtt_f3800 import SolixMqttDeviceF3800
import common

_LOGGER: logging.Logger = logging.getLogger(__name__)
CONSOLE: logging.Logger = common.CONSOLE

async def main():
    """Example of controlling A1790P device via MQTT."""
    async with ClientSession() as websession:
        # Initialize API
        myapi = AnkerSolixApi(
            common.user(), common.password(), common.country(), websession, _LOGGER
        )

        # Update device information
        await myapi.update_sites()
        await myapi.update_device_details()

        # Find A1790P device
        device_sn = None
        for sn, device in myapi.devices.items():
            if device.get("device_pn") == "A1790P":
                device_sn = sn
                CONSOLE.info(f"Found A1790P device: {sn}")
                break

        if not device_sn:
            CONSOLE.info("No A1790P device found")
            return

        # Initialize device control using F3800 MQTT device class
        mqttdevice = SolixMqttDeviceF3800(api_instance=myapi, device_sn=device_sn)

        # Start MQTT session for real-time data
        mqtt_session = await myapi.startMqttSession()
        if not mqtt_session:
            CONSOLE.info("Failed to start MQTT session")
            return

        # Example commands using F3800 wrapper methods
        try:
            # Generate AC output ON hex (test mode, no publish)
            CONSOLE.info("\nGenerating AC output ON hex (test mode, no publish)...")
            await mqttdevice.set_ac_output(enabled=True, toFile=True)
            await asyncio.sleep(1)

            # Turn on 12V DC Car output (wrapper)
            CONSOLE.info("\nTurning 12V DC (Car) output ON...")
            result = await mqttdevice.set_dc_output(enabled=True)
            CONSOLE.info(f"Result: {'Success' if result else 'Failed'}")
            await asyncio.sleep(2)

            # Turn light ON (wrapper)
            CONSOLE.info("\nTurning light ON...")
            result = await mqttdevice.set_light(mode=1)  # 1=Low, 2=Medium, 3=High, 4=Blinking
            CONSOLE.info(f"Result: {'Success' if result else 'Failed'}")
            await asyncio.sleep(2)

            # Set screen ON (wrapper)
            CONSOLE.info("\nTurning screen ON...")
            result = await mqttdevice.set_display(enabled=True)
            CONSOLE.info(f"Result: {'Success' if result else 'Failed'}")
            await asyncio.sleep(2)

            # Set brightness HIGH (wrapper)
            CONSOLE.info("\nSetting brightness to HIGH...")
            result = await mqttdevice.set_display_mode(mode=3)  # 3=High
            CONSOLE.info(f"Result: {'Success' if result else 'Failed'}")
            await asyncio.sleep(2)

            # Temporarily change max load to 1000W, wait 5 seconds, then restore to 200W
            CONSOLE.info("\nTemporarily setting max load to 1000W for 5 seconds...")
            result = await mqttdevice.set_max_load(max_watts=1000)
            CONSOLE.info(f"Set max load to 1000W: {'Success' if result else 'Failed'}")
            await asyncio.sleep(5)

            CONSOLE.info("Restoring max load to 200W...")
            result = await mqttdevice.set_max_load(max_watts=200)
            CONSOLE.info(f"Restore max load to 200W: {'Success' if result else 'Failed'}")
            await asyncio.sleep(2)

            # Set Real-Time Data ON (not implemented in wrapper yet)
            # You may add a wrapper for this in the future

            # Return to normal settings
            CONSOLE.info("\nReturning to normal settings...")
            await mqttdevice.set_display(enabled=False)
            await mqttdevice.set_light(mode=0)
            await mqttdevice.set_dc_output(enabled=False)
            CONSOLE.info("Done!")

        except Exception as e:
            CONSOLE.error(f"Error during device control: {e}")
        finally:
            # Clean up
            if mqtt_session and mqtt_session.client:
                mqtt_session.cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        CONSOLE.info("\nOperation cancelled by user")
    except Exception as err:
        CONSOLE.error(f"Error: {err}")