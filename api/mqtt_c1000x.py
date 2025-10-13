"""C1000X MQTT device control methods for AnkerSolixApi.

This module contains control methods specific to the Anker C1000X (A1761) portable power station.
These methods provide comprehensive device control via MQTT commands.
C1000X devices use MQTT-only communication for control operations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .mqtt_device import SolixMqttDevice

if TYPE_CHECKING:
    from .api import AnkerSolixApi

# Define supported Models for this class
MODELS = ["A1761"]


class SolixMqttDeviceC1000x(SolixMqttDevice):
    """Define the class to handle an Anker Solix MQTT device for controls."""

    def __init__(self, api_instance: AnkerSolixApi, device_sn: str) -> None:
        """Initialize."""
        super().__init__(api_instance=api_instance, device_sn=device_sn)

    def validate_command_value(self, command_id: str, value: Any) -> bool:
        """Validate command value ranges for device controls."""
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
        if enabled is not None and await self._send_mqtt_command(
            command="c1000x_ac_output",
            parameters={"enabled": enabled},
            description=f"AC output {'enabled' if enabled else 'disabled'}",
            toFile=toFile,
        ):
            resp["switch_ac_output_power"] = enabled
        if mode is not None and await self._send_mqtt_command(
            command="c1000x_ac_output_mode",
            parameters={"mode": mode},
            description=f"AC output mode set to {original_mode if isinstance(original_mode, str) else mode}",
            toFile=toFile,
        ):
            resp["ac_output_mode"] = mode
        if toFile:
            self._filedata.update(resp)
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
        if enabled is not None and await self._send_mqtt_command(
            command="c1000x_dc_output",
            parameters={"enabled": enabled},
            description=f"12V DC output {'enabled' if enabled else 'disabled'}",
            toFile=toFile,
        ):
            resp["switch_12v_dc_output_power"] = enabled
        if mode is not None and await self._send_mqtt_command(
            command="c1000x_dc_output_mode",
            parameters={"mode": mode},
            description=f"12V DC output mode set to {original_mode if isinstance(original_mode, str) else mode}",
            toFile=toFile,
        ):
            resp["12v_dc_output_mode"] = mode
        if toFile:
            self._filedata.update(resp)
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
        if enabled is not None and await self._send_mqtt_command(
            command="c1000x_display",
            parameters={"enabled": enabled},
            description=f"display {'enabled' if enabled else 'disabled'}",
            toFile=toFile,
        ):
            resp["switch_display"] = enabled
        if mode is not None and await self._send_mqtt_command(
            command="c1000x_display_mode",
            parameters={"mode": mode},
            description=f"display mode set to {original_mode if isinstance(original_mode, str) else mode}",
            toFile=toFile,
        ):
            resp["display_mode"] = mode
        if toFile:
            self._filedata.update(resp)
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
        if enabled is not None and await self._send_mqtt_command(
            command="c1000x_backup_charge",
            parameters={"enabled": enabled},
            description=f"backup charge mode {'enabled' if enabled else 'disabled'}",
            toFile=toFile,
        ):
            resp["backup_charge"] = enabled
        if toFile:
            self._filedata.update(resp)
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
        if fahrenheit is not None and await self._send_mqtt_command(
            command="c1000x_temp_unit",
            parameters={"fahrenheit": fahrenheit},
            description=f"temperature unit set to {'Fahrenheit' if fahrenheit else 'Celsius'}",
            toFile=toFile,
        ):
            resp["temp_unit_fahrenheit"] = fahrenheit
        if toFile:
            self._filedata.update(resp)
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
        if mode is not None and await self._send_mqtt_command(
            command="c1000x_light_mode",
            parameters={"mode": mode},
            description=f"light mode set to {original_mode if isinstance(original_mode, str) else mode}",
            toFile=toFile,
        ):
            resp["light_mode"] = mode
        if toFile:
            self._filedata.update(resp)
        return resp or False
