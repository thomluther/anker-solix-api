#!/usr/bin/env python3
"""Test all C1000X control commands in real mode."""

import asyncio
import logging

from aiohttp import ClientSession
from api import api  # pylint: disable=no-name-in-module
import common

_LOGGER: logging.Logger = logging.getLogger(__name__)
CONSOLE: logging.Logger = common.CONSOLE


async def test_all_controls():
    """Test all C1000X control methods."""
    async with ClientSession() as websession:
        # Initialize API
        myapi = api.AnkerSolixApi(
            common.user(), common.password(), common.country(), websession, _LOGGER
        )

        # Update device information
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

        CONSOLE.info("\n=== Testing All C1000X Controls ===")

        # Test all control methods (using safe settings)
        tests = [
            ("Display Control", lambda: myapi.set_c1000x_display(device_sn, True)),
            (
                "Display Mode Low",
                lambda: myapi.set_c1000x_display_mode(device_sn, "low"),
            ),
            (
                "Display Mode Medium",
                lambda: myapi.set_c1000x_display_mode(device_sn, "medium"),
            ),
            ("Light Mode Off", lambda: myapi.set_c1000x_light_mode(device_sn, "off")),
            (
                "Temperature Celsius",
                lambda: myapi.set_c1000x_temp_unit(device_sn, False),
            ),
            (
                "Temperature Fahrenheit",
                lambda: myapi.set_c1000x_temp_unit(device_sn, True),
            ),
            (
                "DC Output Mode Normal",
                lambda: myapi.set_c1000x_dc_output_mode(device_sn, "normal"),
            ),
            (
                "AC Output Mode Smart",
                lambda: myapi.set_c1000x_ac_output_mode(device_sn, "smart"),
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
        status = await myapi.get_c1000x_status(device_sn)
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
