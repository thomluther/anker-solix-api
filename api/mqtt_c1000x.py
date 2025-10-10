"""C1000X (A1761) device control methods for AnkerSolixApi.

This module contains control methods specific to the Anker C1000X (A1761) portable power station.
These methods provide comprehensive device control via MQTT commands.
C1000X devices use MQTT-only communication for control operations.
"""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .api import AnkerSolixApi


def validate_command_value(command_id: str, value: Any) -> bool:
    """Validate command value ranges for C1000X controls."""
    validation_rules = {
        "ac_output_control": lambda v: v in [0, 1],
        "dc_12v_output_control": lambda v: v in [0, 1],
        "display_control": lambda v: v in [0, 1],
        "backup_charge_control": lambda v: v in [0, 1],
        "temp_unit_control": lambda v: v in [0, 1],
        "display_mode_select": lambda v: v in [0, 1, 2, 3],
        "light_mode_select": lambda v: v in [0, 1, 2, 3, 4],
        "dc_output_mode_select": lambda v: v in [1, 2],
        "ac_output_mode_select": lambda v: v in [1, 2],
    }
    rule = validation_rules.get(command_id)
    return rule(value) if rule else True


async def _send_c1000x_mqtt_command(
    self: AnkerSolixApi,
    device_sn: str,
    command: str,
    parameters: dict,
    description: str,
) -> bool:
    """Send MQTT command to C1000X device.

    Args:
        self: The API instance
        device_sn: Device serial number
        command: Command name for get_command_data
        parameters: Command parameters
        description: Human-readable description for logging

    Returns:
        bool: True if command was sent successfully, False otherwise
    """
    try:
        # Ensure MQTT session is started
        if not self.mqttsession:
            await self.startMqttSession()
        if not self.mqttsession:
            self._logger.error("Failed to start MQTT session for C1000X control")
            return False
        # Get device info for MQTT publish
        device = self.devices.get(device_sn)
        if not device:
            self._logger.error("Device %s not found for MQTT command", device_sn)
            return False
        device_dict = {
            "device_sn": device_sn,
            "device_pn": device.get("device_pn", "A1761"),
        }
        # Generate command hex data
        hex_data = self.mqttsession.get_command_data(command, parameters)
        if not hex_data:
            self._logger.error("Failed to generate MQTT command data for %s", command)
            return False
        # Publish MQTT command
        _, mqtt_info = self.mqttsession.publish(device_dict, hex_data)
        # Wait for publish completion with timeout
        with contextlib.suppress(ValueError, RuntimeError):
            mqtt_info.wait_for_publish(timeout=5)
        if not mqtt_info.is_published():
            self._logger.error(
                "Failed to publish MQTT command for C1000X %s %s",
                device_sn,
                description,
            )
            return False
    except Exception as e:  # pylint: disable=broad-exception-caught  # noqa: BLE001
        self._logger.error("Error sending MQTT command to C1000X %s: %s", device_sn, e)
        return False
    else:
        self._logger.info("C1000X %s %s", device_sn, description)
        return True


async def set_c1000x_ac_output(
    self: AnkerSolixApi,
    deviceSn: str,
    enabled: bool,
    toFile: bool = False,
) -> bool | dict:
    """Control C1000X AC output power via MQTT.

    Args:
        self: The API instance
        deviceSn: Device serial number
        enabled: True to enable AC output, False to disable
        toFile: If True, return mock response (for testing compatibility)

    Returns:
        dict: Mock response if successful, False otherwise

    Example:
        await api.set_c1000x_ac_output("DEVICE_SN", True)
    """
    # Validate device
    device = self.devices.get(deviceSn)
    if not device or device.get("device_pn") != "A1761":
        self._logger.error("Device %s is not a C1000X (A1761) or not found", deviceSn)
        return False

    # Validate command value
    value = 1 if enabled else 0
    if not validate_command_value("ac_output_control", value):
        self._logger.error("Invalid AC output value: %s", value)
        return False

    # Handle test mode
    if toFile:
        return {"switch_ac_output_power": value}

    # Send MQTT command
    success = await _send_c1000x_mqtt_command(
        self,
        deviceSn,
        "c1000x_ac_output",
        {"enabled": enabled},
        f"AC output {'enabled' if enabled else 'disabled'}",
    )

    if success:
        # Return mock response for compatibility with existing code
        return {"switch_ac_output_power": value}
    return False


async def set_c1000x_dc_output(
    self: AnkerSolixApi,
    deviceSn: str,
    enabled: bool,
    toFile: bool = False,
) -> bool | dict:
    """Control C1000X 12V DC output power via MQTT.

    Args:
        self: The API instance
        deviceSn: Device serial number
        enabled: True to enable 12V DC output, False to disable
        toFile: If True, return mock response (for testing compatibility)

    Returns:
        dict: Mock response if successful, False otherwise

    Example:
        await api.set_c1000x_dc_output("DEVICE_SN", True)
    """
    # Validate device
    device = self.devices.get(deviceSn)
    if not device or device.get("device_pn") != "A1761":
        self._logger.error("Device %s is not a C1000X (A1761) or not found", deviceSn)
        return False

    # Validate command value
    value = 1 if enabled else 0
    if not validate_command_value("dc_12v_output_control", value):
        self._logger.error("Invalid 12V DC output value: %s", value)
        return False

    # Handle test mode
    if toFile:
        return {"switch_12v_dc_output_power": value}

    # Send MQTT command
    success = await _send_c1000x_mqtt_command(
        self,
        deviceSn,
        "c1000x_dc_output",
        {"enabled": enabled},
        f"12V DC output {'enabled' if enabled else 'disabled'}",
    )

    if success:
        # Return mock response for compatibility with existing code
        return {"switch_12v_dc_output_power": value}
    return False


async def set_c1000x_display(
    self: AnkerSolixApi,
    deviceSn: str,
    enabled: bool,
    toFile: bool = False,
) -> bool | dict:
    """Control C1000X display on/off via MQTT.

    Args:
        self: The API instance
        deviceSn: Device serial number
        enabled: True to turn display on, False to turn off
        toFile: If True, return mock response (for testing compatibility)

    Returns:
        dict: Mock response if successful, False otherwise

    Example:
        await api.set_c1000x_display("DEVICE_SN", True)
    """
    # Validate device
    device = self.devices.get(deviceSn)
    if not device or device.get("device_pn") != "A1761":
        self._logger.error("Device %s is not a C1000X (A1761) or not found", deviceSn)
        return False

    # Validate command value
    value = 1 if enabled else 0
    if not validate_command_value("display_control", value):
        self._logger.error("Invalid display value: %s", value)
        return False

    # Handle test mode
    if toFile:
        return {"switch_display": value}

    # Send MQTT command
    success = await _send_c1000x_mqtt_command(
        self,
        deviceSn,
        "c1000x_display",
        {"enabled": enabled},
        f"display {'enabled' if enabled else 'disabled'}",
    )

    if success:
        return {"switch_display": value}
    return False


async def set_c1000x_backup_charge(
    self: AnkerSolixApi,
    deviceSn: str,
    enabled: bool,
    toFile: bool = False,
) -> bool | dict:
    """Control C1000X backup charge mode via MQTT.

    Args:
        self: The API instance
        deviceSn: Device serial number
        enabled: True to enable backup charge mode, False to disable
        toFile: If True, return mock response (for testing compatibility)

    Returns:
        dict: Mock response if successful, False otherwise

    Example:
        await api.set_c1000x_backup_charge("DEVICE_SN", True)
    """
    # Validate device
    device = self.devices.get(deviceSn)
    if not device or device.get("device_pn") != "A1761":
        self._logger.error("Device %s is not a C1000X (A1761) or not found", deviceSn)
        return False

    # Validate command value
    value = 1 if enabled else 0
    if not validate_command_value("backup_charge_control", value):
        self._logger.error("Invalid backup charge value: %s", value)
        return False

    # Handle test mode
    if toFile:
        return {"backup_charge": value}

    # Send MQTT command
    success = await _send_c1000x_mqtt_command(
        self,
        deviceSn,
        "c1000x_backup_charge",
        {"enabled": enabled},
        f"backup charge mode {'enabled' if enabled else 'disabled'}",
    )

    if success:
        return {"backup_charge": value}
    return False


async def set_c1000x_temp_unit(
    self: AnkerSolixApi,
    deviceSn: str,
    fahrenheit: bool,
    toFile: bool = False,
) -> bool | dict:
    """Set C1000X temperature unit via MQTT.

    Args:
        self: The API instance
        deviceSn: Device serial number
        fahrenheit: True for Fahrenheit, False for Celsius
        toFile: If True, return mock response (for testing compatibility)

    Returns:
        dict: Mock response if successful, False otherwise

    Example:
        await api.set_c1000x_temp_unit("DEVICE_SN", False)  # Celsius
    """
    # Validate device
    device = self.devices.get(deviceSn)
    if not device or device.get("device_pn") != "A1761":
        self._logger.error("Device %s is not a C1000X (A1761) or not found", deviceSn)
        return False

    # Validate command value
    value = 1 if fahrenheit else 0
    if not validate_command_value("temp_unit_control", value):
        self._logger.error("Invalid temperature unit value: %s", value)
        return False

    # Handle test mode
    if toFile:
        return {"temp_unit_fahrenheit": value}

    # Send MQTT command
    success = await _send_c1000x_mqtt_command(
        self,
        deviceSn,
        "c1000x_temp_unit",
        {"fahrenheit": fahrenheit},
        f"temperature unit set to {'Fahrenheit' if fahrenheit else 'Celsius'}",
    )

    if success:
        return {"temp_unit_fahrenheit": value}
    return False


async def set_c1000x_display_mode(
    self: AnkerSolixApi,
    deviceSn: str,
    mode: int | str,
    toFile: bool = False,
) -> bool | dict:
    """Set C1000X display brightness mode via MQTT.

    Args:
        self: The API instance
        deviceSn: Device serial number
        mode: Display mode - 0=Off, 1=Low, 2=Medium, 3=High
              Can also be string: "off", "low", "medium", "high"
        toFile: If True, return mock response (for testing compatibility)

    Returns:
        dict: Mock response if successful, False otherwise

    Example:
        await api.set_c1000x_display_mode("DEVICE_SN", 2)  # Medium
        await api.set_c1000x_display_mode("DEVICE_SN", "high")
    """
    # Validate device
    device = self.devices.get(deviceSn)
    if not device or device.get("device_pn") != "A1761":
        self._logger.error("Device %s is not a C1000X (A1761) or not found", deviceSn)
        return False

    # Convert string mode to int
    mode_map = {"off": 0, "low": 1, "medium": 2, "high": 3}
    original_mode = mode
    if isinstance(mode, str):
        mode = mode_map.get(mode.lower())
        if mode is None:
            self._logger.error("Invalid display mode string: %s", original_mode)
            return False

    # Validate command value
    if not validate_command_value("display_mode_select", mode):
        self._logger.error("Invalid display mode value: %s", mode)
        return False

    # Handle test mode
    if toFile:
        return {"display_mode": mode}

    # Send MQTT command
    success = await _send_c1000x_mqtt_command(
        self,
        deviceSn,
        "c1000x_display_mode",
        {"mode": mode},
        f"display mode set to {original_mode if isinstance(original_mode, str) else mode}",
    )

    if success:
        return {"display_mode": mode}
    return False


async def set_c1000x_light_mode(
    self: AnkerSolixApi,
    deviceSn: str,
    mode: int | str,
    toFile: bool = False,
) -> bool | dict:
    """Set C1000X light mode via MQTT.

    Args:
        self: The API instance
        deviceSn: Device serial number
        mode: Light mode - 0=Off, 1=Low, 2=Medium, 3=High, 4=Blinking
              Can also be string: "off", "low", "medium", "high", "blinking"
        toFile: If True, return mock response (for testing compatibility)

    Returns:
        dict: Mock response if successful, False otherwise

    Example:
        await api.set_c1000x_light_mode("DEVICE_SN", 3)  # High
        await api.set_c1000x_light_mode("DEVICE_SN", "blinking")
    """
    # Validate device
    device = self.devices.get(deviceSn)
    if not device or device.get("device_pn") != "A1761":
        self._logger.error("Device %s is not a C1000X (A1761) or not found", deviceSn)
        return False

    # Convert string mode to int
    mode_map = {"off": 0, "low": 1, "medium": 2, "high": 3, "blinking": 4}
    original_mode = mode
    if isinstance(mode, str):
        mode = mode_map.get(mode.lower())
        if mode is None:
            self._logger.error("Invalid light mode string: %s", original_mode)
            return False

    # Validate command value
    if not validate_command_value("light_mode_select", mode):
        self._logger.error("Invalid light mode value: %s", mode)
        return False

    # Handle test mode
    if toFile:
        return {"light_mode": mode}

    # Send MQTT command
    success = await _send_c1000x_mqtt_command(
        self,
        deviceSn,
        "c1000x_light_mode",
        {"mode": mode},
        f"light mode set to {original_mode if isinstance(original_mode, str) else mode}",
    )

    if success:
        return {"light_mode": mode}
    return False


async def set_c1000x_dc_output_mode(
    self: AnkerSolixApi,
    deviceSn: str,
    mode: int | str,
    toFile: bool = False,
) -> bool | dict:
    """Set C1000X 12V DC output mode via MQTT.

    Args:
        self: The API instance
        deviceSn: Device serial number
        mode: DC output mode - 1=Normal, 2=Smart
              Can also be string: "normal", "smart"
        toFile: If True, return mock response (for testing compatibility)

    Returns:
        dict: Mock response if successful, False otherwise

    Example:
        await api.set_c1000x_dc_output_mode("DEVICE_SN", 2)  # Smart
        await api.set_c1000x_dc_output_mode("DEVICE_SN", "normal")
    """
    # Validate device
    device = self.devices.get(deviceSn)
    if not device or device.get("device_pn") != "A1761":
        self._logger.error("Device %s is not a C1000X (A1761) or not found", deviceSn)
        return False

    # Convert string mode to int
    mode_map = {"normal": 1, "smart": 2}
    original_mode = mode
    if isinstance(mode, str):
        mode = mode_map.get(mode.lower())
        if mode is None:
            self._logger.error("Invalid DC output mode string: %s", original_mode)
            return False

    # Validate command value
    if not validate_command_value("dc_output_mode_select", mode):
        self._logger.error("Invalid DC output mode value: %s", mode)
        return False

    # Handle test mode
    if toFile:
        return {"12v_dc_output_mode": mode}

    # Send MQTT command
    success = await _send_c1000x_mqtt_command(
        self,
        deviceSn,
        "c1000x_dc_output_mode",
        {"mode": mode},
        f"12V DC output mode set to {original_mode if isinstance(original_mode, str) else mode}",
    )

    if success:
        return {"12v_dc_output_mode": mode}
    return False


async def set_c1000x_ac_output_mode(
    self: AnkerSolixApi,
    deviceSn: str,
    mode: int | str,
    toFile: bool = False,
) -> bool | dict:
    """Set C1000X AC output mode via MQTT.

    Args:
        self: The API instance
        deviceSn: Device serial number
        mode: AC output mode - 1=Normal, 2=Smart
              Can also be string: "normal", "smart"
        toFile: If True, return mock response (for testing compatibility)

    Returns:
        dict: Mock response if successful, False otherwise

    Example:
        await api.set_c1000x_ac_output_mode("DEVICE_SN", 1)  # Normal
        await api.set_c1000x_ac_output_mode("DEVICE_SN", "smart")
    """
    # Validate device
    device = self.devices.get(deviceSn)
    if not device or device.get("device_pn") != "A1761":
        self._logger.error("Device %s is not a C1000X (A1761) or not found", deviceSn)
        return False

    # Convert string mode to int
    mode_map = {"normal": 1, "smart": 2}
    original_mode = mode
    if isinstance(mode, str):
        mode = mode_map.get(mode.lower())
        if mode is None:
            self._logger.error("Invalid AC output mode string: %s", original_mode)
            return False

    # Validate command value
    if not validate_command_value("ac_output_mode_select", mode):
        self._logger.error("Invalid AC output mode value: %s", mode)
        return False

    # Handle test mode
    if toFile:
        return {"ac_output_mode": mode}

    # Send MQTT command
    success = await _send_c1000x_mqtt_command(
        self,
        deviceSn,
        "c1000x_ac_output_mode",
        {"mode": mode},
        f"AC output mode set to {original_mode if isinstance(original_mode, str) else mode}",
    )

    if success:
        return {"ac_output_mode": mode}
    return False


async def get_c1000x_status(
    self: AnkerSolixApi,
    deviceSn: str,
    fromFile: bool = False,
) -> dict:
    """Get comprehensive C1000X device status via MQTT data.

    Args:
        self: The API instance
        deviceSn: Device serial number
        fromFile: If True, read from test file instead of using MQTT data

    Returns:
        dict: Device status including all switch states, modes, and settings
              Uses MQTT data cache for real-time values

    Example:
        status = await api.get_c1000x_status("DEVICE_SN")
        print(f"AC Output: {status.get('switch_ac_output_power')}")
        print(f"Battery SOC: {status.get('battery_soc')}%")
    """
    # Validate device
    device = self.devices.get(deviceSn)
    if not device or device.get("device_pn") != "A1761":
        self._logger.error("Device %s is not a C1000X (A1761) or not found", deviceSn)
        return {}

    # Handle test mode
    if fromFile:
        # Return a mock status for testing
        return {
            "switch_ac_output_power": 1,
            "switch_12v_dc_output_power": 1,
            "switch_display": 1,
            "backup_charge": 0,
            "temp_unit_fahrenheit": 0,
            "display_mode": 2,
            "light_mode": 0,
            "12v_dc_output_mode": 1,
            "ac_output_mode": 1,
            "battery_soc": 85,
            "temperature": 25,
            "max_load": 1000,
            "device_timeout_minutes": 60,
            "display_timeout_seconds": 60,
        }

    # For C1000X, use MQTT data cache instead of cloud API
    if self.mqttsession and hasattr(self.mqttsession, "mqtt_data"):
        mqtt_data = self.mqttsession.mqtt_data.get(deviceSn, {})
        if mqtt_data:
            self._logger.info("C1000X %s status retrieved from MQTT data", deviceSn)
            # Return only the fields we have MQTT mappings for
            status = {}
            mqtt_fields = [
                "battery_soc",
                "temperature",
                "battery_soh",
                "ac_output_power",
                "dc_input_power",
                "grid_to_battery_power",
                "usbc_1_power",
                "usbc_2_power",
                "usba_1_power",
                "usba_2_power",
                "exp_1_soc",
                "exp_1_soh",
                "exp_1_temperature",
                "sw_version",
                "hw_version",
                "device_sn",
            ]
            for field in mqtt_fields:
                if field in mqtt_data:
                    status[field] = mqtt_data[field]
            return status

    # Fallback: If no MQTT data available, return empty dict
    self._logger.warning("No MQTT data available for C1000X %s status", deviceSn)
    return {}
