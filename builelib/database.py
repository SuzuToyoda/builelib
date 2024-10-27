# # current directory
import json
import os

from builelib import climate

database_directory = os.path.dirname(os.path.abspath(__file__)) + "/database/"
climate_data_directory = os.path.dirname(os.path.abspath(__file__)) + "/climatedata/"


def get_flow_control():
    with open(database_directory + 'flow_control.json', 'r', encoding='utf-8') as f:
        return json.load(f)


def get_heat_source_performance():
    with open(database_directory + 'heat_source_performance.json', 'r', encoding='utf-8') as f:
        return json.load(f)


def get_area():
    with open(database_directory + 'area.json', 'r', encoding='utf-8') as f:
        return json.load(f)


def get_building_type():
    with open(database_directory + 'building_type.json', 'r', encoding='utf-8') as f:
        return json.load(f)


def get_window_heat_transfer_performance():
    with open(database_directory + 'window_heat_transfer_performance.json', 'r', encoding='utf-8') as f:
        return json.load(f)


def get_ac_operation_mode():
    with open(database_directory + 'ac_operation_mode.json', 'r', encoding='utf-8') as f:
        return json.load(f)


def get_glass2window():
    with open(database_directory + 'glass2window.json', 'r', encoding='utf-8') as f:
        return json.load(f)


def get_thermal_conductivity():
    with open(database_directory + 'heat_thermal_conductivity.json', 'r', encoding='utf-8') as f:
        return json.load(f)


def get_thermal_conductivity_model():
    with open(database_directory + 'heat_thermal_conductivity_model.json', 'r', encoding='utf-8') as f:
        return json.load(f)


def get_qroom_coefficient_by_area(region_number: int):
    with open(database_directory + 'qroom_coeffi_area' + str(region_number) + '.json', 'r',
              encoding='utf-8') as f:
        return json.load(f)


def get_room_usage_schedule():
    with open(database_directory + 'room_usage_schedule.json', 'r', encoding='utf-8') as f:
        return json.load(f)


def get_lighting_control():
    with open(database_directory + 'lighting_control.json', 'r', encoding='utf-8') as f:
        return json.load(f)


def get_calender():
    with open(database_directory + 'calender.json', 'r', encoding='utf-8') as f:
        return json.load(f)


def get_ventilation_control():
    with open(database_directory + 'ventilation_control.json', 'r', encoding='utf-8') as f:
        return json.load(f)


def get_climate_data_from_area(region_number: int, area: dict):
    [t_out_all, x_out_all, iod_all, ios_all, inn_all] = \
        climate.read_hasp_climate_data(
            climate_data_directory + "/" + area[str(region_number) + "地域"]["気象データファイル名"])
    return t_out_all, x_out_all, iod_all, ios_all, inn_all
