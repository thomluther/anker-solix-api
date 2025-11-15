"""C1000X MQTT device control methods for AnkerSolixApi.

This module contains control methods specific to the Anker C1000X (A1761) portable power station.
These methods provide comprehensive device control via MQTT commands.
C1000X devices use MQTT-only communication for control operations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .apitypes import SolixDefaults
from .mqtt_device import SolixMqttDevice
from .mqttcmdmap import SolixMqttCommands

if TYPE_CHECKING:
    from .api import AnkerSolixApi

# Define supported Models for this class
MODELS = {"A1761"}
# Define supported and validated controls per Model
FEATURES = {
    SolixMqttCommands.realtime_trigger: MODELS,
    SolixMqttCommands.temp_unit_switch: MODELS,
    SolixMqttCommands.device_max_load: MODELS,
    SolixMqttCommands.device_timeout_minutes: MODELS,
    SolixMqttCommands.ac_charge_switch: MODELS,
    SolixMqttCommands.ac_charge_limit: MODELS,
    SolixMqttCommands.ac_output_switch: MODELS,
    SolixMqttCommands.ac_fast_charge_switch: MODELS,
    SolixMqttCommands.ac_output_mode_select: MODELS,
    SolixMqttCommands.dc_output_switch: MODELS,
    SolixMqttCommands.dc_12v_output_mode_select: MODELS,
    SolixMqttCommands.display_switch: MODELS,
    SolixMqttCommands.display_mode_select: MODELS,
    SolixMqttCommands.light_mode_select: MODELS,
}


class SolixMqttDeviceC1000x(SolixMqttDevice):
    """Define the class to handle an Anker Solix MQTT device for controls."""

    def __init__(self, api_instance: AnkerSolixApi, device_sn: str) -> None:
        """Initialize."""
        self.models = MODELS
        self.features = FEATURES
        super().__init__(api_instance=api_instance, device_sn=device_sn)

    def validate_command_value(self, command_id: str, value: Any) -> bool:
        """Validate command value ranges for device controls."""
        validation_rules = {
            "realtime_trigger": lambda v: SolixDefaults.TRIGGER_TIMEOUT_MIN
            <= v
            <= SolixDefaults.TRIGGER_TIMEOUT_MAX,
            "ac_output_control": lambda v: v in [0, 1],
            "dc_12v_output_control": lambda v: v in [0, 1],
            "display_control": lambda v: v in [0, 1],
            "temp_unit_control": lambda v: v in [0, 1],
            "display_mode_select": lambda v: v in [0, 1, 2, 3],
            "light_mode_select": lambda v: v in [0, 1, 2, 3, 4],
            "dc_output_mode_select": lambda v: v in [0, 1],  # 0=Smart, 1=Normal
            "ac_output_mode_select": lambda v: v in [0, 1],  # 0=Smart, 1=Normal
            "device_timeout_minutes": lambda v: 30 <= v <= 1440,
            "max_load": lambda v: 100 <= v <= 2000,
            "ac_charge_limit": lambda v: 100 <= v <= 800,
            "ultrafast_charging": lambda v: v in [0, 1],
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
        mode_map = {"normal": 1, "smart": 0}
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
        mode_map = {"normal": 1, "smart": 0}
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
            resp["dc_output_power_switch"] = enabled
        if mode is not None and await self._send_mqtt_command(
            command="c1000x_dc_output_mode",
            parameters={"mode": mode},
            description=f"12V DC output mode set to {original_mode if isinstance(original_mode, str) else mode}",
            toFile=toFile,
        ):
            resp["dc_12v_output_mode"] = mode
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
            "temp_unit_control", fahrenheit
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

    async def set_device_timeout(
        self,
        timeout_minutes: int | None = None,
        toFile: bool = False,
    ) -> dict | bool:
        """Set device auto-off timeout.

        Args:
            timeout_minutes: Timeout in minutes (30-1440)
            toFile: If True, return mock response (for testing compatibility)

        Returns:
            dict: Response with device_timeout_minutes if successful, False otherwise

        Example:
            # Set 8 hour timeout
            result = await device.set_device_timeout(timeout_minutes=480)
        """
        resp = {}
        if timeout_minutes is not None and not self.validate_command_value(
            "device_timeout_minutes", timeout_minutes
        ):
            self._logger.error(
                "Device %s %s control error - Invalid timeout value: %s",
                self.pn,
                self.sn,
                timeout_minutes,
            )
            return False
        if timeout_minutes is not None:
            if toFile or await self._send_mqtt_command(
                command="c1000x_device_timeout",
                parameters={"timeout_minutes": timeout_minutes},
                description=f"Device timeout set to {timeout_minutes} minutes",
                toFile=toFile,
            ):
                resp["device_timeout_minutes"] = timeout_minutes
                if toFile:
                    self._filedata["device_timeout_minutes"] = timeout_minutes
        return resp or False

    async def set_max_load(
        self,
        max_watts: int | None = None,
        toFile: bool = False,
    ) -> dict | bool:
        """Set maximum AC input load (current limit).

        Args:
            max_watts: Maximum load in watts (100-2000)
            toFile: If True, return mock response (for testing compatibility)

        Returns:
            dict: Response with max_load if successful, False otherwise

        Example:
            # Set 800W max load
            result = await device.set_max_load(max_watts=800)
        """
        resp = {}
        if max_watts is not None and not self.validate_command_value(
            "max_load", max_watts
        ):
            self._logger.error(
                "Device %s %s control error - Invalid max load value: %s",
                self.pn,
                self.sn,
                max_watts,
            )
            return False
        if max_watts is not None:
            if toFile or await self._send_mqtt_command(
                command="c1000x_max_load",
                parameters={"max_watts": max_watts},
                description=f"Max load set to {max_watts}W",
                toFile=toFile,
            ):
                resp["max_load"] = max_watts
                if toFile:
                    self._filedata["max_load"] = max_watts
        return resp or False

    async def set_ultrafast_charging(
        self,
        enabled: bool,
        toFile: bool = False,
    ) -> dict | bool:
        """Set UltraFast charging mode (1300W max).

        Args:
            enabled: True to enable UltraFast charging, False to disable
            toFile: If True, return mock response (for testing compatibility)

        Returns:
            dict: Response with ultrafast_charging status if successful, False otherwise

        Example:
            # Enable UltraFast charging (1300W max)
            result = await device.set_ultrafast_charging(enabled=True)
        """
        resp = {}
        if enabled is not None and not self.validate_command_value(
            "ultrafast_charging", 1 if enabled else 0
        ):
            self._logger.error(
                "Device %s %s control error - Invalid ultrafast charging value: %s",
                self.pn,
                self.sn,
                enabled,
            )
            return False
        if enabled is not None:
            if toFile or await self._send_mqtt_command(
                command="c1000x_ultrafast_toggle",
                parameters={"enabled": enabled},
                description=f"UltraFast charging {'enabled' if enabled else 'disabled'}",
                toFile=toFile,
            ):
                resp["ultrafast_charging"] = enabled
                if toFile:
                    self._filedata["ultrafast_charging"] = enabled
        return resp or False

    def has_expansion_pack(self) -> bool:
        """Detect if the C1000X has an expansion pack installed.

        Uses multiple detection methods based on real device analysis:
        1. Primary indicator fields (expansion_packs_a, expansion_packs_b)
        2. Expansion data presence (exp_1_soc, exp_1_type, etc.)
        3. Fallback to primary expansion_packs field

        Returns:
            bool: True if expansion pack is detected, False otherwise

        Example:
            if device.has_expansion_pack():
                print(f"Total battery SOC: {device.get_expansion_battery_soc()}%")
        """
        # Get current MQTT data
        data = self.mqttdata

        if not data:
            self._logger.debug("No MQTT data available for expansion pack detection")
            return False

        # Method 1: Check indicator fields (most reliable based on real device data)
        expansion_indicators = [
            data.get('expansion_packs_a', 0),
            data.get('expansion_packs_b', 0),
            data.get('expansion_packs_c', 0)
        ]

        # If any indicator field shows expansion (value > 0)
        if any(val and int(val or 0) > 0 for val in expansion_indicators if val is not None):
            self._logger.debug(f"Expansion detected via indicator fields: {expansion_indicators}")
            return True

        # Method 2: Check for expansion-specific data presence
        expansion_data_fields = [
            data.get('exp_1_soc'),
            data.get('exp_1_soh'),
            data.get('exp_1_type'),
            data.get('sw_expansion')
        ]

        # If we have meaningful expansion data (SOC > 0, type defined, etc.)
        if (data.get('exp_1_soc') and int(data.get('exp_1_soc', 0)) > 0) or \
           data.get('exp_1_type'):
            self._logger.debug(f"Expansion detected via data presence: SOC={data.get('exp_1_soc')}, type={data.get('exp_1_type')}")
            return True

        # Method 3: Fallback to primary field
        primary_expansion = data.get('expansion_packs', 0)
        if primary_expansion and int(primary_expansion) > 0:
            self._logger.debug(f"Expansion detected via primary field: {primary_expansion}")
            return True

        self._logger.debug("No expansion pack detected")
        return False

    def get_expansion_battery_soc(self) -> int | None:
        """Get the expansion battery state of charge.

        Returns:
            int | None: Expansion battery SOC percentage, or None if no expansion
        """
        if not self.has_expansion_pack():
            return None

        exp_soc = self.mqttdata.get('exp_1_soc')
        return int(exp_soc) if exp_soc is not None else None

    def get_total_battery_soc(self) -> int | None:
        """Get the combined battery state of charge (main + expansion).

        For devices with expansion packs, this provides the total SOC.
        For devices without expansion, returns the main battery SOC.

        Returns:
            int | None: Total battery SOC percentage
        """
        data = self.mqttdata

        # Check if device provides battery_soc_total directly
        if 'battery_soc_total' in data and data['battery_soc_total'] is not None:
            return int(data['battery_soc_total'])

        # Calculate from individual batteries if expansion present
        if self.has_expansion_pack():
            main_soc = data.get('battery_soc')
            exp_soc = data.get('exp_1_soc')

            if main_soc is not None and exp_soc is not None:
                # Average SOC of both 1056Wh batteries (equal capacity)
                return round((int(main_soc) + int(exp_soc)) / 2)

        # Return main battery SOC for devices without expansion
        main_soc = data.get('battery_soc')
        return int(main_soc) if main_soc is not None else None

    def get_expansion_info(self) -> dict:
        """Get comprehensive expansion pack information.

        Returns:
            dict: Expansion pack details including detection method, SOC, health, type
        """
        data = self.mqttdata

        return {
            "has_expansion": self.has_expansion_pack(),
            "detection_fields": {
                "expansion_packs": data.get('expansion_packs', 0),
                "expansion_packs_a": data.get('expansion_packs_a', 0),
                "expansion_packs_b": data.get('expansion_packs_b', 0),
                "expansion_packs_c": data.get('expansion_packs_c', 0)
            },
            "expansion_data": {
                "soc": data.get('exp_1_soc'),
                "soh": data.get('exp_1_soh'),
                "type": data.get('exp_1_type'),
                "temperature": data.get('exp_1_temperature'),
                "firmware": data.get('sw_expansion')
            },
            "total_soc": self.get_total_battery_soc()
        }
