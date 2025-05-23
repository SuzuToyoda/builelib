# %%
import csv
import math

import numpy as np


def read_csv_climate_data(filename):
    """
    気象データ（csvファイル）を読み込む関数。太陽光発電用。
    8760の行列
    """

    # CSVファイルの読み込み
    with open(filename, encoding='cp932') as f:
        reader = csv.reader(f)
        data = [row for row in reader]

    # numpy array型に変換(8760,5)
    npArrayData = np.array(data)

    # 外気温 [℃]
    tout = npArrayData[2:8762, 0].astype('float')
    # 法線面直達日射量 [MJ/m2h]
    iod = npArrayData[2:8762, 1].astype('float')
    # 水平面天空日射量 [MJ/m2h]
    ios = npArrayData[2:8762, 2].astype('float')
    # 太陽高度[°]
    sun_altitude = npArrayData[2:8762, 3].astype('float')
    # 太陽方位角[°]
    sun_azimuth = npArrayData[2:8762, 4].astype('float')

    return tout, iod, ios, sun_altitude, sun_azimuth


def read_hasp_climate_data(filename):
    """
    気象データ（hasファイル）を読み込む関数。
    365×24の行列
    """

    # hasファイルの読み込み
    with open(filename, encoding='utf-8') as f:
        hasData = f.readlines()

    tout = list()  # 最終的に365×24の行列になる。
    xout = list()  # 最終的に365×24の行列になる。
    iod = list()  # 最終的に365×24の行列になる。
    ios = list()  # 最終的に365×24の行列になる。
    inn = list()  # 最終的に365×24の行列になる。

    for line in hasData:

        # 初期化
        tmp = []

        if line[-2] == '1':  # 外気温 [℃]

            # 時刻別の気温を読み込み、格納
            for hh in range(0, 24):
                tmp.append((float(line[3 * hh:3 * (hh + 1)]) - 500) / 10)
            tout.append(tmp)

        elif line[-2] == '2':  # 外気絶対湿度 [kg/kgDA]

            # 時刻別の湿度を読み込み、格納
            for hh in range(0, 24):
                tmp.append((float(line[3 * hh:3 * (hh + 1)]) / 1000) / 10)
            xout.append(tmp)

        elif line[-2] == '3':  # 法線面直達日射量 [kcal/m2h] → [W/m2]

            # 時刻別の湿度を読み込み、格納
            for hh in range(0, 24):
                tmp.append(float(line[3 * hh:3 * (hh + 1)]) * 4.18 * 1000 / 3600)
            iod.append(tmp)

        elif line[-2] == '4':  # 水平面天空日射量 [kcal/m2h] → [W/m2]

            # 時刻別の湿度を読み込み、格納
            for hh in range(0, 24):
                tmp.append(float(line[3 * hh:3 * (hh + 1)]) * 4.18 * 1000 / 3600)
            ios.append(tmp)

        elif line[-2] == '5':  # 水平面夜間放射量 [kcal/m2h] → [W/m2]

            # 時刻別の湿度を読み込み、格納
            for hh in range(0, 24):
                tmp.append(float(line[3 * hh:3 * (hh + 1)]) * 4.18 * 1000 / 3600)
            inn.append(tmp)

    tout = np.array(tout)
    xout = np.array(xout)
    iod = np.array(iod)
    ios = np.array(ios)
    inn = np.array(inn)

    return tout, xout, iod, ios, inn


def del04(month, day):
    """
    日赤緯を求める関数
    入力  month : 月
    入力  day : 日
    出力  declination:日赤緯 [rad]
    """

    # 通日を計算する
    n = math.floor(
        30 * (month - 1) + math.floor((month + math.floor(month / 8)) / 2) - math.floor((month + 7) / 10) + day)

    # 一年を周期とする角度を計算する
    w = n * 2.0 * math.pi / 366.0

    # HASP教科書等より2項目の括弧内の2項目の係数を変更（+0.2070988 → -0.2070988）
    declination = 0.006322 - 0.405748 * math.cos(w + 0.153231) - 0.005880 * math.cos(
        2.0 * w - 0.207099) - 0.003233 * math.cos(3 * w + 0.620129)

    return declination


def del04_array():
    d = np.arange(1, 366)
    rad_per_day = 2.0 * np.pi / 366.0

    w_1 = d * rad_per_day + 0.153231
    w_2 = 2 * d * rad_per_day - 0.207099
    w_3 = 3 * d * rad_per_day + 0.620129

    w_1_array = np.cos(w_1)
    w_2_array = np.cos(w_2)
    w_3_array = np.cos(w_3)

    declination = 0.006322 - 0.405748 * w_1_array - 0.005880 * w_2_array - 0.003233 * w_3_array
    return np.tile(declination, (24, 1)).T


def eqt04(month, day):
    """
    均時差を求める関数
    入力  month : 月
    入力  day   : 日 
    出力  e     : 均時差 [h]
    """

    # 通日を計算する
    n = math.floor(
        30 * (month - 1) + math.floor((month + math.floor(month / 8)) / 2) - math.floor((month + 7) / 10) + day)

    # 均時差を計算する(HASP 教科書 p24)
    # 一年を周期とする角度を計算する

    w = n * 2.0 * math.pi / 366.0
    equal_time_difference = - 0.0002786409 + 0.1227715 * math.cos(w + 1.498311) - 0.1654575 * math.cos(
        2.0 * w - 1.261546) - 0.00535383 * math.cos(3.0 * w - 1.1571)

    return equal_time_difference


def eqt04_array():
    d = np.arange(1, 366)
    rad_per_day = 2.0 * np.pi / 366.0
    w_1 = (d * rad_per_day) + 1.498311
    w_2 = 2 * (d * rad_per_day) - 1.261546
    w_3 = 3 * (d * rad_per_day) - 1.1571

    w_1_array = np.cos(w_1)
    w_2_array = np.cos(w_2)
    w_3_array = np.cos(w_3)

    equal_time_difference = (
            -0.0002786409
            + 0.1227715 * w_1_array
            - 0.1654575 * w_2_array
            - 0.00535383 * w_3_array
    )
    return np.tile(equal_time_difference, (24, 1)).T


def deg2rad(degree):
    """
    degree 度[°] を ラジアン [rad]に変換する関数
    """
    radian = degree * math.pi / 180

    return radian


def solar_radiation_by_azimuth(alp, bet, latitude, longitude, iod_all, ios_all, inn_all):
    """
    方位角・傾斜角別の日射量を算出する関数
    入力 alp : 方位角（0が南、45が南西、180が北）
    入力 bet : 傾斜角（0が水平、90が垂直）
    入力 latitude : 緯度
    入力 longitude : 経度
    入力 iod_all : 直達日射量（365×24、np.array） [W/m2]
    入力 ios_all : 天空日射量（365×24、np.array） [W/m2]
    入力 inn_all : 夜間日射量（365×24、np.array） [W/m2]
    出力 DSR    : 方位別の積算直達日射量（365日分） [Wh/m2/day]
    出力 DSRita : 方位別の積算直達日射量、入射角特性込み（365日分）[Wh/m2/day]
    出力 ISR    : 積算天空日射量（365日分）[Wh/m2/day]
    出力 NSR    : 積算夜間日射量（365日分）[Wh/m2/day]
    """

    go = 1
    rad = np.pi / 180
    # 通算日数(1月1日が1、12月31日が365)
    sinlatitude = np.sin(deg2rad(latitude))  # 緯度の正弦
    coslatitude = np.cos(deg2rad(latitude))  # 緯度の余弦
    sinAlp = np.sin(alp * rad)  # 方位角正弦
    cosAlp = np.cos(alp * rad)  # 方位角余弦
    sinBet = np.sin(bet * rad)  # 傾斜角正弦
    cosBet = np.cos(bet * rad)  # 傾斜角余弦
    h = np.arange(24).reshape(1, -1).repeat(365, axis=0)
    # 日赤緯を求める(HASP教科書P24(2-22)参照)
    declination = del04_array()
    # 均時差を求める
    equal_time_difference = eqt04_array()
    tim = (15.0 * (h + 1) + 15.0 * equal_time_difference + longitude - 315.0) * rad
    cos_tim = np.cos(tim)
    sin_tim = np.sin(tim)
    # 日射量 [W/m2]
    iod = iod_all  # 法線面直達日射量 [W/m2]
    ios = ios_all  # 水平面天空日射量 [W/m2]
    Ion = inn_all  # 水平面夜間放射量 [W/m2]

    sin_del = np.sin(declination)
    cos_del = np.cos(declination)
    # 太陽高度の正弦を求める(HASP教科書 P25 (2.25)参照 )
    sinh = sinlatitude * sin_del + coslatitude * cos_del * cos_tim

    # 太陽高度の余弦、太陽方位の正弦・余弦を求める(HASP 教科書P25 (2.25)参照)
    cosh = np.sqrt(1 - sinh ** 2)  # 太陽高度の余弦
    sinA = cos_del * sin_tim / cosh  # 太陽方位の正弦
    cosA = (sinh * sinlatitude - sin_del) / (cosh * coslatitude)  # 太陽方位の余弦
    # 傾斜壁から見た太陽高度を求める(HASP 教科書 P26(2.26)参照)
    sinh2 = sinh * cosBet + cosh * sinBet * (cosA * cosAlp + sinA * sinAlp)
    sinh2 = np.clip(sinh2, 0, None)

    # 入射角特性
    ita = 2.392 * sinh2 - 3.8636 * sinh2 ** 3 + 3.7568 * sinh2 ** 5 - 1.3952 * sinh2 ** 7
    # 傾斜面入射日射量(直達日射量)（W/m2）
    Id = go * iod * sinh2

    # 傾斜面入射日射量(直達日射量)（W/m2）　入射角特性込み（0.89で除して基準化済み）
    Id_ita = go * iod * sinh2 * ita / 0.89

    # 傾斜面入射日射量(天空日射量)（W/m2）
    if bet == 90:
        Is = 0.5 * ios + 0.1 * 0.5 * (ios + iod * sinh)
    elif bet == 0:
        Is = ios
    else:
        # 太陽熱利用の計算用：要検証
        rhoG = 0.8
        Is = (1 + cosBet) / 2 * ios + (1 - cosBet) / 2 * rhoG * (ios + iod * sinh)

    # 長波長放射
    if bet == 90:
        Insr = np.sum(inn_all, 1) / 2
    elif bet == 0:
        Insr = np.sum(inn_all, 1)
    else:
        Insr = None

    return np.sum(Id, axis=1), np.sum(Id_ita, axis=1), np.sum(Is, axis=1), Insr


if __name__ == '__main__':
    pass

    # # 2024.8.12 気象データを統一する際の検証：
    # import os
    # import json

    # database_directory =  os.path.dirname(os.path.abspath(__file__)) + "/database/"

    # # 地域別データの読み込み
    # with open('./builelib/database/area.json', 'r', encoding='utf-8') as f:
    #     area = json.load(f)

    # area_name = "8地域"

    # # 空調用と給湯用の気象データの比較
    # filename_HASP = "./builelib/climatedata/C1_" +area[area_name]["気象データファイル名"]
    # filename_dat  = "./builelib/climatedata/" + area[area_name]["気象データファイル名（給湯）"]

    # toa_ave_dat = read_dat_climate_data(filename_dat)

    # [tout, xout, iod, ios, inn] = read_hasp_climate_data(filename_hasp)
    # toa_ave_hasp = np.mean(tout,1)

    # np.savetxt('気象データ検証_' + area_name + '.csv', np.stack([toa_ave_dat, toa_ave_hasp, toa_ave_dat-toa_ave_hasp], 1) ,delimiter=',',fmt='%.3f')
