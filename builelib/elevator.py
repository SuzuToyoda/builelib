import json
import math
import os
import sys
from enum import Enum

import numpy as np

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import commons as bc


class ElevatorControlType(Enum):
    AC_FEEDBACK_CONTROL = "交流帰還制御"
    VVVF_WITH_REGENERATION = "VVVF(電力回生あり)"
    VVVF_WITHOUT_REGENERATION = "VVVF(電力回生なし)"
    VVVF_WITH_REGENERATION_GEARLESS = "VVVF(電力回生あり、ギアレス)"
    VVVF_WITHOUT_REGENERATION_GEARLESS = "VVVF(電力回生なし、ギアレス)"


def calc_energy(input_data, DEBUG, calender, room_usage_schedule):
    # ----------------------------------------------------------------------------------
    # 計算結果を格納する変数
    # ----------------------------------------------------------------------------------
    result_json = {
        "E_elevator": 0,
        "Es_elevator": 0,
        "BEI_EV": 0,
        "elevators": {},
        "for_cgs": {
            "Edesign_MWh_day": np.zeros(365)
        }
    }

    # ----------------------------------------------------------------------------------
    # 解説書 6.2 速度制御方式に応じて定められる係数
    # ----------------------------------------------------------------------------------
    for room_name in input_data["elevators"]:
        for unit_id, unit_configure in enumerate(input_data["elevators"][room_name]["elevator"]):
            control_type = unit_configure["control_type"]
            if control_type == ElevatorControlType.AC_FEEDBACK_CONTROL.value:
                input_data["elevators"][room_name]["elevator"][unit_id]["control_type_coefficient"] = 1 / 20
            elif control_type == ElevatorControlType.VVVF_WITHOUT_REGENERATION.value:
                input_data["elevators"][room_name]["elevator"][unit_id]["control_type_coefficient"] = 1 / 40
            elif control_type == ElevatorControlType.VVVF_WITH_REGENERATION.value:
                input_data["elevators"][room_name]["elevator"][unit_id]["control_type_coefficient"] = 1 / 45
            elif control_type == ElevatorControlType.VVVF_WITHOUT_REGENERATION_GEARLESS.value:
                input_data["elevators"][room_name]["elevator"][unit_id]["control_type_coefficient"] = 1 / 45
            elif control_type == ElevatorControlType.VVVF_WITH_REGENERATION_GEARLESS.value:
                input_data["elevators"][room_name]["elevator"][unit_id]["control_type_coefficient"] = 1 / 50

            else:
                raise Exception("速度制御方式 が不正です。")
    # ----------------------------------------------------------------------------------
    # 解説書 6.3 昇降機系統に属する昇降機1台あたりの年間電力消費量
    # ----------------------------------------------------------------------------------

    for room_name in input_data["elevators"]:
        # 建物用途、室用途、室面積の取得
        building_type = input_data["rooms"][room_name]["building_type"]
        room_type = input_data["rooms"][room_name]["room_type"]

        # 年間照明点灯時間 [時間]
        if building_type == "共同住宅":
            input_data["elevators"][room_name]["operation_time"] = 5480
            input_data["elevators"][room_name]["operation_schedule_hourly"] = 5480 / 8760 * np.ones((365, 24))
        else:
            input_data["elevators"][room_name]["operation_schedule_hourly"] = bc.get_daily_ope_schedule_lighting(
                building_type, room_type, calender, room_usage_schedule)
            input_data["elevators"][room_name]["operation_time"] = np.sum(
                np.sum(input_data["elevators"][room_name]["operation_schedule_hourly"]))

    # エネルギー消費量計算 [kWh/年]
    Edesign_MWh_hour = np.zeros((365, 24))
    for room_name in input_data["elevators"]:
        for unit_id, unit_configure in enumerate(input_data["elevators"][room_name]["elevator"]):

            input_data["elevators"][room_name]["elevator"][unit_id]["energy_consumption"] = \
                unit_configure["number"] * \
                unit_configure["velocity"] * unit_configure["load_limit"] * unit_configure[
                    "control_type_coefficient"] * \
                input_data["elevators"][room_name]["operation_time"] / 860

            if DEBUG:
                print(f'室 {room_name} に設置された {unit_id + 1} 台目の昇降機')
                print(f'　- 台数  {unit_configure["number"]}')
                print(f'　- 速度  {unit_configure["velocity"]}')
                print(f'　- 積載量  {unit_configure["load_limit"]}')
                print(f'　- 速度制御方式による係数  {unit_configure["control_type_coefficient"]}')
                print(
                    f'　- エネルギー消費量 kWh/年 {input_data["elevators"][room_name]["elevator"][unit_id]["energy_consumption"]}')

            # 時刻別エネルギー消費量 [MWh]
            Edesign_MWh_hour += \
                unit_configure["number"] * \
                unit_configure["velocity"] * unit_configure["load_limit"] * unit_configure[
                    "control_type_coefficient"] * \
                input_data["elevators"][room_name]["operation_schedule_hourly"] / 860 / 1000

    # ----------------------------------------------------------------------------------
    # 解説書 6.4 昇降機の設計一次エネルギー消費量
    # ----------------------------------------------------------------------------------

    # 設計一次エネルギー消費量計算 [MJ/年]
    for room_name in input_data["elevators"]:
        for unit_id, unit_configure in enumerate(input_data["elevators"][room_name]["elevator"]):
            result_json["E_elevator"] += unit_configure["energy_consumption"] * 9760 / 1000

    if DEBUG:
        print(f'昇降機の設計一次エネルギー消費量  {result_json["E_elevator"]}  MJ/年')

    # ----------------------------------------------------------------------------------
    # 解説書 10.5 昇降機の基準一次エネルギー消費量
    # ----------------------------------------------------------------------------------

    # エネルギー消費量計算 [kWh/年]
    for room_name in input_data["elevators"]:
        for unit_id, unit_configure in enumerate(input_data["elevators"][room_name]["elevator"]):
            input_data["elevators"][room_name]["elevator"][unit_id]["Es"] = \
                unit_configure["number"] * \
                unit_configure["velocity"] * unit_configure["load_limit"] * (1 / 40) * \
                unit_configure["transport_capacity_factor"] * \
                input_data["elevators"][room_name]["operation_time"] / 860

            input_data["elevators"][room_name]["elevator"][unit_id]["energyRatio"] = \
                input_data["elevators"][room_name]["elevator"][unit_id]["energy_consumption"] / \
                input_data["elevators"][room_name]["elevator"][unit_id]["Es"]

            # 基準一次エネルギー消費量計算 [MJ/年]
            result_json["Es_elevator"] += input_data["elevators"][room_name]["elevator"][unit_id][
                                              "Es"] * 9760 / 1000

    if DEBUG:
        print(f'昇降機の基準一次エネルギー消費量  {result_json["Es_elevator"]}  MJ/年')

    # 単位変換
    result_json["E_elevator_GJ"] = result_json["E_elevator"] / 1000
    result_json["Es_elevator_GJ"] = result_json["Es_elevator"] / 1000

    # 入力データも出力
    result_json["elevators"] = input_data["elevators"]

    # BEI/Vの計算
    if result_json["Es_elevator"] != 0:
        result_json["BEI_EV"] = result_json["E_elevator"] / result_json["Es_elevator"]
        result_json["BEI_EV"] = math.ceil(result_json["BEI_EV"] * 100) / 100
    else:
        result_json["BEI_EV"] = np.nan
    # 日積算値
    result_json["for_cgs"]["Edesign_MWh_day"] = np.sum(Edesign_MWh_hour, 1)
    return result_json


if __name__ == '__main__':
    print('----- elevator.py -----')
    filename = './sample/Builelib_sample_SP7-1.json'

    # 入力ファイルの読み込み
    with open(filename, 'r', encoding='utf-8') as f:
        input_data = json.load(f)

    result_json = calc_energy(input_data, DEBUG=True)

    with open("result_json_EV.json", 'w', encoding='utf-8') as fw:
        json.dump(result_json, fw, indent=4, ensure_ascii=False, cls=bc.MyEncoder)
