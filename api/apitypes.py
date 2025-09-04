"""Default definitions required for the Anker Power/Solix Cloud API."""

from dataclasses import InitVar, asdict, dataclass, field
from datetime import datetime
from enum import Enum, IntEnum, StrEnum
import struct
from typing import Any, ClassVar

# API servers per region. Country assignment not clear, defaulting to EU server
API_SERVERS = {
    "eu": "https://ankerpower-api-eu.anker.com",
    "com": "https://ankerpower-api.anker.com",
}
API_LOGIN = "passport/login"
API_KEY_EXCHANGE = "openapi/oauth/key/exchange"
API_HEADERS = {
    "content-type": "application/json",
    "model-type": "DESKTOP",
    # "model-type": "PHONE",
    # "app-version": "3.6.0",
    "app-name": "anker_power",
    "os-type": "android",
}
API_COUNTRIES = {
    "com": [
        "DZ",
        "LB",
        "SY",
        "EG",
        "LY",
        "TN",
        "IL",
        "MA",
        "JO",
        "PS",
        "AR",
        "AU",
        "BR",
        "HK",
        "IN",
        "JP",
        "MX",
        "NG",
        "NZ",
        "RU",
        "SG",
        "ZA",
        "KR",
        "TW",
        "US",
        "CA",
    ],
    "eu": [
        "DE",
        "BE",
        "EL",
        "LT",
        "PT",
        "BG",
        "ES",
        "LU",
        "RO",
        "CZ",
        "FR",
        "HU",
        "SI",
        "DK",
        "HR",
        "MT",
        "SK",
        "IT",
        "NL",
        "FI",
        "EE",
        "CY",
        "AT",
        "SE",
        "IE",
        "LV",
        "PL",
        "UK",
        "IS",
        "NO",
        "LI",
        "CH",
        "BA",
        "ME",
        "MD",
        "MK",
        "GE",
        "AL",
        "RS",
        "TR",
        "UA",
        "XK",
        "AM",
        "BY",
        "AZ",
    ],
}  # TODO(2): Expand or update list once ID assignments are wrong or missing

"""Following are the Anker Power/Solix Cloud API power_service endpoints known so far. Some are common, others are mainly for balcony power systems"""
API_ENDPOINTS = {
    # Power endpoints */v1/site/*
    "homepage": "power_service/v1/site/get_site_homepage",  # Scene info for configured site(s), content as presented on App Home Page (mostly empty for shared accounts)
    "site_list": "power_service/v1/site/get_site_list",  # List of available site ids for the user, will also show sites shared withe the account
    "site_detail": "power_service/v1/site/get_site_detail",  # Information for given site_id, can also be used by shared accounts
    "site_rules": "power_service/v1/site/get_site_rules",  # Information for supported power site types and their min and max qty per device model types
    "scene_info": "power_service/v1/site/get_scen_info",  # Scene info for provided site id (contains most information as the App home screen, with some but not all device details)
    "user_devices": "power_service/v1/site/list_user_devices",  # List Device details of owned devices, not all device details information included
    "charging_devices": "power_service/v1/site/get_charging_device",  # List of Portable Power Station devices?
    "get_device_parm": "power_service/v1/site/get_site_device_param",  # Get settings of a device for the provided site id and param type (e.g. Schedules), types [1 2 3 4 5 6 7 12 13 16]
    "set_device_parm": "power_service/v1/site/set_site_device_param",  # Apply provided settings to a device for the provided site id and param type (e.g. Schedules),
    "energy_analysis": "power_service/v1/site/energy_analysis",  # Fetch energy data for given time frames
    "home_load_chart": "power_service/v1/site/get_home_load_chart",  # Fetch data as displayed in home load chart for schedule adjustments for given site_id and optional device SN (empty if solarbank not connected)
    "wifi_list": "power_service/v1/site/get_wifi_info_list",  # List of available networks for provided site id
    "get_site_price": "power_service/v1/site/get_site_price",  # List defined power price and CO2 for given site, works only for site owner account
    "update_site_price": "power_service/v1/site/update_site_price",  # Update power price and CO2 for given site, works only for site owner account
    "get_forecast_schedule": "power_service/v1/site/get_schedule",  # get remaining energy and negative price slots, works as member, {"site_id": siteId}
    "get_co2_ranking": "power_service/v1/site/co2_ranking",  # get CO2 ranking for SB2/3 site_id, works as member, {"site_id": siteId}
    "get_site_power_limit": "power_service/v1/site/get_power_limit",  # needs owner, lists power limits for system
    # Power endpoints */v1/app/*
    "get_auto_upgrade": "power_service/v1/app/get_auto_upgrade",  # List of Auto-Upgrade configuration and enabled devices, only works for site owner account
    "set_auto_upgrade": "power_service/v1/app/set_auto_upgrade",  # Set/Enable Auto-Upgrade configuration, works only for site owner account
    "bind_devices": "power_service/v1/app/get_relate_and_bind_devices",  # List with details of locally connected/bound devices, includes firmware version, works only for owner account
    "get_device_load": "power_service/v1/app/device/get_device_home_load",  # Get defined device schedule (same data as provided with device param query)
    "set_device_load": "power_service/v1/app/device/set_device_home_load",  # Set defined device schedule, Accepts the new schedule, but does NOT change it? Maybe future use for schedules per device
    "get_ota_info": "power_service/v1/app/compatible/get_ota_info",  # Get OTA status for solarbank and/or inverter serials
    "get_ota_update": "power_service/v1/app/compatible/get_ota_update",  # Get info of available OTA update
    "solar_info": "power_service/v1/app/compatible/get_compatible_solar_info",  # Solar inverter definition for solarbanks, works only with owner account
    "get_cutoff": "power_service/v1/app/compatible/get_power_cutoff",  # Get Power Cutoff settings (Min SOC) for provided site id and device sn, works only with owner account
    "set_cutoff": "power_service/v1/app/compatible/set_power_cutoff",  # Set Min SOC for device, only works for owner accounts
    "compatible_process": "power_service/v1/app/compatible/get_compatible_process",  # contains solar_info plus OTA processing codes, works only with owner account
    "get_device_fittings": "power_service/v1/app/get_relate_device_fittings",  # Device fittings for given site id and device sn. Shows Accessories like Solarbank 0W Switch info
    "get_upgrade_record": "power_service/v1/app/get_upgrade_record",  # get list of firmware update history
    "check_upgrade_record": "power_service/v1/app/check_upgrade_record",  # show an upgrade record for the device, types 1-3 show different info, only works for owner account
    "get_device_attributes": "power_service/v1/app/device/get_device_attrs",  # for solarbank and/or smart meter? {"device_sn":sn,"attributes":["rssi","pv_power_limit"]}
    "set_device_attributes": "power_service/v1/app/device/set_device_attrs",  # attr name may be different than for get, {"device_sn":sn,"attributes":{"pv_power_limit":800,"ac_power_limit":1200,"power_limit":800}}
    "get_config": "power_service/v1/app/get_config",  # shows empty config list, also for shared account
    "get_installation": "power_service/v1/app/compatible/get_installation",  # shows install_mode and solar_sn, also for shared account
    "set_installation": "power_service/v1/app/compatible/set_installation",  # not explored yet
    "get_third_platforms": "power_service/v1/app/third/platform/list",  # list supported third party device models
    "get_token_by_userid": "power_service/v1/app/get_token_by_userid",  # get token for authenticated user. Is that the token to be used to query shelly status?
    "get_shelly_status": "power_service/v1/app/get_user_op_shelly_status",  # get op_list with correct token
    "get_device_income": "power_service/v1/app/device/get_device_income",  # {"device_sn": deviceSn, "start_time": "00:00"})) # Get income data for device, works for member
    "get_device_group": "power_service/v1/app/group/get_group_devices",  # works as member, shows whether device is grouped with sub devices, {"device_sn": deviceSn}
    "get_device_charge_order_stats": "power_service/v1/app/order/get_charge_order_stats",  # works as member, date_type[week month year all], show EV_charger stats, {"device_sn":deviceSn,"date_type":"all","start_date":"","end_date":""}))
    "get_device_charge_order_stats_list": "power_service/v1/app/order/get_charge_order_stats_list",  # works as member, date_type[week month year all], order_Status unknown, {"device_sn":deviceSn,"order_status":1,"date_type":"all","start_date":"","end_date":"","page":0,"page_size":10}
    "get_ocpp_endpoint_list": "power_service/v1/app/get_ocpp_endpoint_list",  # lists ocpp endpoints used by Anker, including source number per endpoint
    "get_device_ocpp_info": "power_service/v1/app/get_ocpp_info",  # works as member also for empty device SN, {"device_sn": deviceSn}, list device endpoint source number, default 0 if nothing found explicetly? (Useful only for EV charger devices)
    "get_vehicle_brands": "power_service/v1/app/get_brand_list",  # get vehicle brand list
    "get_vehicle_brand_models": "power_service/v1/app/get_models",  # get model list for given brand, {"brand_name": "BMW"}
    "get_vehicle_model_years": "power_service/v1/app/get_model_years",  # get prodictive year list for given model, {"brand_name": "BMW", "model_name": "iX3"}
    "get_vehicle_year_attributes": "power_service/v1/app/get_model_list",  # get attributes for model and productive year, {"brand_name": "BMW", "model_name": "iX3", "productive_year": 2023}
    "get_user_vehicles": "power_service/v1/app/vehicle/get_vehicle_list",  # list of vehicles with details for account
    "get_user_vehicle_details": "power_service/v1/app/vehicle/get_vehicle_detail",  # deteils for given vehicle id, {"vehicle_id": vehicleId}
    "vehicle_add": "power_service/v1/app/vehicle/add_vehicle",  # add vehicles to account, {"user_vehicle_info": [{"vehicle_name": "MyCar","brand": "Audi","model": "eTron","productive_year": 2024}]}
    "vehicle_update": "power_service/v1/app/vehicle/update_vehicle",  # update any vehicle detail, {"vehicle_id": vehicleId, "vehicle_name": "MyCar","brand": "Audi","model": "eTron","productive_year": 2024, "battery_capacity": 80, "ac_max_charging_power": 11, "energy_consumption_per_100km": 18}
    "vehicle_delete": "power_service/v1/app/vehicle/delete_vehicle",
    "vehicle_set_charging": "power_service/v1/app/vehicle/set_charging_vehicle",  #  needs EV_Charger device, {"vehicle_id": vehicleId, "device_sn": deviceSn, "transaction_id": 1}
    "vehicle_set_default": "power_service/v1/app/vehicle/set_default",  # set vehicle id as default, {"vehicle_id": vehicleId}
    # Power endpoints */v1/device/*
    "get_tamper_records": "power_service/v1/device/get_tamper_records",  # needs owner, not sure what it does, {"device_sn": deviceSn, "page_num": 1, "page_size": 10}
    "get_currency_list": "power_service/v1/currency/get_list",  # get list of supported currencies for power sites
    # Power endpoints */v1/dynamic_price/*
    "get_dynamic_price_sites": "power_service/v1/dynamic_price/check_available",  # Get available site id_s for dynamic prices of account, works as member but list empty
    "get_dynamic_price_providers": "power_service/v1/dynamic_price/support_option",  # Get available provider list for device_pn and login country, works as member, {"device_pn": "A5102"}
    "get_dynamic_price_details": "power_service/v1/dynamic_price/price_detail",  # {"area": "GER", "company": "Nordpool", "date": "1748908800", "device_sn": ""})) # works for members, device_sn may be empty, date is int posix timestamp as string
    # Power endpoints */v1/*
    "get_message_unread": "power_service/v1/get_message_unread",  # GET method to show if there are unread messages for account
    "get_message": "power_service/v1/get_message",  # GET method to list Messages from certain time, not explored or used (last_time format unknown)
    "get_product_categories": "power_service/v1/product_categories",  # GET method to list all supported products with details and web picture links
    "get_product_accessories": "power_service/v1/product_accessories",  # GET method to list all supported products accessories with details and web picture links
    # Power endpoints */v1/ai_ems/*
    "get_ai_ems_status": "power_service/v1/ai_ems/get_status",  # Get status of AI learning mode and remaining seconds, works as member, {"site_id": siteId}))
    "get_ai_ems_profit": "power_service/v1/ai_ems/profit",  # Type is unclear, may work as member,  {"site_id": siteId, "start_time": "00:00", "end_time": "24:00", "type": "grid"}))
    # App endpoints
    "get_ota_batch": "app/ota/batch/check_update",  # get OTA information and latest version for device SN list, works also for shared accounts, but data only received for owner accounts
    "get_mqtt_info": "app/devicemanage/get_user_mqtt_info",  # post method to list mqtt server and certificates for a site, not explored or used
    "get_shared_device": "app/devicerelation/get_shared_device",  # works as member, list device sharing details, {"device_sn": deviceSn}, sharing works only for EV charger or any device?
    # Endpoints for standalone Anker inverter devices
    "get_device_pv_status": "charging_pv_svc/getPvStatus",  # post method get the current activity status and power generation of one or multiple devices
    "get_device_pv_total_statistics": "charging_pv_svc/getPvTotalStatistics",  # post method the get total statistics (generated power, saved money, saved CO2) of a device
    "get_device_pv_statistics": "charging_pv_svc/statisticsPv",  # post method to get detailed statistics on a daily, weekly, monthly or yearly basis
    "get_device_pv_price": "charging_pv_svc/selectUserTieredElecPrice",  # post method to get defined price tiers for stand alone inverter (only first tier is applied for full day)
    "set_device_pv_price": "charging_pv_svc/updateUserTieredElecPrice",  # post method to set price tiers for stand alone inverter (only first tier is applied for full day)
    "set_device_pv_power": "charging_pv_svc/set_aps_power",  # post method to set stand alone inverter limit
    "get_device_rfid_cards": "power_service/v1/rfid/get_device_cards",  # needs owner. get rfid cards (for EV charger?), {"device_sn": deviceSn}
    # Endpoints for standalone Anker power charger devices
    "charger_get_charging_modes": "mini_power/v1/app/charging/get_charging_mode_list",  # {"device_sn": deviceSn}
    "charger_get_triggers": "mini_power/v1/app/egg/get_easter_egg_trigger_list",  # {"device_sn": deviceSn}
    "charger_get_statistics": "mini_power/v1/app/power/get_day_power_data",  # {"device_sn": deviceSn, "device_model": "A2345", "date": "2025-02-27"}
    "charger_get_device_setting": "mini_power/v1/app/setting/get_device_setting",  # {"device_sn": deviceSn}
    "charger_get_screensavers": "mini_power/v1/app/style/get_clock_screensavers",  # works for {"device_sn": deviceSn, "product_code": "A2345"} => Prime charger
}

"""Following are the Anker Power/Solix Cloud API charging_energy_service endpoints known so far. They are used for Power Panels."""
API_CHARGING_ENDPOINTS = {
    "get_error_info": "charging_energy_service/get_error_infos",  # No input param needed, show errors for account?
    "get_system_running_info": "charging_energy_service/get_system_running_info",  # Cumulative Home/System Energy Savings since Home creation date
    "energy_statistics": "charging_energy_service/energy_statistics",  # Energy stats for PPS and Home Panel, # source type [solar hes grid home pps diesel]
    "get_rom_versions": "charging_energy_service/get_rom_versions",  # Check for firmware update and download available packages, needs owner account
    "get_device_info": "charging_energy_service/get_device_infos",  # Wifi and MAC infos for provided devices, needs owner account
    "get_wifi_info": "charging_energy_service/get_wifi_info",  # Displays WiFi network connected to Home Power Panel, needs owner account
    "get_installation_inspection": "charging_energy_service/get_installation_inspection",  # appears to say which page last viewed on App, needs owner account
    "get_utility_rate_plan": "charging_energy_service/get_utility_rate_plan",  # needs owner account
    "report_device_data": "charging_energy_service/report_device_data",  # ctrol [0 1], works but data is null (may need owner account?)
    "get_configs": "charging_energy_service/get_configs",  # json={"siteId": "SITEID", "sn": "POWERPANELSN", "param_types": []})) # needs owner account, list of parm types not clear
    "get_sns": "charging_energy_service/get_sns",  # json={"main_sn": "POWERPANELSN","macs": ["F38001MAC001","F38002MAC002"]})) # needs owner account, Displays Serial Numbers of attached PPS in Home
    "get_monetary_units": "charging_energy_service/get_world_monetary_unit",  # monetary unit list for system, needs owner account
}

"""Following are the Anker Power/Solix Cloud API charging_hes_svc endpoints known so far. They are used for Home Energy Systems like X1."""
API_HES_SVC_ENDPOINTS = {
    "get_product_info": "charging_hes_svc/get_device_product_info",  # List of Anker HES devices, works with shared account
    "get_heat_pump_plan": "charging_hes_svc/get_heat_pump_plan_json",  # heat pump plan, works with shared account
    "get_electric_plan_list": "charging_hes_svc/get_electric_utility_and_electric_plan_list",  # Energy plan if available for country & state combination, works with shared account
    "get_system_running_info": "charging_hes_svc/get_system_running_info",  # system runtime info, works with shared account
    "get_system_profit": "charging_hes_svc/get_system_profit_detail",  # works as member, {"siteId": siteId,"dateType": "year","start": "2025","end": ""} [day 2025-01-01, week, month 2025-01, year 2025], weekly syntax unklear
    "energy_statistics": "charging_hes_svc/get_energy_statistics",  # Energy stats for HES, # source type [solar hes grid home]
    "get_monetary_units": "charging_hes_svc/get_world_monetary_unit",  # monetary unit list for system, works with shared account
    "get_install_info": "charging_hes_svc/get_install_info",  # get system install info, works with shared account. Shows installation location
    "get_wifi_info": "charging_hes_svc/get_wifi_info",  # get device wifi info, works with shared account
    "get_installer_info": "charging_hes_svc/get_installer_info",  # no shared account access, Shows contact information of the installer
    "get_system_running_time": "charging_hes_svc/get_system_running_time",  # no shared account access, needs HES site?
    "get_mi_layout": "charging_hes_svc/get_mi_layout",  # no shared account access, needs HES site?
    "get_conn_net_tips": "charging_hes_svc/get_conn_net_tips",  # no shared account access, needs HES site?
    "get_hes_dev_info": "charging_hes_svc/get_hes_dev_info",  # works with shared account, lists hes device structure and SNs
    "report_device_data": "charging_hes_svc/report_device_data",  # no shared account access, needs HES site and installer system?
    "get_evcharger_standalone": "charging_hes_svc/get_user_bind_and_not_in_station_evchargers",  # works as member, but list may be empty
    "get_evcharger_station_info": "charging_hes_svc/get_evcharger_station_info",  # works as member, {"evChargerSn": deviceSn, "featuretype": 1}, featuretype [1,2]
}

""" Other endpoints neither implemented nor explored: 63 + 68 used => 131
    'power_service/v1/get_message_not_disturb',  # get do not disturb messages settings
    'power_service/v1/message_not_disturb',  # change do not disturb messages settings
    'power_service/v1/read_message', # payload format unknown
    'power_service/v1/add_message',
    'power_service/v1/del_message',
    'power_service/v1/dynamic_price/check_adjust',  # works for members, but only applies on owned devices?, not sure what it does, {}, lists owned SB3 device with status code but also others
    'power_service/v1/rfid/save_device_card',
    'power_service/v1/rfid/delete_device_card',
    'power_service/v1/site/can_create_site',
    'power_service/v1/site/create_site',
    'power_service/v1/site/update_site',
    'power_service/v1/site/delete_site',
    'power_service/v1/site/add_charging_device',
    'power_service/v1/site/update_charging_device',
    'power_service/v1/site/reset_charging_device',
    'power_service/v1/site/delete_charging_device',
    'power_service/v1/site/add_site_devices',
    'power_service/v1/site/delete_site_devices',
    'power_service/v1/site/update_site_devices',
    'power_service/v1/site/get_addable_site_list', # show to which defined site a given model type can be added
    'power_service/v1/site/get_comb_addable_sites',
    'power_service/v1/site/shift_power_site_type', # maybe to convert to different system type, {"site_id": siteId, "power_site_type": 11}
    'power_service/v1/site/local_net',
    'power_service/v1/site/set_device_feature', # Set device feature for site_id and smart_plug list, may require owner, usage unknown, {"site_id": siteId, "smart_plug" : [value]}) May be used for automatic control of plugs in smart mode?
    'power_service/v1/app/compatible/check_third_sn',
    'power_service/v1/app/compatible/confirm_permissions_settings',
    'power_service/v1/app/compatible/get_confirm_permissions', # works as member, {"device_model": "A17C0"} => "data": {"is_confirm": 1,"confirm_type": "APs"}
    'power_service/v1/app/compatible/installation_popup',
    'power_service/v1/app/compatible/save_compatible_solar',
    'power_service/v1/app/compatible/set_ota_update',
    'power_service/v1/app/compatible/save_ota_complete_status',
    'power_service/v1/app/device/get_mes_device_info', # shows laser_sn field but no more info
    'power_service/v1/app/device/get_relate_belong' # shows belonging of site type for given device
    'power_service/v1/app/device/remove_param_config_key'
    'power_service/v1/app/group/replace_group_devices',
    'power_service/v1/app/group/save_group_devices',
    'power_service/v1/app/group/force_save_group_devices',
    'power_service/v1/app/group/delete_group_devices',
    'power_service/v1/app/order/get_charging_order_list',  # may need real EV_Charger?, {"device_sn": deviceSn, "start_time": "<timestamp>"}
    'power_service/v1/app/order/get_charging_order_detail',  # may need real EV_Charger? {"device_sn": deviceSn}
    'power_service/v1/app/order/get_charging_order_sec_detail',  # may need real EV_Charger? {"order_id": "1","start_time": "<timestamp>"}
    'power_service/v1/app/order/get_charging_order_sec_preview',  # may need real EV_Charger? {"order_id": "1"}
    'power_service/v1/app/order/export_charge_order',
    'power_service/v1/app/after_sale/get_popup',  # works as site member, {"site_id": siteId}, get active pop ups with code
    'power_service/v1/app/after_sale/check_popup',
    'power_service/v1/app/after_sale/check_sn',  # checks whether any account device SN is eligable for replacement of battery (recall programs?)
    'power_service/v1/app/after_sale/mark_sn',
    'power_service/v1/app/share_site/anonymous_join_site',
    'power_service/v1/app/share_site/delete_site_member',
    'power_service/v1/app/share_site/invite_member',
    'power_service/v1/app/share_site/delete_inviting_member',
    'power_service/v1/app/share_site/get_invited_list',
    'power_service/v1/app/share_site/join_site',
    2*'power_service/v1/app/user/get_user_param', # works as member, {"params": []} parameters are unknown
    2*"power_service/v1/app/user/set_user_param",
    'power_service/v1/app/whitelist/feature/check', # Unclear what this is used for, requires check_list with objects for unknown feature_code e.g. {"check_list": [{"feature_code": "smartmeter", "product_code": "A17C5"}]}
    'power_service/v1/app/get_phonecode_list',
    'power_service/v1/app/get_annual_report',  # new report starting Jan 2025?
    'power_service/v1/app/report_tlv_event',  # tamper event? unknown what events to report, {"device_sn": deviceSn, "events": [{}]}
    'power_service/v1/app/shelly_ctrl_device', # {"device_sn": deviceSn, "op_type": "parameter", "value": value})) # Control shelly device settings, may require owner, usage known
    'power_service/v1/app/upgrade_event_report', # post an entry to upgrade event report

related to micro inverter without system: 1 + 6 used => 7 total
    'charging_pv_svc/getMiStatus',

App related: 18 + 3 used => 21 total
    'app/devicemanage/update_relate_device_info',
    'app/cloudstor/get_app_up_token_general',
    'app/cloudstor/get_app_up_token_without_login',
    'app/logging/get_device_logging',
    'app/logging/upload',
    'app/logging/upload_pb_events',
    'app/devicerelation/up_alias_name',  # Update Alias name of device? Fails with (10003) Failed to request
    'app/devicerelation/un_relate_and_unbind_device',
    'app/devicerelation/relate_device',
    'app/devicerelation/device_invite', # Sharing of EV charger devices, {"nick_name": "lol***", "email": "<email>", "invites": [{"device_sn": deviceSn, "member_type": 1}]}
    'app/devicerelation/confirm_invite', # accept invite
    'app/devicerelation/ignore_invite',
    'app/devicerelation/update_share',
    'app/devicerelation/clear_share',
    'app/news/get_popups',
    'app/news/popup_record',
    'app/push/clear_count',
    'app/push/register_push_token',

Passport related: 30 + 0 used => 30 total
    'passport/get_user_param', # specify param_type which must be parsable as list of int, but does not show anything in response
    'passport/update_user_param',
    'passport/get_subscriptions,  #  get user email, accept_survey, subscribe, phone_number, sms_subscribe
    'passport/set_subscriptions',
    'passport/get_profile', # get email, nickname, geokey, userid and some profile info
    'passport/login',
    'passport/logout',
    'passport/update_profile',
    'passport/change_password',
    'passport/forget_password',
    'passport/set_account_password',
    'passport/validate_pass',
    'passport/destroy_user',
    'passport/phone_reset_password',
    'passport/phone_verification_login',
    'passport/phone_verification_regist',
    'passport/phone_code_list',
    'passport/external_login',
    'passport/third_party_login',
    'passport/freeze_account',
    'passport/register',
    'passport/resend_active_email',
    'passport/validate_email', # verify if an email is already registered
    'passport/terminal_id',
    'passport/estimate_domain',
    'passport/phone_bind_account',
    'passport/phone_verification_code',
    'passport/subscription_configs',  # get show_sms
    'passport/discount_desc',  # get title, sub_title, button and sub_button

PPS and Power Panel related: 6 + 12 used => 18 total
    "charging_energy_service/sync_installation_inspection", #Unknown at this time
    "charging_energy_service/sync_config",
    "charging_energy_service/restart_peak_session",
    "charging_energy_service/preprocess_utility_rate_plan",
    "charging_energy_service/ack_utility_rate_plan",
    "charging_energy_service/adjust_station_price_unit",

    "charging_common_svc/location/get",  # Get default and identifier location for identifier_id, identifier_type, business_type with longitude, latitude, country_code, place_id, display_name, formatted_address
    "charging_common_svc/location/set",  # Set default and identifier location
    "charging_common_svc/location/support",

Home Energy System related (X1): 44 + 17 used => 61 total
    "charging_hes_svc/adjust_station_price_unit",
    "charging_hes_svc/cancel_pop",
    "charging_hes_svc/check_update",
    "charging_hes_svc/check_device_bluetooth_password",
    "charging_hes_svc/check_function",
    "charging_hes_svc/device_command",
    "charging_hes_svc/device_self_check",
    "charging_hes_svc/deal_share_data",
    "charging_hes_svc/download_energy_statistics",
    "charging_hes_svc/get_auto_disaster_prepare_status",
    "charging_hes_svc/get_auto_disaster_prepare_detail",
    "charging_hes_svc/get_back_up_history",
    "charging_hes_svc/get_current_disaster_prepare_detail",
    "charging_hes_svc/get_device_command",
    "charging_hes_svc/get_device_pn_info",
    "charging_hes_svc/get_device_card_list",
    "charging_hes_svc/get_device_card_details",
    "charging_hes_svc/get_device_self_check",
    "charging_hes_svc/get_external_device_config",
    "charging_hes_svc/get_history_setting", # needs owner
    "charging_hes_svc/get_site_mi_list",
    "charging_hes_svc/get_station_config_and_status",
    "charging_hes_svc/get_system_device_time",
    "charging_hes_svc/get_tou_price_plan_detail",
    "charging_hes_svc/get_user_fault_info",
    "charging_hes_svc/get_station_evchargers",  # needs owner
    "charging_hes_svc/get_utility_rate_plan",
    "charging_hes_svc/get_vpp_check_code",
    "charging_hes_svc/get_vpp_service_policy_by_agg_user",
    "charging_hes_svc/update_device_info_by_app",
    "charging_hes_svc/update_hes_utility_rate_plan",
    "charging_hes_svc/update_wifi_config",
    "charging_hes_svc/upload_device_status",
    "charging_hes_svc/user_event_alarm",
    "charging_hes_svc/user_fault_alarm",
    "charging_hes_svc/ota",
    "charging_hes_svc/quit_auto_disaster_prepare",
    "charging_hes_svc/remove_user_fault_info",
    "charging_hes_svc/restart_peak_session",
    "charging_hes_svc/start",
    2*"charging_hes_svc/set_station_evchargers",
    "charging_hes_svc/set_evcharger_station_feature",
    "charging_hes_svc/sync_back_up_history",

Home Energy System related (X1): 5 + 0 used => 5 total
    "charging_hes_dynamic_price_svc/get_area_by_code", # needs owner
    "charging_hes_dynamic_price_svc/get_price_company", # needs owner
    "charging_hes_dynamic_price_svc/get_price", # needs owner
    "charging_hes_dynamic_price_svc/save_time_of_use", # needs owner
    "charging_hes_dynamic_price_svc/save_dynamic_price", # needs owner

related to what, seem to work with Power Panel sites: 7 + 0 used => 7 total
    'charging_disaster_prepared/get_site_device_disaster', # {"identifier_id": siteId, "type": 2})) # works with Power panel site and shared account
    'charging_disaster_prepared/get_site_device_disaster_status', # {"identifier_id": siteId, "type": 2})) # works with Power panel site and shared account
    'charging_disaster_prepared/set_site_device_disaster',
    'charging_disaster_prepared/clear',
    'charging_disaster_prepared/quit_disaster_prepare',
    'charging_disaster_prepared/get_support_func', # {"identifier_id": siteId, "type": 2})) # works with Power panel site and shared account
    'charging_disaster_prepared/disaster_detail',

related to Prime charger models: 7 + 5 used => 12 total
    'mini_power/v1/app/charging/update_charging_mode',
    'mini_power/v1/app/charging/add_charging_mode',
    'mini_power/v1/app/charging/delete_charging_mode',
    'mini_power/v1/app/setting/set_charging_mode_status',
    'mini_power/v1/app/egg/add_easter_egg_trigger_record',
    'mini_power/v1/app/egg/report_easter_egg_trigger_status', # {"device_sn": deviceSn, "report_time": 1734969388, "egg_type": 1}
    'mini_power/v1/app/setting/set_compatibility_status',

Structure of the JSON response for an API Login Request:
An unexpired token_id must be used for API request, along with the gtoken which is an MD5 hash of the returned(encrypted) user_id.
The combination of the provided token and MD5 hashed user_id authenticate the client to the server.
The Login Response is cached in a JSON file per email user account and can be reused by this API class without further login request.

ATTENTION: Anker allows only 1 active token on the server per user account. Any login for the same account (e.g. via Anker mobile App) will kickoff the token used in this Api instance and further requests are no longer authorized.
Currently, the Api will re-authenticate automatically and therefore may kick off the other user that obtained the actual access token (e.g. kick out the App user again when used for regular Api requests)

NOTES: Parallel Api instances should use different user accounts. They may work in parallel when all using the same cached authentication data. The first API instance with failed authorization will restart a new Login request and updates
the cached JSON file. Other instances should recognize an update of the cached JSON file and will refresh their login credentials in the instance for the actual token and gtoken without new login request.
"""

# Following are the JSON filename prefixes for exported endpoint names as defined previously
API_FILEPREFIXES = {
    # power_service endpoint file prefixes
    "homepage": "homepage",
    "site_list": "site_list",
    "bind_devices": "bind_devices",
    "user_devices": "user_devices",
    "charging_devices": "charging_devices",
    "get_auto_upgrade": "auto_upgrade",
    "get_config": "config",
    "site_rules": "list_site_rules",
    "get_installation": "installation",
    "get_site_price": "price",
    "get_site_power_limit": "power_limit",
    "get_device_parm": "device_parm",
    "get_product_categories": "list_products",
    "get_product_accessories": "list_accessories",
    "get_third_platforms": "list_third_platforms",
    "get_token_by_userid": "get_token",
    "get_shelly_status": "shelly_status",
    "scene_info": "scene",
    "site_detail": "site_detail",
    "wifi_list": "wifi_list",
    "energy_solarbank": "energy_solarbank",
    "energy_solar_production": "energy_solar_production",
    "energy_home_usage": "energy_home_usage",
    "energy_grid": "energy_grid",
    "solar_info": "solar_info",
    "compatible_process": "compatible_process",
    "get_cutoff": "power_cutoff",
    "get_device_fittings": "device_fittings",
    "get_device_load": "device_load",
    "get_ota_batch": "ota_batch",
    "get_ota_update": "ota_update",
    "get_ota_info": "ota_info",
    "get_upgrade_record": "upgrade_record",
    "check_upgrade_record": "check_upgrade_record",
    "get_shared_device": "shared_device",
    "get_device_attributes": "device_attrs",
    "get_message_unread": "message_unread",
    "get_currency_list": "currency_list",
    "get_co2_ranking": "co2_ranking",
    "get_forecast_schedule": "forecast_schedule",
    "get_dynamic_price_sites": "dynamic_price_sites",
    "get_dynamic_price_providers": "dynamic_price_providers",
    "get_dynamic_price_details": "dynamic_price_details",
    "get_device_income": "device_income",
    "get_ai_ems_status": "ai_ems_status",
    "get_ai_ems_profit": "ai_ems_profit",
    "get_tamper_records": "tamper_records",
    "get_device_rfid_cards": "rfid_cards",
    "get_device_group": "device_group",
    "get_device_charge_order_stats": "charge_order_stats",
    "get_device_charge_order_stats_list": "charge_order_stats_list",
    "get_ocpp_endpoint_list": "ocpp_endpoint_list",
    "get_device_ocpp_info": "ocpp_info",
    "get_vehicle_brands": "vehicle_brands",
    "get_vehicle_brand_models": "vehicle_brand_models",
    "get_vehicle_model_years": "vehicle_model_years",
    "get_vehicle_year_attributes": "vehicle_year_attributes",
    "get_user_vehicles": "user_vehicles",
    "get_user_vehicle_details": "user_vehicle_details",
    "api_account": "api_account",
    "api_sites": "api_sites",
    "api_devices": "api_devices",
    # charging_pv_svc endpoint file prefixes
    "get_device_pv_status": "device_pv_status",
    "get_device_pv_total_statistics": "device_pv_total_statistics",
    "get_device_pv_statistics": "device_pv_statistics",
    "get_device_pv_price": "device_pv_price",
    # power charger endpoint file prefixes
    "charger_get_charging_modes": "charger_charging_modes",
    "charger_get_triggers": "charger_triggers",
    "charger_get_statistics": "charger_statistics",
    "charger_get_device_setting": "charger_device_setting",
    "charger_get_screensavers": "charger_screensavers",
    # charging_energy_service endpoint file prefixes
    "charging_get_error_info": "charging_error_info",
    "charging_get_system_running_info": "charging_system_running_info",
    "charging_energy_solar": "charging_energy_solar",
    "charging_energy_hes": "charging_energy_hes",
    "charging_energy_pps": "charging_energy_pps",
    "charging_energy_home": "charging_energy_home",
    "charging_energy_grid": "charging_energy_grid",
    "charging_energy_diesel": "charging_energy_diesel",
    "charging_energy_solar_today": "charging_energy_solar_today",
    "charging_energy_hes_today": "charging_energy_hes_today",
    "charging_energy_pps_today": "charging_energy_pps_today",
    "charging_energy_home_today": "charging_energy_home_today",
    "charging_energy_grid_today": "charging_energy_grid_today",
    "charging_energy_diesel_today": "charging_energy_diesel_today",
    "charging_get_rom_versions": "charging_rom_versions",
    "charging_get_device_info": "charging_device_info",
    "charging_get_wifi_info": "charging_wifi_info",
    "charging_get_installation_inspection": "charging_installation_inspection",
    "charging_get_utility_rate_plan": "charging_utility_rate_plan",
    "charging_report_device_data": "charging_report_device_data",
    "charging_get_configs": "charging_configs",
    "charging_get_sns": "charging_sns",
    "charging_get_monetary_units": "charging_monetary_units",
    # charging_energy_service endpoint file prefixes
    "hes_get_product_info": "hes_product_info",
    "hes_get_heat_pump_plan": "hes_heat_pump_plan",
    "hes_get_electric_plan_list": "hes_electric_plan",
    "hes_get_system_running_info": "hes_system_running_info",
    "hes_energy_solar": "hes_energy_solar",
    "hes_energy_hes": "hes_energy_hes",
    "hes_energy_pps": "hes_energy_pps",
    "hes_energy_home": "hes_energy_home",
    "hes_energy_grid": "hes_energy_grid",
    "hes_energy_solar_today": "hes_energy_solar_today",
    "hes_energy_hes_today": "hes_energy_hes_today",
    "hes_energy_pps_today": "hes_energy_pps_today",
    "hes_energy_home_today": "hes_energy_home_today",
    "hes_energy_grid_today": "hes_energy_grid_today",
    "hes_get_monetary_units": "hes_monetary_units",
    "hes_get_install_info": "hes_install_info",
    "hes_get_wifi_info": "hes_wifi_info",
    "hes_get_installer_info": "hes_installer_info",
    "hes_get_system_profit": "hes_system_profit",
    "hes_get_system_running_time": "hes_system_running_time",
    "hes_get_mi_layout": "hes_mi_layout",
    "hes_get_conn_net_tips": "hes_conn_net_tips",
    "hes_get_hes_dev_info": "hes_dev_info",
    "hes_report_device_data": "hes_report_device_data",
    "hes_get_evcharger_standalone": "hes_evcharger_standalone",
    "hes_get_evcharger_station_info": "hes_evcharger_station_info",
}


LOGIN_RESPONSE: dict = {
    "user_id": str,
    "email": str,
    "nick_name": str,
    "auth_token": str,
    "token_expires_at": int,
    "avatar": str,
    "mac_addr": str,
    "domain": str,
    "ab_code": str,
    "token_id": int,
    "geo_key": str,
    "privilege": int,
    "phone_code": str,
    "phone": str,
    "phone_number": str,
    "phone_code_2fa": str,
    "phone_2fa": str,
    "server_secret_info": {"public_key": str},
    "params": list,
    "trust_list": list,
    "fa_info": {"step": int, "info": str},
    "country_code": str,
    "ap_cloud_user_id": str,
}


class SolixDeviceType(Enum):
    """Enumeration for Anker Solix device types."""

    ACCOUNT = "account"
    SYSTEM = "system"
    VIRTUAL = "virtual"
    SOLARBANK = "solarbank"
    INVERTER = "inverter"
    SMARTMETER = "smartmeter"
    SMARTPLUG = "smartplug"
    PPS = "pps"
    POWERPANEL = "powerpanel"
    POWERCOOLER = "powercooler"
    HES = "hes"
    SOLARBANK_PPS = "solarbank_pps"
    CHARGER = "charger"
    EV_CHARGER = "ev_charger"
    VEHICLE = "vehicle"


class SolixParmType(Enum):
    """Enumeration for Anker Solix Parameter types."""

    SOLARBANK_SCHEDULE = "4"
    SOLARBANK_2_SCHEDULE = "6"
    SOLARBANK_SCHEDULE_ENFORCED = "9"  # No longer supported by cloud as of July 2025
    SOLARBANK_TARIFF_SCHEDULE = "12"
    SOLARBANK_AUTHORIZATIONS = "13"
    SOLARBANK_POWERDOCK = "16"


class SolarbankPowerMode(IntEnum):
    """Enumeration for Anker Solix Solarbank 1 Power setting modes."""

    unknown = 0
    normal = 1
    advanced = 2


class SolarbankDischargePriorityMode(IntEnum):
    """Enumeration for Anker Solix Solarbank 1 Discharge priority setting modes."""

    unknown = -1
    off = 0
    on = 1


class SolarbankAiemsStatus(IntEnum):
    """Enumeration for Anker Solix Solarbank Anker Intelligence status."""

    unknown = 0
    untrained = 3
    learning = 4
    trained = 5


class SolarbankAiemsRuntimeStatus(IntEnum):
    """Enumeration for Anker Solix Solarbank Anker Intelligence runtime status.

    Following combinations of ai_ems status abd ai_ems runtime information were seen:
    - left_time > 0 with runtime status 0 => learning phase status 4 without runtime failure
    - left_time < 0 with runtime status 1 => trained and continues collecting data
    - left_time < 0 with runtime status 2 => untrained, most likely failure during learning or learning stopped
    """

    unknown = -1
    inactive = 0
    running = 1
    failure = 2


class SolixTariffTypes(IntEnum):
    """Enumeration for Anker Solix Solarbank 2 AC / 3 Use Time Tariff Types."""

    UNKNOWN = 0  # Pseudo type to reflect no known tariff defined
    PEAK = 1  # maximize PV and Battery usage, no AC charge
    MID_PEAK = 2  # maximize PV and Battery usage, no AC charge
    OFF_PEAK = 3  # maximize PV and Battery usage, no AC charge, discharge only above 80% SOC, Reserve charge utilized only for PEAK & MID PEAK times
    VALLEY = (
        4  # AC charge allowed, charge power depends on SOC and available VALLEY time
    )


class SolixPriceTypes(StrEnum):
    """Enumeration for Anker Solix Solarbank 2 AC / 3 Use Time Tariff Types."""

    UNKNOWN = "unknown"
    FIXED = "fixed"
    USE_TIME = "use_time"
    DYNAMIC = "dynamic"


class SolixDayTypes(StrEnum):
    """Enumeration for Anker Solix Solarbank 2 AC / 3 Use Time Day Types."""

    WEEKDAY = "weekday"
    WEEKEND = "weekend"
    ALL = "all"


class SolarbankUsageMode(IntEnum):
    """Enumeration for Anker Solix Solarbank 2/3 Power Usage modes."""

    unknown = 0  # AC output based on measured smart meter power
    smartmeter = 1  # AC output based on measured smart meter power
    smartplugs = 2  # AC output based on measured smart plug power
    manual = 3  # manual time plan for home load output
    backup = 4  # This is used to reflect active backup mode in scene_info, but this mode cannot be set directly in schedule and mode is just temporary
    use_time = 5  # Use Time plan with AC types and smart meter
    # smart_learning = 6  # TODO(SB3): To be confirmed
    smart = 7  # Smart mode for AI based charging and discharging
    time_slot = 8  # Time slot mode for dynamic tariffs


@dataclass(frozen=True)
class SolarbankRatePlan:
    """Dataclass for Anker Solix Solarbank 2/3 rate plan types per usage mode."""

    # rate plan per usage mode
    unknown: str = ""
    smartmeter: str = ""  # does not use a plan
    smartplugs: str = "blend_plan"
    manual: str = "custom_rate_plan"
    backup: str = "manual_backup"
    use_time: str = "use_time"
    # smart_learning: str = "" # TODO(SB3): To be confirmed if this is a valid mode and plan
    smart: str = ""  # does not use a plan "ai_ems"
    time_slot: str = "time_slot"


@dataclass(frozen=True)
class ApiEndpointServices:
    """Dataclass to specify supported Api endpoint services. Each service type should be implemented with dedicated Api class."""

    # Note: The service endpoints may not be supported on every cloud server. It may depend on supported Anker products per geo
    power: str = "power_service"
    charging: str = "charging_energy_service"
    hes_svc: str = "charging_hes_svc"


@dataclass(frozen=True)
class ApiCategories:
    """Dataclass to specify supported Api categories for regular Api cache refresh cycles."""

    site_price: str = "site_price"
    device_auto_upgrade: str = "device_auto_upgrade"
    device_tag: str = "device_tag"
    solar_energy: str = "solar_energy"
    solarbank_energy: str = "solarbank_energy"
    solarbank_fittings: str = "solarbank_fittings"
    solarbank_cutoff: str = "solarbank_cutoff"
    solarbank_solar_info: str = "solarbank_solar_info"
    smartmeter_energy: str = "smartmeter_energy"
    smartplug_energy: str = "smartplug_energy"
    powerpanel_energy: str = "powerpanel_energy"
    powerpanel_avg_power: str = "powerpanel_avg_power"
    hes_energy: str = "hes_energy"
    hes_avg_power: str = "hes_avg_power"


@dataclass(frozen=True)
class SolixDeviceNames:
    """Dataclass for Anker Solix device names that are now provided via the various product list queries."""

    SHEM3: str = "Shelly 3EM"
    SHEMP3: str = "Shelly Pro 3EM"
    SHPPS: str = "Shelly Plus Plug S"


@dataclass(frozen=True)
class SolixDeviceCapacity:
    """Dataclass for Anker Solix device battery capacities in Wh by Part Number."""

    A17C0: int = 1600  # SOLIX Solarbank E1600
    A17C1: int = 1600  # SOLIX Solarbank 2 E1600 Pro
    A17C2: int = 1600  # SOLIX Solarbank 2 E1600 AC
    A17C3: int = 1600  # SOLIX Solarbank 2 E1600 Plus
    A17C5: int = 2688  # SOLIX Solarbank 3 E2700 Pro
    A1720: int = 256  # Anker PowerHouse 521 Portable Power Station
    A1722: int = 288  # SOLIX C300 Portable Power Station
    A1723: int = 230  # SOLIX C200 Portable Power Station
    A1725: int = 230  # SOLIX C200 Portable Power Station
    A1726: int = 288  # SOLIX C300 DC Portable Power Station
    A1727: int = 230  # SOLIX C200 DC Portable Power Station
    A1728: int = 288  # SOLIX C300 X Portable Power Station
    A1751: int = 512  # Anker PowerHouse 535 Portable Power Station
    A1753: int = 768  # SOLIX C800 Portable Power Station
    A1754: int = 768  # SOLIX C800 Plus Portable Power Station
    A1755: int = 768  # SOLIX C800X Portable Power Station
    A1760: int = 1024  # Anker PowerHouse 555 Portable Power Station
    A1761: int = 1056  # SOLIX C1000(X) Portable Power Station
    A1762: int = 1056  # SOLIX Portable Power Station 1000
    # A17C1: int = 1056  # SOLIX C1000 Expansion Battery # same PN as Solarbank 2?
    A1770: int = 1229  # Anker PowerHouse 757 Portable Power Station
    A1771: int = 1229  # SOLIX F1200 Portable Power Station
    A1772: int = 1536  # SOLIX F1500 Portable Power Station
    A1780: int = 2048  # SOLIX F2000 Portable Power Station (PowerHouse 767)
    A1780_1: int = 2048  # Expansion Battery for F2000
    A1780P: int = 2048  # SOLIX F2000 Portable Power Station (PowerHouse 767) with WIFI
    A1781: int = 2560  # SOLIX F2600 Portable Power Station
    A1782: int = 3072  # SOLIX F3000 Portable Power Station with Smart Meter support
    A1790: int = 3840  # SOLIX F3800 Portable Power Station
    A1790_1: int = 3840  # SOLIX BP3800 Expansion Battery for F3800
    A1790P: int = 3840  # SOLIX F3800 Portable Power Station
    A5220: int = 5000  # SOLIX X1 Battery module


@dataclass(frozen=True)
class SolixSiteType:
    """Dataclass for Anker Solix System/Site types according to the main device in site rules."""

    t_0 = SolixDeviceType.VIRTUAL.value  # Virtual site, only standalone inverter A5143
    t_1 = SolixDeviceType.PPS.value  # Main A5143 + FS1200
    t_2 = SolixDeviceType.SOLARBANK.value  # Main A17C0 SB1
    t_3 = SolixDeviceType.HES.value  # Main A5103, Note: This is not listed in actual site rules, but X1 export showing type 3 instead of 9 as site rules say
    t_4 = SolixDeviceType.POWERPANEL.value  # Main A17B1
    t_5 = SolixDeviceType.SOLARBANK.value  # Main A17C1 SB2 Pro, can also add SB1
    t_6 = SolixDeviceType.HES.value  # Main A5341 HES Backup Controller
    t_7 = SolixDeviceType.HES.value  # Main A5101 HES
    t_8 = SolixDeviceType.HES.value  # Main A5102 HES
    t_9 = SolixDeviceType.HES.value  # Main A5103 HES
    t_10 = SolixDeviceType.SOLARBANK.value  # Main A17C3 SB2 Plus, can also add SB1
    t_11 = SolixDeviceType.SOLARBANK.value  # Main A17C2 SB2 AC
    t_12 = SolixDeviceType.SOLARBANK.value  # Main A17C5 SB3 Pro
    t_13 = SolixDeviceType.SOLARBANK_PPS.value  # Main A1782 SOLIX F3000 Portable Power Station (Solarbank PPS) with Smart Meter support for US market
    t_14 = SolixDeviceType.EV_CHARGER.value  # Main A5191 Smart EV Charger


@dataclass(frozen=True)
class SolixDeviceCategory:
    """Dataclass for Anker Solix device types by Part Number to be used for standalone/unbound device categorization."""

    # Solarbanks
    A17C0: str = (
        SolixDeviceType.SOLARBANK.value + "_1"
    )  # SOLIX Solarbank E1600, generation 1
    A17C1: str = (
        SolixDeviceType.SOLARBANK.value + "_2"
    )  # SOLIX Solarbank 2 E1600 Pro, generation 2
    A17C2: str = (
        SolixDeviceType.SOLARBANK.value + "_2"
    )  # SOLIX Solarbank 2 E1600 AC, generation 2
    A17C3: str = (
        SolixDeviceType.SOLARBANK.value + "_2"
    )  # SOLIX Solarbank 2 E1600 Plus, generation 2
    A17C5: str = (
        SolixDeviceType.SOLARBANK.value + "_3"
    )  # SOLIX Solarbank 3 E2700 Pro, generation 3
    # Inverter
    A5140: str = SolixDeviceType.INVERTER.value  # MI60 Inverter
    A5143: str = SolixDeviceType.INVERTER.value  # MI80 Inverter
    # Smart Meter
    A17X7: str = SolixDeviceType.SMARTMETER.value  # SOLIX Smart Meter
    A17X7US: str = SolixDeviceType.SMARTMETER.value  # SOLIX Smart Meter for US
    AE1R0: str = SolixDeviceType.SMARTMETER.value  # SOLIX P1 Meter
    SHEM3: str = SolixDeviceType.SMARTMETER.value  # Shelly 3EM Smart Meter
    SHEMP3: str = SolixDeviceType.SMARTMETER.value  # Shelly 3EM Pro Smart Meter
    # Smart Plug
    A17X8: str = SolixDeviceType.SMARTPLUG.value  # SOLIX Smart Plug
    SHPPS: str = SolixDeviceType.SMARTPLUG.value  # Shelly Smart Plug
    # Portable Power Stations (PPS)
    A1720: str = (
        SolixDeviceType.PPS.value
    )  # Anker PowerHouse 521 Portable Power Station
    A1722: str = SolixDeviceType.PPS.value  # SOLIX C300 Portable Power Station
    A1723: str = SolixDeviceType.PPS.value  # SOLIX C200 Portable Power Station
    A1725: str = SolixDeviceType.PPS.value  # SOLIX C200 Portable Power Station
    A1726: str = SolixDeviceType.PPS.value  # SOLIX C300 DC Portable Power Station
    A1727: str = SolixDeviceType.PPS.value  # SOLIX C200 DC Portable Power Station
    A1728: str = SolixDeviceType.PPS.value  # SOLIX C300X Portable Power Station
    A1751: str = (
        SolixDeviceType.PPS.value
    )  # Anker PowerHouse 535 Portable Power Station
    A1753: str = SolixDeviceType.PPS.value  # SOLIX C800 Portable Power Station
    A1754: str = SolixDeviceType.PPS.value  # SOLIX C800 Plus Portable Power Station
    A1755: str = SolixDeviceType.PPS.value  # SOLIX C800X Portable Power Station
    A1760: str = (
        SolixDeviceType.PPS.value
    )  # Anker PowerHouse 555 Portable Power Station
    A1761: str = SolixDeviceType.PPS.value  # SOLIX C1000(X) Portable Power Station
    A1762: str = SolixDeviceType.PPS.value  # SOLIX Portable Power Station 1000
    A1770: str = (
        SolixDeviceType.PPS.value
    )  # Anker PowerHouse 757 Portable Power Station
    A1771: str = SolixDeviceType.PPS.value  # SOLIX F1200 Portable Power Station
    A1772: str = SolixDeviceType.PPS.value  # SOLIX F1500 Portable Power Station
    A1780: str = (
        SolixDeviceType.PPS.value
    )  # SOLIX F2000 Portable Power Station (PowerHouse 767)
    A1781: str = SolixDeviceType.PPS.value  # SOLIX F2600 Portable Power Station
    A1782: str = (
        SolixDeviceType.SOLARBANK_PPS.value
    )  # SOLIX F3000 Portable Power Station with SM support (US Market)
    A1790: str = SolixDeviceType.PPS.value  # SOLIX F3800 Portable Power Station
    A1790P: str = SolixDeviceType.PPS.value  # SOLIX F3800 Plus Portable Power Station
    # Home Power Panels
    A17B1: str = (
        SolixDeviceType.POWERPANEL.value
    )  # SOLIX Home Power Panel for SOLIX F3800
    # Home Energy System (HES)
    A5101: str = SolixDeviceType.HES.value  # SOLIX X1 P6K US
    A5102: str = SolixDeviceType.HES.value  # SOLIX X1 Energy module 1P H(3.68~6)K
    A5103: str = SolixDeviceType.HES.value  # SOLIX X1 Energy module 3P H(5~12)K
    A5150: str = SolixDeviceType.HES.value  # SOLIX X1 Microinverter
    A5220: str = SolixDeviceType.HES.value  # SOLIX X1 Battery module
    A5341: str = SolixDeviceType.HES.value  # SOLIX X1 Backup Controller
    A5450: str = SolixDeviceType.HES.value  # SOLIX X1 Zigbee Dongle
    # Power Cooler
    A17A0: str = SolixDeviceType.POWERCOOLER.value  # SOLIX Power Cooler 30
    A17A1: str = SolixDeviceType.POWERCOOLER.value  # SOLIX Power Cooler 40
    A17A2: str = SolixDeviceType.POWERCOOLER.value  # SOLIX Power Cooler 50
    A17A3: str = SolixDeviceType.POWERCOOLER.value  # SOLIX Everfrost 2 23L
    A17A4: str = SolixDeviceType.POWERCOOLER.value  # SOLIX Everfrost 2 40L
    A17A5: str = SolixDeviceType.POWERCOOLER.value  # SOLIX Everfrost 2 58L
    # Charging Stations
    A2345: str = SolixDeviceType.CHARGER.value  # Anker 250W Prime Charger
    A91B2: str = SolixDeviceType.CHARGER.value  # Anker 240W Charging Station
    # EV Charger
    A5191: str = SolixDeviceType.EV_CHARGER.value  # SOLIX EV Charger


@dataclass(frozen=True)
class SolarbankDeviceMetrics:
    """Dataclass for Anker Solarbank metrics which should be tracked in device details cache depending on model type."""

    # SOLIX Solarbank E1600, single MPPT without channel reporting
    A17C0: ClassVar[set[str]] = set()
    # SOLIX Solarbank 2 E1600 Pro, with 4 MPPT channel reporting and AC socket
    A17C1: ClassVar[set[str]] = {
        "sub_package_num",
        "solar_power_1",
        "solar_power_2",
        "solar_power_3",
        "solar_power_4",
        "ac_power",
        "to_home_load",
        "pei_heating_power",
    }
    # SOLIX Solarbank 2 E1600 AC, witho 2 MPPT channel and AC socket
    A17C2: ClassVar[set[str]] = {
        "sub_package_num",
        "bat_charge_power",
        "solar_power_1",
        "solar_power_2",
        "ac_power",
        "to_home_load",
        "pei_heating_power",
        "micro_inverter_power",  # This is external inverter input, counts to Solar power
        "micro_inverter_power_limit",
        "micro_inverter_low_power_limit",
        "grid_to_battery_power",
        "other_input_power",  # This is AC input for charging typically
    }
    # SOLIX Solarbank 2 E1600 Plus, with 2 MPPT
    A17C3: ClassVar[set[str]] = {
        "sub_package_num",
        "solar_power_1",
        "solar_power_2",
        "to_home_load",
        "pei_heating_power",
    }
    # SOLIX Solarbank 3 E2700, with 4 MPPT channel and AC socket
    A17C5: ClassVar[set[str]] = {
        "sub_package_num",
        "bat_charge_power",
        "solar_power_1",
        "solar_power_2",
        "solar_power_3",
        "solar_power_4",
        "ac_power",
        "to_home_load",
        "pei_heating_power",
        # "micro_inverter_power",  # external inverter input not supported by SB3
        # "micro_inverter_power_limit",  # external inverter input not supported by SB3
        # "micro_inverter_low_power_limit",  # external inverter input not supported by SB3
        "grid_to_battery_power",
        "other_input_power",  # This is AC input for charging typically
    }
    # Inverter Output Settings
    INVERTER_OUTPUT_OPTIONS: ClassVar[dict[str, Any]] = {
        "A5143": ["600", "800"],
        "A17C1": ["350", "600", "800", "1000"],
        "A17C2": ["350", "600", "800", "1000"],
        "A17C3": ["350", "600", "800", "1000"],
        "A17C5": ["350", "600", "800", "1200"],
    }
    MPPT_INPUT_OPTIONS: ClassVar[dict[str, Any]] = {
        "A17C5": ["2000", "3600"],
    }


@dataclass(frozen=True)
class SolixDefaults:
    """Dataclass for Anker Solix defaults to be used."""

    # Output Power presets for Solarbank schedule timeslot settings
    PRESET_MIN: int = 100
    PRESET_MAX: int = 800
    PRESET_DEF: int = 100
    PRESET_NOSCHEDULE: int = 200
    PRESET_MAX_MULTISYSTEM: int = 3600
    # Export Switch preset for Solarbank schedule timeslot settings
    ALLOW_EXPORT: bool = True
    # Preset power mode for Solarbank schedule timeslot settings
    POWER_MODE: int = SolarbankPowerMode.normal.value
    # Preset usage mode for Solarbank 2 schedules
    USAGE_MODE: int = SolarbankUsageMode.manual.value
    # Charge Priority limit preset for Solarbank schedule timeslot settings
    CHARGE_PRIORITY_MIN: int = 0
    CHARGE_PRIORITY_MAX: int = 100
    CHARGE_PRIORITY_DEF: int = 80
    # Discharge Priority preset for Solarbank schedule timeslot settings
    DISCHARGE_PRIORITY_DEF: int = SolarbankDischargePriorityMode.off.value
    # AC tariff settings for Use Time plan
    TARIFF_DEF: int = SolixTariffTypes.OFF_PEAK.value
    TARIFF_PRICE_DEF: str = "0.00"
    TARIFF_WE_SAME: bool = True
    CURRENCY_DEF: str = "€"
    # Seconds delay for subsequent Api requests in methods to update the Api cache dictionaries
    REQUEST_DELAY_MIN: float = 0.0
    REQUEST_DELAY_MAX: float = 10.0
    REQUEST_DELAY_DEF: float = 0.3
    # Request limit per endpoint per minute
    ENDPOINT_LIMIT_DEF: int = 10
    # Inverter limit
    MICRO_INVERTER_LIMIT_MIN: int = 0
    MICRO_INVERTER_LIMIT_MAX: int = 800
    # Dynamic tariff defaults
    DYNAMIC_TARIFF_PRICE_FEE: ClassVar[dict[str, float]] = {
        "UK": 0.1131,
        "SE": 0.0643,
        "AT": 0.11332,
        "BE": 0.01316,
        "FR": 0.1329,
        "DE": 0.17895,
        "PL": 0.0786,
        "DEFAULT": 0,
    }
    DYNAMIC_TARIFF_SELL_FEE: ClassVar[dict[str, float]] = {
        "UK": 0.03,
        "SE": 0.2,
        "AT": 0.0973,
        "BE": 0.01305,
        "FR": 0.127,
        "DE": 0.0794,
        "PL": 0,
        "DEFAULT": 0,
    }
    DYNAMIC_TARIFF_PRICE_VAT: ClassVar[dict[str, float]] = {
        "UK": 5,
        "SE": 25,
        "AT": 20,
        "BE": 21,
        "FR": 20,
        "DE": 19,
        "PL": 23,
        "DEFAULT": 0,
    }


class SolixDeviceStatus(StrEnum):
    """Enumeration for Anker Solix Device status."""

    # The device status code seems to be used for cloud connection status.
    offline = "0"
    online = "1"
    unknown = "unknown"


class SolarbankStatus(StrEnum):
    """Enumeration for Anker Solix Solarbank status."""

    detection = "0"  # Rare for SB1, frequent for SB2 especially in combination with Smartmeter in the morning
    protection_charge = "03"  # For SB2 only when there is charge while output below demand in detection mode
    bypass = "1"  # Bypass solar without charge
    bypass_discharge = (
        "12"  # pseudo state for SB2 if discharging in bypass mode, not possible for SB1
    )
    discharge = "2"  # only seen if no solar available
    charge = "3"  # normal charge for battery
    charge_bypass = "31"  # pseudo state, the solarbank does not distinguish this
    charge_ac = "32"  # pseudo state, the solarbank does not distinguish this
    charge_priority = "37"  # pseudo state, the solarbank does not distinguish this, when no output power exists while preset is ignored
    wakeup = "4"  # Not clear what happens during this state, but observed short intervals during night, probably hourly? resync with the cloud
    cold_wakeup = "116"  # At cold temperatures, 116 was observed instead of 4. Not sure why this state is different at low temps?
    fully_charged = "5"  # Seen for SB2 when SOC is 100%
    full_bypass = "6"  # seen at cold temperature, when battery must not be charged and the Solarbank bypasses all directly to inverter, also solar power < 25 W. More often with SB2
    standby = "7"
    unknown = "unknown"
    # TODO(SB3): Is there a new mode for AC charging? Can it be distinguished from existing values?


class SmartmeterStatus(StrEnum):
    """Enumeration for Anker Solix Smartmeter status."""

    # TODO(#106) Update Smartmeter grid status description once known
    ok = "0"  # normal grid state when smart meter is measuring
    unknown = "unknown"


class SolixGridStatus(StrEnum):
    """Enumeration for Anker Solix grid status."""

    # TODO(X1) Update grid status description once known
    ok = "0"  # normal grid state when hes pcu grid status is ok
    unknown = "unknown"


class SolixRoleStatus(StrEnum):
    """Enumeration for Anker Solix role status of devices."""

    # The device role status codes as used for HES devices
    # TODO(X1): The proper description of those codes has to be confirmed
    primary = "1"  # Master role in Api
    subordinate = "2"  # Slave role in Api, to be confirmed!!!
    unknown = "unknown"


class SolixNetworkStatus(StrEnum):
    """Enumeration for Anker Solix HES network status."""

    # TODO(X1): The proper description of those codes has to be confirmed
    wifi = "1"  # to be confirmed
    lan = "2"  # this was seen on LAN connected systems
    mobile = "3"  # HES systems support also 5G connections, code to be confirmed
    unknown = "unknown"


@dataclass
class SolarbankTimeslot:
    """Dataclass to define customizable attributes of an Anker Solix Solarbank time slot as used for the schedule definition or update."""

    start_time: datetime
    end_time: datetime
    appliance_load: int | None = (
        None  # mapped to appliance_loads setting using a default 50% share for dual solarbank setups
    )
    device_load: int | None = (
        None  # mapped to device load setting of provided solarbank serial
    )
    allow_export: bool | None = None  # mapped to the turn_on boolean
    charge_priority_limit: int | None = None  # mapped to charge_priority setting
    discharge_priority: int | None = None  # mapped to discharge priority setting


@dataclass
class Solarbank2Timeslot:
    """Dataclass to define customizable attributes of an Anker Solix Solarbank 2/3 time slot as used for the schedule definition, update or deletion."""

    start_time: datetime | None
    end_time: datetime | None
    appliance_load: int | None = None  # mapped to appliance_load setting
    weekdays: set[int | str] | None = (
        None  # set of weekday numbers or abbreviations where this slot applies, defaulting to all if None. sun = 0, sat = 6
    )


@dataclass(order=True, kw_only=True)
class SolixPriceProvider:
    """Dataclass to define dynamic price provider attributes and representation of them."""

    country: str | None = None
    company: str | None = None
    area: str | None = None
    provider: InitVar[dict | str | None] = None

    def __post_init__(self, provider) -> None:
        """Init the dataclass from an optional provider representation or priceinfo dictionary."""
        if isinstance(provider, dict):
            self.country = provider.get("country")
            self.company = provider.get("company")
            self.area = provider.get("area")
        elif isinstance(provider, str) and (keys := provider.split("/")):
            self.country = s if (s := (keys[0:1] or [None])[0]) != "-" else None
            self.company = s if (s := (keys[1:2] or [None])[0]) != "-" else None
            self.area = s if (s := (keys[2:3] or [None])[0]) != "-" else None

    def __str__(self) -> str:
        """Print the class fields."""
        return f"{self.country or '-'}/{self.company or '-'}/{self.area or '-'}"

    def asdict(self) -> dict:
        """Return a dictionary representation of the class fields."""
        return asdict(self)


@dataclass(order=True, kw_only=True)
class SolixVehicle:
    """Dataclass to define vehicle attributes and representation of them."""

    brand: str = ""
    model: str = ""
    productive_year: int = 0
    model_id: int | None = None
    battery_capacity: float = 0
    ac_max_charging_power: float = 0
    energy_consumption_per_100km: float = 0
    vehicle: InitVar[dict | str | None] = None

    def __post_init__(self, vehicle) -> None:
        """Post init the dataclass from an optional vehicle representation or dictionary."""
        if isinstance(vehicle, dict):
            self.update(attributes=vehicle)
        elif isinstance(vehicle, str) and (keys := vehicle.split("/")):
            self.update(
                attributes={
                    "brand:": s if (s := (keys[0:1] or [None])[0]) != "-" else "",
                    "model": s if (s := (keys[1:2] or [None])[0]) != "-" else "",
                    "productive_year": (keys[2:3] or [None])[0],
                    "model_id": (keys[3:4] or [None])[0],
                }
            )
        else:
            # General type conversion for parameters as required
            self.brand = str(self.brand) if self.brand else ""
            self.model = str(self.model) if self.model else ""
            self.productive_year = (
                int(self.productive_year) if str(self.productive_year).isdigit() else 0
            )
            self.model_id = int(self.model_id) if str(self.model_id).isdigit() else None
            self.battery_capacity = (
                float(self.battery_capacity)
                if str(self.battery_capacity).replace(".", "", 1).isdigit()
                else 0
            )
            self.ac_max_charging_power = (
                float(self.ac_max_charging_power)
                if str(self.ac_max_charging_power).replace(".", "", 1).isdigit()
                else 0
            )
            self.energy_consumption_per_100km = (
                float(self.energy_consumption_per_100km)
                if str(self.energy_consumption_per_100km).replace(".", "", 1).isdigit()
                else 0
            )

    def __str__(self) -> str:
        """Print the class fields."""
        return f"{(self.brand or '-')!s}/{(self.model or '-')!s}/{(self.productive_year or '-')!s}"

    def idAttributes(self) -> str:
        """Print the model ID with key attribute fields."""
        return f"{('-' if self.model_id is None else self.model_id)!s}/{(self.battery_capacity or '-')!s} kWh/{(self.ac_max_charging_power or '-')!s} kW"

    def update(self, attributes: dict) -> None:
        """Update attributes based on provided dictionary fields."""
        if isinstance(attributes, dict):
            self.brand = (
                str(brand)
                if (brand := attributes.get("brand") or attributes.get("brand_name"))
                else self.brand
            )
            self.model = (
                str(model)
                if (model := attributes.get("model") or attributes.get("model_name"))
                else self.model
            )
            self.productive_year = (
                int(year)
                if str(year := attributes.get("productive_year")).isdigit()
                else self.productive_year
            )
            self.model_id = (
                int(mid)
                if str(
                    mid := attributes.get("id") or attributes.get("model_id")
                ).isdigit()
                else self.model_id
            )
            self.battery_capacity = (
                float(capacity)
                if str(capacity := attributes.get("battery_capacity"))
                .replace(".", "", 1)
                .isdigit()
                else self.battery_capacity
            )
            self.ac_max_charging_power = (
                float(limit)
                if str(
                    limit := attributes.get("ac_max_charging_power")
                    or attributes.get("ac_max_power")
                )
                .replace(".", "", 1)
                .isdigit()
                else self.ac_max_charging_power
            )
            self.energy_consumption_per_100km = (
                float(consumption)
                if str(
                    consumption := attributes.get("energy_consumption_per_100km")
                    or attributes.get("hundred_fuel_consumption")
                )
                .replace(".", "", 1)
                .isdigit()
                else self.energy_consumption_per_100km
            )

    def asdict(self, skip_empty: bool = False) -> dict:
        """Return a dictionary representation of the class fields."""
        d = asdict(self)
        if skip_empty:
            keys = d.keys()
            for key in [key for key in keys if not d[key] or key in ["id"]]:
                d.pop(key, None)
        return d


class Color(StrEnum):
    """Define ASCII colors."""

    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    CYAN = "\033[36m"
    MAG = "\033[35m"
    WHITE = "\033[37m"
    OFF = "\033[0m"


class DeviceHexDataTypes(Enum):
    """Enumeration for Anker Solix HEX data value types."""

    str = bytes.fromhex("00")  # x bytes,  string
    ui = bytes.fromhex("01")  # 1 byte, unsigned int
    sile = bytes.fromhex("02")  # 2 bytes, signed int LE
    var = bytes.fromhex(
        "03"
    )  # 4 bytes, various, could be 4 * int, 2 * signed int LE or float LE?
    bin = bytes.fromhex("04")  # multiple bytes, mostly 00 or 01, setting pattern
    sfle = bytes.fromhex("05")  # 4 bytes, signed float LE
    unk = bytes.fromhex("FF")  # unkonwn


@dataclass(order=True, kw_only=True)
class DeviceHexDataHeader:
    """Dataclass to structure Solix device hex data headers as received from MQTT or BT transmissions.

        Message header structure 9-10 Bytes:
        FF 09    | 2 Bytes fixed message prefix for Anker Solix message
        XX XX    | 2 Bytes message length (including prefix), little endian format
        XX XX XX | 3 Bytes pattern that seem identical across all messages (supposed `03 00/01 0f` for send/receive)
        XX XX    | 2 Bytes pattern for type of message, e.g. `84 05` on telemetry packets and `04 09` for others, depends on device model, to be figured out
        XX       | 1 optional Byte, seems increment for certain messages, fix for others or not used
    "ff09 3b00 03010f 0407 a10132a21100415a5636593630443330323030373036a3110031756e64312d486f6d65536572766572a4020140a502010128"
    """

    prefix: bytearray = b""
    msglength: int = 0
    pattern: bytearray = b""
    msgtype: bytearray = b""
    increment: bytearray = b""
    hexbytes: InitVar[bytearray | bytes | str | None] = None
    cmd_msg: InitVar[bytearray | bytes | str | None] = None

    def __post_init__(self, hexbytes, cmd_msg) -> None:
        """Init the dataclass from optional hexbytes or for new cmf_msg."""
        self.msglength = 0
        if isinstance(hexbytes, str):
            hexbytes = bytearray(bytes.fromhex(hexbytes))
        elif isinstance(hexbytes, bytes):
            hexbytes = bytearray(hexbytes)
        if isinstance(cmd_msg, str):
            cmd_msg = bytearray(bytes.fromhex(cmd_msg))
        elif isinstance(cmd_msg, bytes):
            cmd_msg = bytearray(cmd_msg)
        if isinstance(hexbytes, bytearray):
            if len(hexbytes) >= 9:
                self.prefix = hexbytes[0:2]
                self.msglength = int.from_bytes(hexbytes[2:4], byteorder="little")
                self.pattern = hexbytes[4:7]
                self.msgtype = hexbytes[7:9]
            if len(hexbytes) >= 10 and hexbytes[9:10] != bytearray.fromhex("a1"):
                self.increment = hexbytes[9:10]
            else:
                self.increment = b""
        elif isinstance(cmd_msg, bytearray):
            # Initialize for publish command with given message pattern
            self.prefix = bytearray(bytes.fromhex("ff09"))
            self.pattern = bytearray(bytes.fromhex("03000f"))
            self.msgtype = cmd_msg[0:2]
            self.increment = cmd_msg[2:3]
            self.msglength = len(self) + 2

    def __len__(self) -> int:
        """Return Bytes used for header."""
        return (
            len(self.prefix)
            + len(self.pattern)
            + len(self.msgtype)
            + len(self.increment)
            + 2 * (self.msglength > 0)
        )

    def __str__(self) -> str:
        """Print the class fields."""
        return f"prefix:{self.prefix.hex()}, msglength:{self.msglength!s}, pattern:{self.pattern.hex()}, msgtype:{self.msgtype.hex()}, increment:{self.increment.hex()}"

    def hex(self, sep: str = "") -> str:
        """Get the header as hex string."""
        b = (
            self.prefix
            + self.msglength.to_bytes(2, byteorder="little")
            + self.pattern
            + self.msgtype
            + self.increment
        )
        if sep:
            return f"{b.hex(sep=sep)}"
        return f"{b.hex()}"

    def decode(self) -> str:
        """Print the header fields representation in human readable format."""
        if len(self) > 0:
            s = f"{self.prefix.hex(' '):<8}: 2 Byte Anker Solix message marker (supposed 'ff 09')"
            s += f"\n{int.to_bytes(self.msglength, length=2, byteorder='little').hex(' '):<8}: 2 Byte total message length ({self.msglength}) in Bytes (Little Endian format)"
            s += f"\n{self.pattern.hex(' '):<8}: 3 Byte fixed message pattern (supposed `03 00/01 0f` for send/receive)"
            s += f"\n{(Color.GREEN + self.msgtype.hex(' ') + '   ' + Color.OFF)!s:<8}: 2 Byte message type pattern (varies per device model and message type)"
            s += f"\n{self.increment.hex(' '):<8}: 1 Byte optional message increment ({int.from_bytes(self.increment):>3})"
        else:
            s = ""
        return s

    def asdict(self) -> dict:
        """Return a dictionary representation of the class fields."""
        return asdict(self)


@dataclass(order=True, kw_only=True)
class DeviceHexDataField:
    """Dataclass to structure Solix device hex data field as received from MQTT or BT transmissions.

    Common data field structure:
    XX     | data field type/name (A1, A2, A3 ...). Meaning can be different per device model
    XX     | data length (bytes following until end of field)
    XX ... | data, where first byte in the data (if the data length is above 2) seems to indicate what value type the data is
    """

    f_name: bytes = b""
    f_length: int = 0
    f_type: bytes = b""
    f_value: bytes = b""
    hexbytes: InitVar[bytearray | bytes | str | None] = None

    def __post_init__(self, hexbytes) -> None:
        """Init the dataclass from an optional hexbytes."""
        if isinstance(hexbytes, str):
            hexbytes = bytearray(bytes.fromhex(hexbytes))
        elif isinstance(hexbytes, bytes):
            hexbytes = bytearray(hexbytes)
        if isinstance(hexbytes, bytearray) and len(hexbytes) >= 2:
            self.f_name = hexbytes[0:1]
            self.f_length = int.from_bytes(hexbytes[1:2])
            if 0 < self.f_length <= len(hexbytes) - 2:
                if self.f_length > 1:
                    # field with format
                    self.f_type = hexbytes[2:3]
                    self.f_value = hexbytes[3 : 2 + self.f_length]
                else:
                    # field with single value byte
                    self.f_type = b""
                    self.f_value = hexbytes[2:3]
            else:
                self.f_type = b""
                self.f_value = b""
        else:
            # ensure to update data length if initialized without hexbytes
            self.f_length = len(self.f_type) + len(self.f_value)

    def __len__(self) -> int:
        """Return Bytes used for field."""
        return (
            len(self.f_name)
            + len(self.f_type)
            + len(self.f_value)
            + 1 * (self.f_length > 0)
        )

    def __str__(self) -> str:
        """Print the class fields."""
        return f"f_name:{self.f_name.hex()}, f_length:{self.f_length!s}, f_type:{self.f_type.hex()}, f_value:{self.f_value.hex(':')}"

    def hex(self, sep: str = "") -> str:
        """Get the field as hex string."""
        b = self.f_name + self.f_length.to_bytes() + self.f_type + self.f_value
        if sep:
            return f"{b.hex(sep=sep)}"
        return f"{b.hex()}"

    def asdict(self) -> dict:
        """Return a dictionary representation of the class fields."""
        return asdict(self)

    def decode(self) -> str:
        """Print the data field representation in human readable format."""
        if self.f_name:
            typ = (
                DeviceHexDataTypes(self.f_type).name
                if self.f_type in DeviceHexDataTypes
                else DeviceHexDataTypes.unk.name
            )
            tcol = (
                [
                    Color.BLUE,
                    Color.GREEN,
                    Color.CYAN,
                    Color.YELLOW,
                    Color.RED,
                    Color.MAG,
                ][ti]
                if 0 <= (ti := int.from_bytes(self.f_type)) <= 5
                else Color.RED
            )

            if typ not in [DeviceHexDataTypes.str.name, DeviceHexDataTypes.bin.name]:
                # unsigned int little endian
                uile = (
                    ";".join(
                        [
                            str(
                                int.from_bytes(
                                    self.f_value[0:2], byteorder="little", signed=True
                                )
                            ),
                            str(
                                int.from_bytes(
                                    self.f_value[2:4], byteorder="little", signed=True
                                )
                            ),
                        ]
                    )
                    if typ == DeviceHexDataTypes.var.name
                    else int.from_bytes(self.f_value, byteorder="little")
                )
                # unsigned int big endian => Does not seem to be used
                # uibe = int.from_bytes(self.f_value, byteorder="big")
                # signed int little endian
                sile = str(
                    int.from_bytes(self.f_value, byteorder="little", signed=True)
                )
                # signed int big endian => Does not seem to be used
                # sibe = int.from_bytes(self.f_value, byteorder="big", signed=True)
                # convert to float via struct
                # '<f' little-endian 32-bit float (4 Bytes, single)
                fle = (
                    f"{struct.unpack('<f', self.f_value)[0]:>5.2f}"
                    if len(self.f_value) == 4
                    else ""
                )
                # '>f' → big-endian 32-bit float  (4 Bytes, single) => Does not seem to be used
                # fbe = f"{struct.unpack('>f', self.f_value)[0]:>5.2f}" if len(self.f_value) == 4 else  ""
                # '<d' → little-endian 64-bit float (8 Bytes, double)
                dle = (
                    f"{struct.unpack('<d', self.f_value)[0]:>5.2f}"
                    if len(self.f_value) == 8
                    else ";".join(
                        [
                            str(int.from_bytes(self.f_value[i : i + 1]))
                            for i in range(len(self.f_value))
                        ]
                    )
                    if 2 <= len(self.f_value) <= 4
                    else ""
                )
                # '>d' → big-endian 64-bit float (8 Bytes, double) => Does not seem to be used
                # dbe = f"{struct.unpack('>d', self.f_value)[0]:>5.2f}" if len(self.f_value) == 8 else  ""
            else:
                uile = str(bytes(self.f_value))
                # uibe = ""
                sile = ""
                # sibe = ""
                fle = ""
                # fbe = ""
                dle = ""
                # dbe = ""
            s = f"{Color.RED + self.f_name.hex() + Color.OFF + ' '!s:<4} {int.to_bytes(self.f_length).hex():<3} {tcol + (self.f_type.hex() or '--') + Color.OFF!s:<4}  {self.f_value.hex(':')}"
            s += f"\n{'└->':<3} {self.f_length!s:>3} {tcol + typ + Color.OFF!s:<5} {uile:>12} {sile:>12} {fle:>12} {dle:>12}"
        else:
            s = ""
        return s


@dataclass(order=True, kw_only=True)
class DeviceHexData:
    """Dataclass to structure Solix device hex data as received from MQTT or BT transmissions.

    Messages structure:
    FF 09    | fixed message prefix for Anker Solix message
    XX XX    | message length (including prefix)
    XX XX XX | pattern that seem identical across all messages (`03 01 0f`)
    XX XX    | pattern for type of message, e.g. `84 05` on telemetry packets and `04 09` for others, to be figured out
    XX       | seems to increment certain messages, fix for others
    Starting from 11th Byte there is message data with 1 or more fields, where each field can be of variable length.
    Common data field structure:
    XX     | data field type/name (A1, A2, A3 ...). Meaning can be different per device model
    XX     | data length (bytes following until end of field)
    XX ... | data, where first byte in the data (if the data length is above 2) seems to indicate what value type the data is

    """

    hexbytes: bytearray = field(default_factory=bytearray)
    model: str = ""
    length: int = 0
    msg_header: DeviceHexDataHeader = field(default_factory=DeviceHexDataHeader)
    msg_fields: dict[str, DeviceHexDataField] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Post init the dataclass to decode the bytes into fields."""
        idx = 10
        if isinstance(self.hexbytes, str):
            self.hexbytes = bytearray(bytes.fromhex(self.hexbytes.replace(":", "")))
        elif isinstance(self.hexbytes, bytes):
            self.hexbytes = bytearray(self.hexbytes)
        if self.hexbytes:
            self.length = len(self.hexbytes)
            self.msg_header = DeviceHexDataHeader(hexbytes=self.hexbytes[0:idx])
            self.msg_fields = {}
            idx = len(self.msg_header)
            while 9 <= idx < self.length - 1:
                f = DeviceHexDataField(hexbytes=self.hexbytes[idx:])
                if f.f_name:
                    self.msg_fields[f.f_name.hex()] = f
                idx += int(f.f_length) + 2
        else:
            # update length and hexbytes if not initialized via hexbytes
            self._update_hexbytes()

    def __len__(self) -> int:
        """Return Byte count of hex data."""
        return self.length

    def __str__(self) -> str:
        """Print the fields and hex bytes with separator."""
        return f"model:{self.model}, header:{{{self.msg_header!s}}}, hexbytes:{self.hexbytes.hex()}"

    def _update_hexbytes(self) -> None:
        # init length and hexbytes
        self.length = len(self.msg_header)
        self.hexbytes = b""
        for f in (self.msg_fields or {}).values():
            self.length += len(f)
            self.hexbytes += bytes.fromhex(f.hex())
        if self.length:
            # update message length in header
            self.msg_header.msglength = self.length
        # generate hexbytes
        self.hexbytes = bytearray(
            bytes.fromhex(self.msg_header.hex()) + self.hexbytes
        )

    def hex(self, sep: str = "") -> str:
        """Print the hex bytes with optional separator."""
        if sep:
            return self.hexbytes.hex(sep=sep)
        return self.hexbytes.hex()

    def decode(self) -> str:
        """Print the field representation in human readable format."""
        if self.length > 0:
            msgtype = self.msg_header.msgtype.hex()
            pn = (
                f" {str(getattr(SolixDeviceCategory, self.model, 'Unknown Device')).capitalize()} / {Color.CYAN + self.model + Color.OFF} / {Color.GREEN + msgtype + Color.OFF} /"
                if self.model
                else ""
            )
            s = f"{pn + ' Header ':-^80}\n{self.msg_header.decode()}\n{' Fields ':-^12}|{'- Value (Hex/Decode Options)':-<67}"
            if self.msg_fields:
                s += f"\n{'Fld':<3} {'Len':<3} {'Typ':<5} {'uIntLe/var':^12} {'sIntLe':^12} {'floatLe':^12} {'dblLe/4int':^12}"
                fieldmap = (
                    (SOLIXMQTTMAP.get(self.model).get(msgtype) or {})
                    if self.model in SOLIXMQTTMAP
                    else {}
                )
                for f in self.msg_fields.values():
                    name = (
                        (fld := fieldmap.get(f.f_name.hex()) or {}).get("name")
                        or (fld.get("bytes") or {})
                        or ""
                    )
                    s += f"\n{f.decode().rstrip()}{Color.CYAN + ' --> ' + str(name) + Color.OFF if name else ''}"
                s += f"\n{80 * '-'}"
        else:
            s = ""
        return s

    def asdict(self) -> dict:
        """Return a dictionary representation of the class fields."""
        return asdict(self)

    def update_field(self, datafield: DeviceHexDataField) -> None:
        """Add or update the given field if header exists and ensure correct sequence of all fields."""
        if (
            self.msg_header
            and isinstance(datafield, DeviceHexDataField)
            and datafield.f_name
        ):
            self.msg_fields = self.msg_fields or {}
            self.msg_fields.update({datafield.f_name.hex(): datafield})
            # sort fields
            fieldlist = list(self.msg_fields.keys())
            fieldlist.sort()
            new_fields = {name: self.msg_fields[name] for name in fieldlist}
            self.msg_fields = new_fields
            # update length and hexbytes
            self._update_hexbytes()

    def add_timestamp_field(self, fieldname: str | bytes = "fe") -> None:
        """Add or update a timestamp field as maybe required to publish command data."""
        if isinstance(fieldname, str):
            fieldname = bytes.fromhex(fieldname)
        datafield = DeviceHexDataField(
            f_name=fieldname, f_type=DeviceHexDataTypes.var.value, f_value=int(datetime.now().timestamp()).to_bytes(4, byteorder="little")
        )
        self.update_field(datafield=datafield)

    def pop_field(
        self, datafield: str | bytes | DeviceHexDataField
    ) -> DeviceHexDataField | None:
        """Remove the given field name and return it, or return None if not found."""
        if isinstance(datafield, bytes):
            datafield = datafield.hex()
        elif isinstance(datafield, DeviceHexDataField):
            datafield = datafield.f_name.hex()
        else:
            datafield = str(datafield)
        df = (self.msg_fields or {}).pop(datafield, None)
        # update length and hexbytes
        self._update_hexbytes()
        return df


# Define mapping for MQTT messages field conversions depending on Anker Solix model
# Nested structure for model.messagetype.fieldname.attributes
# field format 0x03 may use 1-4 individual values or all bytes for a signed int typically,
# specified values count reflects how many bytes to consider individually, 0 considers all for single int value (default)
# field format 0x04 is a bitmask pattern, byte number [0..len-1] reflects position, mask reflects the bit relevant for the value/toggle
# factor can be used optionally to indicate a required conversion of the standard field value,
# e.g. field value -123456 with factor -0.01 must be converted to get real value of 1234.56
SOLIXMQTTMAP = {
    "A17C5": {
        "0405": {
            "topic": "param_info",
            "a2": {"name": "device_sn"},
            "a7": {"name": "sw_version", "values": 4},
            "a8": {"name": "sw_controller", "values": 4},
            "a9": {"name": "sw_expansion", "values": 4},
            "d4": {"name": "temperature"},
            "bd": {"name": "max_load"},
            "be": {"name": "max_load_legal"},
            "d5": {"name": "pv_limit"},
            "d6": {"name": "ac_input_limit"},
        },
        "0408": {
            "topic": "state_info",
            "a2": {"name": "device_sn"},
            "cc": {"name": "temperature"},
        },
    },
    "A17C0": {
        "0405": {
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
                    "12": [{"name": "allow_export_switch", "mask": 0x64}],
                    "15": [{"name": "priority_discharge_switch", "mask": 0x01}],
                }
            },
            "b0": {"name": "charging_power", "values": 1},
            "b4": {"name": "output_cutoff_data"},
            "b5": {"name": "lowpower_input_data"},
            "b6": {"name": "input_cutoff_data"},
            "b7": {"name": "inverter_brand"},
            "b8": {"name": "inverter_model"},
            "b9": {"name": "min_load?"},
        },
        "0407": {
            "topic": "state_info",
            "a2": {"name": "device_sn"},
            "a3": {"name": "wifi_name"},
            "a4": {"name": "wifi_signal"},
            "a5": {"name": "wifi_type"},
        },
        "0408": {
            "topic": "state_info",
            "a2": {"name": "device_sn"},
            "a8": {"name": "charging_status"},
            "a9": {"name": "output_preset"},
            "aa": {"name": "photovoltaic_power"},
            "ab": {"name": "charging_power"},
            "ac": {"name": "output_power"},
            "ad": {"name": "?"},
            "ae": {"name": "?"},
            "b0": {"name": "battery_soc"},
            "b6": {"name": "temperature"},
        },
    },
    "A17X7": {
        "0405": {
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
}
