"""Solarbank MQTT device control methods for AnkerSolixApi.

This module contains control methods specific to the Anker Solix Solarbank device family.
These methods provide comprehensive device control via MQTT commands.
Solarbanks can also be controlled via Api, these methods cover settings only controllable via MQTT.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .mqtt_device import SolixMqttDevice

if TYPE_CHECKING:
    from .api import AnkerSolixApi

# Define supported Models for this class
MODELS = ["A17C0"]
# Define supported and validated controls per Model
FEATURES = {
    "realtime_trigger": MODELS,
    "set_temp_unit": MODELS,
    "set_power_cutoff": MODELS,
}


class SolixMqttDeviceSolarbank(SolixMqttDevice):
    """Define the class to handle an Anker Solix MQTT device for controls."""

    def __init__(self, api_instance: AnkerSolixApi, device_sn: str) -> None:
        """Initialize."""
        self.models = MODELS
        self.features = FEATURES
        super().__init__(api_instance=api_instance, device_sn=device_sn)

    def validate_command_value(self, command_id: str, value: Any) -> bool:
        """Validate command value ranges for controls."""
        validation_rules = {
            "realtime_trigger": lambda v: 30 <= v <= 600,
            "temp_unit_control": lambda v: v in [0, 1],
            "power_cutoff_select": lambda v: v in [5, 10],
        }
        rule = validation_rules.get(command_id)
        return rule(value) if rule else True

    async def set_temp_unit(
        self,
        fahrenheit: bool,
        toFile: bool = False,
    ) -> bool | dict:
        """Set temperature unit via MQTT.

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
            command="solarbank_temp_unit",
            parameters={"fahrenheit": fahrenheit},
            description=f"temperature unit set to {'Fahrenheit' if fahrenheit else 'Celsius'}",
            toFile=toFile,
        ):
            resp["temp_unit_fahrenheit"] = fahrenheit
        if toFile:
            self._filedata.update(resp)
        return resp or False

    async def set_power_cutoff(
        self,
        limit: int | str,
        toFile: bool = False,
    ) -> bool | dict:
        """Set temperature unit via MQTT.

        Args:
            limit: True for Fahrenheit, False for Celsius
            toFile: If True, return mock response (for testing compatibility)

        Returns:
            dict: Mock response if successful, False otherwise

        Example:
            await mydevice.set_temp_unit(fahrenheit=False)  # Celsius
        """
        # response
        resp = {}
        # Validate command value
        limit = (
            int(limit)
            if str(limit).replace("-", "", 1).replace(".", "", 1).isdigit()
            else 10
        )
        if limit is not None and not self.validate_command_value(
            "power_cutoff_select", limit
        ):
            self._logger.error(
                "Device %s %s control error - Invalid temperature unit fahrenheit value: %s",
                self.pn,
                self.sn,
                limit,
            )
            return False
        # Send MQTT commands
        if limit is not None and await self._send_mqtt_command(
            command="solarbank_power_cutoff",
            parameters={"limit": limit},
            description=f"Power cutoff set to {limit!s} %",
            toFile=toFile,
        ):
            resp["output_cutoff_data"] = limit
            resp["lowpower_input_data"] = 4 if limit == 5 else 5
            resp["input_cutoff_data"] = limit
        if toFile:
            self._filedata.update(resp)
        return resp or False
