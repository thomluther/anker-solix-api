"""MQTT device factory for creating appropriate device control instances."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .apitypes import SolixDeviceType
from .mqtt_device import SolixMqttDevice
from .mqttmap import SOLIXMQTTMAP

if TYPE_CHECKING:
    from .api import AnkerSolixApi


def create_mqtt_device(api_instance: "AnkerSolixApi", device_sn: str) -> SolixMqttDevice | None:
    """Create the appropriate MQTT device control instance based on device type.

    Args:
        api_instance: The API instance
        device_sn: The device serial number

    Returns:
        Appropriate MQTT device instance or None if device not found
    """
    if device_data := api_instance.devices.get(device_sn):
        if category := (device_data.get("type") or "").upper():
            pn = device_data.get("device_pn") or ""

            # Use lazy imports to avoid circular dependencies
            if category in [SolixDeviceType.PPS.name] and pn in SOLIXMQTTMAP:
                if pn in ["A1761"]:  # C1000X
                    from .mqtt_c1000x import SolixMqttDeviceC1000x
                    return SolixMqttDeviceC1000x(api_instance, device_sn)
                else:  # Other PPS devices
                    from .mqtt_pps import SolixMqttDevicePps
                    return SolixMqttDevicePps(api_instance, device_sn)

            if category in [SolixDeviceType.SOLARBANK.name] and pn in SOLIXMQTTMAP:
                from .mqtt_solarbank import SolixMqttDeviceSolarbank
                return SolixMqttDeviceSolarbank(api_instance, device_sn)

            # return default MQTT device supporting only the realtime trigger control
            return SolixMqttDevice(api_instance, device_sn)

    return None