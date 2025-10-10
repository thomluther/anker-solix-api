# C1000X API Reference

Complete API reference for Anker SOLIX C1000X (A1761) portable power station control and monitoring.

## Table of Contents
- [Overview](#overview)
- [Control Methods](#control-methods)
  - [set_c1000x_ac_output](#set_c1000x_ac_output)
  - [set_c1000x_dc_output](#set_c1000x_dc_output)
  - [set_c1000x_display](#set_c1000x_display)
  - [set_c1000x_display_mode](#set_c1000x_display_mode)
  - [set_c1000x_light_mode](#set_c1000x_light_mode)
  - [set_c1000x_backup_charge](#set_c1000x_backup_charge)
  - [set_c1000x_temp_unit](#set_c1000x_temp_unit)
  - [set_c1000x_dc_output_mode](#set_c1000x_dc_output_mode)
  - [set_c1000x_ac_output_mode](#set_c1000x_ac_output_mode)
- [Status Methods](#status-methods)
  - [get_c1000x_status](#get_c1000x_status)
- [Device Attributes](#device-attributes)
- [Error Handling](#error-handling)

## Overview

All C1000X control methods are implemented as async methods in the `AnkerSolixApi` class. They provide:
- Input validation for device model and parameter values
- Automatic device attribute updates via cloud API
- Detailed logging of operations
- Consistent return values (dict on success, False on failure)

### Common Parameters

Most control methods share these common parameters:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `deviceSn` | str | Yes | Device serial number (e.g., "YOUR_DEVICE_SERIAL") |
| `toFile` | bool | No | If True, save to test file instead of API call (default: False) |

### Common Return Values

Control methods return:
- **Success**: `dict` containing updated device attributes
- **Failure**: `False` (with error logged)

Status retrieval methods return:
- **Success**: `dict` containing requested attributes
- **Failure**: Empty `dict` `{}` (with error logged)

## Control Methods

### set_c1000x_ac_output

Control the AC output power state.

```python
async def set_c1000x_ac_output(
    self,
    deviceSn: str,
    enabled: bool,
    toFile: bool = False
) -> bool | dict
```

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `deviceSn` | str | Yes | Device serial number |
| `enabled` | bool | Yes | True to enable AC output, False to disable |
| `toFile` | bool | No | Save to test file instead of API call |

#### Device Attribute

- **Name**: `switch_ac_output_power`
- **Values**: 0 (disabled), 1 (enabled)

#### Return Value

- **Success**: Dict with updated `switch_ac_output_power` attribute
- **Failure**: `False`

#### Example Usage

```python
from api import api
import asyncio
from aiohttp import ClientSession

async def control_ac_output():
    async with ClientSession() as session:
        myapi = api.AnkerSolixApi(
            "user@example.com",
            "password",
            "US",
            session,
            logger
        )

        device_sn = "YOUR_DEVICE_SERIAL"

        # Enable AC output
        result = await myapi.set_c1000x_ac_output(device_sn, True)
        if result:
            print(f"AC output enabled: {result}")
        else:
            print("Failed to enable AC output")

        # Disable AC output
        result = await myapi.set_c1000x_ac_output(device_sn, False)
        if result:
            print(f"AC output disabled: {result}")

asyncio.run(control_ac_output())
```

#### Error Conditions

- Device not found or not model A1761
- Device offline
- Invalid parameter type
- API communication error

---

### set_c1000x_dc_output

Control the 12V DC car port output state.

```python
async def set_c1000x_dc_output(
    self,
    deviceSn: str,
    enabled: bool,
    toFile: bool = False
) -> bool | dict
```

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `deviceSn` | str | Yes | Device serial number |
| `enabled` | bool | Yes | True to enable 12V DC output, False to disable |
| `toFile` | bool | No | Save to test file instead of API call |

#### Device Attribute

- **Name**: `switch_12v_dc_output_power`
- **Values**: 0 (disabled), 1 (enabled)

#### Return Value

- **Success**: Dict with updated `switch_12v_dc_output_power` attribute
- **Failure**: `False`

#### Example Usage

```python
# Enable 12V DC output
result = await myapi.set_c1000x_dc_output("YOUR_DEVICE_SERIAL", True)

# Disable 12V DC output
result = await myapi.set_c1000x_dc_output("YOUR_DEVICE_SERIAL", False)
```

#### Error Conditions

- Device not found or not model A1761
- Device offline
- Invalid parameter type
- API communication error

---

### set_c1000x_display

Control the LCD display on/off state.

```python
async def set_c1000x_display(
    self,
    deviceSn: str,
    enabled: bool,
    toFile: bool = False
) -> bool | dict
```

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `deviceSn` | str | Yes | Device serial number |
| `enabled` | bool | Yes | True to turn display on, False to turn off |
| `toFile` | bool | No | Save to test file instead of API call |

#### Device Attribute

- **Name**: `switch_display`
- **Values**: 0 (off), 1 (on)

#### Return Value

- **Success**: Dict with updated `switch_display` attribute
- **Failure**: `False`

#### Example Usage

```python
# Turn display on
result = await myapi.set_c1000x_display("YOUR_DEVICE_SERIAL", True)

# Turn display off
result = await myapi.set_c1000x_display("YOUR_DEVICE_SERIAL", False)
```

#### Notes

- Display will auto-off based on `display_timeout_seconds` setting
- Common timeout values: 20, 30, 60, 300, 1800 seconds

---

### set_c1000x_display_mode

Set the display brightness level.

```python
async def set_c1000x_display_mode(
    self,
    deviceSn: str,
    mode: int | str,
    toFile: bool = False
) -> bool | dict
```

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `deviceSn` | str | Yes | Device serial number |
| `mode` | int or str | Yes | Display brightness mode (see values below) |
| `toFile` | bool | No | Save to test file instead of API call |

#### Device Attribute

- **Name**: `display_mode`
- **Values**:
  - `0` or `"off"` - Display off
  - `1` or `"low"` - Low brightness
  - `2` or `"medium"` - Medium brightness
  - `3` or `"high"` - High brightness

#### Return Value

- **Success**: Dict with updated `display_mode` attribute
- **Failure**: `False`

#### Example Usage

```python
# Set using numeric value
result = await myapi.set_c1000x_display_mode("YOUR_DEVICE_SERIAL", 2)

# Set using string value (case-insensitive)
result = await myapi.set_c1000x_display_mode("YOUR_DEVICE_SERIAL", "high")
result = await myapi.set_c1000x_display_mode("YOUR_DEVICE_SERIAL", "LOW")

# Turn off via mode
result = await myapi.set_c1000x_display_mode("YOUR_DEVICE_SERIAL", "off")
```

#### Error Conditions

- Device not found or not model A1761
- Invalid mode value (must be 0-3 or valid string)
- Device offline
- API communication error

---

### set_c1000x_light_mode

Set the front LED light mode.

```python
async def set_c1000x_light_mode(
    self,
    deviceSn: str,
    mode: int | str,
    toFile: bool = False
) -> bool | dict
```

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `deviceSn` | str | Yes | Device serial number |
| `mode` | int or str | Yes | Light mode (see values below) |
| `toFile` | bool | No | Save to test file instead of API call |

#### Device Attribute

- **Name**: `light_mode`
- **Values**:
  - `0` or `"off"` - Light off
  - `1` or `"low"` - Low brightness
  - `2` or `"medium"` - Medium brightness
  - `3` or `"high"` - High brightness
  - `4` or `"blinking"` - Blinking mode (emergency signal)

#### Return Value

- **Success**: Dict with updated `light_mode` attribute
- **Failure**: `False`

#### Example Usage

```python
# Set using numeric value
result = await myapi.set_c1000x_light_mode("YOUR_DEVICE_SERIAL", 3)

# Set using string value
result = await myapi.set_c1000x_light_mode("YOUR_DEVICE_SERIAL", "blinking")
result = await myapi.set_c1000x_light_mode("YOUR_DEVICE_SERIAL", "off")

# Cycle through modes
modes = ["off", "low", "medium", "high", "blinking"]
for mode in modes:
    await myapi.set_c1000x_light_mode("YOUR_DEVICE_SERIAL", mode)
    await asyncio.sleep(2)
```

#### Error Conditions

- Device not found or not model A1761
- Invalid mode value (must be 0-4 or valid string)
- Device offline
- API communication error

---

### set_c1000x_backup_charge

Control backup charge mode to maintain battery at 100% for emergency power.

```python
async def set_c1000x_backup_charge(
    self,
    deviceSn: str,
    enabled: bool,
    toFile: bool = False
) -> bool | dict
```

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `deviceSn` | str | Yes | Device serial number |
| `enabled` | bool | Yes | True to enable backup mode, False to disable |
| `toFile` | bool | No | Save to test file instead of API call |

#### Device Attribute

- **Name**: `backup_charge`
- **Values**: 0 (disabled), 1 (enabled)

#### Return Value

- **Success**: Dict with updated `backup_charge` attribute
- **Failure**: `False`

#### Example Usage

```python
# Enable backup charge mode (keeps battery at 100%)
result = await myapi.set_c1000x_backup_charge("YOUR_DEVICE_SERIAL", True)

# Disable backup charge mode (normal operation)
result = await myapi.set_c1000x_backup_charge("YOUR_DEVICE_SERIAL", False)
```

#### Notes

- When enabled, device will charge to and maintain 100% SOC
- Useful for emergency preparedness or storm situations
- May reduce battery lifespan if used continuously
- Recommended to disable for normal daily use

---

### set_c1000x_temp_unit

Set temperature display unit preference.

```python
async def set_c1000x_temp_unit(
    self,
    deviceSn: str,
    fahrenheit: bool,
    toFile: bool = False
) -> bool | dict
```

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `deviceSn` | str | Yes | Device serial number |
| `fahrenheit` | bool | Yes | True for Fahrenheit, False for Celsius |
| `toFile` | bool | No | Save to test file instead of API call |

#### Device Attribute

- **Name**: `temp_unit_fahrenheit`
- **Values**: 0 (Celsius), 1 (Fahrenheit)

#### Return Value

- **Success**: Dict with updated `temp_unit_fahrenheit` attribute
- **Failure**: `False`

#### Example Usage

```python
# Set to Celsius
result = await myapi.set_c1000x_temp_unit("YOUR_DEVICE_SERIAL", False)

# Set to Fahrenheit
result = await myapi.set_c1000x_temp_unit("YOUR_DEVICE_SERIAL", True)
```

#### Notes

- This only affects display unit, not the actual temperature values
- MQTT data may still report in Celsius - convert as needed
- Setting is persisted on device

---

### set_c1000x_dc_output_mode

Set the 12V DC output power management mode.

```python
async def set_c1000x_dc_output_mode(
    self,
    deviceSn: str,
    mode: int | str,
    toFile: bool = False
) -> bool | dict
```

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `deviceSn` | str | Yes | Device serial number |
| `mode` | int or str | Yes | DC output mode (see values below) |
| `toFile` | bool | No | Save to test file instead of API call |

#### Device Attribute

- **Name**: `12v_dc_output_mode`
- **Values**:
  - `1` or `"normal"` - Always on when enabled
  - `2` or `"smart"` - Auto shutoff when no load detected

#### Return Value

- **Success**: Dict with updated `12v_dc_output_mode` attribute
- **Failure**: `False`

#### Example Usage

```python
# Set to normal mode (always on)
result = await myapi.set_c1000x_dc_output_mode("YOUR_DEVICE_SERIAL", 1)
result = await myapi.set_c1000x_dc_output_mode("YOUR_DEVICE_SERIAL", "normal")

# Set to smart mode (auto shutoff)
result = await myapi.set_c1000x_dc_output_mode("YOUR_DEVICE_SERIAL", 2)
result = await myapi.set_c1000x_dc_output_mode("YOUR_DEVICE_SERIAL", "smart")
```

#### Notes

- Smart mode saves power by shutting off when no load detected
- Normal mode keeps output on continuously when enabled
- Smart mode may not work with very low power devices
- Detection threshold varies by device

---

### set_c1000x_ac_output_mode

Set the AC output power management mode.

```python
async def set_c1000x_ac_output_mode(
    self,
    deviceSn: str,
    mode: int | str,
    toFile: bool = False
) -> bool | dict
```

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `deviceSn` | str | Yes | Device serial number |
| `mode` | int or str | Yes | AC output mode (see values below) |
| `toFile` | bool | No | Save to test file instead of API call |

#### Device Attribute

- **Name**: `ac_output_mode`
- **Values**:
  - `1` or `"normal"` - Always on when enabled
  - `2` or `"smart"` - Auto shutoff when no load detected

#### Return Value

- **Success**: Dict with updated `ac_output_mode` attribute
- **Failure**: `False`

#### Example Usage

```python
# Set to normal mode
result = await myapi.set_c1000x_ac_output_mode("YOUR_DEVICE_SERIAL", "normal")

# Set to smart mode
result = await myapi.set_c1000x_ac_output_mode("YOUR_DEVICE_SERIAL", "smart")
```

#### Notes

- Smart mode conserves battery by auto-shutoff when no load
- Useful for devices that may not draw power continuously
- Normal mode better for refrigerators or continuous loads
- Smart detection may take 30-60 seconds to trigger shutoff

---

## Status Methods

### get_c1000x_status

Retrieve comprehensive device status including all control states and sensor values.

```python
async def get_c1000x_status(
    self,
    deviceSn: str,
    fromFile: bool = False
) -> dict
```

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `deviceSn` | str | Yes | Device serial number |
| `fromFile` | bool | No | Read from test file instead of API call |

#### Return Value

Returns dictionary containing current device status attributes:

```python
{
    # Power Output States
    "switch_ac_output_power": 1,        # 0=off, 1=on
    "switch_12v_dc_output_power": 1,    # 0=off, 1=on

    # Display States
    "switch_display": 1,                 # 0=off, 1=on
    "display_mode": 2,                   # 0-3 (off/low/medium/high)
    "light_mode": 0,                     # 0-4 (off/low/medium/high/blinking)

    # System Settings
    "backup_charge": 0,                  # 0=off, 1=on
    "temp_unit_fahrenheit": 0,           # 0=C, 1=F

    # Power Modes
    "12v_dc_output_mode": 1,             # 1=normal, 2=smart
    "ac_output_mode": 1,                 # 1=normal, 2=smart

    # Battery Status
    "battery_soc": 85,                   # Percentage 0-100

    # System Information
    "temperature": 28,                   # Degrees C or F
    "max_load": 1000,                    # Watts
    "device_timeout_minutes": 60,        # Minutes
    "display_timeout_seconds": 60        # Seconds
}
```

#### Example Usage

```python
# Get complete status
status = await myapi.get_c1000x_status("YOUR_DEVICE_SERIAL")

# Check specific values
if status:
    print(f"Battery: {status.get('battery_soc')}%")
    print(f"AC Output: {'On' if status.get('switch_ac_output_power') else 'Off'}")
    print(f"Temperature: {status.get('temperature')}C")
    print(f"Display Mode: {status.get('display_mode')}")

    # Make decisions based on status
    if status.get('battery_soc', 0) < 20:
        await myapi.set_c1000x_ac_output(device_sn, False)
        print("Battery low - AC output disabled")
```

#### Retrieved Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `switch_ac_output_power` | int | AC output state (0/1) |
| `switch_12v_dc_output_power` | int | 12V DC output state (0/1) |
| `switch_display` | int | Display on/off (0/1) |
| `backup_charge` | int | Backup charge mode (0/1) |
| `temp_unit_fahrenheit` | int | Temperature unit (0=C, 1=F) |
| `display_mode` | int | Display brightness (0-3) |
| `light_mode` | int | Light mode (0-4) |
| `12v_dc_output_mode` | int | DC power mode (1-2) |
| `ac_output_mode` | int | AC power mode (1-2) |
| `battery_soc` | int | Battery percentage (0-100) |
| `temperature` | int | Device temperature |
| `max_load` | int | Maximum load watts |
| `device_timeout_minutes` | int | Auto-off timeout |
| `display_timeout_seconds` | int | Display timeout |

#### Error Conditions

- Device not found or not model A1761
- Device offline
- API communication error
- Returns empty dict `{}` on error

---

## Device Attributes

Complete reference of all C1000X device attributes that can be read or controlled.

### Control Attributes

| Attribute Name | Type | Access | Values | Description |
|----------------|------|--------|--------|-------------|
| `switch_ac_output_power` | int | R/W | 0, 1 | AC outlet power switch |
| `switch_12v_dc_output_power` | int | R/W | 0, 1 | 12V car port power switch |
| `switch_display` | int | R/W | 0, 1 | LCD display on/off |
| `display_mode` | int | R/W | 0-3 | Display brightness level |
| `light_mode` | int | R/W | 0-4 | Front LED light mode |
| `backup_charge` | int | R/W | 0, 1 | Backup charge mode |
| `temp_unit_fahrenheit` | int | R/W | 0, 1 | Temperature unit preference |
| `12v_dc_output_mode` | int | R/W | 1, 2 | 12V DC power management |
| `ac_output_mode` | int | R/W | 1, 2 | AC power management |

### Status Attributes (Read-only)

| Attribute Name | Type | Unit | Description |
|----------------|------|------|-------------|
| `battery_soc` | int | % | Battery state of charge |
| `temperature` | int | C/F | Device temperature |
| `max_load` | int | W | Maximum load capacity |
| `device_timeout_minutes` | int | min | Device auto-shutoff timeout |
| `display_timeout_seconds` | int | sec | Display auto-off timeout |

### MQTT-only Attributes

These attributes are available through MQTT monitoring but not via cloud API:

| Attribute Name | Type | Unit | Description |
|----------------|------|------|-------------|
| `ac_output_power` | int | W | Current AC output power |
| `ac_output_power_total` | int | W | Total AC capacity |
| `usbc_1_power` | int | W | USB-C port 1 power |
| `usbc_2_power` | int | W | USB-C port 2 power |
| `usba_1_power` | int | W | USB-A port 1 power |
| `usba_2_power` | int | W | USB-A port 2 power |
| `dc_input_power` | int | W | DC charging input |
| `grid_to_battery_power` | int | W | AC charging input |
| `battery_soh` | int | % | Battery state of health |
| `exp_1_soc` | int | % | Expansion battery SOC |
| `exp_1_soh` | int | % | Expansion battery SOH |
| `exp_1_temperature` | int | C/F | Expansion temperature |
| `exp_1_type` | int | - | Expansion pack type code |
| `sw_version` | str | - | Software version |
| `sw_controller` | str | - | Controller version |
| `sw_expansion` | str | - | Expansion firmware |
| `hw_version` | str | - | Hardware version |
| `device_sn` | str | - | Device serial number |

---

## Error Handling

### Error Return Values

All control methods follow consistent error handling:

```python
result = await myapi.set_c1000x_ac_output(device_sn, True)

if result is False:
    # Error occurred - check logs
    print("Command failed")
elif isinstance(result, dict):
    # Success - result contains updated attributes
    print(f"Command succeeded: {result}")
```

### Common Error Scenarios

#### Device Validation Errors

```python
# Device not found
result = await myapi.set_c1000x_ac_output("INVALID_SN", True)
# Logs: "Device INVALID_SN is not a C1000X (A1761) or not found"
# Returns: False

# Wrong device model
result = await myapi.set_c1000x_ac_output("SOLARBANK_SN", True)
# Logs: "Device SOLARBANK_SN is not a C1000X (A1761) or not found"
# Returns: False
```

#### Parameter Validation Errors

```python
# Invalid display mode
result = await myapi.set_c1000x_display_mode(device_sn, 5)
# Logs: "Invalid display mode value: 5"
# Returns: False

# Invalid mode string
result = await myapi.set_c1000x_light_mode(device_sn, "invalid")
# Logs: "Invalid light mode string: invalid"
# Returns: False
```

#### API Communication Errors

```python
# Device offline or API error
result = await myapi.set_c1000x_ac_output(device_sn, True)
# Logs: "Failed to set C1000X {device_sn} AC output"
# Returns: False
```

### Error Handling Best Practices

```python
async def safe_control_device(api, device_sn, enable_ac):
    """Example of comprehensive error handling."""
    try:
        # Verify device exists and is online
        device = api.devices.get(device_sn)
        if not device:
            print(f"Device {device_sn} not found")
            return False

        if device.get("device_pn") != "A1761":
            print(f"Device is not C1000X, found: {device.get('device_pn')}")
            return False

        if not device.get("wifi_online"):
            print("Device is offline")
            return False

        # Execute control command
        result = await api.set_c1000x_ac_output(device_sn, enable_ac)

        if result is False:
            print("Control command failed - check API logs")
            return False

        # Verify state change
        await asyncio.sleep(2)  # Wait for state update
        status = await api.get_c1000x_status(device_sn)

        expected_state = 1 if enable_ac else 0
        actual_state = status.get("switch_ac_output_power")

        if actual_state != expected_state:
            print(f"State mismatch: expected {expected_state}, got {actual_state}")
            return False

        print(f"AC output {'enabled' if enable_ac else 'disabled'} successfully")
        return True

    except Exception as e:
        print(f"Unexpected error: {e}")
        return False
```

### Logging

The API uses Python's logging module. Enable detailed logging:

```python
import logging

# Set API logger to DEBUG for detailed output
logger = logging.getLogger("api")
logger.setLevel(logging.DEBUG)

# Create handler
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)

# Add formatter
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)
logger.addHandler(handler)
```

This will show detailed information including:
- API requests and responses
- Device validation steps
- Attribute updates
- Error details

---

## Complete Usage Example

```python
import asyncio
import logging
from aiohttp import ClientSession
from api import api

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Complete example of C1000X control and monitoring."""

    async with ClientSession() as session:
        # Initialize API
        myapi = api.AnkerSolixApi(
            "your_email@example.com",
            "your_password",
            "US",
            session,
            logger
        )

        # Update device information
        await myapi.update_sites()
        await myapi.update_device_details()

        # Find C1000X device
        device_sn = None
        for sn, device in myapi.devices.items():
            if device.get("device_pn") == "A1761":
                device_sn = sn
                print(f"Found C1000X: {sn}")
                print(f"Alias: {device.get('alias')}")
                print(f"Online: {device.get('wifi_online')}")
                break

        if not device_sn:
            print("No C1000X device found")
            return

        # Get initial status
        print("\n=== Initial Status ===")
        status = await myapi.get_c1000x_status(device_sn)
        print(f"Battery SOC: {status.get('battery_soc')}%")
        print(f"Temperature: {status.get('temperature')}C")
        print(f"AC Output: {'On' if status.get('switch_ac_output_power') else 'Off'}")
        print(f"Display Mode: {status.get('display_mode')}")

        # Control device
        print("\n=== Control Operations ===")

        # Enable AC output
        result = await myapi.set_c1000x_ac_output(device_sn, True)
        print(f"Enable AC: {'Success' if result else 'Failed'}")

        # Set display to high brightness
        result = await myapi.set_c1000x_display_mode(device_sn, "high")
        print(f"Set display high: {'Success' if result else 'Failed'}")

        # Enable smart AC mode
        result = await myapi.set_c1000x_ac_output_mode(device_sn, "smart")
        print(f"Set smart mode: {'Success' if result else 'Failed'}")

        # Get updated status
        print("\n=== Updated Status ===")
        await asyncio.sleep(2)  # Wait for state update
        status = await myapi.get_c1000x_status(device_sn)
        print(f"AC Output: {'On' if status.get('switch_ac_output_power') else 'Off'}")
        print(f"AC Mode: {'Smart' if status.get('ac_output_mode') == 2 else 'Normal'}")
        print(f"Display Mode: {status.get('display_mode')}")

if __name__ == "__main__":
    asyncio.run(main())
```

This API reference provides complete documentation for integrating and controlling the Anker SOLIX C1000X portable power station. For integration examples and troubleshooting, see the [C1000X Integration Guide](C1000X_Integration_Guide.md).
