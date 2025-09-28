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

SOLIXMQTTMAP = {
    # C300 DC
    "A1728": {
        "0830": {
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
    # Solarbank C1000(X) + B1000 Extension
    "A1761": {
        "0405": {
            "topic": "param_info",
            "a5": {"name": "ac_power_in?"},
            "a6": {"name": "ac_power_out?"},
            "a7": {"name": "usbc_1_power?"},
            "a8": {"name": "usbc_2_power?"},
            "a9": {"name": "usba_1_power?"},
            "aa": {"name": "usba_2_power?"},
            "ae": {"name": "dc_power_in?"},
            "c1": {"name": "battery_soc?"},
            "c2": {"name": "exp_1_battery_soc?"},
            "b0": {"name": "ac_power_out_total?"},
            "b3": {"name": "sw_version?", "values": 1},
            "b9": {"name": "sw_exp_1?", "values": 1},
            "ba": {"name": "sw_controller?", "values": 1},
            "bd": {"name": "temperature?"},
            "be": {"name": "exp_1_temperature?"},
            "d0": {"name": "device_sn"},
            "d1": {"name": "ac_power_out_limit"},
            "d2": {"name": "device_sleeptime"},
            "fd": {"name": "exp_1_type"},
            "fe": {"name": "msg_timestamp"},
        },
    },
    # Solarbank 1 E1600
    "A17C0": {
        "0405": {
            # Interval: ~3-5 seconds, but only with realtime trigger?
            "topic": "param_info",
            "a2": {"name": "device_sn"},
            "a3": {"name": "battery_soc"},
            "a6": {"name": "sw_version", "values": 1},
            "a7": {"name": "sw_controller", "values": 1},
            "a8": {"name": "sw_esp?", "values": 1},
            "aa": {"name": "temperature"},
            "ab": {"name": "photovoltaic_power"},
            "ac": {"name": "output_power"},
            "ad": {"name": "charging_status"},
            "ae": {
                "bytes": {
                    "12": [{"name": "allow_export_switch?", "mask": 0x64}],
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
            "b9": {"name": "min_load?"},
            "fe": {"name": "msg_timestamp"},
        },
        "0407": {
            # Interval: ~10-60 seconds or upon change?
            "topic": "state_info",
            "a2": {"name": "device_sn"},
            "a3": {"name": "wifi_name"},
            "a4": {"name": "wifi_signal"},
        },
        "0408": {
            # Interval: ~60 seconds
            "topic": "state_info",
            "a2": {"name": "device_sn"},
            "a3": {"name": "local_timestamp"},
            "a4": {"name": "utc_timestamp"},
            "a5": {"name": "unknown_408_1?"},
            "a6": {"name": "unknown_408_2?"},
            "a8": {"name": "charging_status"},
            "a9": {"name": "output_preset"},
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
            "b7": {"name": "unknown_408_5?"},
            "b8": {"name": "unknown_408_6?"},
            "b9": {"name": "unknown_408_7"},
        },
    },
    # Solarbank 3 Pro E2700
    "A17C5": {
        "0405": {
            # Interval: ~?? seconds
            "topic": "param_info",
            "a2": {"name": "device_sn"},
            "a3": {"name": "battery_soc"},
            "a5": {"name": "temperature"},
            "a7": {"name": "sw_version", "values": 4},
            "a8": {"name": "sw_esp?", "values": 4},
            "a9": {"name": "sw_expansion", "values": 4},
            "ac": {"name": "battery_power_signed"},
            "ad": {"name": "output_power"},
            "ae": {"name": "ac_output_power_signed?"},
            "b0": {"name": "photovoltaic_energy?"},
            "b1": {"name": "energy_2?"},
            "b2": {"name": "discharge_energy?"},
            "b3": {"name": "energy_4?"},
            "b5": {"name": "output_cutoff_data_exp_1?"},
            "b6": {"name": "output_cutoff_data_exp_2?"},
            "b7": {"name": "output_cutoff_data_exp_3?"},
            "b8": {"name": "usage_mode"},
            "b9": {"name": "home_load_preset"},
            "bb": {"name": "heating_power"},
            "bc": {"name": "grid_to_battery_power?"},
            "bd": {"name": "max_load"},
            "be": {"name": "max_load_legal"},
            "bf": {"name": "timestamp_1?"},
            "c0": {"name": "timestamp_2?"},
            "c2": {"name": "photovoltaic_power?"},
            "c4": {"name": "grid_power_signed"},
            "c5": {"name": "home_demand"},
            "c6": {"name": "pv_1_name?"},
            "c7": {"name": "pv_2_name?"},
            "c8": {"name": "pv_3_name?"},
            "c9": {"name": "pv_4_name?"},
            "d5": {"name": "pv_limit"},
            "d6": {"name": "ac_input_limit"},
            "fe": {"name": "msg_timestamp"},
        },
        "0407": {
            # Interval: ~?? seconds
            "topic": "state_info",
            "a2": {"name": "device_sn"},
            "a3": {"name": "wifi_name"},
            "a4": {"name": "wifi_signal"},
        },
        "0408": {
            # Interval: ~?? seconds
            "topic": "state_info",
            "a2": {"name": "device_sn"},
            "a3": {"name": "timestamp_3?"},
            "a4": {"name": "timestamp_4?"},
            "aa": {"name": "home_load_preset"},
            "cc": {"name": "temperature"},
        },
        "040a": {
            # Expansion data
            # Interval: ~?? seconds
            "topic": "param_info",
            "a3": {"name": "controller_soc_or_exp_avg?"},
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
                        "name": "exp_1_position",
                        "type": DeviceHexDataTypes.ui.value,
                    },
                    "19": {
                        "name": "exp_1_temperature",
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
                        "name": "exp_2_position",
                        "type": DeviceHexDataTypes.ui.value,
                    },
                    "19": {
                        "name": "exp_2_temperature",
                        "type": DeviceHexDataTypes.ui.value,
                    },
                    "21": {
                        "name": "exp_2_soc",
                        "type": DeviceHexDataTypes.ui.value,
                    },
                    "22": {
                        "name": "exp_2_soc_limit",
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
                        "name": "exp_3_position",
                        "type": DeviceHexDataTypes.ui.value,
                    },
                    "19": {
                        "name": "exp_3_temperature",
                        "type": DeviceHexDataTypes.ui.value,
                    },
                    "21": {
                        "name": "exp_3_soc",
                        "type": DeviceHexDataTypes.ui.value,
                    },
                    "22": {
                        "name": "exp_3_soc_limit",
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
                        "name": "exp_4_position",
                        "type": DeviceHexDataTypes.ui.value,
                    },
                    "19": {
                        "name": "exp_4_temperature",
                        "type": DeviceHexDataTypes.ui.value,
                    },
                    "21": {
                        "name": "exp_4_soc",
                        "type": DeviceHexDataTypes.ui.value,
                    },
                    "22": {
                        "name": "exp_4_soc_limit",
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
                        "name": "exp_5_position",
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
                        "name": "exp_5_soc_limit",
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
        },
        "0420": {
            # appears to be multisystem message
            # Interval: ~?? seconds
            "topic": "state_info",
            "a2": {"name": "device_sn"},
            "a3": {"name": "timestamp_5?"},
            "a4": {"name": "timestamp_6?"},
            "a7": {"name": "battery_soc"},
            "ac": {"name": "charging_power?"},
            "ae": {"name": "charging_power?"},
            "b1": {"name": "photovoltaic_power?"},
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
            "c1": {"name": "parallel_1_device_sn"},
            "c2": {"name": "parallel_1_photovoltaic_power?"},
        },
    },
    "A17X7": {
        "0405": {
            # Interval: ~?? seconds
            "topic": "param_info",
            "a2": {"name": "device_sn"},
            "a6": {"name": "sw_version", "values": 4},
            "a7": {"name": "sw_controller", "values": 4},
            "a8": {"name": "grid_to_home_power?"},
            "a9": {"name": "?"},
            "aa": {"name": "grid_to_home_energy", "factor": 0.01},
            "ab": {"name": "photovoltaic_to_grid_energy", "factor": 0.01},
            "ad": {"name": "photovoltaic_to_grid_power"},
        },
    },
    "SHEMP3": {
        "0405": {
            # Interval: ~?? seconds
            "topic": "param_info",
            "a2": {"name": "device_sn"},
            "a8": {"name": "grid_to_home_power", "factor": 0.01},
            "a9": {"name": "?"},
            "aa": {"name": "grid_to_home_energy", "factor": 0.00001},
            "ab": {"name": "photovoltaic_to_grid_energy", "factor": 0.00001},
            "ad": {"name": "photovoltaic_to_grid_power?"},
            "fe": {"name": "msg_timestamp"},
        },
    },
}
