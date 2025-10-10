# Anker SOLIX C1000X Integration Guide

## Table of Contents
- [Device Overview](#device-overview)
- [MQTT Data Structure](#mqtt-data-structure)
- [Available Sensors](#available-sensors)
- [Available Controls](#available-controls)
- [Setup Instructions](#setup-instructions)
- [Home Assistant Integration](#home-assistant-integration)
- [Troubleshooting](#troubleshooting)

## Device Overview

The Anker SOLIX C1000X (Model A1761) is a portable power station with 1056Wh capacity. This library provides comprehensive monitoring and control capabilities through both the Anker cloud API and real-time MQTT messaging.

### Key Specifications
- **Model**: A1761
- **Capacity**: 1056Wh
- **AC Output**: 1000W continuous, 2000W surge
- **DC Outputs**: 12V car port, USB-C, USB-A ports
- **Expansion**: Supports B1000 expansion battery packs
- **Connectivity**: WiFi, Bluetooth

### Capabilities
- Real-time power monitoring across all ports
- Battery state of charge (SOC) and state of health (SOH) monitoring
- Temperature monitoring for device and expansion packs
- Full control over AC and DC outputs
- Display and lighting controls
- Smart power management modes
- Backup charge mode for emergency power

## MQTT Data Structure

The C1000X communicates real-time data through MQTT messages at 3-5 second intervals when monitoring is active.

### Message Types

#### 0x0405 - Real-time Parameter Information
Provides live power readings and device status updates every 3-5 seconds during active monitoring.

**Key Fields:**
- Power values: AC output, USB-C/A ports, DC input
- Battery status: SOC, SOH for main and expansion
- Temperature readings
- All control states and settings

#### 0x0830 - Device Information
Provides hardware and software version information, typically sent on app actions.

**Key Fields:**
- Hardware version
- Software version

### Triggering Real-time Data

MQTT real-time data requires the monitoring trigger to be enabled:

```python
from api import api
import asyncio
from aiohttp import ClientSession

async def enable_monitoring(device_sn: str):
    async with ClientSession() as session:
        myapi = api.AnkerSolixApi(
            "your_email",
            "your_password",
            "your_country",
            session,
            logger
        )
        # Enable real-time data trigger
        await myapi.mqtt_trigger_realtime_data(device_sn)
```

## Available Sensors

### Power Monitoring

| Sensor | MQTT Field | Unit | Description |
|--------|------------|------|-------------|
| AC Output Power | `ac_output_power` | W | Current AC output power |
| AC Output Total | `ac_output_power_total` | W | Total AC output including surge |
| USB-C 1 Power | `usbc_1_power` | W | USB-C port 1 output |
| USB-C 2 Power | `usbc_2_power` | W | USB-C port 2 output |
| USB-A 1 Power | `usba_1_power` | W | USB-A port 1 output |
| USB-A 2 Power | `usba_2_power` | W | USB-A port 2 output |
| DC Input Power | `dc_input_power` | W | DC charging input power |
| Grid to Battery | `grid_to_battery_power` | W | AC charging input power |

### Battery Status

| Sensor | MQTT Field | Unit | Description |
|--------|------------|------|-------------|
| Battery SOC | `battery_soc` | % | Main battery state of charge |
| Battery SOH | `battery_soh` | % | Main battery state of health |
| Expansion 1 SOC | `exp_1_soc` | % | Expansion battery SOC |
| Expansion 1 SOH | `exp_1_soh` | % | Expansion battery SOH |

### Temperature Monitoring

| Sensor | MQTT Field | Unit | Description |
|--------|------------|------|-------------|
| Device Temperature | `temperature` | C or F | Main device temperature |
| Expansion Temperature | `exp_1_temperature` | C or F | Expansion pack temperature |

### System Information

| Sensor | MQTT Field | Unit | Description |
|--------|------------|------|-------------|
| Software Version | `sw_version` | - | Device firmware version |
| Controller Version | `sw_controller` | - | Controller firmware version |
| Expansion Version | `sw_expansion` | - | Expansion firmware version |
| Hardware Version | `hw_version` | - | Hardware version |
| Max Load | `max_load` | W | Maximum load capacity |
| Device Timeout | `device_timeout_minutes` | min | Auto-shutoff timeout |
| Display Timeout | `display_timeout_seconds` | sec | Display auto-off timeout |
| Device Serial | `device_sn` | - | Device serial number |
| Expansion Type | `exp_1_type` | - | Expansion pack type code |

## Available Controls

### Power Output Controls

#### AC Output
Control the main AC outlet power.

```python
# Enable AC output
await api.set_c1000x_ac_output("DEVICE_SN", True)

# Disable AC output
await api.set_c1000x_ac_output("DEVICE_SN", False)
```

**Attribute**: `switch_ac_output_power`
**Values**: 0 (disabled), 1 (enabled)

#### 12V DC Output
Control the 12V car port output.

```python
# Enable 12V DC output
await api.set_c1000x_dc_output("DEVICE_SN", True)

# Disable 12V DC output
await api.set_c1000x_dc_output("DEVICE_SN", False)
```

**Attribute**: `switch_12v_dc_output_power`
**Values**: 0 (disabled), 1 (enabled)

### Display Controls

#### Display Power
Turn the LCD display on or off.

```python
# Turn display on
await api.set_c1000x_display("DEVICE_SN", True)

# Turn display off
await api.set_c1000x_display("DEVICE_SN", False)
```

**Attribute**: `switch_display`
**Values**: 0 (off), 1 (on)

#### Display Brightness Mode
Set the display brightness level.

```python
# Set display brightness (numeric or string)
await api.set_c1000x_display_mode("DEVICE_SN", 2)  # Medium
await api.set_c1000x_display_mode("DEVICE_SN", "high")
```

**Attribute**: `display_mode`
**Values**:
- 0 or "off" - Display off
- 1 or "low" - Low brightness
- 2 or "medium" - Medium brightness
- 3 or "high" - High brightness

#### Light Mode
Control the front LED light.

```python
# Set light mode (numeric or string)
await api.set_c1000x_light_mode("DEVICE_SN", 3)  # High
await api.set_c1000x_light_mode("DEVICE_SN", "blinking")
```

**Attribute**: `light_mode`
**Values**:
- 0 or "off" - Light off
- 1 or "low" - Low brightness
- 2 or "medium" - Medium brightness
- 3 or "high" - High brightness
- 4 or "blinking" - Blinking mode

### System Controls

#### Backup Charge Mode
Enable or disable backup charge mode to maintain battery at 100% for emergency power.

```python
# Enable backup charge mode
await api.set_c1000x_backup_charge("DEVICE_SN", True)

# Disable backup charge mode
await api.set_c1000x_backup_charge("DEVICE_SN", False)
```

**Attribute**: `backup_charge`
**Values**: 0 (disabled), 1 (enabled)

#### Temperature Unit
Set temperature display unit.

```python
# Set to Celsius
await api.set_c1000x_temp_unit("DEVICE_SN", False)

# Set to Fahrenheit
await api.set_c1000x_temp_unit("DEVICE_SN", True)
```

**Attribute**: `temp_unit_fahrenheit`
**Values**: 0 (Celsius), 1 (Fahrenheit)

### Smart Mode Controls

#### 12V DC Output Mode
Switch between normal and smart power saving mode for the 12V output.

```python
# Set DC output mode (numeric or string)
await api.set_c1000x_dc_output_mode("DEVICE_SN", 1)  # Normal
await api.set_c1000x_dc_output_mode("DEVICE_SN", "smart")
```

**Attribute**: `12v_dc_output_mode`
**Values**:
- 1 or "normal" - Always on when enabled
- 2 or "smart" - Auto shutoff when no load

#### AC Output Mode
Switch between normal and smart power saving mode for AC outputs.

```python
# Set AC output mode (numeric or string)
await api.set_c1000x_ac_output_mode("DEVICE_SN", 2)  # Smart
await api.set_c1000x_ac_output_mode("DEVICE_SN", "normal")
```

**Attribute**: `ac_output_mode`
**Values**:
- 1 or "normal" - Always on when enabled
- 2 or "smart" - Auto shutoff when no load

### Status Retrieval

Get comprehensive device status including all control states:

```python
status = await api.get_c1000x_status("DEVICE_SN")

print(f"AC Output: {status.get('switch_ac_output_power')}")
print(f"Battery SOC: {status.get('battery_soc')}%")
print(f"Temperature: {status.get('temperature')}C")
print(f"Display Mode: {status.get('display_mode')}")
```

## Setup Instructions

### Prerequisites
- Python 3.12 or 3.13
- Anker account with C1000X registered
- Network connectivity for the C1000X device

### Installation

1. Install the library dependencies:
```bash
pip install cryptography aiohttp aiofiles paho-mqtt
```

Or using poetry:
```bash
poetry install
```

2. Set up environment variables (recommended):
```bash
export ANKERUSER="your_email@example.com"
export ANKERPASSWORD="your_password"
export ANKERCOUNTRY="US"  # or your country code
```

### Basic Usage Example

```python
import asyncio
import logging
from aiohttp import ClientSession
from api import api

async def main():
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    async with ClientSession() as session:
        # Create API instance
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

        # Find your C1000X device
        c1000x_sn = None
        for sn, device in myapi.devices.items():
            if device.get("device_pn") == "A1761":
                c1000x_sn = sn
                print(f"Found C1000X: {sn}")
                break

        if c1000x_sn:
            # Get current status
            status = await myapi.get_c1000x_status(c1000x_sn)
            print(f"Battery SOC: {status.get('battery_soc')}%")
            print(f"AC Output: {status.get('switch_ac_output_power')}")

            # Control the device
            await myapi.set_c1000x_ac_output(c1000x_sn, True)
            await myapi.set_c1000x_display_mode(c1000x_sn, "high")

if __name__ == "__main__":
    asyncio.run(main())
```

### MQTT Monitoring Setup

```python
import asyncio
from api import api
from aiohttp import ClientSession

async def monitor_c1000x():
    async with ClientSession() as session:
        myapi = api.AnkerSolixApi(
            "your_email",
            "your_password",
            "US",
            session,
            logger
        )

        # Find your device
        await myapi.update_sites()
        c1000x_sn = "YOUR_DEVICE_SN"

        # Enable MQTT real-time monitoring
        await myapi.mqtt_trigger_realtime_data(c1000x_sn)

        # Connect to MQTT (implement your MQTT client here)
        # Messages will arrive every 3-5 seconds with real-time data

asyncio.run(monitor_c1000x())
```

For comprehensive MQTT monitoring, use the included `mqtt_monitor.py` tool:
```bash
poetry run python ./mqtt_monitor.py
```

## Home Assistant Integration

The C1000X can be integrated into Home Assistant using the [ha-anker-solix](https://github.com/thomluther/ha-anker-solix) custom integration, which uses this library.

### Entity Types Created

When integrated, the C1000X will create the following entities in Home Assistant:

#### Sensors
- `sensor.c1000x_battery_soc` - Battery percentage
- `sensor.c1000x_battery_soh` - Battery health
- `sensor.c1000x_ac_output_power` - AC output power
- `sensor.c1000x_usbc_1_power` - USB-C port 1 power
- `sensor.c1000x_usbc_2_power` - USB-C port 2 power
- `sensor.c1000x_usba_1_power` - USB-A port 1 power
- `sensor.c1000x_usba_2_power` - USB-A port 2 power
- `sensor.c1000x_dc_input_power` - DC input charging power
- `sensor.c1000x_temperature` - Device temperature
- `sensor.c1000x_max_load` - Maximum load capacity

#### Switches
- `switch.c1000x_ac_output` - AC output control
- `switch.c1000x_dc_output` - 12V DC output control
- `switch.c1000x_display` - Display on/off
- `switch.c1000x_backup_charge` - Backup charge mode

#### Selects
- `select.c1000x_display_mode` - Display brightness (off/low/medium/high)
- `select.c1000x_light_mode` - Light mode (off/low/medium/high/blinking)
- `select.c1000x_dc_output_mode` - DC mode (normal/smart)
- `select.c1000x_ac_output_mode` - AC mode (normal/smart)
- `select.c1000x_temp_unit` - Temperature unit (Celsius/Fahrenheit)

### Example Automations

#### Auto-enable AC Output When Battery Above 20%
```yaml
automation:
  - alias: "C1000X - Enable AC when battery sufficient"
    trigger:
      - platform: numeric_state
        entity_id: sensor.c1000x_battery_soc
        above: 20
    condition:
      - condition: state
        entity_id: switch.c1000x_ac_output
        state: "off"
    action:
      - service: switch.turn_on
        target:
          entity_id: switch.c1000x_ac_output
```

#### Auto-disable AC Output When Battery Low
```yaml
automation:
  - alias: "C1000X - Disable AC when battery low"
    trigger:
      - platform: numeric_state
        entity_id: sensor.c1000x_battery_soc
        below: 10
    action:
      - service: switch.turn_off
        target:
          entity_id: switch.c1000x_ac_output
      - service: notify.mobile_app
        data:
          title: "C1000X Battery Low"
          message: "Battery at {{ states('sensor.c1000x_battery_soc') }}%. AC output disabled."
```

#### Enable Backup Charge Mode During Storms
```yaml
automation:
  - alias: "C1000X - Enable backup mode for weather alerts"
    trigger:
      - platform: state
        entity_id: sensor.weather_alerts
        to: "severe"
    action:
      - service: switch.turn_on
        target:
          entity_id: switch.c1000x_backup_charge
      - service: notify.mobile_app
        data:
          title: "C1000X Emergency Mode"
          message: "Backup charge enabled due to weather alert"
```

#### Smart Display Auto-off
```yaml
automation:
  - alias: "C1000X - Auto dim display at night"
    trigger:
      - platform: time
        at: "22:00:00"
    action:
      - service: select.select_option
        target:
          entity_id: select.c1000x_display_mode
        data:
          option: "low"

  - alias: "C1000X - Restore display brightness morning"
    trigger:
      - platform: time
        at: "07:00:00"
    action:
      - service: select.select_option
        target:
          entity_id: select.c1000x_display_mode
        data:
          option: "high"
```

### Dashboard Example

```yaml
type: vertical-stack
cards:
  - type: entity
    entity: sensor.c1000x_battery_soc
    name: Battery Level
    icon: mdi:battery

  - type: horizontal-stack
    cards:
      - type: entity
        entity: sensor.c1000x_ac_output_power
        name: AC Power
      - type: entity
        entity: sensor.c1000x_dc_input_power
        name: Charging

  - type: entities
    title: C1000X Controls
    entities:
      - entity: switch.c1000x_ac_output
        name: AC Output
      - entity: switch.c1000x_dc_output
        name: 12V DC Output
      - entity: switch.c1000x_display
        name: Display
      - entity: select.c1000x_display_mode
        name: Brightness
      - entity: switch.c1000x_backup_charge
        name: Backup Mode

  - type: glance
    title: USB Ports
    entities:
      - entity: sensor.c1000x_usbc_1_power
        name: USB-C 1
      - entity: sensor.c1000x_usbc_2_power
        name: USB-C 2
      - entity: sensor.c1000x_usba_1_power
        name: USB-A 1
      - entity: sensor.c1000x_usba_2_power
        name: USB-A 2
```

## Troubleshooting

### Device Not Found

**Problem**: Device serial number not found in API response.

**Solution**:
1. Ensure device is registered in your Anker account
2. Check device is online and connected to WiFi
3. Update sites and device details:
```python
await myapi.update_sites()
await myapi.update_device_details()
```

### Control Commands Failing

**Problem**: Control commands return `False` or error.

**Solution**:
1. Verify device model is A1761:
```python
device = myapi.devices.get("DEVICE_SN")
print(device.get("device_pn"))  # Should be "A1761"
```
2. Check device is online: `device.get("wifi_online")` should be `True`
3. Ensure you have permission (owner or shared with control access)
4. Check for API rate limiting - wait a few seconds between commands

### MQTT Data Not Received

**Problem**: No MQTT messages or data not updating.

**Solution**:
1. Enable real-time data trigger:
```python
await myapi.mqtt_trigger_realtime_data(device_sn)
```
2. Verify MQTT connection is established
3. Check device is online and WiFi connected
4. Open Anker mobile app - this activates real-time streaming
5. MQTT data requires active monitoring (app open or trigger enabled)

### Invalid Command Values

**Problem**: Commands rejected with "Invalid value" error.

**Solution**:
1. Check value ranges:
   - Display mode: 0-3
   - Light mode: 0-4
   - AC/DC modes: 1-2
   - Switches: 0 or 1 (or True/False)
2. Use string values if numeric values fail:
```python
# Instead of:
await api.set_c1000x_display_mode(sn, 5)  # Invalid!

# Use:
await api.set_c1000x_display_mode(sn, "high")  # Valid
```

### Device State Synchronization Issues

**Problem**: Device state in API doesn't match actual device state.

**Solution**:
1. Refresh device attributes:
```python
status = await myapi.get_c1000x_status(device_sn, fromFile=False)
```
2. Wait 2-3 seconds after control commands for state to update
3. Use MQTT monitoring for real-time state updates
4. Cloud API updates can lag by 3-5 seconds

### Expansion Battery Not Detected

**Problem**: Expansion battery SOC/SOH showing as 0 or null.

**Solution**:
1. Verify expansion is physically connected and powered on
2. Check MQTT field `exp_1_type` for expansion type code
3. Expansion data may take 10-15 seconds to appear after connection
4. Some expansion data only available via MQTT, not cloud API

### Temperature Reading Issues

**Problem**: Temperature shows 0 or unexpected values.

**Solution**:
1. Check `temp_unit_fahrenheit` setting (0=Celsius, 1=Fahrenheit)
2. Temperature unit setting doesn't convert values, just indicates display
3. MQTT provides raw values - apply conversion if needed:
```python
temp_c = status.get('temperature')
temp_f = (temp_c * 9/5) + 32 if temp_c else None
```

### API Rate Limiting

**Problem**: Commands fail with "Too many requests" error.

**Solution**:
1. Space commands at least 1-2 seconds apart
2. Avoid rapid polling of device status
3. Use MQTT for real-time data instead of repeated API calls
4. Implement exponential backoff for retries

For additional support and community discussion, visit:
- [GitHub Issues](https://github.com/thomluther/anker-solix-api/issues)
- [Home Assistant Community Discussion](https://community.home-assistant.io/t/feature-request-integration-or-addon-for-anker-solix-e1600-solarbank/641086)
