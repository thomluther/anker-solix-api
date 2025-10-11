#!/usr/bin/env python3
"""Example: C1000X MQTT integration with monitoring and control."""

import asyncio
import logging

from aiohttp import ClientSession
from api.api import AnkerSolixApi  # pylint: disable=no-name-in-module
import common

_LOGGER: logging.Logger = logging.getLogger(__name__)
CONSOLE: logging.Logger = common.CONSOLE


class C1000XController:
    """Example C1000X device controller using MQTT."""

    def __init__(self, api_instance: AnkerSolixApi, device_sn: str) -> None:
        """Initialize."""
        self.api = api_instance
        self.device_sn = device_sn
        self.last_battery_soc: int | None = None

    async def get_realtime_data(self):
        """Get real-time data from MQTT cache."""
        if self.api.mqttsession and hasattr(self.api.mqttsession, "mqtt_data"):
            return self.api.mqttsession.mqtt_data.get(self.device_sn, {})
        return {}

    async def monitor_battery_and_control(self):
        """Example: Monitor battery and automatically control outputs."""
        data = await self.get_realtime_data()
        battery_soc = data.get("battery_soc")

        if battery_soc is not None:
            CONSOLE.info(f"Battery SOC: {battery_soc}%")

            # Auto-control based on battery level
            if (
                battery_soc < 20
                and self.last_battery_soc
                and self.last_battery_soc >= 20
            ):
                # Battery dropped below 20% - disable non-essential outputs
                CONSOLE.info("Battery low - disabling AC output")
                await self.api.set_c1000x_ac_output(self.device_sn, False)

                # Set display to low brightness
                await self.api.set_c1000x_display_mode(self.device_sn, "low")

            elif (
                battery_soc > 80
                and self.last_battery_soc
                and self.last_battery_soc <= 80
            ):
                # Battery above 80% - enable outputs
                CONSOLE.info("Battery sufficient - enabling AC output")
                await self.api.set_c1000x_ac_output(self.device_sn, True)

                # Set display to high brightness
                await self.api.set_c1000x_display_mode(self.device_sn, "high")

            self.last_battery_soc = battery_soc

        # Show other data
        temperature = data.get("temperature")
        if temperature is not None:
            CONSOLE.info(f"Temperature: {temperature}°C")

        power_data = {
            "AC Output": data.get("ac_output_power", 0),
            "USB-C 1": data.get("usbc_1_power", 0),
            "USB-C 2": data.get("usbc_2_power", 0),
            "USB-A 1": data.get("usba_1_power", 0),
            "USB-A 2": data.get("usba_2_power", 0),
            "DC Input": data.get("dc_input_power", 0),
        }

        active_outputs = {k: v for k, v in power_data.items() if v > 0}
        if active_outputs:
            CONSOLE.info(f"Active outputs: {active_outputs}")

    async def emergency_mode(self):
        """Example: Set device to emergency mode."""
        CONSOLE.info("Activating emergency mode...")

        # Enable backup charge to maintain 100%
        await self.api.set_c1000x_backup_charge(self.device_sn, True)

        # Set display to always on, high brightness
        await self.api.set_c1000x_display(self.device_sn, True)
        await self.api.set_c1000x_display_mode(self.device_sn, "high")

        # Enable blinking light for visibility
        await self.api.set_c1000x_light_mode(self.device_sn, "blinking")

        # Ensure AC output is enabled
        await self.api.set_c1000x_ac_output(self.device_sn, True)

        CONSOLE.info("Emergency mode activated")

    async def normal_mode(self):
        """Example: Return device to normal operation."""
        CONSOLE.info("Returning to normal mode...")

        # Disable backup charge for normal use
        await self.api.set_c1000x_backup_charge(self.device_sn, False)

        # Set display to medium brightness
        await self.api.set_c1000x_display_mode(self.device_sn, "medium")

        # Turn off light
        await self.api.set_c1000x_light_mode(self.device_sn, "off")

        # Enable smart modes for efficiency
        await self.api.set_c1000x_ac_output_mode(self.device_sn, "smart")
        await self.api.set_c1000x_dc_output_mode(self.device_sn, "smart")

        CONSOLE.info("Normal mode activated")


async def main():
    """Main example demonstrating C1000X MQTT integration."""
    async with ClientSession() as websession:
        # Initialize API
        myapi = AnkerSolixApi(
            common.user(), common.password(), common.country(), websession, _LOGGER
        )

        # Update device information
        CONSOLE.info("Checking for C1000X devices...")
        await myapi.update_sites()
        await myapi.update_device_details()

        # Find C1000X device
        device_sn = None
        for sn, device in myapi.devices.items():
            if device.get("device_pn") == "A1761":
                device_sn = sn
                CONSOLE.info(f"Found C1000X device: {sn}")
                break

        if not device_sn:
            CONSOLE.info("No C1000X device found")
            return

        # Initialize controller
        controller = C1000XController(myapi, device_sn)

        # Start MQTT session for real-time data
        mqtt_session = await myapi.startMqttSession()
        if not mqtt_session:
            CONSOLE.info("Failed to start MQTT session")
            return

        CONSOLE.info("\n=== C1000X MQTT Integration Example ===")

        # Example 1: Set up device for normal operation
        CONSOLE.info("\n1. Setting up normal operation mode")
        await controller.normal_mode()

        # Example 2: Demonstrate various controls
        CONSOLE.info("\n2. Testing various controls")

        # Cycle through display modes
        modes = ["low", "medium", "high"]
        for mode in modes:
            CONSOLE.info(f"Setting display to {mode}")
            await myapi.set_c1000x_display_mode(device_sn, mode)
            await asyncio.sleep(1)

        # Example 3: Monitor data for a short period
        CONSOLE.info("\n3. Monitoring device for 30 seconds...")

        # Enable real-time data trigger if needed
        try:
            device_dict = {"device_sn": device_sn, "device_pn": "A1761"}
            mqtt_session.realtime_trigger(device_dict, timeout=300)
            CONSOLE.info("Real-time data trigger sent")
        except Exception as e:  # pylint: disable=broad-exception-caught  # noqa: BLE001
            CONSOLE.info(f"Could not trigger real-time data: {e}")

        # Monitor for a short period
        for i in range(6):  # 30 seconds
            await asyncio.sleep(5)
            await controller.monitor_battery_and_control()
            CONSOLE.info(f"Monitoring cycle {i + 1}/6 completed")

        # Example 4: Emergency mode demonstration
        CONSOLE.info("\n4. Demonstrating emergency mode")
        await controller.emergency_mode()
        await asyncio.sleep(3)

        # Return to normal
        CONSOLE.info("\n5. Returning to normal mode")
        await controller.normal_mode()

        CONSOLE.info("\n=== Integration Example Complete ===")
        CONSOLE.info("Key benefits of MQTT-based control:")
        CONSOLE.info("- Real-time data updates (3-5 second intervals)")
        CONSOLE.info("- Reliable command delivery")
        CONSOLE.info("- Efficient battery management")
        CONSOLE.info("- Immediate response to device state changes")


if __name__ == "__main__":
    try:
        asyncio.run(main(), debug=False)
    except Exception as err:  # pylint: disable=broad-exception-caught  # noqa: BLE001
        CONSOLE.info(f"{type(err)}: {err}")
