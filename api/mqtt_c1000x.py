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

# Define supported Models for this class
MODELS = ["A1761"]


class SolixMqttDeviceC1000x:
    """Define the class to handle an Anker Solix MQTT device for controls."""

    def __init__(self, api_instance: AnkerSolixApi, device_sn: str) -> None:
        """Initialize."""
        self.api: AnkerSolixApi = api_instance
        self.sn: str = device_sn
        self.pn: str = ""
        self.device: dict = {}
        self.mqttdata: dict = {}
        self.testdir: str = self.api.testDir()
        self._logger = api_instance.logger()
        self._filedata: dict = {}
        # initialize device data
        self.update_device(device=self.api.devices.get(self.sn))
        # register callback for Api
        self.api.register_device_callback(deviceSn=self.sn, func=self.update_device)

    def update_device(self, device: dict) -> None:
        """Define callback for Api device updates."""
        if isinstance(device, dict) and device.get("device_sn") == self.sn:
            # Validate device type
            if (pn := device.get("device_pn")) in MODELS:
                self.pn = pn
                self.device = device
                self.mqttdata = device.get("mqtt_data", {})
            else:
                self._logger.error(
                    "Device %s %s is not in supported models %s for MQTT control",
                    self.pn,
                    self.sn,
                    MODELS,
                )
                self.pn = ""
                self.device = {}
                self.mqttdata = {}

    def validate_command_value(self, command_id: str, value: Any) -> bool:
        """Validate command value ranges for C1000X controls."""
        validation_rules = {
            "realtime_trigger": lambda v: 30 <= v <= 600,
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

    async def _send_mqtt_command(
        self,
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
            if not self.api.mqttsession:
                if not await self.api.startMqttSession():
                    self._logger.error(
                        "Failed to start MQTT session for device control"
                    )
                    return False
            # Generate command hex data
            if not (
                hex_data := self.api.mqttsession.get_command_data(command, parameters)
            ):
                self._logger.error(
                    "Failed to generate MQTT command data for %s", command
                )
                return False
            # Publish MQTT command
            _, mqtt_info = self.api.mqttsession.publish(self.device, hex_data)
            # Wait for publish completion with timeout
            with contextlib.suppress(ValueError, RuntimeError):
                mqtt_info.wait_for_publish(timeout=5)
            if not mqtt_info.is_published():
                self._logger.error(
                    "Failed to publish MQTT command for device %s %s %s",
                    self.pn,
                    self.sn,
                    description,
                )
                return False
        except Exception as e:  # pylint: disable=broad-exception-caught  # noqa: BLE001
            self._logger.error(
                "Error sending MQTT command to device %s %s: %s", self.pn, self.sn, e
            )
            return False
        else:
            self._logger.info("Device %s %s %s", self.pn, self.sn, description)
            return True

    def realtime_trigger(self, timeout: int = 60) -> bool:
        """Trigger device realtime data publish.

        Args:
            timeout: Seconds for realtime publish to stop

        Returns:
            bool: True if message was published, false otherwise

        Example:
            await mydevice.realtime_trigger(timeout=300)
        """
        # Validate command value
        if not self.validate_command_value("realtime_trigger", timeout):
            self._logger.error(
                "Device %s %s control error - Invalid realtime trigger timeout: %s",
                self.pn,
                self.sn,
                timeout,
            )
            return False
        # Validate MQTT connection prior trigger
        if not (self.api.mqttsession and self.api.mqttsession.client.is_connected()):
            self._logger.error(
                "Device %s %s control error - No MQTT connection active",
                self.pn,
                self.sn,
            )
            return False
        msginfo = self.api.mqttsession.realtime_trigger(self.device, timeout=timeout)
        with contextlib.suppress(ValueError, RuntimeError):
            msginfo.wait_for_publish(timeout=2)
        if not msginfo.is_published():
            self._logger.error(
                "Error sending MQTT realtime trigger to device %s %s", self.pn, self.sn
            )
            return False
        return True

    async def set_ac_output(
        self,
        enabled: bool | None = None,
        mode: int | str | None = None,
        toFile: bool = False,
    ) -> bool | dict:
        """Control C1000X AC output power via MQTT.

        Args:
            enabled: True to enable AC output, False to disable
            mode: AC output mode - 1=Normal, 2=Smart
                Can also be string: "normal", "smart"
            toFile: If True, return mock response (for testing compatibility)

        Returns:
            dict: Mock response if successful, False otherwise

        Example:
            await mydevice.set_ac_output(enabled=True)
            await mydevice.set_ac_output(mode=1)  # Normal
            await mydevice.set_ac_output(mode="smart")
        """
        # response
        resp = {}
        # Validate command value
        enabled = 1 if enabled else 0 if enabled is not None else None
        if enabled is not None and not self.validate_command_value(
            "ac_output_control", enabled
        ):
            self._logger.error(
                "Device %s %s control error - Invalid AC output enabled value: %s",
                self.pn,
                self.sn,
                enabled,
            )
            return False
        # Convert string mode to int
        mode_map = {"normal": 1, "smart": 2}
        original_mode = mode
        if isinstance(mode, str):
            if (mode := mode_map.get(mode.lower())) is None:
                self._logger.error(
                    "Device %s %s control error - Invalid AC output mode string: %s",
                    self.pn,
                    self.sn,
                    original_mode,
                )
                return False
        if mode is not None and not self.validate_command_value(
            "ac_output_mode_select", mode
        ):
            self._logger.error(
                "Device %s %s control error - Invalid AC output mode value: %s",
                self.pn,
                self.sn,
                mode,
            )
            return False
        # Send MQTT commands
        if enabled is not None:
            if toFile or await self._send_mqtt_command(
                command="c1000x_ac_output",
                parameters={"enabled": enabled},
                description=f"AC output {'enabled' if enabled else 'disabled'}",
            ):
                resp["switch_ac_output_power"] = enabled
                if toFile:
                    self._filedata["switch_ac_output_power"] = enabled
        if mode is not None:
            if toFile or await self._send_mqtt_command(
                command="c1000x_ac_output_mode",
                parameters={"mode": mode},
                description=f"AC output mode set to {original_mode if isinstance(original_mode, str) else mode}",
            ):
                resp["ac_output_mode"] = mode
                if toFile:
                    self._filedata["ac_output_mode"] = mode
        return resp or False

    async def set_dc_output(
        self,
        enabled: bool | None = None,
        mode: int | str | None = None,
        toFile: bool = False,
    ) -> bool | dict:
        """Control C1000X 12V DC output power via MQTT.

        Args:
            enabled: True to enable 12V DC output, False to disable
            mode: DC output mode - 1=Normal, 2=Smart
                Can also be string: "normal", "smart"
            toFile: If True, return mock response (for testing compatibility)

        Returns:
            dict: Mock response if successful, False otherwise

        Example:
            await mydevice.set_dc_output(enabled=True)
            await mydevice.set_dc_output(mode=2)  # Smart
            await mydevice.set_dc_output(mode="normal")
        """
        # response
        resp = {}
        # Validate command value
        enabled = 1 if enabled else 0 if enabled is not None else None
        if enabled is not None and not self.validate_command_value(
            "dc_12v_output_control", enabled
        ):
            self._logger.error(
                "Device %s %s control error - Invalid DC output enabled value: %s",
                self.pn,
                self.sn,
                enabled,
            )
            return False
        # Convert string mode to int
        mode_map = {"normal": 1, "smart": 2}
        original_mode = mode
        if isinstance(mode, str):
            if (mode := mode_map.get(mode.lower())) is None:
                self._logger.error(
                    "Device %s %s control error - Invalid DC output mode string: %s",
                    self.pn,
                    self.sn,
                    original_mode,
                )
                return False
        if mode is not None and not self.validate_command_value(
            "dc_output_mode_select", mode
        ):
            self._logger.error(
                "Device %s %s control error - Invalid DC output mode value: %s",
                self.pn,
                self.sn,
                mode,
            )
            return False
        # Send MQTT commands
        if enabled is not None:
            if toFile or await self._send_mqtt_command(
                command="c1000x_dc_output",
                parameters={"enabled": enabled},
                description=f"12V DC output {'enabled' if enabled else 'disabled'}",
            ):
                resp["switch_12v_dc_output_power"] = enabled
                if toFile:
                    self._filedata["switch_12v_dc_output_power"] = enabled
        if mode is not None:
            if toFile or await self._send_mqtt_command(
                command="c1000x_dc_output_mode",
                parameters={"mode": mode},
                description=f"12V DC output mode set to {original_mode if isinstance(original_mode, str) else mode}",
            ):
                resp["12v_dc_output_mode"] = mode
                if toFile:
                    self._filedata["12v_dc_output_mode"] = mode
        return resp or False

    async def set_display(
        self,
        enabled: bool | None = None,
        mode: int | str | None = None,
        toFile: bool = False,
    ) -> bool | dict:
        """Control C1000X display settings via MQTT.

        Args:
            enabled: True to turn display on, False to turn off
            mode: Display mode - 0=Off, 1=Low, 2=Medium, 3=High
                Can also be string: "off", "low", "medium", "high"
            toFile: If True, return mock response (for testing compatibility)

        Returns:
            dict: Mock response if successful, False otherwise

        Example:
            await mydevice.set_display(enabled=True)
            await mydevice.set_display(mode=2)  # Medium
            await mydevice.set_display(mode="high")
        """
        # response
        resp = {}
        # Validate command value
        enabled = 1 if enabled else 0 if enabled is not None else None
        if enabled is not None and not self.validate_command_value(
            "display_control", enabled
        ):
            self._logger.error(
                "Device %s %s control error - Invalid display enabled value: %s",
                self.pn,
                self.sn,
                enabled,
            )
            return False
        # Convert string mode to int
        mode_map = {"off": 0, "low": 1, "medium": 2, "high": 3}
        original_mode = mode
        if isinstance(mode, str):
            if (mode := mode_map.get(mode.lower())) is None:
                self._logger.error(
                    "Device %s %s control error - Invalid display mode string: %s",
                    self.pn,
                    self.sn,
                    original_mode,
                )
                return False
        if mode is not None and not self.validate_command_value(
            "display_mode_select", mode
        ):
            self._logger.error(
                "Device %s %s control error - Invalid display mode value: %s",
                self.pn,
                self.sn,
                mode,
            )
            return False
        # Send MQTT commands
        if enabled is not None:
            if toFile or await self._send_mqtt_command(
                command="c1000x_display",
                parameters={"enabled": enabled},
                description=f"display {'enabled' if enabled else 'disabled'}",
            ):
                resp["switch_display"] = enabled
                if toFile:
                    self._filedata["switch_display"] = enabled
        if mode is not None:
            if toFile or await self._send_mqtt_command(
                command="c1000x_display_mode",
                parameters={"mode": mode},
                description=f"display mode set to {original_mode if isinstance(original_mode, str) else mode}",
            ):
                resp["display_mode"] = mode
                if toFile:
                    self._filedata["display_mode"] = mode
        return resp or False

    async def set_backup_charge(
        self,
        enabled: bool,
        toFile: bool = False,
    ) -> bool | dict:
        """Control C1000X backup charge mode via MQTT.

        Args:
            enabled: True to enable backup charge mode, False to disable
            toFile: If True, return mock response (for testing compatibility)

        Returns:
            dict: Mock response if successful, False otherwise

        Example:
            await mydevice.set_backup_charge(enabled=True)
        """
        # response
        resp = {}
        # Validate command value
        enabled = 1 if enabled else 0 if enabled is not None else None
        if enabled is not None and not self.validate_command_value(
            "backup_charge_control", enabled
        ):
            self._logger.error(
                "Device %s %s control error - Invalid backup charge enabled value: %s",
                self.pn,
                self.sn,
                enabled,
            )
            return False
        # Send MQTT commands
        if enabled is not None:
            if toFile or await self._send_mqtt_command(
                command="c1000x_backup_charge",
                parameters={"enabled": enabled},
                description=f"backup charge mode {'enabled' if enabled else 'disabled'}",
            ):
                resp["backup_charge"] = enabled
                if toFile:
                    self._filedata["backup_charge"] = enabled
        return resp or False

    async def set_temp_unit(
        self,
        fahrenheit: bool,
        toFile: bool = False,
    ) -> bool | dict:
        """Set C1000X temperature unit via MQTT.

        Args:
            fahrenheit: True for Fahrenheit, False for Celsius
            toFile: If True, return mock response (for testing compatibility)

        Returns:
            dict: Mock response if successful, False otherwise

        Example:
            await mydevice.set_temp_unit(fahrenheit=False)  # Celsius
        """
        # response
        resp = {}
        # Validate command value
        fahrenheit = 1 if fahrenheit else 0 if fahrenheit is not None else None
        if fahrenheit is not None and not self.validate_command_value(
            "backup_charge_control", fahrenheit
        ):
            self._logger.error(
                "Device %s %s control error - Invalid temperature unit fahrenheit value: %s",
                self.pn,
                self.sn,
                fahrenheit,
            )
            return False
        # Send MQTT commands
        if fahrenheit is not None:
            if toFile or await self._send_mqtt_command(
                command="c1000x_temp_unit",
                parameters={"fahrenheit": fahrenheit},
                description=f"temperature unit set to {'Fahrenheit' if fahrenheit else 'Celsius'}",
            ):
                resp["temp_unit_fahrenheit"] = fahrenheit
                if toFile:
                    self._filedata["temp_unit_fahrenheit"] = fahrenheit
        return resp or False

    async def set_light(
        self,
        mode: int | str,
        toFile: bool = False,
    ) -> bool | dict:
        """Set C1000X light mode via MQTT.

        Args:
            mode: Light mode - 0=Off, 1=Low, 2=Medium, 3=High, 4=Blinking
                Can also be string: "off", "low", "medium", "high", "blinking"
            toFile: If True, return mock response (for testing compatibility)

        Returns:
            dict: Mock response if successful, False otherwise

        Example:
            await mydevice.set_light_mode(mode=3)  # High
            await mydevice.set_light_mode(mode="blinking")
        """
        # response
        resp = {}
        # Convert string mode to int
        mode_map = {"off": 0, "low": 1, "medium": 2, "high": 3, "blinking": 4}
        original_mode = mode
        # Validate command value
        if isinstance(mode, str):
            if (mode := mode_map.get(mode.lower())) is None:
                self._logger.error(
                    "Device %s %s control error - Invalid light mode string: %s",
                    self.pn,
                    self.sn,
                    original_mode,
                )
                return False
        if mode is not None and not self.validate_command_value(
            "light_mode_select", mode
        ):
            self._logger.error(
                "Device %s %s control error - Invalid light mode value: %s",
                self.pn,
                self.sn,
                mode,
            )
            return False
        # Send MQTT commands
        if mode is not None:
            if toFile or await self._send_mqtt_command(
                command="c1000x_light_mode",
                parameters={"mode": mode},
                description=f"light mode set to {original_mode if isinstance(original_mode, str) else mode}",
            ):
                resp["light_mode"] = mode
                if toFile:
                    self._filedata["light_mode"] = mode
        return resp or False

    def get_status(
        self,
        fromFile: bool = False,
    ) -> dict:
        """Get comprehensive C1000X device status via MQTT data.

        Args:
            fromFile: If True, read from test file instead of using MQTT data

        Returns:
            dict: Device status including all switch states, modes, and settings
                Uses MQTT data cache for real-time values

        Example:
            status = api.get_status()
            print(f"AC Output: {status.get('switch_ac_output_power')}")
            print(f"Battery SOC: {status.get('battery_soc')}%")
        """
        # TODO: Remove mock once file mode is supported for MQTT data
        # Handle test mode
        if fromFile:
            # Update real data with modifications from testing
            self._logger.info(
                "Device %s %s status with optional MQTT test control changes",
                self.pn,
                self.sn,
            )
            return self.mqttdata | self._filedata

        # Return accumulated MQTT data cache instead of API cache for device status
        if self.mqttdata:
            self._logger.info(
                "Device %s %s status retrieved from MQTT data", self.pn, self.sn
            )
        else:
            self._logger.warning(
                "No MQTT data available for device %s %s status", self.pn, self.sn
            )
        return self.mqttdata
