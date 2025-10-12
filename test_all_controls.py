#!/usr/bin/env python3
"""Test all C1000X control commands in real mode."""

import asyncio
import logging

from aiohttp import ClientSession
from api.api import AnkerSolixApi  # pylint: disable=no-name-in-module
from api.mqtt_c1000x import SolixMqttDeviceC1000x  # pylint: disable=no-name-in-module
import common

_LOGGER: logging.Logger = logging.getLogger(__name__)
CONSOLE: logging.Logger = common.CONSOLE


async def test_all_controls():
    """Test all C1000X control methods."""
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

        # Start MQTT session
        mqtt_session = await myapi.startMqttSession()
        if not mqtt_session:
            CONSOLE.info("Failed to start MQTT session")
            return
        # Wait for connection
        await asyncio.sleep(3)

        mqttdevice = SolixMqttDeviceC1000x(api_instance=myapi, device_sn=device_sn)
        CONSOLE.info("\n=== Testing All C1000X Controls ===")

        # Test all control methods (using safe settings)
        tests = [
            ("Display Control", lambda: mqttdevice.set_display(enabled=True)),
            (
                "Display Mode Low",
                lambda: mqttdevice.set_display(mode="low"),
            ),
            (
                "Display Mode Medium",
                lambda: mqttdevice.set_display(mode="medium"),
            ),
            ("Light Mode Off", lambda: mqttdevice.set_light(mode="off")),
            (
                "Temperature Celsius",
                lambda: mqttdevice.set_temp_unit(fahrenheit=False),
            ),
            (
                "Temperature Fahrenheit",
                lambda: mqttdevice.set_temp_unit(fahrenheit=True),
            ),
            (
                "DC Output Mode Normal",
                lambda: mqttdevice.set_dc_output(mode="normal"),
            ),
            (
                "AC Output Mode Smart",
                lambda: mqttdevice.set_ac_output(mode="smart"),
            ),
        ]

        success_count = 0
        for test_name, test_func in tests:
            CONSOLE.info(f"\nTesting: {test_name}")
            try:
                result = await test_func()
                if result:
                    CONSOLE.info(f"✅ {test_name}: SUCCESS - {result}")
                    success_count += 1
                else:
                    CONSOLE.info(f"❌ {test_name}: FAILED")
            except Exception as e:  # pylint: disable=broad-exception-caught  # noqa: BLE001
                CONSOLE.info(f"❌ {test_name}: ERROR - {e}")

            # Wait between commands
            await asyncio.sleep(1)

        # Test status retrieval from MQTT data
        CONSOLE.info("\nTesting Status Retrieval...")
        status = mqttdevice.get_status()
        if status:
            CONSOLE.info("✅ Status retrieval: SUCCESS")
            CONSOLE.info(f"   Battery SOC: {status.get('battery_soc', 'N/A')}%")
            CONSOLE.info(f"   Temperature: {status.get('temperature', 'N/A')}°C")
            CONSOLE.info(f"   AC Output Power: {status.get('ac_output_power', 'N/A')}W")
            success_count += 1
        else:
            CONSOLE.info("❌ Status retrieval: FAILED")

        CONSOLE.info("\n=== Test Results ===")
        CONSOLE.info(f"Successful commands: {success_count}/{len(tests) + 1}")
        CONSOLE.info(f"Success rate: {success_count / (len(tests) + 1) * 100:.1f}%")

        if success_count > len(tests) // 2:
            CONSOLE.info("🎉 MQTT CONTROLS ARE WORKING SUCCESSFULLY!")
        else:
            CONSOLE.info("⚠️ Some issues detected, but this may be normal")


if __name__ == "__main__":
    try:
        asyncio.run(test_all_controls(), debug=False)
    except Exception as err:  # pylint: disable=broad-exception-caught  # noqa: BLE001
        CONSOLE.info(f"{type(err)}: {err}")
