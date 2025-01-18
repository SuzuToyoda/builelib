import json
import math
import os
import traceback
from dataclasses import dataclass

import numpy as np

from builelib import (
    airconditioning_webpro,
    ventilation,
    lighting,
    hotwatersupply,
    elevator,
    photovoltaic,
    other_energy,
    cogeneration, database,
)
from builelib.domain.request import AreaByDirection, Room, Building, BuilelibRequest


# json.dump用のクラス
class MyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, set):
            return list(obj)
        else:
            return super(MyEncoder, self).default(obj)


@dataclass
class GetBeiResponse:
    # 設計一次エネルギー消費量[MJ]
    energy_consumption_design: float = 0
    # 基準一次エネルギー消費量[MJ]
    energy_consumption_standard: float = 0
    # 設計一次エネルギー消費量（その他除き）[MJ]
    energy_consumption_design_other: float = 0
    # 基準一次エネルギー消費量（その他除き）[MJ]
    energy_consumption_standard_other: float = 0
    # BEI
    bei: float = 0
    # 設計一次エネルギー消費量（再エネ、その他除き）[MJ]
    energy_consumption_design_renewable_other: float = 0
    # BEI（再エネ除き）
    bei_renewable: float = 0
    # 設計一次エネルギー消費量（空調）[MJ]
    energy_consumption_design_ac: float = 0
    # 基準一次エネルギー消費量（空調）[MJ]
    energy_consumption_standard_ac: float = 0
    # BEI_AC
    bei_ac: float = 0
    # 設計一次エネルギー消費量（換気）[MJ]
    energy_consumption_design_ventilation: float = 0
    # 基準一次エネルギー消費量（換気）[MJ]
    energy_consumption_standard_ventilation: float = 0
    # BEI_V
    bei_ventilation: float = 0
    # 設計一次エネルギー消費量（照明）[MJ]
    energy_consumption_design_lighting: float = 0
    # 基準一次エネルギー消費量（照明）[MJ]
    energy_consumption_standard_lighting: float = 0
    # BEI_L
    bei_lighting: float = 0
    # 設計一次エネルギー消費量（給湯
    energy_consumption_design_hot_water: float = 0
    # 基準一次エネルギー消費量（給湯）[MJ]
    energy_consumption_standard_hot_water: float = 0
    # BEI_HW
    bei_hot_water: float = 0
    # 設計一次エネルギー消費量（昇降機）[MJ]
    energy_consumption_design_elevator: float = 0
    # 基準一次エネルギー消費量（昇降機）[MJ]
    energy_consumption_standard_elevator: float = 0
    # BEI_EV
    bei_elevator: float = 0
    # その他一次エネルギー消費量[MJ]
    other_energy_consumption: float = 0
    # 創エネルギー量（太陽光）[MJ]
    renewable_energy_photovoltaic: float = 0
    # 創エネルギー量（コジェネ）[MJ]
    renewable_energy_cogeneration: float = 0


def get_bei(
        exec_calculation,
        input_data,
        flow_control,
        heat_source_performance,
        area,
        ac_operation_mode,
        window_heat_transfer_performance,
        glass2window,
        heat_thermal_conductivity,
        heat_thermal_conductivity_model,
        t_out_all,
        x_out_all,
        iod_all,
        ios_all,
        inn_all,
        q_room_coeffi,
        room_usage_schedule,
        calender,
        lighting_ctrl,
        ventilation_ctrl
):
    """Builelibを実行するプログラム
    Args:
        exec_calculation (float): 計算の実行 （True: 計算も行う、 False: 計算は行わない）
        input_file_name (str): 入力ファイルの名称
    """
    # ------------------------------------
    # 引数の受け渡し
    # ------------------------------------
    exec_calculation = bool(
        exec_calculation
    )
    # input_file_name = str(input_file_name)

    # ------------------------------------
    # 出力ファイルの定義
    # ------------------------------------
    result = GetBeiResponse()

    # CGSの計算に必要となる変数
    result_json_for_cgs = {
        "AC": {},
        "V": {},
        "L": {},
        "HW": {},
        "EV": {},
        "PV": {},
        "OT": {},
    }

    # 設計一次エネルギー消費量[MJ]
    energy_consumption_design = 0
    # 基準一次エネルギー消費量[MJ]
    energy_consumption_standard = 0

    # ------------------------------------
    # 空気調和設備の計算の実行
    # ------------------------------------

    # 実行
    result_data_AC = {}

    if exec_calculation:

        try:
            if input_data[
                "air_conditioning_zone"
            ]:  # air_conditioning_zone が 空 でなければ
                area_info = area[str(input_data["building"]["region"]) + "地域"]
                ac_mode = ac_operation_mode[area_info["空調運転モードタイプ"]]
                room_temperature_setting, room_humidity_setting, room_enthalpy_setting = airconditioning_webpro.make_ac_list(
                    ac_mode)
                result_data_AC = airconditioning_webpro.calc_energy(
                    input_data,
                    False,
                    flow_control,
                    heat_source_performance,
                    area,
                    ac_operation_mode,
                    window_heat_transfer_performance,
                    glass2window,
                    str(input_data["building"]["region"]),
                    heat_thermal_conductivity,
                    heat_thermal_conductivity_model,
                    t_out_all,
                    x_out_all,
                    iod_all,
                    ios_all,
                    inn_all,
                    q_room_coeffi,
                    room_usage_schedule,
                    calender,
                    room_temperature_setting, room_humidity_setting, room_enthalpy_setting
                )
                # CGSの計算に必要となる変数
                result_json_for_cgs["AC"] = result_data_AC["for_cgs"]

                # 設計一次エネ・基準一次エネに追加
                energy_consumption_design += result_data_AC[
                    "設計一次エネルギー消費量[MJ/年]"
                ]
                energy_consumption_standard += result_data_AC[
                    "基準一次エネルギー消費量[MJ/年]"
                ]
                result.energy_consumption_design_ac = result_data_AC[
                    "設計一次エネルギー消費量[MJ/年]"
                ]
                result.energy_consumption_standard_ac = result_data_AC[
                    "基準一次エネルギー消費量[MJ/年]"
                ]
                result.bei_ac = math.ceil(result_data_AC["BEI/AC"] * 100) / 100

            else:
                result_data_AC = {"message": "空気調和設備はありません。"}

        except:
            result_data_AC = {
                "error": "空気調和設備の計算時に予期せぬエラーが発生しました。"
            }

    else:
        result_data_AC = {"error": "空気調和設備の計算は実行されませんでした。"}
    # ------------------------------------
    # 機械換気設備の計算の実行
    # ------------------------------------

    # 実行
    result_data_V = {}
    if exec_calculation:

        try:
            if input_data["ventilation_room"]:  # ventilation_room が 空 でなければ

                result_data_V = ventilation.calc_energy(input_data, ventilation_ctrl, DEBUG=False)

                # CGSの計算に必要となる変数
                result_json_for_cgs["V"] = result_data_V["for_cgs"]

                # 設計一次エネ・基準一次エネに追加
                energy_consumption_design += result_data_V[
                    "設計一次エネルギー消費量[MJ/年]"
                ]
                energy_consumption_standard += result_data_V[
                    "基準一次エネルギー消費量[MJ/年]"
                ]
                result.energy_consumption_design_ventilation = result_data_V[
                    "設計一次エネルギー消費量[MJ/年]"
                ]
                result.energy_consumption_standard_ventilation = result_data_V[
                    "基準一次エネルギー消費量[MJ/年]"
                ]
                result.bei_ventilation = math.ceil(result_data_V["BEI/V"] * 100) / 100

            else:
                result_data_V = {"message": "機械換気設備はありません。"}

        except:
            result_data_V = {
                "error": "機械換気設備の計算時に予期せぬエラーが発生しました。"
            }

    else:
        result_data_V = {"error": "機械換気設備の計算は実行されませんでした。"}

    # ------------------------------------
    # 照明設備の計算の実行
    # ------------------------------------

    # 実行
    result_data_L = {}
    if exec_calculation:

        try:
            if input_data["lighting_systems"]:  # lighting_systems が 空 でなければ

                result_data_L = lighting.calc_energy(input_data, lighting_ctrl, calender, room_usage_schedule,
                                                     DEBUG=False)
                # CGSの計算に必要となる変数
                result_json_for_cgs["L"] = result_data_L["for_cgs"]

                # 設計一次エネ・基準一次エネに追加
                energy_consumption_design += result_data_L["E_lighting"]
                energy_consumption_standard += result_data_L["Es_lighting"]
                result.energy_consumption_design_lighting = result_data_L["E_lighting"]
                result.energy_consumption_standard_lighting = result_data_L["Es_lighting"]
                result.bei_lighting = math.ceil(result_data_L["BEI_L"] * 100) / 100

            else:
                result_data_L = {"message": "照明設備はありません。"}

        except:
            result_data_L = {"error": "照明設備の計算時に予期せぬエラーが発生しました。"}

    else:
        result_data_L = {"error": "照明設備の計算は実行されませんでした。"}

    # ------------------------------------
    # 給湯設備の計算の実行
    # ------------------------------------

    # 実行
    result_data_HW = {}

    if exec_calculation:

        try:
            if input_data["hot_water_room"]:  # hot_water_room が 空 でなければ

                result_data_HW = hotwatersupply.calc_energy(input_data, DEBUG=False)

                # CGSの計算に必要となる変数
                result_json_for_cgs["HW"] = result_data_HW["for_cgs"]

                # 設計一次エネ・基準一次エネに追加
                energy_consumption_design += result_data_HW[
                    "設計一次エネルギー消費量[MJ/年]"
                ]
                energy_consumption_standard += result_data_HW[
                    "基準一次エネルギー消費量[MJ/年]"
                ]
                result.energy_consumption_design_hot_water = result_data_HW[
                    "設計一次エネルギー消費量[MJ/年]"
                ]
                result.energy_consumption_standard_hot_water = result_data_HW[
                    "基準一次エネルギー消費量[MJ/年]"
                ]
                result.bei_hot_water = math.ceil(result_data_HW["BEI_HW"] * 100) / 100

            else:
                result_data_HW = {"message": "給湯設備はありません。"}

        except:
            result_data_HW = {
                "error": "給湯設備の計算時に予期せぬエラーが発生しました。"
            }

    else:
        result_data_HW = {"error": "給湯設備の計算は実行されませんでした。"}

    # ------------------------------------
    # 昇降機の計算の実行
    # ------------------------------------

    # 実行
    result_data_EV = {}
    if exec_calculation:

        try:
            if len(input_data["elevators"]) > 0:
                result_data_EV = elevator.calc_energy(input_data, False, calender, room_usage_schedule)
                # CGSの計算に必要となる変数
                result_json_for_cgs["EV"] = result_data_EV["for_cgs"]

                # 設計一次エネ・基準一次エネに追加
                energy_consumption_design += result_data_EV["E_elevator"]
                energy_consumption_standard += result_data_EV["Es_elevator"]
                result.energy_consumption_design_elevator = result_data_EV["E_elevator"]
                result.energy_consumption_standard_elevator = result_data_EV["Es_elevator"]
                result.bei_elevator = math.ceil(result_data_EV["BEI_EV"] * 100) / 100

            else:
                result_data_EV = {"message": "昇降機はありません。"}
        except:
            result_data_EV = {"error": "昇降機の計算時に予期せぬエラーが発生しました。"}

    else:
        result_data_EV = {"error": "昇降機の計算は実行されませんでした。"}

    # ------------------------------------
    # 太陽光発電の計算の実行
    # ------------------------------------

    # 実行
    result_data_PV = {}
    if exec_calculation:

        try:
            if input_data[
                "photovoltaic_systems"
            ]:  # photovoltaic_systems が 空 でなければ

                result_data_PV = photovoltaic.calc_energy(input_data, DEBUG=False)

                # CGSの計算に必要となる変数
                result_json_for_cgs["PV"] = result_data_PV["for_cgs"]

                # 設計一次エネ・基準一次エネに追加
                energy_consumption_design -= result_data_PV["E_photovoltaic"]
                result.renewable_energy_photovoltaic = result_data_PV["E_photovoltaic"]

            else:
                result_data_PV = {"message": "太陽光発電設備はありません。"}
        # except:
        #     result_data_PV = {
        #         "error": "太陽光発電設備の計算時に予期せぬエラーが発生しました。"
        #     }
        except Exception as e:
            # エラー詳細とスタックトレースをキャプチャ
            result_data_PV = {
                "error": "太陽光発電設備の計算時に予期せぬエラーが発生しました。",
                "details": str(e),
                "traceback": traceback.format_exc()  # スタックトレースを追加
            }
    else:
        result_data_PV = {"error": "太陽光発電設備の計算は実行されませんでした。"}

    # ------------------------------------
    # その他の計算の実行
    # ------------------------------------

    # 実行
    result_data_OT = {}
    if exec_calculation:

        try:
            if input_data["rooms"]:  # rooms が 空 でなければ

                result_data_OT = other_energy.calc_energy(input_data, DEBUG=False)

                # CGSの計算に必要となる変数
                result_json_for_cgs["OT"] = result_data_OT["for_cgs"]
                result.other_energy_consumption = result_data_OT["E_other"]

            else:
                result_data_OT = {"message": "その他一次エネルギー消費量は0です。"}
        except:
            result_data_OT = {
                "error": "その他一次エネルギー消費量の計算時に予期せぬエラーが発生しました。"
            }
    else:
        result_data_OT = {
            "error": "その他一次エネルギー消費量の計算は実行されませんでした。"
        }

    # ------------------------------------
    # コジェネの計算の実行
    # ------------------------------------

    # 実行
    result_data_CGS = {}
    if exec_calculation:

        try:
            if input_data[
                "cogeneration_systems"
            ]:  # cogeneration_systems が 空 でなければ
                result_data_CGS = cogeneration.calc_energy(
                    input_data,
                    result_json_for_cgs,
                    t_out_all,
                    x_out_all,
                    iod_all,
                    ios_all,
                    inn_all,
                    DEBUG=False
                )

                # 設計一次エネ・基準一次エネに追加
                energy_consumption_design -= (
                        result_data_CGS["年間一次エネルギー削減量"] * 1000
                )
                result.renewable_energy_cogeneration = (
                        result_data_CGS["年間一次エネルギー削減量"] * 1000
                )
            else:
                result_data_CGS = {"message": "コージェネレーション設備はありません。"}
        except:
            result_data_CGSa_OT = {
                "error": "コージェネレーション設備の計算時に予期せぬエラーが発生しました。"
            }
    else:
        result_data_CGS = {
            "error": "コージェネレーション設備の計算は実行されませんでした。"
        }

    # ------------------------------------
    # BEIの計算
    # ------------------------------------

    if energy_consumption_standard != 0:
        result.energy_consumption_design = energy_consumption_design
        result.energy_consumption_standard = energy_consumption_standard
        result.bei = energy_consumption_design / energy_consumption_standard
        result.bei = math.ceil(result.bei * 100) / 100
        result.energy_consumption_design_renewable_other = energy_consumption_design + result.renewable_energy_photovoltaic
        result.bei_renewable = result.energy_consumption_design_renewable_other / energy_consumption_standard
        result.bei_renewable = math.ceil(result.bei_renewable * 100) / 100

        # 設計一次エネ・基準一次エネにその他を追加
        if "E_other" in result_data_OT:
            result.energy_consumption_design_other = energy_consumption_design + result_data_OT["E_other"]
            result.energy_consumption_standard_other = energy_consumption_standard + result_data_OT["E_other"]

    return result


if __name__ == "__main__":
    req = BuilelibRequest(
        height=20,
        rooms=[Room(is_air_conditioned=True, room_type="事務室"), Room(is_air_conditioned=True, room_type="事務室"), Room(is_air_conditioned=True, room_type="事務室"), Room(is_air_conditioned=True, room_type="事務室"), Room(is_air_conditioned=True, room_type="事務室")],
        areas=[AreaByDirection(direction="north", area=1000), AreaByDirection(direction="south", area=1000),
               AreaByDirection(direction="east", area=1000), AreaByDirection(direction="west", area=1000)],
        floor_number=5,
        wall_u_value=0.5,
        glass_u_value=0.5,
        glass_solar_heat_gain_rate=3,
        window_ratio=0.4,
        building_type="事務所等",
        model_building_type="事務所モデル",
        lighting_number=10,
        lighting_power=3000,
        elevator_number=2,
        is_solar_power=True,
        building_information=Building(
            name="test",
            prefecture="北海道",
            city="札幌市",
            address="北1条西1丁目",
            region_number=1,
            annual_solar_region="A3"
        ),
        air_heat_exchange_rate_cooling=1000,
        air_heat_exchange_rate_heating=2900,
    )
    req_json = req.create_default_json_file()

    database_directory = os.path.dirname(os.path.abspath(__file__)) + "/builelib/database/"
    climate_data_directory = os.path.dirname(os.path.abspath(__file__)) + "/builelib/climatedata/"

    flow_control = database.get_flow_control()
    heat_source_performance = database.get_heat_source_performance()
    area = database.get_area()
    ac_operation_mode = database.get_ac_operation_mode()
    window_heat_transfer_performance = database.get_window_heat_transfer_performance()
    glass2window = database.get_glass2window()
    heat_thermal_conductivity = database.get_thermal_conductivity()
    heat_thermal_conductivity_model = database.get_thermal_conductivity_model()
    [t_out_all, x_out_all, iod_all, ios_all, inn_all] = database.get_climate_data_from_area(
        req.building_information.region_number, area
    )
    q_room_coeffi = database.get_qroom_coefficient_by_area(req.building_information.region_number)
    room_usage_schedule = database.get_room_usage_schedule()
    calender = database.get_calender()
    lighting_ctrl = database.get_lighting_control()
    ventilation_ctrl = database.get_ventilation_control()
    r = get_bei(
        True,
        req_json,
        flow_control,
        heat_source_performance,
        area,
        ac_operation_mode,
        window_heat_transfer_performance,
        glass2window,
        heat_thermal_conductivity,
        heat_thermal_conductivity_model,
        t_out_all,
        x_out_all,
        iod_all,
        ios_all,
        inn_all,
        q_room_coeffi,
        room_usage_schedule,
        calender,
        lighting_ctrl,
        ventilation_ctrl
    )
    print(r)
