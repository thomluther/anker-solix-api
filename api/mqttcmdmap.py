"""Define mapping for MQTT command messages and field conversions."""

from .apitypes import DeviceHexDataTypes

# SOLIX MQTT COMMAND MAP descriptions:
# Each command typically uses a certain message type (2 bytes). Same command may be used by various devices
# Each command message field must be described with a name and the type. If the field does not use a type, it can be omitted
# Those command message maps should be reused in the overall mqttmap
# At a later stage, these command maps may be enhanced to compose the hex command message automatically from the description

CMD_COMMON = {
    # Common command pattern seen in most of the commands
    "topic": "req",
    "a1": {"name": "pattern_22"},
    "fe": {
        "name": "msg_timestamp",
        "type": DeviceHexDataTypes.var.value,
    },
}

CMD_REALTIME_TRIGGER = CMD_COMMON | {
    # Command: Real time data message trigger
    "a2": {
        "name": "set_realtime_data",  # Disable (0) | Enable (1)
        "type": DeviceHexDataTypes.ui.value,
    },
    "a3": {
        "name": "set_timeout",  # realtime timeout in seconds when enabled
        "type": DeviceHexDataTypes.var.value,
    },
}

CMD_TEMP_UNIT = CMD_COMMON | {
    # Command: Set temperature unit
    "a2": {
        "name": "set_temp_unit_fahrenheit",  # Celcius (0) | Fahrenheit (1)
        "type": DeviceHexDataTypes.ui.value,
    },
}

CMD_DEVICE_MAX_LOAD = CMD_COMMON | {
    # Command: Set device max home load in Watt
    "a2": {
        "name": "set_device_max_load",  # supported value in Watt
        "type": DeviceHexDataTypes.sile.value,
    },
}

CMD_DEVICE_TIMEOUT_MIN = CMD_COMMON | {
    # Command: Set device timeout in minutes
    "a2": {
        "name": "set_device_timeout_min",  # supported value in minutes
        "type": DeviceHexDataTypes.sile.value,
    },
}

CMD_AC_CHARGE_LIMIT = CMD_COMMON | {
    # Command: Set AC backup charge limit
    "e5": { # TODO: Validate whether e5 is correct
        "name": "set_ac_charge_limit",  # supported Watt value
        "type": DeviceHexDataTypes.ui.value,
    },
}

CMD_AC_OUTPUT_SWITCH = CMD_COMMON | {
    # Command: PPS AC output switch setting
    "a2": {
        "name": "set_ac_output_switch",  # Disable (0) | Enable (1)
        "type": DeviceHexDataTypes.ui.value,
    },
}

CMD_AC_FAST_CHARGE_SWITCH = CMD_COMMON | {
    # Command: PPS AC (ultra)fast charge switch setting
    "a2": {
        "name": "set_ac_fast_charge_switch",  # Disable (0) | Enable (1)
        "type": DeviceHexDataTypes.ui.value,
    },
}

CMD_AC_OUTPUT_MODE = CMD_COMMON | {
    # Command: PPS AC output mode setting
    "a2": {
        "name": "set_ac_output_mode",  # Normal (1), Smart (0)
        "type": DeviceHexDataTypes.ui.value,
    },
}

CMD_DC_OUTPUT_SWITCH = CMD_COMMON | {
    # Command: PPS DC output switch setting
    "a2": {
        "name": "set_dc_output_switch",  # Disable (0) | Enable (1)
        "type": DeviceHexDataTypes.ui.value,
    },
}

CMD_12V_DC_OUTPUT_MODE = CMD_COMMON | {
    # Command: PPS 12V DC output mode setting
    "a2": {
        "name": "set_12v_dc_output_mode",  # Normal (1), Smart (0)
        "type": DeviceHexDataTypes.ui.value,
    },
}

CMD_LIGHT_MODE = CMD_COMMON | {
    # Command: PPS light mode setting
    "a2": {
        "name": "set_light_mode",  # Off (0), Low (1), Medium (2), High (3), Blinking (4)
        "type": DeviceHexDataTypes.ui.value,
    },
}

CMD_DISPLAY_SWITCH = CMD_COMMON | {
    # Command: PPS display switch setting
    "a2": {
        "name": "set_display_switch",  # Off (0), On (1)
        "type": DeviceHexDataTypes.ui.value,
    },
}

CMD_DISPLAY_MODE = CMD_COMMON | {
    # Command: PPS display mode setting
    "a2": {
        "name": "set_display_mode",  # Off (0), Low (1), Medium (2), High (3)
        "type": DeviceHexDataTypes.ui.value,
    },
}

CMD_PORT_MEMORY_SWITCH = CMD_COMMON | {
    # Command: PPS port memory switch setting
    "a2": {
        "name": "set_port_memory_switch",  # Off (0), On (1)
        "type": DeviceHexDataTypes.ui.value,
    },
}

CMD_SB_STATUS_CHECK = (
    CMD_COMMON
    | {
        # Command: Solarbank 1 Status check request?
        "a2": {
            "name": "device_sn",
            "type": DeviceHexDataTypes.str.value,
            "length": 16,
        },
        "a3": {
            "name": "charging_status",
            "type": DeviceHexDataTypes.ui.value,
        },
        "a4": {
            "name": "output_preset",  # in W
            "type": DeviceHexDataTypes.var.value,
        },
        "a5": {
            "name": "status_timeout_sec?",  # timeout for next status message?
            "type": DeviceHexDataTypes.var.value,
        },
        "a6": {
            "name": "local_timestamp",  # used for time synchronization?
            "type": DeviceHexDataTypes.var.value,
        },
        "a7": {
            "name": "next_status_timestamp",  # Requested time for next status message +56-57 seconds
            "type": DeviceHexDataTypes.var.value,
        },
        "a8": {
            "name": "unknown_1?",
            "type": DeviceHexDataTypes.ui.value,
        },
        "a9": {
            "name": "unknown_2?",
            "type": DeviceHexDataTypes.ui.value,
        },
        "aa": {
            "name": "unknown_3?",
            "type": DeviceHexDataTypes.ui.value,
        },
    }
)

CMD_SB_POWER_CUTOFF = CMD_COMMON | {
    # Command: Solarbank Set Power cutoff
    "a2": {
        "name": "output_cutoff_data",  # 10 | 5 %
        "type": DeviceHexDataTypes.ui.value,
    },
    "a3": {
        "name": "lowpower_input_data",  # 5 | 4 %
        "type": DeviceHexDataTypes.ui.value,
    },
    "a4": {
        "name": "input_cutoff_data",  # 10 | 5 %
        "type": DeviceHexDataTypes.ui.value,
    },
}

CMD_SB_INVERTER_TYPE = CMD_COMMON | {
    # Command: Solarbank 1 set Inverter Type and limits
    "a2": {
        "name": "output_cutoff_data",  # 10 | 5 %
        "type": DeviceHexDataTypes.ui.value,
    },
    "a3": {
        "name": "lowpower_input_data",  # 5 | 4 %
        "type": DeviceHexDataTypes.ui.value,
    },
    "a4": {
        "name": "input_cutoff_data",  # 10 | 5 %
        "type": DeviceHexDataTypes.ui.value,
    },
    "a5": {
        "name": "inverter_brand",  # Hex bytes of brand name, length varies
        "type": DeviceHexDataTypes.bin.value,
    },
    "a6": {
        "name": "inverter_model",  # Hey bytes of model name, length varies
        "type": DeviceHexDataTypes.bin.value,
    },
    "a7": {
        "name": "set_min_load",  # in W
        "type": DeviceHexDataTypes.sile.value,
    },
    "a8": {
        "name": "set_max_load",  # in W
        "type": DeviceHexDataTypes.sile.value,
    },
    "a9": {
        "name": "unknown_1?",  # May be 0 typically
        "type": DeviceHexDataTypes.ui.value,
    },
    "aa": {
        "name": "ch_1_min_what?",  # 500 or other, supported values unknown
        "type": DeviceHexDataTypes.var.value,
    },
    "ab": {
        "name": "ch_1_max_what?",  # 10000 or other, supported values unknown
        "type": DeviceHexDataTypes.var.value,
    },
    "ac": {
        "name": "ch_2_min_what?",  # 500 or other, supported values unknown
        "type": DeviceHexDataTypes.var.value,
    },
    "ad": {
        "name": "ch_2_max_what?",  # 10000 or other, supported values unknown
        "type": DeviceHexDataTypes.var.value,
    },
}
