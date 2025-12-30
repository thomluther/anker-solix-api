#!/usr/bin/env python3
"""Test script for C1000X MQTT-based controls."""

import asyncio
import logging
from pathlib import Path  # noqa: F401
import traceback

from aiohttp import ClientSession
from api.api import AnkerSolixApi  # pylint: disable=no-name-in-module
from api.mqtt_factory import SolixMqttDeviceFactory  # pylint: disable=no-name-in-module
from api.mqtt_pps import SolixMqttDevicePps  # pylint: disable=no-name-in-module
import common

_LOGGER: logging.Logger = logging.getLogger(__name__)
CONSOLE: logging.Logger = common.CONSOLE
FOLDER = None
# Specify FOLDER with system export including MQTT messages for testing from files
#FOLDER = Path(__file__).parent / "exports" / "Mqtt_C1000_Gen2"
#FOLDER = Path(__file__).parent / "exports" / "Mqtt_C1000_Expansion"


async def test_c1000x_mqtt_controls() -> None:  # noqa: C901
    """Test C1000X MQTT control functionality."""
    async with ClientSession() as websession:
        # Initialize API
        myapi = AnkerSolixApi(
            common.user(), common.password(), common.country(), websession, _LOGGER
        )
        if use_file := bool(FOLDER):
            myapi.testDir(FOLDER)
        # File poller task
        mqtt_task: asyncio.Task | None = None

        # Update device information to get C1000X device
        await myapi.update_sites(fromFile=use_file)
        await myapi.update_device_details(fromFile=use_file)

        # Find C1000X device
        device_sn = None
        for sn, device in myapi.devices.items():
            if device.get("device_pn") in ["A1761", "A1763", "A1765"]:
                device_sn = sn
                CONSOLE.info(f"Found C1000X device: {sn}")
                break
        if not device_sn:
            CONSOLE.info("No C1000X device found")
            return

        # create MQTT device
        mqttdevice: SolixMqttDevicePps = SolixMqttDeviceFactory(
            api_instance=myapi, device_sn=device_sn
        ).create_device()

        # Test 1: MQTT Connection and Sensor Data
        CONSOLE.info("\n--- Testing MQTT Connection and Sensor Data ---")
        CONSOLE.info("Note: These require device to be online and MQTT connected")
        try:
            # Start MQTT session
            CONSOLE.info("Starting MQTT session...")
            mqtt_session = await myapi.startMqttSession(fromFile=use_file)
            if mqtt_session:
                CONSOLE.info("✓ MQTT session started successfully")
                # FORCE immediate data collection via update trigger if connected
                if mqtt_session.is_connected():
                    CONSOLE.info("✓ MQTT session connected, subscribing device...")
                    topic = f"{mqtt_session.get_topic_prefix(deviceDict=mqttdevice.device)}#"
                    resp = mqtt_session.subscribe(topic)
                    if resp and resp.is_failure:
                        CONSOLE.info(f"✗ Failed subscription for topic: {topic}")
                    CONSOLE.info("Forcing immediate device data update...")
                    if await mqttdevice.realtime_trigger(timeout=60):
                        CONSOLE.info("✓ Update trigger published successfully")
                    else:
                        CONSOLE.info("✗ Failed to send update trigger")
                elif use_file:
                    # Create task for polling mqtt messages from files for testing
                    mqtt_task = asyncio.get_running_loop().create_task(
                        mqtt_session.file_poller(
                            folderdict={"folder": FOLDER},
                            speed=1,
                        )
                    )
                    CONSOLE.info("✓ MQTT file data poller task was started.")
                else:
                    CONSOLE.info("✗ MQTT not connected - cannot force device update")
                # Wait for data to be collected (shorter timeout since we forced update)
                max_wait = 30
                CONSOLE.info(f"Waiting for MQTT data collection (up to {max_wait} seconds)...")
                for i in range(max_wait):
                    await asyncio.sleep(1)

                    # Check if we have MQTT data
                    if mqttdevice.mqttdata:
                        CONSOLE.info(f"✓ MQTT data collected after {i + 1} seconds")
                        break

                    # Show progress every 5 seconds
                    if i % 5 == 4:
                        CONSOLE.info(f"  Still waiting for data... ({i + 1}/{max_wait})")
                        if mqtt_session.mqtt_stats:
                            msg_count = mqtt_session.mqtt_stats.dev_messages.get(
                                "count", 0
                            )
                            bytes_received = mqtt_session.mqtt_stats.bytes_received
                            CONSOLE.info(
                                f"  MQTT messages received: {msg_count}, bytes: {bytes_received}"
                            )

                        # Show device WiFi status
                        wifi_status = mqttdevice.device.get("wifi_online", "Unknown")
                        is_online = mqttdevice.device.get("is_online", "Unknown")
                        CONSOLE.info(
                            f"  Device online: {is_online}, WiFi: {wifi_status}"
                        )
                else:
                    CONSOLE.info(
                        "⚠ No data received - device may be offline or not responding to triggers"
                    )

                # Comprehensive sensor data dump
                CONSOLE.info("\n=== SENSOR DATA DUMP ===")
                # Dump data for our C1000X device
                raw_data = mqtt_session.mqtt_data.get(device_sn, {})
                if mqttdevice.mqttdata:
                    CONSOLE.info(f"\n--- C1000X {device_sn} Sensor Data ---")

                    # Power monitoring fields
                    power_fields = {
                        "grid_to_battery_power": "AC charging power to battery (W)",
                        "ac_output_power": "Individual AC outlet power (W)",
                        "output_power_total": "Total combined output power (W)",
                        "usbc_1_power": "USB-C port 1 output power (W)",
                        "usbc_2_power": "USB-C port 2 output power (W)",
                        "usba_1_power": "USB-A port 1 output power (W)",
                        "usba_2_power": "USB-A port 2 output power (W)",
                        "dc_input_power": "DC input power - solar/car charging (W)",
                    }
                    CONSOLE.info("Power Monitoring:")
                    for field, description in power_fields.items():
                        value = mqttdevice.mqttdata.get(field, "N/A")
                        CONSOLE.info(f"  {field}: {value} - {description}")

                    # Battery status fields
                    battery_fields = {
                        "battery_soc": "Main battery state of charge (%)",
                        "exp_1_soc": "Expansion battery 1 state of charge (%)",
                        "battery_soh": "Main battery state of health (%)",
                        "exp_1_soh": "Expansion battery 1 state of health (%)",
                    }
                    CONSOLE.info("\nBattery Status:")
                    for field, description in battery_fields.items():
                        value = mqttdevice.mqttdata.get(field, "N/A")
                        CONSOLE.info(f"  {field}: {value} - {description}")

                    # Temperature monitoring
                    temp_fields = {
                        "temperature": "Main device temperature (°C)",
                        "exp_1_temperature": "Expansion battery 1 temperature (°C)",
                    }
                    CONSOLE.info("\nTemperature Monitoring:")
                    for field, description in temp_fields.items():
                        value = mqttdevice.mqttdata.get(field, "N/A")
                        CONSOLE.info(f"  {field}: {value} - {description}")

                    # Control switches and modes
                    control_fields = {
                        "ac_output_power_switch": "AC output switch (0=Disabled, 1=Enabled)",
                        "dc_output_power_switch": "12V DC output switch (0=Disabled, 1=Enabled)",
                        "display_switch": "Display switch (0=Off, 1=On)",
                        "backup_charge_switch": "Backup charge mode (0=Off, 1=On)",
                        "temp_unit_fahrenheit": "Temperature unit (0=Celsius, 1=Fahrenheit)",
                        "display_mode": "Display brightness (0=Off, 1=Low, 2=Medium, 3=High)",
                        "light_mode": "LED light mode (0=Off, 1=Low, 2=Medium, 3=High, 4=Blinking)",
                        "dc_12v_output_mode": "12V DC mode (1=Normal, 2=Smart)",
                        "ac_output_mode": "AC output mode (1=Normal, 2=Smart)",
                    }
                    CONSOLE.info("\nControl Switches and Modes:")
                    for field, description in control_fields.items():
                        value = mqttdevice.mqttdata.get(field, "N/A")
                        CONSOLE.info(f"  {field}: {value} - {description}")

                    # Device information
                    device_fields = {
                        "sw_version": "Main firmware version",
                        "sw_expansion": "Expansion firmware version",
                        "sw_controller": "Controller firmware version",
                        "hw_version": "Hardware version",
                        "device_sn": "Device serial number",
                        "max_load": "Maximum load setting (W)",
                        "device_timeout_minutes": "Device auto-off timeout (minutes)",
                        "display_timeout_seconds": "Display timeout (seconds)",
                        "exp_1_type": "Expansion battery type identifier",
                        "msg_timestamp": "Message timestamp",
                    }
                    CONSOLE.info("\nDevice Information:")
                    for field, description in device_fields.items():
                        value = mqttdevice.mqttdata.get(field, "N/A")
                        CONSOLE.info(f"  {field}: {value} - {description}")

                    # Raw data dump
                    CONSOLE.info(f"\nAll Raw MQTT Data ({len(raw_data)} fields):")
                    for key, value in sorted(raw_data.items()):
                        CONSOLE.info(f"  {key}: {value}")

                else:
                    CONSOLE.info(f"No MQTT data available for device {device_sn}")
                    CONSOLE.info("This could mean:")
                    CONSOLE.info("  - Device is offline or not connected")
                    CONSOLE.info("  - MQTT session hasn't received data yet")
                    CONSOLE.info("  - Device isn't sending MQTT messages")

                # Test 3: Control Commands with Verification (only if we have MQTT data)
                if mqttdevice.get_status(fromFile=use_file):
                    CONSOLE.info(
                        "\n--- Testing MQTT Control Commands with Verification ---"
                    )

                    def get_current_values():
                        """Get current device values from MQTT data."""
                        return {
                            "temp_unit": mqttdevice.get_status(fromFile=use_file).get(
                                "temp_unit_fahrenheit", 0
                            ),
                            "display": mqttdevice.get_status(fromFile=use_file).get(
                                "display_switch", 0
                            ),
                            "light_mode": mqttdevice.get_status(fromFile=use_file).get(
                                "light_mode", 0
                            ),
                        }

                    # Get initial values
                    initial_values = get_current_values()
                    CONSOLE.info(f"Initial values: {initial_values}")

                    # Test 1: Temperature unit toggle
                    CONSOLE.info("\n1. Testing temperature unit toggle...")
                    current_temp_unit = initial_values["temp_unit"]
                    new_temp_unit = not bool(current_temp_unit)  # Toggle
                    CONSOLE.info(
                        f"Current temp unit: {'Fahrenheit' if current_temp_unit else 'Celsius'}"
                    )
                    CONSOLE.info(
                        f"Setting to: {'Fahrenheit' if new_temp_unit else 'Celsius'}"
                    )
                    result = await mqttdevice.set_temp_unit(
                        unit="fahrenheit" if new_temp_unit else "celsius",
                        toFile=use_file,
                    )
                    CONSOLE.info(f"Command result: {'Success' if result else 'Failed'}")
                    if result:
                        # Wait for next update message in RT mode
                        CONSOLE.info("Waiting for device status update...")
                        await asyncio.sleep(3)  # Wait for update
                        new_values = get_current_values()
                        if new_values["temp_unit"] != initial_values["temp_unit"]:
                            CONSOLE.info(
                                f"✓ Temperature unit changed successfully: {new_values['temp_unit']}"
                            )
                        else:
                            CONSOLE.info(
                                f"⚠ Temperature unit may not have changed: {new_values['temp_unit']}"
                            )
                    await asyncio.sleep(3)

                    # Test 2: Display toggle
                    CONSOLE.info("\n2. Testing display toggle...")
                    current_display = get_current_values()["display"]
                    new_display = not bool(current_display)  # Toggle
                    CONSOLE.info(
                        f"Current display: {'On' if current_display else 'Off'}"
                    )
                    CONSOLE.info(f"Setting to: {'On' if new_display else 'Off'}")
                    result = await mqttdevice.set_display(
                        enabled=new_display, toFile=use_file
                    )
                    CONSOLE.info(f"Command result: {'Success' if result else 'Failed'}")
                    if result:
                        # Wait for next update message in RT mode
                        CONSOLE.info("Waiting for device status update...")
                        await asyncio.sleep(3)
                        new_values = get_current_values()
                        if new_values["display"] != current_display:
                            CONSOLE.info(
                                f"✓ Display state changed successfully: {'On' if new_values['display'] else 'Off'}"
                            )
                        else:
                            CONSOLE.info(
                                f"⚠ Display state may not have changed: {'On' if new_values['display'] else 'Off'}"
                            )
                    await asyncio.sleep(3)

                    # Test 3: Light mode cycle (safe, visible change)
                    CONSOLE.info("\n3. Testing light mode change...")
                    current_light = get_current_values()["light_mode"]
                    # Cycle through modes: 0=Off, 1=Low, 2=Medium, 3=High
                    new_light = (current_light + 1) % 4  # Cycle 0->1->2->3->0
                    light_names = ["Off", "Low", "Medium", "High"]
                    CONSOLE.info(
                        f"Current light mode: {light_names[current_light]} ({current_light})"
                    )
                    CONSOLE.info(f"Setting to: {light_names[new_light]} ({new_light})")
                    result = await mqttdevice.set_light(mode=new_light, toFile=use_file)
                    CONSOLE.info(f"Command result: {'Success' if result else 'Failed'}")
                    if result:
                        # Wait for next update message in RT mode
                        CONSOLE.info("Waiting for device status update...")
                        await asyncio.sleep(3)
                        new_values = get_current_values()
                        if new_values["light_mode"] != current_light:
                            CONSOLE.info(
                                f"✓ Light mode changed successfully: {light_names[new_values['light_mode']]} ({new_values['light_mode']})"
                            )
                        else:
                            CONSOLE.info(
                                f"⚠ Light mode may not have changed: {light_names[new_values['light_mode']]} ({new_values['light_mode']})"
                            )

                    # Test 4: Verify vs asking user
                    if not use_file:
                        CONSOLE.info("\n4. Manual verification...")
                        CONSOLE.info("Please check your C1000X device physically:")
                        CONSOLE.info("- Did the display state change?")
                        CONSOLE.info("- Did the LED light mode change?")
                        CONSOLE.info(
                            "- Is the temperature unit setting different in the display?"
                        )

                    # Final status check
                    CONSOLE.info("\nFinal device status:")
                    final_values = get_current_values()
                    for key, value in final_values.items():
                        CONSOLE.info(f"  {key}: {value}")

                else:
                    CONSOLE.info("\n--- Skipping Control Commands ---")
                    CONSOLE.info("No MQTT data received, device may not be connected")

            else:
                CONSOLE.info("✗ Failed to start MQTT session")
                CONSOLE.info("Troubleshooting steps:")
                CONSOLE.info(
                    "  1. Ensure device is powered on and connected to internet"
                )
                CONSOLE.info("  2. Check that account credentials are correct")
                CONSOLE.info("  3. Verify device is registered to your account")
                CONSOLE.info(
                    "  4. Try updating device details first: await myapi.update_sites()"
                )

            CONSOLE.info("\n=== Command Information ===")
            CONSOLE.info("C1000X uses MQTT-only controls with these commands:")
            CONSOLE.info(f"{list(mqttdevice.controls.keys())}")

        except Exception as e:  # pylint: disable=broad-exception-caught  # noqa: BLE001
            CONSOLE.info(f"MQTT error: {e}")
            CONSOLE.info(f"Full traceback: {traceback.format_exc()}")

        # Cleanup MQTT session
        if mqtt_task:
            mqtt_task.cancel()
            # Wait for the task to finish cancellation
            try:
                await mqtt_task
            except asyncio.CancelledError:
                CONSOLE.info("MQTT file data poller task was cancelled.")
        myapi.stopMqttSession()


if __name__ == "__main__":
    try:
        asyncio.run(test_c1000x_mqtt_controls(), debug=False)
    except Exception as err:  # pylint: disable=broad-exception-caught  # noqa: BLE001
        CONSOLE.info(f"{type(err)}: {err}")
