"""Define mapping for MQTT messages field conversions depending on Anker Solix model."""

from enum import Enum


class DeviceHexDataTypes(Enum):
    """Enumeration for Anker Solix HEX data value types."""

    str = bytes.fromhex("00")  # various number of bytes, string (Base type)
    ui = bytes.fromhex("01")  # 1 byte fix, unsigned int (Base type)
    sile = bytes.fromhex("02")  # 2 bytes fix, signed int LE (Base type)
    # var is always 4 bytes, but could be 1-4 * int, 1-2 * signed int LE or 4 Byte signed int LE
    # mapping must specify "values" to indicate number of values in bytes from beginning. Default is 0 for 1 value in 4 bytes
    var = bytes.fromhex("03")
    # bin is multiple bytes, mostly 00 or 01 but also others, bitmap pattern for settings
    # mapping must specify start byte string ("00"-"xx") for fields and field description is a list, since single field can be used for various named settings
    # each named setting must describe a "mask" integer to indicate which bit(s) are relevant for the named setting, e.g. mask 0x64 => 0100 0000
    bin = bytes.fromhex("04")
    sfle = bytes.fromhex("05")  # 4 bytes, signed float LE (Base type)
    # 06 can be many bytes, mix of Str and Byte values
    # mapping must specify start byte string ("00"-"len-1") for fields, field description needs "type" with a DeviceHexDataTypes base type vor value conversion.
    # The "length" with int for byte count can be specified (default is 1 Byte), where Length of 0 indicates that first byte contains variable field length
    strb = bytes.fromhex("06")
    unk = bytes.fromhex("FF")  # unkonwn marker


# SOLIXMQTTMAP descriptions:
# It is a nested structure to describe value extraction from Solix MQTT messages per model.messagetype.fieldname.attributes
# Field format 0x00 is variable number of bytes, string value (Base type), no special mapping attributes
# Field format 0x01 is 1 byte fix, unsigned int (Base type), "factor" can be specified optionally for value conversion
# Field format 0x02 is 2 bytes fix, signed int LE (Base type), "factor" can be specified optionally for value conversion
# Field format 0x03 is always 4 bytes, but could be 1-4 * int, 1-2 * signed int LE or 4 Bytes signed int LE
#   The mapping must specify "values" to indicate number of values in bytes from beginning. Default is 0 for 1 value in 4 bytes
#   "factor" can be specified optionally for value conversion (applies to all values)
# Field format 0x04 is a bit mask pattern, byte number [00..len-1] reflects position, mask reflects the bit relevant for the value/toggle
#   The mapping must specify start byte string ("00"-"len-1") for fields, field description is a list, since single field can be used for various named settings
#   Each named setting must describe a "mask" integer to indicate which bit(s) are relevant for the named setting, e.g. mask 0x64 => 0100 0000
# Field format 0x05 is 4 bytes, signed float LE (Base type), "factor" can be specified optionally for value conversion
# Field format 0x06 can be many bytes, mix of Str and Byte values
#   The mapping must specify start byte string ("00"-"len-1") for fields, field description needs "type" with a DeviceHexDataTypes base type vor value conversion.
#   The "length" with int for byte count can be specified (default is 1 Byte), where Length of 0 indicates that first byte contains variable field length
#   "factor" can be specified optionally for value conversion
# "factor" usage example: e.g. int field value -123456 with factor -0.001 will convert the value to float 123.456 (maintaining factor's precision)
# Timestamp values should contain "timestamp" in name to allow decoder methods to convert value to human readable format
# Version declaration bytes should contain "sw_" or "version" in name to convert the value(s) into version string
# Names with ? are hints for fields still to be validated. Names without ? should really be validated for correctness in various situations of the device
# Duplicate names for different fields must be avoided for same device types across its various message types. If same values show up in different message types
# the field name should be the same, so they can be merged once extracting the values from the messages into a consolidated dictionary for the device.

# To simplify the defined map, smaller and re-usable mappings should be defined independently and just re-used in the overall SOLIXMQTTMAP for
# the model types that use same field mapping structure. For example various models of the same family most likely share complete or subset of message maps

A17C0_0407 = {
    # Solarbank network message
    "topic": "state_info",
    "a2": {"name": "device_sn"},
    "a3": {"name": "wifi_name"},
    "a4": {"name": "wifi_signal"},
}

A17C1_0405 = {
    # Solarbank 2 param info
    "topic": "param_info",
    "a2": {"name": "device_sn"},
    "a3": {"name": "battery_soc"},
    "a6": {"name": "sw_version", "values": 4},
    "a7": {"name": "sw_controller?", "values": 4},
    "a8": {"name": "sw_expansion", "values": 4},
    "aa": {"name": "temperature"},
    "ab": {"name": "photovoltaic_power", "factor": 0.1},
    "ad": {"name": "battery_soc_total"},
    "b1": {"name": "pv_yield?", "factor": 0.0001},
    "b2": {"name": "charged_energy?", "factor": 0.00001},
    "b3": {"name": "home_consumption?", "factor": 0.0001},
    "b4": {"name": "output_cutoff_data"},
    "b5": {"name": "lowpower_input_data"},
    "b6": {"name": "input_cutoff_data"},
    "b8": {"name": "usage_mode"},
    "c2": {"name": "max_load"},
    "c7": {"name": "home_load_preset"},
    "ca": {"name": "pv_1_power", "factor": 0.1},
    "cb": {"name": "pv_2_power", "factor": 0.1},
    "cc": {"name": "pv_3_power", "factor": 0.1},
    "cd": {"name": "pv_4_power", "factor": 0.1},
    "fb": {
        "bytes": {
            "00": [{"name": "grid_export_disabled", "mask": 0x01}],
        }
    },
    "fe": {"name": "msg_timestamp"},
    # "ab": {"name": "photovoltaic_power"},
    # "ac": {"name": "battery_power_signed"},
    # "ad": {"name": "output_power"},
    # "ae": {"name": "ac_output_power_signed?"},
    # "b2": {"name": "discharged_energy?"},
    # "b9": {"name": "home_load_preset"},
    # "ba": {
    #     "bytes": {
    #         "00": [
    #             {"name": "light_mode", "mask": 0x40},
    #             {"name": "light_off", "mask": 0x20},
    #             {"name": "ac_socket_enabled", "mask": 0x08},
    #             {"name": "temp_unit_fahrenheit", "mask": 0x01},
    #         ],
    #     }
    # },
    # "bb": {"name": "heating_power"},
    # "bc": {"name": "grid_to_battery_power?"},
    # "be": {"name": "max_load_legal"},
    # "x1": {"name": "photovoltaic_power"},
    # "c4": {"name": "grid_power_signed"},
    # "c5": {"name": "home_demand"},
}

A17C1_0408 = {
    # Solarbank 2 state info
    "topic": "state_info",
    "a2": {"name": "device_sn"},
    "a3": {"name": "local_timestamp"},
    "a4": {"name": "utc_timestamp"},
    "a8": {"name": "charging_status"},
    # "af": {
    #     "bytes": {
    #         "00": [
    #             {"name": "light_mode", "mask": 0x40},
    #             {"name": "light_off", "mask": 0x20},
    #             {"name": "ac_socket_enabled", "mask": 0x08},
    #             {"name": "temp_unit_fahrenheit", "mask": 0x01},
    #         ],
    #     }
    # },
    "b0": {"name": "battery_soc"},
    "b6": {"name": "temperature"},
    "b7": {"name": "usage_mode?"},
    "b8": {"name": "home_load_preset"},
    "ce": {"name": "pv_1_power"},
    "cf": {"name": "pv_2_power"},
    "d0": {"name": "pv_3_power"},
    "d1": {"name": "pv_4_power"},
    # "ab": {"name": "photovoltaic_power"},
    # "ac": {"name": "pv_yield?"},
    # "b1": {"name": "unknown_power_2?"},
    # "b2": {"name": "home_consumption"},
    # "b6": {"name": "unknown_power_3?"},
    # "b7": {"name": "charged_energy?"},
    # "b8": {"name": "discharged_energy?"},
    # "be": {"name": "grid_import_energy"},
    # "bf": {"name": "unknown_energy_5?"},
    # "d3": {"name": "unknown_power_6?"},
    # "d6": {"name": "timestamp_1?"},
    # "dc": {"name": "max_load"},
    # "e0": {"name": "soc_min?"},
    # "e1": {"name": "soc_max?"},
    # "e2": {"name": "pv_power_3rd_party?"},
    # "e6": {"name": "pv_limit"},
    # "e7": {"name": "ac_input_limit"},
}

A17C1_040a = {
    # Solarbank 2 Expansion data
    "topic": "param_info",
    "a2": {"name": "expansion_packs"},
    "a3": {"name": "lowest_soc?"},
    "a4": {
        "bytes": {
            "0": {
                "name": "exp_1_controller_sn?",
                "length": 17,
                "type": DeviceHexDataTypes.str.value,
            },
            "17": {
                "name": "separator?",
                "type": DeviceHexDataTypes.ui.value,
            },
            "18": {
                "name": "exp_1_position?",
                "type": DeviceHexDataTypes.ui.value,
            },
            "19": {
                "name": "exp_1_temperature",
                "type": DeviceHexDataTypes.ui.value,
            },
            "20": {
                "name": "separator?",
                "type": DeviceHexDataTypes.ui.value,
            },
            "21": {
                "name": "exp_1_soc",
                "type": DeviceHexDataTypes.ui.value,
            },
            "22": {
                "name": "exp_1_soc_limit?",
                "type": DeviceHexDataTypes.ui.value,
            },
            "27": {
                "name": "exp_1_sn",
                "length": 17,
                "type": DeviceHexDataTypes.str.value,
            },
            "44": {
                "name": "end_marker?",
                "type": DeviceHexDataTypes.ui.value,
            },
        }
    },
    "a5": {
        "bytes": {
            "0": {
                "name": "exp_2_controller_sn?",
                "length": 17,
                "type": DeviceHexDataTypes.str.value,
            },
            "17": {
                "name": "separator?",
                "type": DeviceHexDataTypes.ui.value,
            },
            "18": {
                "name": "exp_2_position?",
                "type": DeviceHexDataTypes.ui.value,
            },
            "19": {
                "name": "exp_2_temperature",
                "type": DeviceHexDataTypes.ui.value,
            },
            "20": {
                "name": "separator?",
                "type": DeviceHexDataTypes.ui.value,
            },
            "21": {
                "name": "exp_2_soc",
                "type": DeviceHexDataTypes.ui.value,
            },
            "22": {
                "name": "exp_2_soc_limit?",
                "type": DeviceHexDataTypes.ui.value,
            },
            "27": {
                "name": "exp_2_sn",
                "length": 17,
                "type": DeviceHexDataTypes.str.value,
            },
            "44": {
                "name": "end_marker?",
                "type": DeviceHexDataTypes.ui.value,
            },
        }
    },
    "a6": {
        "bytes": {
            "0": {
                "name": "exp_3_controller_sn?",
                "length": 17,
                "type": DeviceHexDataTypes.str.value,
            },
            "17": {
                "name": "separator?",
                "type": DeviceHexDataTypes.ui.value,
            },
            "18": {
                "name": "exp_3_position?",
                "type": DeviceHexDataTypes.ui.value,
            },
            "19": {
                "name": "exp_3_temperature",
                "type": DeviceHexDataTypes.ui.value,
            },
            "20": {
                "name": "separator?",
                "type": DeviceHexDataTypes.ui.value,
            },
            "21": {
                "name": "exp_3_soc",
                "type": DeviceHexDataTypes.ui.value,
            },
            "22": {
                "name": "exp_3_soc_limit?",
                "type": DeviceHexDataTypes.ui.value,
            },
            "27": {
                "name": "exp_3_sn",
                "length": 17,
                "type": DeviceHexDataTypes.str.value,
            },
            "44": {
                "name": "end_marker?",
                "type": DeviceHexDataTypes.ui.value,
            },
        }
    },
    "a7": {
        "bytes": {
            "0": {
                "name": "exp_4_controller_sn?",
                "length": 17,
                "type": DeviceHexDataTypes.str.value,
            },
            "17": {
                "name": "separator?",
                "type": DeviceHexDataTypes.ui.value,
            },
            "18": {
                "name": "exp_4_position?",
                "type": DeviceHexDataTypes.ui.value,
            },
            "19": {
                "name": "exp_4_temperature",
                "type": DeviceHexDataTypes.ui.value,
            },
            "20": {
                "name": "separator?",
                "type": DeviceHexDataTypes.ui.value,
            },
            "21": {
                "name": "exp_4_soc",
                "type": DeviceHexDataTypes.ui.value,
            },
            "22": {
                "name": "exp_4_soc_limit?",
                "type": DeviceHexDataTypes.ui.value,
            },
            "27": {
                "name": "exp_4_sn",
                "length": 17,
                "type": DeviceHexDataTypes.str.value,
            },
            "44": {
                "name": "end_marker?",
                "type": DeviceHexDataTypes.ui.value,
            },
        }
    },
    "a8": {
        "bytes": {
            "0": {
                "name": "exp_5_controller_sn?",
                "length": 17,
                "type": DeviceHexDataTypes.str.value,
            },
            "17": {
                "name": "separator?",
                "type": DeviceHexDataTypes.ui.value,
            },
            "18": {
                "name": "exp_5_position?",
                "type": DeviceHexDataTypes.ui.value,
            },
            "20": {
                "name": "separator?",
                "type": DeviceHexDataTypes.ui.value,
            },
            "19": {
                "name": "exp_5_temperature",
                "type": DeviceHexDataTypes.ui.value,
            },
            "21": {
                "name": "exp_5_soc",
                "type": DeviceHexDataTypes.ui.value,
            },
            "22": {
                "name": "exp_5_soc_limit?",
                "type": DeviceHexDataTypes.ui.value,
            },
            "27": {
                "name": "exp_5_sn",
                "length": 17,
                "type": DeviceHexDataTypes.str.value,
            },
            "44": {
                "name": "end_marker?",
                "type": DeviceHexDataTypes.ui.value,
            },
        }
    },
    "fe": {"name": "msg_timestamp"},
}

A17C5_0405 = {
    # Solarbank 3 param info
    "topic": "param_info",
    "a2": {"name": "device_sn"},
    "a3": {"name": "battery_soc"},
    "a5": {"name": "temperature"},
    "a6": {"name": "battery_soc_total"},
    "a7": {"name": "sw_version", "values": 4},
    "a8": {"name": "sw_controller?", "values": 4},
    "a9": {"name": "sw_expansion", "values": 4},
    "ab": {"name": "photovoltaic_power"},
    "ac": {"name": "battery_power_signed"},
    "ad": {"name": "output_power"},
    "ae": {"name": "ac_output_power_signed"},
    "b0": {"name": "pv_yield?"},
    "b1": {"name": "charged_energy?"},
    "b2": {"name": "discharged_energy?"},
    "b3": {"name": "energy_4?"},
    "b5": {"name": "output_cutoff_controller?"},
    "b6": {"name": "output_cutoff_exp_1?"},
    "b7": {"name": "output_cutoff_exp_2?"},
    "b8": {"name": "usage_mode"},
    "b9": {"name": "home_load_preset"},
    "ba": {
        "bytes": {
            "00": [
                {"name": "light_mode", "mask": 0x40},
                {"name": "light_off", "mask": 0x20},
                {"name": "ac_socket_enabled", "mask": 0x08},
                {"name": "temp_unit_fahrenheit", "mask": 0x01},
            ],
        }
    },
    "bb": {"name": "heating_power"},
    "bc": {"name": "grid_to_battery_power"},
    "bd": {"name": "max_load"},
    "be": {"name": "max_load_legal"},
    "bf": {"name": "timestamp_backup_start"},
    "c0": {"name": "timestamp_backup_end"},
    "c2": {"name": "charge_power?"},
    "c3": {"name": "photovoltaic_power?"},
    "c4": {"name": "grid_power_signed"},
    "c5": {"name": "home_demand"},
    "c6": {"name": "pv_1_power"},
    "c7": {"name": "pv_2_power"},
    "c8": {"name": "pv_3_power"},
    "c9": {"name": "pv_4_power"},
    "cb": {"name": "expansion_packs?"},
    "d4": {"name": "device_timeout_minutes", "factor": 30},
    "d5": {"name": "pv_limit"},
    "d6": {"name": "ac_input_limit"},
    "fb": {
        "bytes": {
            "00": [{"name": "grid_export_disabled", "mask": 0x01}],
        }
    },
    "fe": {"name": "msg_timestamp"},
}

A17C5_0408 = {
    # Solarbank 3 state info
    "topic": "state_info",
    "a2": {"name": "device_sn"},
    "a3": {"name": "local_timestamp"},
    "a4": {"name": "utc_timestamp"},
    "a7": {"name": "battery_soc"},
    "a9": {"name": "usage_mode"},
    "a8": {"name": "charging_status?"},
    "aa": {"name": "home_load_preset"},
    "ab": {"name": "photovoltaic_power"},
    "ac": {"name": "pv_yield?"},
    "ad": {"name": "pv_1_energy?"},
    "ae": {"name": "pv_2_energy?"},
    "af": {"name": "pv_3_energy?"},
    "b0": {"name": "pv_4_energy?"},
    "b1": {"name": "home_demand?"},
    "b2": {"name": "home_consumption"},
    "b6": {"name": "battery_power?"},
    "b7": {"name": "charged_energy?"},
    "b8": {"name": "discharged_energy?"},
    "bd": {"name": "grid_power_signed?"},
    "be": {"name": "grid_import_energy"},
    "bf": {"name": "grid_export_energy?"},
    "c7": {"name": "pv_1_power?"},
    "c8": {"name": "pv_2_power?"},
    "c9": {"name": "pv_3_power?"},
    "ca": {"name": "pv_4_power?"},
    "d3": {"name": "ac_output_power_?"},
    "d6": {"name": "timestamp_1?"},
    "dc": {"name": "max_load"},
    "dd": {"name": "ac_input_limit?"},
    "e0": {"name": "soc_min?"},
    "e1": {"name": "soc_max?"},
    "e2": {"name": "pv_power_3rd_party?"},
    "e6": {"name": "pv_limit"},
    "e7": {"name": "ac_input_limit"},
    "cc": {"name": "temperature"},
}

A17C5_040a = (
    A17C1_040a
    | {
        # Solarbank 3 Expansion data
    }
)

A17C5_0500 = {
    # Only binary fields, format unknown
}

SOLIXMQTTMAP = {
    # Power Charger C300 DC
    "A1728": {
        "0830": {
            # Interval: ?? seconds
            "topic": "param_info",
            "a1": {
                "name": "sw_version?",
                "type": DeviceHexDataTypes.str.value,
            },
            "a2": {
                "name": "sw_esp?",
                "type": DeviceHexDataTypes.str.value,
            },
        },
    },
    # PPS C1000(X) + B1000 Extension
    "A1761": {
        "0405": {
            # Interval: ~3-5 seconds, but only with realtime trigger
            "topic": "param_info",
            "a5": {"name": "grid_to_battery_power"},
            "a6": {"name": "ac_output_power"},
            "a7": {"name": "usbc_1_power"},
            "a8": {"name": "usbc_2_power"},
            "a9": {"name": "usba_1_power"},
            "aa": {"name": "usba_2_power"},
            "ae": {"name": "dc_input_power"},
            "c1": {"name": "battery_soc"},
            "c2": {"name": "exp_1_soc"},
            "b0": {"name": "ac_output_power_total"},
            "b3": {"name": "sw_version", "values": 1},
            "b9": {"name": "sw_expansion", "values": 1},
            "ba": {"name": "sw_controller", "values": 1},
            "bd": {"name": "temperature"},
            "be": {"name": "exp_1_temperature"},
            "d0": {"name": "device_sn"},
            "d1": {"name": "max_load"},
            "d2": {"name": "device_timeout_minutes"},
            "fd": {"name": "exp_1_type"},
            "fe": {"name": "msg_timestamp"},
        },
        "0830": {
            # Interval: ?? seconds, may be triggered on App actions, but no regular interval
            "topic": "param_info",
            "a1": {
                "name": "sw_unknown_2?",
                "type": DeviceHexDataTypes.str.value,
            },
            "a2": {
                "name": "sw_version",
                "type": DeviceHexDataTypes.str.value,
            },
        },
    },
    # Solarbank 1 E1600
    "A17C0": {
        "0405": {
            # Interval: ~3-5 seconds, but only with realtime trigger
            "topic": "param_info",
            "a2": {"name": "device_sn"},
            "a3": {"name": "battery_soc"},
            "a4": {"name": "unknown_405_1?"},
            "a6": {"name": "sw_version", "values": 1},
            "a7": {"name": "sw_controller", "values": 1},
            "a8": {"name": "sw_esp?", "values": 1},
            "ab": {"name": "photovoltaic_power"},
            "ac": {"name": "output_power"},
            "ad": {"name": "unknown_405_2?"},
            "ae": {
                "bytes": {
                    "12": [{"name": "allow_export_switch", "mask": 0x04}],
                    "14": {
                        "name": "charge_priority_limit",
                        "type": DeviceHexDataTypes.ui.value,
                    },
                    "15": [{"name": "priority_discharge_switch", "mask": 0x01}],
                }
            },
            "b0": {"name": "charging_power"},
            "b1": {"name": "pv_yield", "factor": 0.0001},
            "b2": {"name": "charged_energy", "factor": 0.0001},
            "b3": {"name": "output_energy", "factor": 0.0001},
            "b4": {"name": "output_cutoff_data"},
            "b5": {"name": "lowpower_input_data"},
            "b6": {"name": "input_cutoff_data"},
            "b7": {"name": "inverter_brand"},
            "b8": {"name": "inverter_model"},
            "b9": {"name": "min_load"},
            "fe": {"name": "msg_timestamp"},
        },
        # Interval: varies, probably upon change
        "0407": A17C0_0407,
        "0408": {
            # Interval: ~60 seconds
            "topic": "state_info",
            "a2": {"name": "device_sn"},
            "a3": {"name": "local_timestamp"},
            "a4": {"name": "utc_timestamp"},
            "a5": {"name": "unknown_408_1?"},
            "a6": {"name": "unknown_408_2?"},
            "a8": {"name": "charging_status"},
            "a9": {"name": "home_load_preset"},
            "aa": {"name": "photovoltaic_power"},
            "ab": {"name": "charging_power"},
            "ac": {"name": "output_power"},
            "ad": {"name": "unknown_408_3?"},
            "af": {"name": "unknown_408_4?"},
            "b0": {"name": "battery_soc"},
            "b1": {"name": "pv_yield", "factor": 0.0001},
            "b2": {"name": "charged_energy", "factor": 0.0001},
            "b3": {"name": "output_energy", "factor": 0.0001},
            "b4": {"name": "discharged_energy", "factor": 0.0001},
            "b5": {"name": "bypass_energy", "factor": 0.0001},
            "b6": {"name": "temperature"},
            "b7": {"name": "pv_1_voltage?", "factor": 0.01},
            "b8": {"name": "pv_2_voltage?", "factor": 0.01},
            "b9": {"name": "battery_voltage?", "factor": 0.01},
        },
    },
    # Solarbank 2 E1600 Pro
    "A17C1": {
        # Interval: ~3-5 seconds, but only with realtime trigger
        "0405": A17C1_0405,
        # Interval: varies, probably upon change
        "0407": A17C0_0407,
        # Interval: ~300 seconds
        "0408": A17C1_0408,
        # Expansion data
        # Interval: ~3-5 seconds, but only with realtime trigger
        "040a": A17C1_040a,
    },
    # Solarbank 2 E1600 AC
    "A17C2": {
        # Interval: ~3-5 seconds, but only with realtime trigger
        "0405": A17C5_0405,
        # Interval: varies, probably upon change
        "0407": A17C0_0407,
        # Interval: ~300 seconds
        "0408": A17C5_0408,
        # Expansion data
        # Interval: ~3-5 seconds, but only with realtime trigger
        "040a": A17C5_040a,
    },
    # Solarbank 2 E1600 Plus
    "A17C3": {
        # Interval: ~3-5 seconds, but only with realtime trigger
        "0405": A17C1_0405,
        # Interval: varies, probably upon change
        "0407": A17C0_0407,
        # Interval: ~300 seconds
        "0408": A17C1_0408,
        # Expansion data
        # Interval: ~3-5 seconds, but only with realtime trigger
        "040a": A17C1_040a,
    },
    # Solarbank 3 E2700 Pro
    "A17C5": {
        # Interval: ~3-5 seconds, but only with realtime trigger
        "0405": A17C5_0405,
        # Interval: varies, probably upon change
        "0407": A17C0_0407,
        # Interval: ~300 seconds
        "0408": A17C5_0408,
        # Expansion data
        # Interval: ~3-5 seconds, but only with realtime trigger
        "040a": A17C5_040a,
        # multisystem message
        # Interval: ~3-10 seconds, but only with realtime trigger
        "0420": {
            "topic": "state_info",
            "a2": {"name": "device_sn"},
            "a3": {"name": "local_timestamp"},
            "a4": {"name": "utc_timestamp"},
            "a7": {"name": "battery_soc_total"},
            "a8": {"name": "parallel_devices?"},
            "a9": {"name": "expansion_packs?"},
            "ab": {"name": "grid_power_signed?"},
            "ac": {"name": "ac_output_power_signed_total?"},
            "ae": {"name": "output_power_signed_total?"},
            "af": {"name": "home_demand_total?"},
            "b1": {"name": "battery_power_signed_total?"},
            "b3": {
                "bytes": {
                    "0": {
                        "name": "parallel_1_sn",
                        "length": 0,  # First byte is byte count for type
                        "type": DeviceHexDataTypes.str.value,
                    },
                }
            },
            "b4": {
                "bytes": {
                    "0": {
                        "name": "parallel_2_sn",
                        "length": 0,  # First byte is byte count for type
                        "type": DeviceHexDataTypes.str.value,
                    },
                }
            },
            "b5": {
                "bytes": {
                    "0": {
                        "name": "parallel_3_sn",
                        "length": 0,  # First byte is byte count for type
                        "type": DeviceHexDataTypes.str.value,
                    },
                }
            },
            "b6": {
                "bytes": {
                    "0": {
                        "name": "parallel_4_sn",
                        "length": 0,  # First byte is byte count for type
                        "type": DeviceHexDataTypes.str.value,
                    },
                }
            },
            "c1": {"name": "main_device_sn?"},
            "c2": {"name": "pv_power_total?"},
        },
        # multisystem message
        # Interval: ~300 seconds
        "0421": {
            "topic": "state_info",
            "a3": {"name": "pv_limit_parallel_4?"},
            "a4": {"name": "pv_limit_parallel_3?"},
            "a5": {"name": "pv_limit_parallel_2?"},
            "a6": {"name": "pv_limit_parallel_1?"},
            "a7": {"name": "battery_soc_total"},
            "ac": {"name": "soc_max?"},
            "ad": {"name": "max_load_legal?"},
            "fc": {"name": "device_sn"},
            "fd": {"name": "local_timestamp"},
            "fe": {"name": "utc_timestamp"},
        },
        # multisystem message
        # Interval: ~300 seconds
        "0428": {
            "topic": "state_info",
            "a2": {"name": "device_sn"},
            "a3": {"name": "local_timestamp"},
            "a4": {"name": "utc_timestamp"},
            "a5": {"name": "battery_soc_total"},
            "a6": {"name": "expansion_packs?"},
            "ac": {"name": "pv_power_total?"},
            "b5": {"name": "battery_power_signed_total?"},
            "bc": {"name": "battery_power_signed"},
            "d9": {
                "bytes": {
                    "0": {
                        "name": "parallel_1_sn",
                        "length": 0,  # First byte is byte count for type
                        "type": DeviceHexDataTypes.str.value,
                    },
                }
            },
            "da": {
                "bytes": {
                    "0": {
                        "name": "parallel_2_sn",
                        "length": 0,  # First byte is byte count for type
                        "type": DeviceHexDataTypes.str.value,
                    },
                }
            },
            "db": {
                "bytes": {
                    "0": {
                        "name": "parallel_3_sn",
                        "length": 0,  # First byte is byte count for type
                        "type": DeviceHexDataTypes.str.value,
                    },
                }
            },
            "dc": {
                "bytes": {
                    "0": {
                        "name": "parallel_4_sn",
                        "length": 0,  # First byte is byte count for type
                        "type": DeviceHexDataTypes.str.value,
                    },
                }
            },
        },
        # Interval: ~300 seconds
        "0500": A17C5_0500,
    },
    "A17X7": {
        "0405": {
            # Interval: ~5 seconds, but only with realtime trigger
            "topic": "param_info",
            "a2": {"name": "device_sn"},
            "a6": {"name": "sw_version", "values": 4},
            "a7": {"name": "sw_controller", "values": 4},
            "a8": {"name": "grid_to_home_power"},
            "a9": {"name": "pv_to_grid_power"},
            "aa": {"name": "grid_import_energy", "factor": 0.01},
            "ab": {"name": "grid_export_energy", "factor": 0.01},
            "ad": {"name": "pv_to_grid_power"},
        },
    },
    "SHEMP3": {
        "0405": {
            # Interval: ~5 seconds, but only with realtime trigger
            "topic": "param_info",
            "a2": {"name": "device_sn"},
            "a8": {"name": "grid_to_home_power", "factor": 0.01},
            "a9": {"name": "pv_to_grid_power", "factor": 0.01},
            "aa": {"name": "grid_import_energy", "factor": 0.00001},
            "ab": {"name": "grid_export_energy", "factor": 0.00001},
            "fe": {"name": "msg_timestamp"},
        },
    },
}
