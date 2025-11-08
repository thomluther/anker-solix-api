"""MQTT basic device control methods for AnkerSolixApi.

This module contains common control methods for Anker Solix MQTT device classes.
Specific decive classes should be inherited from this base class
"""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Any

from .apitypes import SolixDefaults
from .mqtt import generate_mqtt_command

if TYPE_CHECKING:
    from .api import AnkerSolixApi

# Define supported Models for this class
MODELS = []
# Define supported and validated controls per Model
FEATURES = {"realtime_trigger": MODELS}


class SolixMqttDevice:
    """Define the base class to handle an Anker Solix MQTT device for controls."""

    models: list = MODELS
    features: dict = FEATURES

    def __init__(self, api_instance: AnkerSolixApi, device_sn: str) -> None:
        """Initialize."""
        self.api: AnkerSolixApi = api_instance
        self.sn: str = device_sn
        self.pn: str = ""
        self.models = self.models or MODELS
        self.features = self.features or FEATURES
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
            # Validate device type or accept any if not defined
            if (pn := device.get("device_pn")) in self.models or not self.models:
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
        """Validate command value ranges for device controls."""
        # This has to be updated according to specifc device commands and rules
        validation_rules = {
            "realtime_trigger": lambda v: SolixDefaults.TRIGGER_TIMEOUT_MIN
            <= v
            <= SolixDefaults.TRIGGER_TIMEOUT_MAX,
        }
        rule = validation_rules.get(command_id)
        return rule(value) if rule else True

    async def _send_mqtt_command(
        self, command: str, parameters: dict, description: str, toFile: bool = False
    ) -> str | bool:
        """Send MQTT command to device.

        Args:
            self: The API instance
            command: Command name for get_command_data
            parameters: Command parameters
            description: Human-readable description for logging
            toFile: If true, only create command but don't send it

        Returns:
            str | bool: String with hex command if sent, False otherwise
        """
        # Generate command hex data
        if not (hexdata := generate_mqtt_command(command, parameters)):
            self._logger.error("Failed to generate MQTT command data for %s", command)
            return False
        if toFile:
            # print the decoded command
            self._logger.info(
                "TESTMODE: Generated command for device %s %s %s:\n%s",
                self.pn,
                self.sn,
                description,
                hexdata.decode(),
            )
        else:
            try:
                # Ensure MQTT session is started
                if not self.api.mqttsession:
                    if not await self.api.startMqttSession():
                        self._logger.error(
                            "Failed to start MQTT session for device control"
                        )
                        return False
                # Publish MQTT command
                _, mqtt_info = self.api.mqttsession.publish(self.device, hexdata.hex())
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
            except (ValueError, RuntimeError) as err:
                self._logger.error(
                    "Error sending MQTT command to device %s %s: %s",
                    self.pn,
                    self.sn,
                    err,
                )
                return False
        self._logger.info("Device %s %s %s", self.pn, self.sn, description)
        return True

    def realtime_trigger(
        self,
        timeout: int = SolixDefaults.TRIGGER_TIMEOUT_DEF,
        toFile: bool = False,
    ) -> bool:
        """Trigger device realtime data publish.

        Args:
            timeout: Seconds for realtime publish to stop
            toFile: If True, return mock response (for testing compatibility)

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
        if not toFile:
            # Validate MQTT connection prior trigger
            if not (
                self.api.mqttsession and self.api.mqttsession.is_connected()
            ):
                self._logger.error(
                    "Device %s %s control error - No MQTT connection active",
                    self.pn,
                    self.sn,
                )
                return False
            msginfo = self.api.mqttsession.realtime_trigger(
                self.device, timeout=timeout
            )
            with contextlib.suppress(ValueError, RuntimeError):
                msginfo.wait_for_publish(timeout=2)
            if not msginfo.is_published():
                self._logger.error(
                    "Error sending MQTT realtime trigger to device %s %s",
                    self.pn,
                    self.sn,
                )
                return False
        return True

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
