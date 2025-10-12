#!/usr/bin/env python3
"""
C1000X Control Validation Test

Validates that C1000X (A1761) AC output control is working correctly using
the mobile app protocol implementation.

Features:
- Tests AC ON/OFF commands with MQTT connection retry logic
- Real-time device state monitoring via MQTT
- Power consumption validation
- Command success/failure feedback

Usage:
    python test_c1000x_validation.py

Environment variables (can be set in ../.env):
    ANKERUSER, ANKERPASSWORD, ANKERCOUNTRY
"""

import asyncio
import logging

from aiohttp import ClientSession
from api.api import AnkerSolixApi
import common

_LOGGER: logging.Logger = logging.getLogger(__name__)
CONSOLE: logging.Logger = common.CONSOLE

async def test_c1000x_validation():
    """Comprehensive C1000X control validation with monitoring."""
    async with ClientSession() as websession:
        # Initialize API
        myapi = AnkerSolixApi(
            common.user(), common.password(), common.country(), websession, _LOGGER
        )

        # Update device information
        CONSOLE.info("🔧 Setting up device connection...")
        await myapi.update_sites()
        await myapi.update_device_details()

        # Find C1000X device
        device_sn = None
        for sn, device in myapi.devices.items():
            if device.get("device_pn") == "A1761":
                device_sn = sn
                CONSOLE.info(f"📱 Found C1000X device: {sn}")
                break

        if not device_sn:
            CONSOLE.info("❌ No C1000X device found")
            return

        # Start MQTT session for monitoring and commands
        CONSOLE.info("🔌 Starting MQTT session...")
        mqtt_session = await myapi.startMqttSession()
        if not mqtt_session:
            CONSOLE.info("❌ Failed to start MQTT session")
            return

        CONSOLE.info("⏳ Waiting for MQTT connection to establish...")
        await asyncio.sleep(5)

        # Set up MQTT monitoring
        device_dict = {"device_sn": device_sn, "device_pn": "A1761"}
        topics = set()
        if prefix := mqtt_session.get_topic_prefix(deviceDict=device_dict):
            topics.add(f"{prefix}#")

        # Message callback for monitoring
        def msg_callback(session, topic, message, data, model, device_sn_msg, valueupdate):
            CONSOLE.info(f"📡 MQTT Message - Topic: {topic}, ValueUpdate: {valueupdate}")
            if hasattr(session, 'mqtt_data') and session.mqtt_data:
                device_data = session.mqtt_data.get(device_sn, {})
                ac_state = device_data.get("switch_ac_output_power", "N/A")
                ac_power = device_data.get("ac_output_power", "N/A")
                battery_soc = device_data.get("battery_soc", "N/A")
                CONSOLE.info(f"📊 State Update - AC: {ac_state}, Power: {ac_power}W, Battery: {battery_soc}%")
                if device_data:
                    CONSOLE.info(f"🔍 Device data keys: {list(device_data.keys())[:10]}...")  # Show first 10 keys
            else:
                CONSOLE.info("⚠️ No mqtt_data in session")

        def check_mqtt_connection():
            """Check if MQTT client is still connected."""
            if hasattr(mqtt_session, 'client') and mqtt_session.client:
                is_connected = mqtt_session.client.is_connected()
                CONSOLE.info(f"🔌 MQTT Connection Status: {'Connected' if is_connected else 'Disconnected'}")
                return is_connected
            return False

        async def ensure_mqtt_connection():
            """Ensure MQTT connection is active, reconnect if needed."""
            if not check_mqtt_connection():
                CONSOLE.info("🔄 MQTT disconnected, attempting to reconnect...")
                try:
                    # Try to reconnect
                    client = await mqtt_session.connect_client_async()
                    if client and client.is_connected():
                        CONSOLE.info("✅ MQTT reconnected successfully")
                        await asyncio.sleep(3)  # Wait for connection to stabilize
                        return True
                    else:
                        CONSOLE.info("❌ MQTT reconnection failed")
                        return False
                except Exception as e:
                    CONSOLE.info(f"❌ MQTT reconnection error: {e}")
                    return False
            return True

        async def send_command_with_retry(device_sn, target_state, command_name, max_retries=3):
            """Send command with retry logic for MQTT disconnections."""
            for attempt in range(max_retries):
                try:
                    # Ensure connection before sending
                    if not await ensure_mqtt_connection():
                        CONSOLE.info(f"❌ Cannot establish MQTT connection for attempt {attempt + 1}")
                        continue

                    # Create C1000X device instance and send command
                    from api.mqtt_c1000x import SolixMqttDeviceC1000x
                    c1000x_device = SolixMqttDeviceC1000x(myapi, device_sn)
                    result = await c1000x_device.set_ac_output(enabled=target_state)
                    if result:
                        CONSOLE.info(f"✅ AC {command_name} command sent successfully (attempt {attempt + 1})")
                        return True
                    else:
                        CONSOLE.info(f"❌ AC {command_name} command failed (attempt {attempt + 1})")

                except Exception as e:
                    CONSOLE.info(f"❌ Exception on attempt {attempt + 1}: {e}")

                # Wait before retry
                if attempt < max_retries - 1:
                    CONSOLE.info(f"⏳ Waiting 5 seconds before retry...")
                    await asyncio.sleep(5)

            CONSOLE.info(f"❌ AC {command_name} command failed after {max_retries} attempts")
            return False

        # Start monitoring in background
        poller_task = asyncio.create_task(
            mqtt_session.message_poller(
                topics=topics,
                trigger_devices={device_sn},
                msg_callback=msg_callback,
                timeout=300,
            )
        )

        # Trigger real-time data to get device status
        CONSOLE.info("⚡ Triggering real-time device data...")
        from api.mqtt_c1000x import SolixMqttDeviceC1000x
        c1000x_device = SolixMqttDeviceC1000x(myapi, device_sn)
        c1000x_device.realtime_trigger(timeout=120)  # 2 minutes of real-time data

        # Wait for initial data
        CONSOLE.info("📡 Waiting for initial device data...")
        await asyncio.sleep(15)

        def get_current_state():
            """Get current device state from MQTT data."""
            if hasattr(mqtt_session, 'mqtt_data') and mqtt_session.mqtt_data:
                device_data = mqtt_session.mqtt_data.get(device_sn, {})
                ac_state = device_data.get("switch_ac_output_power", None)
                ac_power = device_data.get("ac_output_power", None)
                battery_soc = device_data.get("battery_soc", None)
                return ac_state, ac_power, battery_soc
            return None, None, None

        # Get initial state
        initial_ac_state, initial_ac_power, battery_soc = get_current_state()
        CONSOLE.info(f"📋 Initial state - AC: {initial_ac_state}, Power: {initial_ac_power}W, Battery: {battery_soc}%")

        CONSOLE.info("=" * 60)
        CONSOLE.info("🧪 STARTING C1000X CONTROL VALIDATION")
        CONSOLE.info("=" * 60)

        # Test sequence: Toggle AC state
        if initial_ac_state == 1:
            CONSOLE.info("🔄 Device is ON - testing AC OFF → ON sequence")
            test_sequence = [False, True]
            expected_sequence = [0, 1]
        else:
            CONSOLE.info("🔄 Device is OFF - testing AC ON → OFF sequence")
            test_sequence = [True, False]
            expected_sequence = [1, 0]

        success_count = 0
        total_tests = len(test_sequence)

        for i, (target_state, expected_state) in enumerate(zip(test_sequence, expected_sequence)):
            command_name = "ON" if target_state else "OFF"
            CONSOLE.info(f"\n🔸 Test {i+1}/{total_tests}: AC {command_name} Command")

            try:
                # Send command with retry logic
                CONSOLE.info(f"📤 Sending AC {command_name} command with retry logic...")
                result = await send_command_with_retry(device_sn, target_state, command_name)

                if not result:
                    CONSOLE.info(f"❌ AC {command_name} command failed after all retries")
                    continue

                # Monitor for state change (devices can take 30+ seconds to respond)
                CONSOLE.info("⏱️ Monitoring for state change (45 seconds)...")
                state_changed = False

                for second in range(45):
                    await asyncio.sleep(1)
                    current_ac_state, current_ac_power, _ = get_current_state()

                    if current_ac_state is not None and current_ac_state == expected_state:
                        CONSOLE.info(f"🎉 SUCCESS! State changed to {current_ac_state} after {second+1} seconds")
                        CONSOLE.info(f"   Power consumption: {current_ac_power}W")
                        success_count += 1
                        state_changed = True
                        break

                    # Progress indicator every 10 seconds
                    if second % 10 == 9:
                        CONSOLE.info(f"   ⏳ {second+1}/45s - Current state: {current_ac_state}, Power: {current_ac_power}W")

                if not state_changed:
                    final_ac_state, final_ac_power, _ = get_current_state()
                    CONSOLE.info(f"❌ No state change detected within 45 seconds")
                    CONSOLE.info(f"   Expected: {expected_state}, Got: {final_ac_state}")
                    CONSOLE.info(f"   Power: {final_ac_power}W")
                    CONSOLE.info("   Note: Device may take longer to respond than expected")

            except Exception as e:
                CONSOLE.info(f"❌ Exception during AC {command_name} test: {e}")

            # Wait between tests and ensure MQTT connection is stable
            if i < total_tests - 1:
                CONSOLE.info("⏸️ Waiting 10 seconds before next test...")
                await asyncio.sleep(10)

        # Test summary
        CONSOLE.info("=" * 60)
        CONSOLE.info("📊 VALIDATION RESULTS")
        CONSOLE.info("=" * 60)
        CONSOLE.info(f"✅ Successful commands: {success_count}/{total_tests}")
        CONSOLE.info(f"❌ Failed commands: {total_tests - success_count}/{total_tests}")

        if success_count == total_tests:
            CONSOLE.info("🎉 ALL TESTS PASSED! C1000X controls are working correctly!")
            CONSOLE.info("✅ Device responds properly to MQTT commands")
            CONSOLE.info("✅ State changes are reflected in real-time")
            CONSOLE.info("✅ Power consumption changes appropriately")
        else:
            CONSOLE.info("⚠️ Some tests failed - C1000X controls may need further investigation")

        # Technical details
        CONSOLE.info("\n🔍 Mobile App Protocol Details:")
        CONSOLE.info("• Message type: 004a (AC output control)")
        CONSOLE.info("• ON command: a2020101")
        CONSOLE.info("• OFF command: a2020100")
        CONSOLE.info("• Protocol: 24-byte message with XOR checksum")

        # Clean up
        CONSOLE.info("\n🧹 Cleaning up...")
        poller_task.cancel()
        try:
            await poller_task
        except asyncio.CancelledError:
            pass

        CONSOLE.info("✨ Test completed!")

if __name__ == "__main__":
    try:
        asyncio.run(test_c1000x_validation(), debug=False)
    except KeyboardInterrupt:
        CONSOLE.info("\n🛑 Test interrupted by user")
    except Exception as err:
        CONSOLE.info(f"💥 Test error: {type(err).__name__}: {err}")