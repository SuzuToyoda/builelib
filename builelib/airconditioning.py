#%%
import sys
import json
import jsonschema
import numpy as np
import math

if 'ipykernel' in sys.modules:
    import builelib_common as bc
    import climate
    import shading
elif __name__ == '__main__':
    import builelib_common as bc
    import climate
    import shading
else:
    import builelib.builelib_common as bc
    import bulielib.climate as climate
    import builelib.shading as shading


if 'ipykernel' in sys.modules:
    directory = "./database/"
else:
    directory = "./builelib/database/"


debugmode = True

# デバッグ用の関数
def debugValues(*args):
    if debugmode:
        flg = 1
        for obj in args:
            for k, v in globals().items():
                if id(v) == id(obj):
                    target = k
                    break
            if flg == 1:
                out = target+' = '+str(obj)
                flg = 0
            else:
                out += ', '+target+' = '+str(obj) 

        print(out, type(obj))


# 計算結果を格納する変数
resultJson = {
    "Qroom": {
    }
}


#%%
##----------------------------------------------------------------------------------
## 入力ファイル（jsonファイル）の指定
##----------------------------------------------------------------------------------

# filename = '../sample/inputdata_test.json'
filename = '../sample/Case01_単室モデル_外皮1枚_大きめ.json'


# 入力データ（json）の読み込み
with open(filename, 'r') as f:
    inputdata = json.load(f)

# 入力ファイルの検証
# bc.inputdata_validation(inputdata)



#%%
##----------------------------------------------------------------------------------
## 計算条件（定数等）の設定
##----------------------------------------------------------------------------------

# 地域の区分
climateAREA  = inputdata["Building"]["Region"]


divL = 10;             # 負荷帯マトリックス分割数
divT =  6;             # 温度帯マトリックス分割数

k_heatup = 0.84;        # ファン・ポンプの発熱比率
Cw = 4.186;             # 水の比熱 [kJ/kg・K]
copDHC_cooling = 1.36;  # 他人から供給された熱の換算係数 20170913追加
copDHC_heating = 1.36;  # 他人から供給された熱の換算係数 20170913追加
aexCoeffiModifyOn = 1   # 全熱交換器の効率補正（１：あり、０：なし）

# 負荷率帯マトリックス mxL
mxL = np.arange(1/divL, 1.01, 1/divL)
mxL = np.append(mxL,1.2)

# 平均負荷率帯マトリックス aveL
aveL = np.zeros(len(mxL))

for iL in range(0,len(mxL)):
    if iL == 0:
        aveL[0] = mxL[0]/2
    elif iL == len(mxL)-1:
        aveL[iL] = 1.2
    else:
        aveL[iL] = mxL[iL-1] + (mxL[iL]-mxL[iL-1])/2


# 地域別データの読み込み
with open(directory + 'AREA.json', 'r') as f:
    Area = json.load(f)

# 空調運転モード
with open(directory + 'ACoperationMode.json', 'r') as f:
    ACoperationMode = json.load(f)


mxTH_min = Area[inputdata["Building"]["Region"]+"地域"]["暖房時外気温下限"]
mxTH_max = Area[inputdata["Building"]["Region"]+"地域"]["暖房時外気温上限"]
mxTC_min = Area[inputdata["Building"]["Region"]+"地域"]["冷房時外気温下限"]
mxTC_max = Area[inputdata["Building"]["Region"]+"地域"]["冷房時外気温上限"]

delTC = (mxTC_max - mxTC_min)/divT
delTH = (mxTH_max - mxTH_min)/divT

mxTC = np.arange(mxTC_min+delTC, mxTC_max+delTC, delTC)
mxTH = np.arange(mxTH_min+delTH, mxTH_max+delTH, delTH)

ToadbC = mxTC - delTC/2
ToadbH = mxTH - delTH/2

# 湿球温度
ToawbC = Area[inputdata["Building"]["Region"]+"地域"]["湿球温度係数_冷房a1"] * ToadbC + Area[inputdata["Building"]["Region"]+"地域"]["湿球温度係数_冷房a0"]
ToawbH = Area[inputdata["Building"]["Region"]+"地域"]["湿球温度係数_暖房a1"] * ToadbH + Area[inputdata["Building"]["Region"]+"地域"]["湿球温度係数_暖房a0"]

TctwC  = ToawbC + 3  # 冷却水温度 [℃]
TctwH  = 15.5 * np.ones(6)  #  水冷式の暖房時熱源水温度（暫定） [℃]



#%%
##----------------------------------------------------------------------------------
## 気象データ（解説書 2.2.1）
##----------------------------------------------------------------------------------

# 気象データ（HASP形式）読み込み ＜365×24の行列＞
[ToutALL, XoutALL, IodALL, IosALL, InnALL] = \
    climate.readHaspClimateData( directory + "climatedata/C1_" + Area[inputdata["Building"]["Region"]+"地域"]["気象データファイル名"] )

# 緯度
phi  = Area[inputdata["Building"]["Region"]+"地域"]["緯度"]
# 経度
longi  = Area[inputdata["Building"]["Region"]+"地域"]["経度"]


##----------------------------------------------------------------------------------
## 冷暖房期間（解説書 2.2.2）
##----------------------------------------------------------------------------------

# 各日の冷暖房期間の種類（冷房期、暖房期、中間期）（365×1の行列）
ac_mode = ACoperationMode[ Area[inputdata["Building"]["Region"]+"地域"]["空調運転モードタイプ"] ]


##----------------------------------------------------------------------------------
## 平均外気温（解説書 2.2.3）
##----------------------------------------------------------------------------------

# 日平均外気温[℃]（365×1）
Toa_ave = np.mean(ToutALL,1)
Toa_day = np.mean(ToutALL[:,[6,7,8,9,10,11,12,13,14,15,16,17]],1)
Toa_ngt = np.mean(ToutALL[:,[0,1,2,3,4,5,18,19,20,21,22,23]],1)

# 日平均外気絶対湿度 [kg/kgDA]（365×1）
Xoa_ave = np.mean(XoutALL,1)
Xoa_day = np.mean(XoutALL[:,[6,7,8,9,10,11,12,13,14,15,16,17]],1)
Xoa_ngt = np.mean(XoutALL[:,[0,1,2,3,4,5,18,19,20,21,22,23]],1)


##----------------------------------------------------------------------------------
## 外気エンタルピー（解説書 2.2.4）
##----------------------------------------------------------------------------------

Hoa_ave = bc.air_enenthalpy(Toa_ave, Xoa_ave)
Hoa_day = bc.air_enenthalpy(Toa_day, Xoa_day)
Hoa_ngt = bc.air_enenthalpy(Toa_ngt, Xoa_ngt)



#%%
##----------------------------------------------------------------------------------
## 空調室の設定温度、室内エンタルピー（解説書 2.3.1、2.3.2）
##----------------------------------------------------------------------------------

TroomSP = np.zeros(365)    # 室内設定温度
RroomSP = np.zeros(365)    # 室内設定湿度
Hroom   = np.zeros(365)    # 室内設定エンタルピー

for dd in range(0,365):

    if ac_mode[dd] == "冷房":
        TroomSP[dd] = 26
        RroomSP[dd] = 50
        Hroom[dd] = 52.91

    elif ac_mode[dd] == "中間":
        TroomSP[dd] = 24
        RroomSP[dd] = 50
        Hroom[dd] = 47.81

    elif ac_mode[dd] == "暖房":
        TroomSP[dd] = 22
        RroomSP[dd] = 40
        Hroom[dd] = 38.81


##----------------------------------------------------------------------------------
## 空調機の稼働状態、内部発熱量（解説書 2.3.3、2.3.4）
##----------------------------------------------------------------------------------

roomAreaTotal = 0
roomScheduleRoom   = {}
roomScheduleLight  = {}
roomSchedulePerson = {}
roomScheduleOAapp  = {}
roomDayMode        = {}

# 空調ゾーン毎にループ
for room_zone_name in inputdata["AirConditioningZone"].keys():

    if room_zone_name in inputdata["Rooms"]:  # ゾーン分けがない場合

        # 建物用途・室用途、ゾーン面積等の取得
        inputdata["AirConditioningZone"][room_zone_name]["buildingType"] = inputdata["Rooms"][room_zone_name]["buildingType"]
        inputdata["AirConditioningZone"][room_zone_name]["roomType"]     = inputdata["Rooms"][room_zone_name]["roomType"]
        inputdata["AirConditioningZone"][room_zone_name]["zoneArea"]     = inputdata["Rooms"][room_zone_name]["roomArea"]
            
    else:

        # 各室のゾーンを検索
        for room_name in inputdata["Rooms"]:
            if inputdata["Rooms"][room_name]["zone"] != None:   # ゾーンがあれば
                for zone_name  in inputdata["Rooms"][room_name]["zone"]:   # ゾーン名を検索
                    if room_zone_name == (room_name+"_"+zone_name):

                        inputdata["AirConditioningZone"][room_zone_name]["buildingType"] = inputdata["Rooms"][room_name]["buildingType"]
                        inputdata["AirConditioningZone"][room_zone_name]["roomType"]     = inputdata["Rooms"][room_name]["roomType"]
                        inputdata["AirConditioningZone"][room_zone_name]["zoneArea"]     = inputdata["Rooms"][room_name]["zone"][zone_name]["zoneArea"]

                        break

    # 365日×24時間分のスケジュール （365×24の行列を格納した dict型）
    roomScheduleRoom[room_zone_name], roomScheduleLight[room_zone_name], roomSchedulePerson[room_zone_name], roomScheduleOAapp[room_zone_name], roomDayMode[room_zone_name] = \
        bc.get_roomUsageSchedule(inputdata["AirConditioningZone"][room_zone_name]["buildingType"], inputdata["AirConditioningZone"][room_zone_name]["roomType"])


    # 空調対象面積の合計
    roomAreaTotal += inputdata["AirConditioningZone"][room_zone_name]["zoneArea"]







#%%
##----------------------------------------------------------------------------------
## 外皮面への入射日射量（解説書 2.4.1）
##----------------------------------------------------------------------------------

solor_radiation = {
    "直達":{
    },
    "直達_入射角特性込":{
    },
    "天空":{
    },
    "夜間":{
    }
}

# 方位角別の日射量
(solor_radiation["直達"]["南"],  solor_radiation["直達_入射角特性込"]["南"], solor_radiation["天空"]["垂直"], solor_radiation["夜間"]["垂直"])  = \
    climate.solarRadiationByAzimuth(  0, 90, phi, longi, IodALL, IosALL, InnALL)
(solor_radiation["直達"]["南西"], solor_radiation["直達_入射角特性込"]["南西"], _, _) = climate.solarRadiationByAzimuth( 45, 90, phi, longi, IodALL, IosALL, InnALL)
(solor_radiation["直達"]["西"],  solor_radiation["直達_入射角特性込"]["西"], _, _)  = climate.solarRadiationByAzimuth( 90, 90, phi, longi, IodALL, IosALL, InnALL)
(solor_radiation["直達"]["北西"], solor_radiation["直達_入射角特性込"]["北西"], _, _) = climate.solarRadiationByAzimuth(135, 90, phi, longi, IodALL, IosALL, InnALL)
(solor_radiation["直達"]["北"],  solor_radiation["直達_入射角特性込"]["北"], _, _)  = climate.solarRadiationByAzimuth(180, 90, phi, longi, IodALL, IosALL, InnALL)
(solor_radiation["直達"]["北東"], solor_radiation["直達_入射角特性込"]["北東"], _, _) = climate.solarRadiationByAzimuth(225, 90, phi, longi, IodALL, IosALL, InnALL)
(solor_radiation["直達"]["東"],  solor_radiation["直達_入射角特性込"]["東"], _, _)  = climate.solarRadiationByAzimuth(270, 90, phi, longi, IodALL, IosALL, InnALL)
(solor_radiation["直達"]["南東"], solor_radiation["直達_入射角特性込"]["南東"], _, _) = climate.solarRadiationByAzimuth(315, 90, phi, longi, IodALL, IosALL, InnALL)
(solor_radiation["直達"]["水平"], solor_radiation["直達_入射角特性込"]["水平"], solor_radiation["天空"]["水平"], solor_radiation["夜間"]["水平"])  = \
    climate.solarRadiationByAzimuth(  0,  0, phi, longi, IodALL, IosALL, InnALL)



#%%
##----------------------------------------------------------------------------------
## 外壁等の熱貫流率の算出（解説書 附属書A.1）
##----------------------------------------------------------------------------------

### ISSUE : 二つのデータベースにわかれてしまっているので統一する。###

# 標準入力法建材データの読み込み
with open(directory + 'HeatThermalConductivity.json', 'r') as f:
    HeatThermalConductivity = json.load(f)

# モデル建物法建材データの読み込み
with open(directory + 'HeatThermalConductivity_model.json', 'r') as f:
    HeatThermalConductivity_model = json.load(f)


if "WallConfigure" in inputdata:  # WallConfigure があれば以下を実行

    for wall_name in inputdata["WallConfigure"].keys():

        if inputdata["WallConfigure"][wall_name]["inputMethod"] == "断熱材種類を入力":

            if inputdata["WallConfigure"][wall_name]["materialID"] == "無": # 断熱材種類が「無」の場合

                inputdata["WallConfigure"][wall_name]["Uvalue_wall"]  = 2.63
                inputdata["WallConfigure"][wall_name]["Uvalue_roof"]  = 1.53
                inputdata["WallConfigure"][wall_name]["Uvalue_floor"] = 2.67

            else: # 断熱材種類が「無」以外、もしくは、熱伝導率が直接入力されている場合

                # 熱伝導率の指定がない場合は「断熱材種類」から推定
                if (inputdata["WallConfigure"][wall_name]["conductivity"] == None):
                    
                    inputdata["WallConfigure"][wall_name]["conductivity"] = \
                        float( HeatThermalConductivity_model[ inputdata["WallConfigure"][wall_name]["materialID"] ] )

                # 熱伝導率と厚みとから、熱貫流率を計算（３種類）
                inputdata["WallConfigure"][wall_name]["Uvalue_wall"] = \
                    0.663 * (inputdata["WallConfigure"][wall_name]["thickness"] / 1000 / inputdata["WallConfigure"][wall_name]["conductivity"]) ** (-0.638)
                inputdata["WallConfigure"][wall_name]["Uvalue_roof"] = \
                    0.548 * (inputdata["WallConfigure"][wall_name]["thickness"] / 1000 / inputdata["WallConfigure"][wall_name]["conductivity"]) ** (-0.524)
                inputdata["WallConfigure"][wall_name]["Uvalue_floor"] = \
                    0.665 * (inputdata["WallConfigure"][wall_name]["thickness"] / 1000 / inputdata["WallConfigure"][wall_name]["conductivity"]) ** (-0.641)


        elif inputdata["WallConfigure"][wall_name]["inputMethod"] == "建材構成を入力":

            Rvalue = 0.11 + 0.04

            for layer in enumerate(inputdata["WallConfigure"][wall_name]["layers"]):

                # 熱伝導率が空欄である場合、建材名称から熱伝導率を見出す。
                if layer[1]["conductivity"] == None:

                    if (layer[1]["materialID"] == "密閉中空層") or (layer[1]["materialID"] == "非密閉中空層"):

                        # 空気層の場合
                        Rvalue += HeatThermalConductivity[layer[1]["materialID"]]["熱抵抗値"]
            
                    else:

                        # 空気層以外の断熱材を指定している場合
                        Rvalue += (layer[1]["thickness"]/1000) / HeatThermalConductivity[layer[1]["materialID"]]["熱伝導率"]

                else:

                    # 熱伝達率を入力している場合
                    Rvalue += (layer[1]["thickness"]/1000) / layer[1]["conductivity"]
                
            inputdata["WallConfigure"][wall_name]["Uvalue"] = 1/Rvalue


#%%
##----------------------------------------------------------------------------------
## 窓の熱貫流率及び日射熱取得率の算出（解説書 附属書A.2）
##----------------------------------------------------------------------------------

# 窓データの読み込み
with open(directory + 'WindowHeatTransferPerformance.json', 'r') as f:
    WindowHeatTransferPerformance = json.load(f)

with open(directory + 'glass2window.json', 'r') as f:
    glass2window = json.load(f)


if "WindowConfigure" in inputdata:

    for window_name in inputdata["WindowConfigure"].keys():

        if inputdata["WindowConfigure"][window_name]["inputMethod"] == "ガラスの種類を入力":

            # 建具の種類の読み替え
            if inputdata["WindowConfigure"][window_name]["frameType"] == "木製" or \
                inputdata["WindowConfigure"][window_name]["frameType"] == "樹脂製":

                inputdata["WindowConfigure"][window_name]["frameType"] = "木製・樹脂製建具"

            elif inputdata["WindowConfigure"][window_name]["frameType"] == "金属木複合製" or \
                inputdata["WindowConfigure"][window_name]["frameType"] == "金属樹脂複合製":

                inputdata["WindowConfigure"][window_name]["frameType"] = "金属木複合製・金属樹脂複合製建具"
            
            elif inputdata["WindowConfigure"][window_name]["frameType"] == "金属製":

                inputdata["WindowConfigure"][window_name]["frameType"] = "金属製建具"


            # ガラスIDと建具の種類から、熱貫流率・日射熱取得率を抜き出す。
            inputdata["WindowConfigure"][window_name]["Uvalue"] = \
            WindowHeatTransferPerformance\
                [ inputdata["WindowConfigure"][window_name]["glassID"] ]\
                [ inputdata["WindowConfigure"][window_name]["frameType"] ]["熱貫流率"]

            inputdata["WindowConfigure"][window_name]["Uvalue_blind"] = \
            WindowHeatTransferPerformance\
                [ inputdata["WindowConfigure"][window_name]["glassID"] ]\
                [ inputdata["WindowConfigure"][window_name]["frameType"] ]["熱貫流率・ブラインド込"]

            inputdata["WindowConfigure"][window_name]["Ivalue"] = \
            WindowHeatTransferPerformance\
                [ inputdata["WindowConfigure"][window_name]["glassID"] ]\
                [ inputdata["WindowConfigure"][window_name]["frameType"] ]["日射熱取得率"]

            inputdata["WindowConfigure"][window_name]["Ivalue_blind"] = \
            WindowHeatTransferPerformance\
                [ inputdata["WindowConfigure"][window_name]["glassID"] ]\
                [ inputdata["WindowConfigure"][window_name]["frameType"] ]["日射熱取得率・ブラインド込"]


        elif inputdata["WindowConfigure"][window_name]["inputMethod"] == "ガラスの性能を入力":

            ku_a = 0
            ku_b = 0
            kita  = 0
            dR = 0

            # 建具の種類の読み替え
            if inputdata["WindowConfigure"][window_name]["frameType"] == "木製" or \
                inputdata["WindowConfigure"][window_name]["frameType"] == "樹脂製":

                inputdata["WindowConfigure"][window_name]["frameType"] = "木製・樹脂製建具"

            elif inputdata["WindowConfigure"][window_name]["frameType"] == "金属木複合製" or \
                inputdata["WindowConfigure"][window_name]["frameType"] == "金属樹脂複合製":

                inputdata["WindowConfigure"][window_name]["frameType"] = "金属木複合製・金属樹脂複合製建具"
            
            elif inputdata["WindowConfigure"][window_name]["frameType"] == "金属製":

                inputdata["WindowConfigure"][window_name]["frameType"] = "金属製建具"


            # 変換係数
            ku_a = glass2window[inputdata["WindowConfigure"][window_name]["frameType"]][inputdata["WindowConfigure"][window_name]["layerType"]]["ku_a1"] \
                / glass2window[inputdata["WindowConfigure"][window_name]["frameType"]][inputdata["WindowConfigure"][window_name]["layerType"]]["ku_a2"]
            ku_b = glass2window[inputdata["WindowConfigure"][window_name]["frameType"]][inputdata["WindowConfigure"][window_name]["layerType"]]["ku_b1"] \
                / glass2window[inputdata["WindowConfigure"][window_name]["frameType"]][inputdata["WindowConfigure"][window_name]["layerType"]]["ku_b2"]
            kita  = glass2window[inputdata["WindowConfigure"][window_name]["frameType"]][inputdata["WindowConfigure"][window_name]["layerType"]]["kita"]            

            inputdata["WindowConfigure"][window_name]["Uvalue"] = ku_a * inputdata["WindowConfigure"][window_name]["glassUvalue"] + ku_b
            inputdata["WindowConfigure"][window_name]["Ivalue"] = kita * inputdata["WindowConfigure"][window_name]["glassIvalue"]

            # ガラスの熱貫流率と日射熱取得率が入力されている場合は、ブラインドの効果を見込む
            dR = (0.021 / inputdata["WindowConfigure"][window_name]["glassUvalue"]) + 0.022

            inputdata["WindowConfigure"][window_name]["Uvalue_blind"] = \
                1 / ( ( 1/inputdata["WindowConfigure"][window_name]["Uvalue"]) + dR )

            inputdata["WindowConfigure"][window_name]["Ivalue_blind"] = \
                inputdata["WindowConfigure"][window_name]["Ivalue"] / inputdata["WindowConfigure"][window_name]["glassIvalue"] \
                    * (-0.1331 * inputdata["WindowConfigure"][window_name]["glassIvalue"] ** 2 +\
                            0.8258 * inputdata["WindowConfigure"][window_name]["glassIvalue"] )


        elif inputdata["WindowConfigure"][window_name]["inputMethod"] == "性能値を入力":

            inputdata["WindowConfigure"][window_name]["Uvalue"] = inputdata["WindowConfigure"][window_name]["windowUvalue"]
            inputdata["WindowConfigure"][window_name]["Ivalue"] = inputdata["WindowConfigure"][window_name]["windowIvalue"]

            # ブラインド込みの値を計算
            dR = 0

            if inputdata["WindowConfigure"][window_name]["glassUvalue"] == None or \
                inputdata["WindowConfigure"][window_name]["glassIvalue"] == None:

                inputdata["WindowConfigure"][window_name]["Uvalue_blind"] = inputdata["WindowConfigure"][window_name]["windowUvalue"]
                inputdata["WindowConfigure"][window_name]["Ivalue_blind"] = inputdata["WindowConfigure"][window_name]["windowIvalue"]

            else:
                # ガラスの熱貫流率と日射熱取得率が入力されている場合は、ブラインドの効果を見込む
                dR = (0.021 / inputdata["WindowConfigure"][window_name]["glassUvalue"]) + 0.022

                inputdata["WindowConfigure"][window_name]["Uvalue_blind"] = \
                    1 / ( ( 1/inputdata["WindowConfigure"][window_name]["windowUvalue"]) + dR )

                inputdata["WindowConfigure"][window_name]["Ivalue_blind"] = \
                    inputdata["WindowConfigure"][window_name]["windowIvalue"] / inputdata["WindowConfigure"][window_name]["glassIvalue"] \
                        * (-0.1331 * inputdata["WindowConfigure"][window_name]["glassIvalue"] ** 2 +\
                             0.8258 * inputdata["WindowConfigure"][window_name]["glassIvalue"] )


#%%
##----------------------------------------------------------------------------------
## 外壁の面積の計算（解説書 2.4.2.1）
##----------------------------------------------------------------------------------

# 外皮面積の算出
for room_zone_name in inputdata["EnvelopeSet"]:

    for wall_id, wall_configure in enumerate(inputdata["EnvelopeSet"][room_zone_name]["WallList"]):
        
        if inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["EnvelopeArea"] == None:  # 外皮面積が空欄であれば、外皮の寸法から面積を計算。

            inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["EnvelopeArea"] = \
                wall_configure["EnvelopeWidth"] * wall_configure["EnvelopeHeight"]

# 窓面積の算出
for window_id in inputdata["WindowConfigure"]:
    if inputdata["WindowConfigure"][window_id]["windowArea"] == None:  # 窓面積が空欄であれば、窓寸法から面積を計算。
        inputdata["WindowConfigure"][window_id]["windowArea"] = \
            inputdata["WindowConfigure"][window_id]["windowWidth"] * inputdata["WindowConfigure"][window_id]["windowHeight"]


# 外壁面積の算出
for room_zone_name in inputdata["EnvelopeSet"]:

    for (wall_id, wall_configure) in enumerate( inputdata["EnvelopeSet"][room_zone_name]["WallList"] ):

        window_total = 0  # 窓面積の集計用

        if "WindowList" in wall_configure:   # 窓がある場合

            # 窓面積の合計を求める（Σ{窓面積×枚数}）
            for (window_id, window_configure) in enumerate(wall_configure["WindowList"]):

                if window_configure["WindowID"] != "無":

                    window_total += \
                        inputdata["WindowConfigure"][ window_configure["WindowID"] ]["windowArea"] * window_configure["WindowNumber"]


        # 壁のみの面積（窓がない場合は、window_total = 0）
        if wall_configure["EnvelopeArea"] > window_total:
            inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["WallArea"] = wall_configure["EnvelopeArea"] - window_total
        else:
            print(room_zone_name)
            print(wall_configure)
            raise Exception('窓面積が外皮面積よりも大きくなっています')



#%%
##----------------------------------------------------------------------------------
## 室の定常熱取得の計算（解説書 2.4.2.2〜2.4.2.7）
##----------------------------------------------------------------------------------

## EnvelopeSet に WallConfigure, WindowConfigure の情報を貼り付ける。
for room_zone_name in inputdata["EnvelopeSet"]:

    # 壁毎にループ
    for (wall_id, wall_configure) in enumerate( inputdata["EnvelopeSet"][room_zone_name]["WallList"]):

        if inputdata["WallConfigure"][  wall_configure["WallSpec"]  ]["inputMethod"] == "断熱材種類を入力":

            if wall_configure["Direction"] == "水平（上）":  # 天井と見なす。

                # 外壁のUA（熱貫流率×面積）を計算
                inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["UA_wall"] = \
                    inputdata["WallConfigure"][  wall_configure["WallSpec"]  ]["Uvalue_roof"] * wall_configure["WallArea"]

            elif wall_configure["Direction"] == "水平（下）":  # 床と見なす。

                # 外壁のUA（熱貫流率×面積）を計算
                inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["UA_wall"] = \
                    inputdata["WallConfigure"][  wall_configure["WallSpec"]  ]["Uvalue_floor"] * wall_configure["WallArea"]

            else:

                # 外壁のUA（熱貫流率×面積）を計算
                inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["UA_wall"] = \
                    inputdata["WallConfigure"][  wall_configure["WallSpec"]  ]["Uvalue_wall"] * wall_configure["WallArea"]

        else:

            # 外壁のUA（熱貫流率×面積）を計算
            inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["UA_wall"] = \
                inputdata["WallConfigure"][  wall_configure["WallSpec"]  ]["Uvalue"] * wall_configure["WallArea"]


        for (window_id, window_configure) in enumerate( inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["WindowList"]):

            if window_configure["WindowID"] != "無":

                # 日よけ効果係数の算出
                if window_configure["EavesID"] == "無":

                    inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["WindowList"][window_id]["shadingEffect_C"] = 1
                    inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["WindowList"][window_id]["shadingEffect_H"] = 1

                else:

                    if inputdata["ShadingConfigure"][ window_configure["EavesID"] ]["shadingEffect_C"] != None and \
                        inputdata["ShadingConfigure"][ window_configure["EavesID"] ]["shadingEffect_H"] != None :

                        inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["WindowList"][window_id]["shadingEffect_C"] = \
                            inputdata["ShadingConfigure"][ window_configure["EavesID"] ]["shadingEffect_C"]
                        inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["WindowList"][window_id]["shadingEffect_H"] = \
                            inputdata["ShadingConfigure"][ window_configure["EavesID"] ]["shadingEffect_H"]

                    else:

                        # 関数 shading.calc_shadingCoefficient で日よけ効果係数を算出。
                        (inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["WindowList"][window_id]["shadingEffect_C"], \
                            inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["WindowList"][window_id]["shadingEffect_H"] ) =  \
                                shading.calc_shadingCoefficient(inputdata["Building"]["Region"],\
                                    wall_configure["Direction"], \
                                    inputdata["ShadingConfigure"][ window_configure["EavesID"] ]["x1"],\
                                    inputdata["ShadingConfigure"][ window_configure["EavesID"] ]["x2"],\
                                    inputdata["ShadingConfigure"][ window_configure["EavesID"] ]["x3"],\
                                    inputdata["ShadingConfigure"][ window_configure["EavesID"] ]["y1"],\
                                    inputdata["ShadingConfigure"][ window_configure["EavesID"] ]["y2"],\
                                    inputdata["ShadingConfigure"][ window_configure["EavesID"] ]["y3"],\
                                    inputdata["ShadingConfigure"][ window_configure["EavesID"] ]["zxPlus"],\
                                    inputdata["ShadingConfigure"][ window_configure["EavesID"] ]["zxMinus"],\
                                    inputdata["ShadingConfigure"][ window_configure["EavesID"] ]["zyPlus"],\
                                    inputdata["ShadingConfigure"][ window_configure["EavesID"] ]["zyMinus"])


                # 窓のUA（熱貫流率×面積）を計算
                if window_configure["isBlind"] == "無":  # ブラインドがない場合

                    inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["WindowList"][window_id]["UA_window"] = \
                        window_configure["WindowNumber"] * inputdata["WindowConfigure"][ window_configure["WindowID"] ]["windowArea"] * \
                        inputdata["WindowConfigure"][ window_configure["WindowID"] ]["Uvalue"]

                    inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["WindowList"][window_id]["IA_window"] = \
                        window_configure["WindowNumber"] * inputdata["WindowConfigure"][ window_configure["WindowID"] ]["windowArea"] * \
                        inputdata["WindowConfigure"][ window_configure["WindowID"] ]["Ivalue"]


                elif window_configure["isBlind"] == "有": # ブラインドがある場合

                    inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["WindowList"][window_id]["UA_window"] = \
                        window_configure["WindowNumber"] * inputdata["WindowConfigure"][ window_configure["WindowID"] ]["windowArea"] * \
                        inputdata["WindowConfigure"][ window_configure["WindowID"] ]["Uvalue_blind"]

                    inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["WindowList"][window_id]["IA_window"] = \
                        window_configure["WindowNumber"] * inputdata["WindowConfigure"][ window_configure["WindowID"] ]["windowArea"] * \
                        inputdata["WindowConfigure"][ window_configure["WindowID"] ]["Ivalue_blind"]



for room_zone_name in inputdata["AirConditioningZone"]:

    Qwall_T  = np.zeros(365)  # 壁からの温度差による熱取得 [W/m2]
    Qwall_S  = np.zeros(365)  # 壁からの日射による熱取得 [W/m2]
    Qwall_N  = np.zeros(365)  # 壁からの夜間放射による熱取得（マイナス）[W/m2]
    Qwind_T  = np.zeros(365)  # 窓からの温度差による熱取得 [W/m2]
    Qwind_S  = np.zeros(365)  # 窓からの日射による熱取得 [W/m2]
    Qwind_N  = np.zeros(365)  # 窓からの夜間放射による熱取得（マイナス）[W/m2]

    resultJson["Qroom"][room_zone_name] = {}

    # 外壁があれば以下を実行
    if room_zone_name in inputdata["EnvelopeSet"]:

        # 壁毎にループ
        for (wall_id, wall_configure) in enumerate( inputdata["EnvelopeSet"][room_zone_name]["WallList"]):

            if wall_configure["WallType"] == "日の当たる外壁":
            
                ## ① 温度差による熱取得
                Qwall_T = Qwall_T + wall_configure["UA_wall"] * (Toa_ave - TroomSP) * 24

                ## ② 日射による熱取得
                if wall_configure["Direction"] == "水平（上）" or wall_configure["Direction"] == "水平（下）":
                    Qwall_S = Qwall_S + wall_configure["UA_wall"] * 0.8 * 0.04 * \
                        (solor_radiation["直達"]["水平"]+solor_radiation["天空"]["水平"])
                else:
                    Qwall_S = Qwall_S + wall_configure["UA_wall"] * 0.8 * 0.04 * \
                        (solor_radiation["直達"][ wall_configure["Direction"] ]+solor_radiation["天空"]["垂直"])

                ## ③ 夜間放射による熱取得（マイナス）
                if wall_configure["Direction"] == "水平（上）" or wall_configure["Direction"] == "水平（下）":
                    Qwall_N = Qwall_N - wall_configure["UA_wall"] * 0.9 * 0.04 * \
                        (solor_radiation["夜間"]["水平"])
                else:
                    Qwall_N = Qwall_N - wall_configure["UA_wall"] * 0.9 * 0.04 * \
                        (solor_radiation["夜間"]["垂直"])                    

            elif wall_configure["WallType"] == "日の当たらない外壁":

                ## ① 温度差による熱取得
                Qwall_T = Qwall_T + wall_configure["UA_wall"] * (Toa_ave - TroomSP) * 24

                ## ③ 夜間放射による熱取得（マイナス）
                if wall_configure["Direction"] == "水平（上）" or wall_configure["Direction"] == "水平（下）":
                    Qwall_N = Qwall_N - wall_configure["UA_wall"] * 0.9 * 0.04 * \
                        (solor_radiation["夜間"]["水平"])
                else:
                    Qwall_N = Qwall_N - wall_configure["UA_wall"] * 0.9 * 0.04 * \
                        (solor_radiation["夜間"]["垂直"])                    

            elif wall_configure["WallType"] == "地盤に接する外壁":
            
                ## ① 温度差による熱取得
                Qwall_T = Qwall_T + wall_configure["UA_wall"] * (np.mean(Toa_ave)* np.ones(365) - TroomSP) * 24


            # 窓毎にループ
            for (window_id, window_configure) in enumerate( wall_configure["WindowList"]):

                if window_configure["WindowID"] != "無":  # 窓がある場合

                    if wall_configure["WallType"] == "日の当たる外壁":
                    
                        ## ① 温度差による熱取得
                        Qwind_T = Qwind_T + window_configure["UA_window"]*(Toa_ave-TroomSP)*24

                        ## ② 日射による熱取得
                        shading_daily = np.zeros(365)

                        for dd in range(0,365):

                            if ac_mode[dd] == "冷房":
                                shading_daily[dd] = window_configure["shadingEffect_C"]
                            elif ac_mode[dd] == "中間":
                                shading_daily[dd] = window_configure["shadingEffect_C"]
                            elif ac_mode[dd] == "暖房":
                                shading_daily[dd] = window_configure["shadingEffect_H"]
                                
                        if wall_configure["Direction"] == "水平（上）" or wall_configure["Direction"] == "水平（下）":

                            Qwind_S = Qwind_S + shading_daily * \
                                (window_configure["IA_window"] / 0.88) * \
                                (solor_radiation["直達_入射角特性込"]["水平"]*0.89 + solor_radiation["天空"]["水平"]*0.808)

                        else:

                            Qwind_S = Qwind_S + shading_daily * \
                                (window_configure["IA_window"] / 0.88) * \
                                (solor_radiation["直達_入射角特性込"][ wall_configure["Direction"] ]*0.89 + solor_radiation["天空"]["垂直"]*0.808)


                        ## ③ 夜間放射による熱取得（マイナス）
                        if wall_configure["Direction"] == "水平（上）" or wall_configure["Direction"] == "水平（下）":
                            Qwind_N = Qwind_N - window_configure["UA_window"] * 0.9 * 0.04 * solor_radiation["夜間"]["水平"]
                        else:
                            Qwind_N = Qwind_N - window_configure["UA_window"] * 0.9 * 0.04 * solor_radiation["夜間"]["垂直"]


                    elif wall_configure["WallType"] == "日の当たらない外壁":

                        ## ③ 夜間放射による熱取得（マイナス）
                        Qwind_N = Qwind_N - window_configure["UA_window"] * 0.9 * 0.04 * solor_radiation["夜間"]["水平"]


    resultJson["Qroom"][room_zone_name]["Qwall_T"] = Qwall_T / inputdata["AirConditioningZone"][room_zone_name]["zoneArea"]
    resultJson["Qroom"][room_zone_name]["Qwall_S"] = Qwall_S / inputdata["AirConditioningZone"][room_zone_name]["zoneArea"]
    resultJson["Qroom"][room_zone_name]["Qwall_N"] = Qwall_N / inputdata["AirConditioningZone"][room_zone_name]["zoneArea"]
    resultJson["Qroom"][room_zone_name]["Qwind_T"] = Qwind_T / inputdata["AirConditioningZone"][room_zone_name]["zoneArea"]
    resultJson["Qroom"][room_zone_name]["Qwind_S"] = Qwind_S / inputdata["AirConditioningZone"][room_zone_name]["zoneArea"]
    resultJson["Qroom"][room_zone_name]["Qwind_N"] = Qwind_N / inputdata["AirConditioningZone"][room_zone_name]["zoneArea"]



##----------------------------------------------------------------------------------
## 室負荷の計算（解説書 2.4.3、2.4.4）
##----------------------------------------------------------------------------------

## 室負荷計算のための係数（解説書 A.3）
with open(directory + 'QROOM_COEFFI_AREA'+ inputdata["Building"]["Region"] +'.json', 'r') as f:
    QROOM_COEFFI = json.load(f)


for room_zone_name in inputdata["AirConditioningZone"]:

    Qroom_CTC = np.zeros(365)
    Qroom_CTH = np.zeros(365)
    Qroom_CSR = np.zeros(365)

    Qcool     = np.zeros(365)
    Qheat     = np.zeros(365)

    # 室が使用されているか否か＝空調運転時間（365日分）
    room_usage = np.sum(roomScheduleRoom[room_zone_name],1)

    btype = inputdata["AirConditioningZone"][room_zone_name]["buildingType"]
    rtype = inputdata["AirConditioningZone"][room_zone_name]["roomType"]

    # 発熱量参照値を読み込む関数（空調）
    (roomHeatGain_Light, roomHeatGain_Person, roomHeatGain_OAapp) = bc.get_roomHeatGain(btype, rtype)

    Heat_light_daily  = np.sum(roomScheduleLight[room_zone_name],1) * roomHeatGain_Light   # 照明からの発熱（日積算）（365日分）
    Heat_person_daily = np.sum(roomSchedulePerson[room_zone_name],1) * roomHeatGain_Person # 人体からの発熱（日積算）（365日分）
    Heat_OAapp_daily  = np.sum(roomScheduleOAapp[room_zone_name],1) * roomHeatGain_OAapp   # 機器からの発熱（日積算）（365日分）

    for dd in range(0,365):

        if room_usage[dd] > 0:

            # 前日の空調の有無
            if "終日空調" in QROOM_COEFFI[ btype ][ rtype ]:
                onoff = "終日空調"
            elif (dd > 0) and (room_usage[dd-1] > 0):
                onoff = "前日空調"
            else:
                onoff = "前日休み"

            if ac_mode[dd] == "冷房":

                Qroom_CTC[dd] = QROOM_COEFFI[ btype ][ rtype ][onoff]["冷房期"]["外気温変動"]["冷房負荷"]["係数"] * \
                    ( resultJson["Qroom"][room_zone_name]["Qwall_T"][dd] + resultJson["Qroom"][room_zone_name]["Qwall_N"][dd] + \
                    resultJson["Qroom"][room_zone_name]["Qwind_T"][dd] + resultJson["Qroom"][room_zone_name]["Qwind_N"][dd] ) + \
                    QROOM_COEFFI[ btype ][ rtype ][onoff]["冷房期"]["外気温変動"]["冷房負荷"]["補正切片"]

                Qroom_CTH[dd] = QROOM_COEFFI[ btype ][ rtype ][onoff]["冷房期"]["外気温変動"]["暖房負荷"]["係数"] * \
                    ( resultJson["Qroom"][room_zone_name]["Qwall_T"][dd] + resultJson["Qroom"][room_zone_name]["Qwall_N"][dd] + \
                    resultJson["Qroom"][room_zone_name]["Qwind_T"][dd] + resultJson["Qroom"][room_zone_name]["Qwind_N"][dd] ) + \
                    QROOM_COEFFI[ btype ][ rtype ][onoff]["冷房期"]["外気温変動"]["暖房負荷"]["補正切片"]

                Qroom_CSR[dd] = QROOM_COEFFI[ btype ][ rtype ][onoff]["冷房期"]["日射量変動"]["冷房負荷"]["係数"] * \
                    ( resultJson["Qroom"][room_zone_name]["Qwall_S"][dd] + resultJson["Qroom"][room_zone_name]["Qwind_S"][dd] ) + \
                    QROOM_COEFFI[ btype ][ rtype ][onoff]["冷房期"]["日射量変動"]["冷房負荷"]["切片"]

            elif ac_mode[dd] == "暖房":

                Qroom_CTC[dd] = QROOM_COEFFI[ btype ][ rtype ][onoff]["暖房期"]["外気温変動"]["冷房負荷"]["係数"] * \
                    ( resultJson["Qroom"][room_zone_name]["Qwall_T"][dd] + resultJson["Qroom"][room_zone_name]["Qwall_N"][dd] + \
                    resultJson["Qroom"][room_zone_name]["Qwind_T"][dd] + resultJson["Qroom"][room_zone_name]["Qwind_N"][dd] ) + \
                    QROOM_COEFFI[ btype ][ rtype ][onoff]["暖房期"]["外気温変動"]["冷房負荷"]["切片"]

                Qroom_CTH[dd] = QROOM_COEFFI[ btype ][ rtype ][onoff]["暖房期"]["外気温変動"]["暖房負荷"]["係数"] * \
                    ( resultJson["Qroom"][room_zone_name]["Qwall_T"][dd] + resultJson["Qroom"][room_zone_name]["Qwall_N"][dd] + \
                    resultJson["Qroom"][room_zone_name]["Qwind_T"][dd] + resultJson["Qroom"][room_zone_name]["Qwind_N"][dd] ) + \
                    QROOM_COEFFI[ btype ][ rtype ][onoff]["暖房期"]["外気温変動"]["暖房負荷"]["切片"]

                Qroom_CSR[dd] = QROOM_COEFFI[ btype ][ rtype ][onoff]["暖房期"]["日射量変動"]["冷房負荷"]["係数"] * \
                    ( resultJson["Qroom"][room_zone_name]["Qwall_S"][dd] + resultJson["Qroom"][room_zone_name]["Qwind_S"][dd] ) + \
                    QROOM_COEFFI[ btype ][ rtype ][onoff]["暖房期"]["日射量変動"]["冷房負荷"]["切片"]
                    
            elif ac_mode[dd] == "中間":

                Qroom_CTC[dd] = QROOM_COEFFI[ btype ][ rtype ][onoff]["中間期"]["外気温変動"]["冷房負荷"]["係数"] * \
                    ( resultJson["Qroom"][room_zone_name]["Qwall_T"][dd] + resultJson["Qroom"][room_zone_name]["Qwall_N"][dd] + \
                    resultJson["Qroom"][room_zone_name]["Qwind_T"][dd] + resultJson["Qroom"][room_zone_name]["Qwind_N"][dd] ) + \
                    QROOM_COEFFI[ btype ][ rtype ][onoff]["中間期"]["外気温変動"]["冷房負荷"]["補正切片"]

                Qroom_CTH[dd] = QROOM_COEFFI[ btype ][ rtype ][onoff]["中間期"]["外気温変動"]["暖房負荷"]["係数"] * \
                    ( resultJson["Qroom"][room_zone_name]["Qwall_T"][dd] + resultJson["Qroom"][room_zone_name]["Qwall_N"][dd] + \
                    resultJson["Qroom"][room_zone_name]["Qwind_T"][dd] + resultJson["Qroom"][room_zone_name]["Qwind_N"][dd] ) + \
                    QROOM_COEFFI[ btype ][ rtype ][onoff]["中間期"]["外気温変動"]["暖房負荷"]["補正切片"]

                Qroom_CSR[dd] = QROOM_COEFFI[ btype ][ rtype ][onoff]["中間期"]["日射量変動"]["冷房負荷"]["係数"] * \
                    ( resultJson["Qroom"][room_zone_name]["Qwall_S"][dd] + resultJson["Qroom"][room_zone_name]["Qwind_S"][dd] ) + \
                    QROOM_COEFFI[ btype ][ rtype ][onoff]["中間期"]["日射量変動"]["冷房負荷"]["切片"]

            if Qroom_CTC[dd] < 0:
                Qroom_CTC[dd] = 0

            if Qroom_CTH[dd] > 0:
                Qroom_CTH[dd] = 0

            if Qroom_CSR[dd] < 0:
                Qroom_CSR[dd] = 0

            # 日射負荷 Qroom_CSR を暖房負荷 Qroom_CTH に足す
            Qcool[dd] = Qroom_CTC[dd]
            Qheat[dd] = Qroom_CTH[dd] + Qroom_CSR[dd]

            # 日射負荷によって暖房負荷がプラスになった場合は、超過分を冷房負荷に加算
            if Qheat[dd] > 0:
                Qcool[dd] = Qcool[dd] + Qheat[dd]
                Qheat[dd] = 0
            
            # 内部発熱を暖房負荷 Qheat に足す
            Qheat[dd] = Qheat[dd] + ( Heat_light_daily[dd] + Heat_person_daily[dd] + Heat_OAapp_daily[dd] )
            
            # 内部発熱によって暖房負荷がプラスになった場合は、超過分を冷房負荷に加算
            if Qheat[dd] > 0:
                Qcool[dd] = Qcool[dd] + Qheat[dd]
                Qheat[dd] = 0
        
        else:

            # 空調OFF時は 0 とする
            Qcool[dd] = 0
            Qheat[dd] = 0


    resultJson["Qroom"][room_zone_name]["QroomDc"] = Qcool * (3600/1000000) * inputdata["AirConditioningZone"][room_zone_name]["zoneArea"]
    resultJson["Qroom"][room_zone_name]["QroomDh"] = Qheat * (3600/1000000) * inputdata["AirConditioningZone"][room_zone_name]["zoneArea"]


print('室負荷計算完了')


#%%
##----------------------------------------------------------------------------------
## 空調機群の一次エネルギー消費量（解説書 2.5）
##----------------------------------------------------------------------------------

## 結果格納用変数
resultJson["AHU"] = {}

for ahu_name in inputdata["AirHandlingSystem"]:

    resultJson["AHU"][ahu_name] = {
        "HoaDayAve": np.zeros(365),                   
        "schedule": np.zeros((365,24)),    # 時刻別の運転スケジュール（365×24）
        "day_mode": [],                    # 運転時間帯（昼、夜、終日）
        "qoaAHU": np.zeros(365),        # 日平均外気負荷 [kW]
        "Tahu_total": np.zeros(365),       # 空調機の日積算運転時間（冷暖合計）
        "cooling":{
            "QroomAHU": np.zeros(365),     # 日積算室負荷 [MJ/day]
            "Tahu": np.zeros(365),         # 空調機（冷房）運転時間
            "AHUVovc": np.zeros(365),      # 外気冷房風量 [kg/s]
            "Qahu_oac": np.zeros(365),     # 外気冷房効果 [MJ/day]
            "Qahu": np.zeros(365)          # 日積算空調負荷 [MJ/day]
        },
        "heating":{
            "QroomAHU": np.zeros(365),     # 日積算室負荷 [MJ/day]
            "Tahu": np.zeros(365),         # 空調機（暖房）運転時間
            "Qahu": np.zeros(365)          # 日積算空調負荷 [MJ/day]
        }
    }

##----------------------------------------------------------------------------------
## 空調機群が処理する日積算室負荷（解説書 2.5.1）
##----------------------------------------------------------------------------------
for room_zone_name in inputdata["AirConditioningZone"]:

    # 室負荷（冷房）
    resultJson["AHU"][ inputdata["AirConditioningZone"][room_zone_name]["AHU_cooling_insideLoad"] ]["cooling"]["QroomAHU"] += \
        resultJson["Qroom"][room_zone_name]["QroomDc"]

    # 室負荷（暖房）
    resultJson["AHU"][ inputdata["AirConditioningZone"][room_zone_name]["AHU_cooling_insideLoad"] ]["heating"]["QroomAHU"] += \
        resultJson["Qroom"][room_zone_name]["QroomDh"]


##----------------------------------------------------------------------------------
## 空調機群の運転時間（解説書 2.5.2）
##----------------------------------------------------------------------------------

## 各時刻における運転の有無（365×24の行列）
for room_zone_name in inputdata["AirConditioningZone"]:

    # 室の空調有無 roomScheduleRoom（365×24）を加算
    resultJson["AHU"][ inputdata["AirConditioningZone"][room_zone_name]["AHU_cooling_insideLoad"] ]["schedule"] += \
        roomScheduleRoom[room_zone_name]

    # 運転時間帯
    resultJson["AHU"][ inputdata["AirConditioningZone"][room_zone_name]["AHU_cooling_insideLoad"] ]["day_mode"].append( roomDayMode[room_zone_name] )


# 各空調機群の運転時間
for ahu_name in inputdata["AirHandlingSystem"]:

    # 運転スケジュールの和が「1以上（どこか一部屋は動いている）」であれば、空調機は稼働しているとする。
    resultJson["AHU"][ahu_name]["schedule"][   resultJson["AHU"][ahu_name]["schedule"] > 1   ] = 1

    # 空調機群の日積算運転時間（冷暖合計）
    resultJson["AHU"][ahu_name]["Tahu_total"] = np.sum(resultJson["AHU"][ahu_name]["schedule"],1)

    # 空調機の運転モード と　外気エンタルピー
    if "終日" in resultJson["AHU"][ahu_name]["day_mode"]:
        resultJson["AHU"][ahu_name]["day_mode"] = "終日"
        resultJson["AHU"][ahu_name]["HoaDayAve"] = Hoa_ave
    elif resultJson["AHU"][ahu_name]["day_mode"].count("昼") == len(resultJson["AHU"][ahu_name]["day_mode"]):
        resultJson["AHU"][ahu_name]["day_mode"] = "昼"
        resultJson["AHU"][ahu_name]["HoaDayAve"] = Hoa_day
    elif resultJson["AHU"][ahu_name]["day_mode"].count("夜") == len(resultJson["AHU"][ahu_name]["day_mode"]):
        resultJson["AHU"][ahu_name]["day_mode"] = "夜"
        resultJson["AHU"][ahu_name]["HoaDayAve"] = Hoa_ngt
    else:
        resultJson["AHU"][ahu_name]["day_mode"]  = "終日"
        resultJson["AHU"][ahu_name]["HoaDayAve"] = Hoa_ave

    # print(resultJson["AHU"][ahu_name]["day_mode"])


for ahu_name in inputdata["AirHandlingSystem"]:

    for dd in range(0,365):

        if resultJson["AHU"][ahu_name]["Tahu_total"][dd] == 0:

            # 日空調時間が0であれば、冷暖房空調時間は0とする。
            resultJson["AHU"][ahu_name]["cooling"]["Tahu"][dd] = 0
            resultJson["AHU"][ahu_name]["heating"]["Tahu"][dd] = 0

        else:

            if (resultJson["AHU"][ahu_name]["cooling"]["QroomAHU"][dd] == 0) and \
                (resultJson["AHU"][ahu_name]["heating"]["QroomAHU"][dd] == 0):

                # 外調機を想定（空調機は動いているが、冷房のTahuも暖房のTahuも0である場合）
                resultJson["AHU"][ahu_name]["cooling"]["Tahu"][dd] = resultJson["AHU"][ahu_name]["Tahu_total"][dd]   # 外調機の場合は「冷房側」に運転時間を押しつける。
                resultJson["AHU"][ahu_name]["heating"]["Tahu"][dd] = 0
        
            elif resultJson["AHU"][ahu_name]["cooling"]["QroomAHU"][dd] == 0:

                resultJson["AHU"][ahu_name]["cooling"]["Tahu"][dd] = 0
                resultJson["AHU"][ahu_name]["heating"]["Tahu"][dd] = resultJson["AHU"][ahu_name]["Tahu_total"][dd]
    
            elif resultJson["AHU"][ahu_name]["heating"]["QroomAHU"][dd] == 0:

                resultJson["AHU"][ahu_name]["cooling"]["Tahu"][dd] = resultJson["AHU"][ahu_name]["Tahu_total"][dd]
                resultJson["AHU"][ahu_name]["heating"]["Tahu"][dd] = 0

            else:

                if abs(resultJson["AHU"][ahu_name]["cooling"]["QroomAHU"][dd]) < abs(resultJson["AHU"][ahu_name]["heating"]["QroomAHU"][dd]):
                    
                    # 暖房負荷の方が大きい場合
                    ratio = abs(resultJson["AHU"][ahu_name]["cooling"]["QroomAHU"][dd]) / \
                        ( abs(resultJson["AHU"][ahu_name]["cooling"]["QroomAHU"][dd]) + abs(resultJson["AHU"][ahu_name]["heating"]["QroomAHU"][dd]) )

                    resultJson["AHU"][ahu_name]["cooling"]["Tahu"][dd] = math.ceil( resultJson["AHU"][ahu_name]["Tahu_total"][dd] * ratio )
                    resultJson["AHU"][ahu_name]["heating"]["Tahu"][dd] = resultJson["AHU"][ahu_name]["Tahu_total"][dd] - resultJson["AHU"][ahu_name]["cooling"]["Tahu"][dd]

                else:

                    # 冷房負荷の方が大きい場合
                    ratio = abs(resultJson["AHU"][ahu_name]["heating"]["QroomAHU"][dd]) / \
                        ( abs(resultJson["AHU"][ahu_name]["cooling"]["QroomAHU"][dd]) + abs(resultJson["AHU"][ahu_name]["heating"]["QroomAHU"][dd]) )

                    resultJson["AHU"][ahu_name]["heating"]["Tahu"][dd] = math.ceil( resultJson["AHU"][ahu_name]["Tahu_total"][dd] * ratio )
                    resultJson["AHU"][ahu_name]["cooling"]["Tahu"][dd] = resultJson["AHU"][ahu_name]["Tahu_total"][dd] - resultJson["AHU"][ahu_name]["heating"]["Tahu"][dd]


#%%
##----------------------------------------------------------------------------------
## 空調機群全体のスペックを整理する。
##----------------------------------------------------------------------------------

for ahu_name in inputdata["AirHandlingSystem"]:

    # 空調機タイプ（1つでも空調機があれば「空調機」と判断する）
    inputdata["AirHandlingSystem"][ahu_name]["AHU_type"] = "空調機以外"
    for unit_id, unit_configure in enumerate(inputdata["AirHandlingSystem"][ahu_name]["AirHandlingUnit"]):
        if unit_configure["Type"] == "空調機":
            inputdata["AirHandlingSystem"][ahu_name]["AHU_type"] = "空調機"
            break
    
    # 空調機の消費電力
    inputdata["AirHandlingSystem"][ahu_name]["PowerConsumption"] = 0
    for unit_id, unit_configure in enumerate(inputdata["AirHandlingSystem"][ahu_name]["AirHandlingUnit"]):
        if unit_configure["FanPowerConsumption"] != None:
            inputdata["AirHandlingSystem"][ahu_name]["PowerConsumption"] += \
                unit_configure["FanPowerConsumption"] * unit_configure["Number"]

    # 空調機の能力
    inputdata["AirHandlingSystem"][ahu_name]["RatedCapacityCooling"] = 0
    inputdata["AirHandlingSystem"][ahu_name]["RatedCapacityHeating"] = 0
    for unit_id, unit_configure in enumerate(inputdata["AirHandlingSystem"][ahu_name]["AirHandlingUnit"]):
        if unit_configure["RatedCapacityCooling"] != None:
            inputdata["AirHandlingSystem"][ahu_name]["RatedCapacityCooling"] += \
                unit_configure["RatedCapacityCooling"] * unit_configure["Number"]

        if unit_configure["RatedCapacityHeating"] != None:
            inputdata["AirHandlingSystem"][ahu_name]["RatedCapacityHeating"] += \
                unit_configure["RatedCapacityHeating"] * unit_configure["Number"]

    # 空調機の風量 [m3/h]
    inputdata["AirHandlingSystem"][ahu_name]["FanAirVolume"] = 0
    for unit_id, unit_configure in enumerate(inputdata["AirHandlingSystem"][ahu_name]["AirHandlingUnit"]):
        if unit_configure["FanAirVolume"] != None:
            inputdata["AirHandlingSystem"][ahu_name]["FanAirVolume"] += \
                unit_configure["FanAirVolume"] * unit_configure["Number"]
    
    # 全熱交換器の効率（一番低いものを採用）
    inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangeRatioCooling"] = None
    inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangeRatioHeating"] = None

    for unit_id, unit_configure in enumerate(inputdata["AirHandlingSystem"][ahu_name]["AirHandlingUnit"]):

        # 冷房の効率
        if (unit_configure["AirHeatExchangeRatioCooling"] != None):
            if inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangeRatioCooling"] == None:
                inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangeRatioCooling"] = unit_configure["AirHeatExchangeRatioCooling"]
            elif inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangeRatioCooling"] > unit_configure["AirHeatExchangeRatioCooling"]:
                inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangeRatioCooling"] = unit_configure["AirHeatExchangeRatioCooling"]

        # 暖房の効率
        if (unit_configure["AirHeatExchangeRatioHeating"] != None):    
            if inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangeRatioHeating"] == None:
                inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangeRatioHeating"] = unit_configure["AirHeatExchangeRatioHeating"]
            elif inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangeRatioHeating"] > unit_configure["AirHeatExchangeRatioHeating"]:
                inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangeRatioHeating"] = unit_configure["AirHeatExchangeRatioHeating"]

    # 全熱交換器のバイパス制御の有無（1つでもあればバイパス制御「有」とする）
    inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangerControl"] = "無"
    for unit_id, unit_configure in enumerate(inputdata["AirHandlingSystem"][ahu_name]["AirHandlingUnit"]):
        if (unit_configure["AirHeatExchangeRatioCooling"] != None) and (unit_configure["AirHeatExchangeRatioHeating"] != None):
            if unit_configure["AirHeatExchangerControl"] == "有":
                inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangerControl"] = "有"

    # 全熱交換器の消費電力 [kW]
    inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangerPowerConsumption"] = 0
    for unit_id, unit_configure in enumerate(inputdata["AirHandlingSystem"][ahu_name]["AirHandlingUnit"]):
        if unit_configure["AirHeatExchangerPowerConsumption"] != None:
            inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangerPowerConsumption"] += \
                unit_configure["AirHeatExchangerPowerConsumption"] * unit_configure["Number"]

    # 全熱交換器の風量 [m3/h]
    inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangerAirVolume"] = 0
    for unit_id, unit_configure in enumerate(inputdata["AirHandlingSystem"][ahu_name]["AirHandlingUnit"]):
        if (unit_configure["AirHeatExchangeRatioCooling"] != None) and (unit_configure["AirHeatExchangeRatioHeating"] != None):
            inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangerAirVolume"]  += \
                unit_configure["FanAirVolume"] * unit_configure["Number"]


##----------------------------------------------------------------------------------
## 各ゾーンの外気導入量を取得
##----------------------------------------------------------------------------------
# 外気導入量 [m3/h]
for ahu_name in inputdata["AirHandlingSystem"]:
    inputdata["AirHandlingSystem"][ ahu_name ]["outdoorAirVolume_cooling"] = 0
    inputdata["AirHandlingSystem"][ ahu_name ]["outdoorAirVolume_heating"] = 0

for room_zone_name in inputdata["AirConditioningZone"]:

    # 各部屋の外気導入量 [m3/h]
    inputdata["AirConditioningZone"][room_zone_name]["outdoorAirVolume"] = \
        bc.get_roomOutdoorAirVolume( inputdata["AirConditioningZone"][room_zone_name]["buildingType"], inputdata["AirConditioningZone"][room_zone_name]["roomType"] ) * \
        inputdata["AirConditioningZone"][room_zone_name]["zoneArea"]

    # 冷房運転時用 [m3/h]
    inputdata["AirHandlingSystem"][ inputdata["AirConditioningZone"][room_zone_name]["AHU_cooling_outdoorLoad"] ]["outdoorAirVolume_cooling"] += \
        inputdata["AirConditioningZone"][room_zone_name]["outdoorAirVolume"]

    # 暖房運転時用 [m3/h]
    inputdata["AirHandlingSystem"][ inputdata["AirConditioningZone"][room_zone_name]["AHU_heating_outdoorLoad"] ]["outdoorAirVolume_heating"] += \
        inputdata["AirConditioningZone"][room_zone_name]["outdoorAirVolume"]



##----------------------------------------------------------------------------------
## 全熱交換効率の補正（解説書 2.5.3）
##----------------------------------------------------------------------------------

for ahu_name in inputdata["AirHandlingSystem"]:

    # 冷房の補正
    if inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangeRatioCooling"] != None:

        ahuaexeff = inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangeRatioCooling"]
        aexCeff = 1 - ((1/0.85)-1) * (1-ahuaexeff)/ahuaexeff
        aexCtol = 0.95
        aexCbal = 0.67
        inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangeRatioCooling"] = \
            ahuaexeff * aexCeff * aexCtol * aexCbal

    # 暖房の補正
    if inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangeRatioHeating"] != None:

        ahuaexeff = inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangeRatioHeating"]
        aexCeff = 1 - ((1/0.85)-1) * (1-ahuaexeff)/ahuaexeff
        aexCtol = 0.95
        aexCbal = 0.67
        inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangeRatioHeating"] = \
            ahuaexeff * aexCeff * aexCtol * aexCbal


##----------------------------------------------------------------------------------
## 外気負荷[kW]の算出（解説書 2.5.3）
##----------------------------------------------------------------------------------

for ahu_name in inputdata["AirHandlingSystem"]:

    for dd in range(0,365):

        if resultJson["AHU"][ahu_name]["Tahu_total"][dd] > 0:

            # 運転モードによって場合分け
            if ac_mode[dd] == "暖房":
                
                ahuVoa  = inputdata["AirHandlingSystem"][ahu_name]["outdoorAirVolume_heating"]
                ahuaexV = inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangerAirVolume"]

                # 全熱交換機を通過する風量 [m3/h]
                if ahuaexV > ahuVoa:
                    inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangerAirVolume"] = ahuVoa
                elif ahuaexV <= 0:
                    inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangerAirVolume"] = 0
                else:
                    inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangerAirVolume"] = ahuaexV
                
                # 外気負荷の算出
                if inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangeRatioHeating"] == None:   # 全熱交換器がない場合

                    resultJson["AHU"][ahu_name]["qoaAHU"][dd] = \
                        (resultJson["AHU"][ahu_name]["HoaDayAve"][dd] - Hroom[dd]) * inputdata["AirHandlingSystem"][ahu_name]["outdoorAirVolume_heating"] *1.293/3600

                else:  # 全熱交換器がある場合
                    
                    if (resultJson["AHU"][ahu_name]["HoaDayAve"][dd] > Hroom[dd]) and (inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangerControl"] == "有"):

                        # バイパス有の場合はそのまま外気導入する。
                        resultJson["AHU"][ahu_name]["qoaAHU"][dd] = \
                            (resultJson["AHU"][ahu_name]["HoaDayAve"][dd] - Hroom[dd]) * inputdata["AirHandlingSystem"][ahu_name]["outdoorAirVolume_heating"] *1.293/3600

                    else:

                        # 全熱交換器による外気負荷削減を見込む。
                        resultJson["AHU"][ahu_name]["qoaAHU"][dd] = \
                            (resultJson["AHU"][ahu_name]["HoaDayAve"][dd] - Hroom[dd]) * \
                            (inputdata["AirHandlingSystem"][ahu_name]["outdoorAirVolume_heating"] - \
                                inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangerAirVolume"] * inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangeRatioHeating"] ) *1.293/3600


            elif (ac_mode[dd] == "中間") or (ac_mode[dd] == "冷房"):
                
                ahuVoa  = inputdata["AirHandlingSystem"][ahu_name]["outdoorAirVolume_cooling"]
                ahuaexV = inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangerAirVolume"]

                # 全熱交換機を通過する風量 [m3/h]
                if ahuaexV > ahuVoa:
                    inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangerAirVolume"] = ahuVoa
                elif ahuaexV <= 0:
                    inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangerAirVolume"] = 0
                else:
                    inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangerAirVolume"] = ahuaexV

                # 外気負荷の算出
                if inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangeRatioCooling"] == None:   # 全熱交換器がない場合

                    resultJson["AHU"][ahu_name]["qoaAHU"][dd] = \
                        (resultJson["AHU"][ahu_name]["HoaDayAve"][dd] - Hroom[dd]) * inputdata["AirHandlingSystem"][ahu_name]["outdoorAirVolume_cooling"] *1.293/3600
                        
                else:  # 全熱交換器がある場合

                    if (resultJson["AHU"][ahu_name]["HoaDayAve"][dd] < Hroom[dd]) and  (inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangerControl"] == "有"):

                        # バイパス有の場合はそのまま外気導入する。
                        resultJson["AHU"][ahu_name]["qoaAHU"][dd] = \
                            (resultJson["AHU"][ahu_name]["HoaDayAve"][dd] - Hroom[dd]) * inputdata["AirHandlingSystem"][ahu_name]["outdoorAirVolume_cooling"] *1.293/3600

                    else:  # 全熱交換器がある場合

                        # 全熱交換器による外気負荷削減を見込む。
                        resultJson["AHU"][ahu_name]["qoaAHU"][dd] = \
                            (resultJson["AHU"][ahu_name]["HoaDayAve"][dd] - Hroom[dd]) * \
                            (inputdata["AirHandlingSystem"][ahu_name]["outdoorAirVolume_cooling"] - \
                                inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangerAirVolume"] * inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangeRatioCooling"] ) *1.293/3600



##----------------------------------------------------------------------------------
## 外気冷房制御による負荷削減量（解説書 2.5.4）
##----------------------------------------------------------------------------------

for ahu_name in inputdata["AirHandlingSystem"]:

    for dd in range(0,365):

        if resultJson["AHU"][ahu_name]["Tahu_total"][dd] > 0:

            # 外気冷房効果の推定
            if (inputdata["AirHandlingSystem"][ahu_name]["isEconomizer"] == "有") and (resultJson["AHU"][ahu_name]["cooling"]["Tahu"][dd]>0):   # 外気冷房ONで冷房運転がされていたら
                
                # 外気冷房時の風量 [kg/s]
                resultJson["AHU"][ahu_name]["cooling"]["AHUVovc"][dd] = \
                    resultJson["AHU"][ahu_name]["cooling"]["QroomAHU"][dd] / \
                    ((Hroom[dd]-resultJson["AHU"][ahu_name]["HoaDayAve"][dd]) * (3600/1000) * resultJson["AHU"][ahu_name]["cooling"]["Tahu"][dd])
                
                # 上限・下限
                if resultJson["AHU"][ahu_name]["cooling"]["AHUVovc"][dd] < inputdata["AirHandlingSystem"][ahu_name]["outdoorAirVolume_cooling"] *1.293/3600:
                    resultJson["AHU"][ahu_name]["cooling"]["AHUVovc"][dd] = inputdata["AirHandlingSystem"][ahu_name]["outdoorAirVolume_cooling"] *1.293/3600  # 下限（外気取入量）
                elif resultJson["AHU"][ahu_name]["cooling"]["AHUVovc"][dd] > inputdata["AirHandlingSystem"][ahu_name]["EconomizerMaxAirVolume"] *1.293/3600:
                    resultJson["AHU"][ahu_name]["cooling"]["AHUVovc"][dd] = inputdata["AirHandlingSystem"][ahu_name]["EconomizerMaxAirVolume"] *1.293/3600  # 上限（給気風量 [m3/h]→[kg/s]）
                
                # 追加すべき外気量（外気冷房用の追加分のみ）[kg/s]
                resultJson["AHU"][ahu_name]["cooling"]["AHUVovc"][dd] = \
                    resultJson["AHU"][ahu_name]["cooling"]["AHUVovc"][dd] - inputdata["AirHandlingSystem"][ahu_name]["outdoorAirVolume_cooling"]

            # 外気冷房効果 [MJ/day]
            if (inputdata["AirHandlingSystem"][ahu_name]["isEconomizer"] == "有"): # 外気冷房があれば

                if resultJson["AHU"][ahu_name]["cooling"]["AHUVovc"][dd] > 0: # 外冷時風量＞０であれば

                    resultJson["AHU"][ahu_name]["cooling"]["Qahu_oac"][dd] = \
                        resultJson["AHU"][ahu_name]["cooling"]["AHUVovc"][dd] * (Hroom[dd]-resultJson["AHU"][ahu_name]["HoaDayAve"][dd])*3600/1000*\
                        resultJson["AHU"][ahu_name]["cooling"]["Tahu"][dd]



##----------------------------------------------------------------------------------
## 日積算空調負荷 Qahu_c, Qahu_h の算出（解説書 2.5.5）
##----------------------------------------------------------------------------------

for ahu_name in inputdata["AirHandlingSystem"]:

    for dd in range(0,365):

        # 外気負荷だけの場合(処理上，冷房負荷に入れておく)
        if (resultJson["AHU"][ahu_name]["cooling"]["Tahu"][dd] == 0) and (resultJson["AHU"][ahu_name]["heating"]["Tahu"][dd] == 0):

            if (inputdata["AirHandlingSystem"][ahu_name]["isOutdoorAirCut"] == "無"):

                resultJson["AHU"][ahu_name]["cooling"]["Qahu"][dd] = \
                    resultJson["AHU"][ahu_name]["qoaAHU"][dd] * resultJson["AHU"][ahu_name]["Tahu_total"][dd] * 3600/1000

            else:

                if resultJson["AHU"][ahu_name]["Tahu_total"][dd] > 1:
                    resultJson["AHU"][ahu_name]["cooling"]["Qahu"][dd] = \
                        resultJson["AHU"][ahu_name]["qoaAHU"][dd] * (resultJson["AHU"][ahu_name]["Tahu_total"][dd]-1) * 3600/1000

                else:

                    resultJson["AHU"][ahu_name]["cooling"]["Qahu"][dd] = \
                        resultJson["AHU"][ahu_name]["qoaAHU"][dd] * resultJson["AHU"][ahu_name]["Tahu_total"][dd] * 3600/1000

            resultJson["AHU"][ahu_name]["heating"]["Qahu"][dd] = 0

        else:

            # 冷房負荷
            if resultJson["AHU"][ahu_name]["cooling"]["Tahu"][dd] > 0:
                
                if (inputdata["AirHandlingSystem"][ahu_name]["isOutdoorAirCut"] == "有") and \
                    (resultJson["AHU"][ahu_name]["cooling"]["Tahu"][dd] > 1) and \
                    (resultJson["AHU"][ahu_name]["cooling"]["Tahu"][dd] >= resultJson["AHU"][ahu_name]["heating"]["Tahu"][dd]):

                    resultJson["AHU"][ahu_name]["cooling"]["Qahu"][dd] = \
                        resultJson["AHU"][ahu_name]["cooling"]["QroomAHU"][dd] + \
                        resultJson["AHU"][ahu_name]["qoaAHU"][dd] * (resultJson["AHU"][ahu_name]["cooling"]["Tahu"][dd] - 1) * 3600/1000
    
                else:

                    resultJson["AHU"][ahu_name]["cooling"]["Qahu"][dd] = \
                        resultJson["AHU"][ahu_name]["cooling"]["QroomAHU"][dd] + \
                        resultJson["AHU"][ahu_name]["qoaAHU"][dd] * (resultJson["AHU"][ahu_name]["cooling"]["Tahu"][dd]) * 3600/1000

            # 暖房負荷
            if resultJson["AHU"][ahu_name]["heating"]["Tahu"][dd] > 0:

                if (inputdata["AirHandlingSystem"][ahu_name]["isOutdoorAirCut"] == "有") and \
                    (resultJson["AHU"][ahu_name]["heating"]["Tahu"][dd] > 1) and \
                    (resultJson["AHU"][ahu_name]["cooling"]["Tahu"][dd] < resultJson["AHU"][ahu_name]["heating"]["Tahu"][dd]):

                    resultJson["AHU"][ahu_name]["heating"]["Qahu"][dd] = \
                        resultJson["AHU"][ahu_name]["heating"]["QroomAHU"][dd] + \
                        resultJson["AHU"][ahu_name]["qoaAHU"][dd] * (resultJson["AHU"][ahu_name]["heating"]["Tahu"][dd] - 1) * 3600/1000
    
                else:

                    resultJson["AHU"][ahu_name]["heating"]["Qahu"][dd] = \
                        resultJson["AHU"][ahu_name]["heating"]["QroomAHU"][dd] + \
                        resultJson["AHU"][ahu_name]["qoaAHU"][dd] * (resultJson["AHU"][ahu_name]["heating"]["Tahu"][dd]) * 3600/1000


print('空調負荷計算完了')


# %%-----------------------------------------------------------------------------------------------------------
# %% 空調エネルギー計算

# % 空調負荷マトリックス作成 (AHUとFCUの運転時間は常に同じで良いか？→日積算であれば判別の仕様がない)
# MxAHUc    = zeros(numOfAHUSET,length(mxL));
# MxAHUh    = zeros(numOfAHUSET,length(mxL));
# MxAHUcE   = zeros(numOfAHUSET,length(mxL));
# MxAHUhE   = zeros(numOfAHUSET,length(mxL));
# MxAHUkW   = zeros(numOfAHUSET,length(mxL));
# AHUaex    = zeros(1,numOfAHUSET);

# % 時刻別計算用（MODE = 0）
# LtAHUc        = zeros(8760,numOfAHUSET);  % AHUの冷房負荷率帯
# LtAHUh        = zeros(8760,numOfAHUSET);  % AHUの暖房負荷率帯
# E_fan_hour    = zeros(8760,numOfAHUSET);  % AHUのエネルギー消費量
# E_fan_c_hour  = zeros(8760,numOfAHUSET);  % AHUのエネルギー消費量（冷房）
# E_fan_h_hour  = zeros(8760,numOfAHUSET);  % AHUのエネルギー消費量（暖房）
# E_AHUaex_hour = zeros(8760,numOfAHUSET);  % 全熱交換器のエネルギー消費量

# % 日別計算用（MODE = 4）
# LdAHUc        = zeros(365,2,numOfAHUSET);  % AHUの冷房負荷率帯
# LdAHUh        = zeros(365,2,numOfAHUSET);  % AHUの暖房負荷率帯
# TdAHUc        = zeros(365,2,numOfAHUSET);  % AHUの冷房運転時間
# TdAHUh        = zeros(365,2,numOfAHUSET);  % AHUの暖房運転時間
# TdAHUc_total  = zeros(365,numOfAHUSET);  % AHUの冷房運転時間
# TdAHUh_total  = zeros(365,numOfAHUSET);  % AHUの冷房運転時間
# E_fan_day     = zeros(365,numOfAHUSET);  % AHUのエネルギー消費量
# E_fan_c_day   = zeros(365,numOfAHUSET);  % AHUのエネルギー消費量（冷房）
# E_fan_h_day   = zeros(365,numOfAHUSET);  % AHUのエネルギー消費量（暖房）
# E_AHUaex_day  = zeros(365,numOfAHUSET);  % 全熱交換器のエネルギー消費量

# for iAHU = 1:numOfAHUSET
    
#     switch MODE
#         case {0}
#             % 時刻別負荷で時刻別エネルギー計算の場合
#             [LtAHUc(:,iAHU),LtAHUh(:,iAHU),~,~] = ...
#                 mytfunc_matrixAHU(MODE,Qahu_hour(:,iAHU),ahuQcmax(iAHU),[],[],ahuQhmax(iAHU),[],AHUCHmode(iAHU),WIN,MID,SUM,mxL);
            
#         case {1}
#             % 時刻別負荷でマトリックス計算の場合
#             [MxAHUc(iAHU,:),MxAHUh(iAHU,:),~,~] = ...
#                 mytfunc_matrixAHU(MODE,Qahu_hour(:,iAHU),ahuQcmax(iAHU),[],[],ahuQhmax(iAHU),[],AHUCHmode(iAHU),WIN,MID,SUM,mxL);
            
#         case {2,3}
#             % 日別負荷でマトリックス計算の場合
#             [MxAHUc(iAHU,:),MxAHUh(iAHU,:),~,~] = ...
#                 mytfunc_matrixAHU(MODE,Qahu_c(:,iAHU),ahuQcmax(iAHU),Tahu_c(:,iAHU),...
#                 Qahu_h(:,iAHU),ahuQhmax(iAHU),Tahu_h(:,iAHU),AHUCHmode(iAHU),WIN,MID,SUM,mxL);
            
#         case {4}
#             % 日別負荷で日別エネルギー計算の場合
#             [LdAHUc(:,:,iAHU),LdAHUh(:,:,iAHU),TdAHUc(:,:,iAHU),TdAHUh(:,:,iAHU)] = ...
#                 mytfunc_matrixAHU(MODE,Qahu_c(:,iAHU),ahuQcmax(iAHU),Tahu_c(:,iAHU),...
#                 Qahu_h(:,iAHU),ahuQhmax(iAHU),Tahu_h(:,iAHU),AHUCHmode(iAHU),WIN,MID,SUM,mxL);
            
#     end
    
#     % エネルギー消費特性
#     tmpEkW = zeros(1,length(mxL));
#     for iAHUele = 1:numOfAHUele(iAHU)
#         for iL = 1:length(mxL)
#             tmpEkW(iL) = tmpEkW(iL) + ahuEfan(iAHU,iAHUele).*ahuFanVAVfunc(iAHU,iAHUele,iL);
#         end
#     end
    
#     % エネルギー消費量計算
#     switch MODE
        
#         case {0}
            
#             for dd = 1:365
#                 for hh = 1:24
                    
#                     % 1月1日0時からの時間数
#                     num = 24*(dd-1)+hh;
                    
#                     % 空調機のエネルギー消費量（冷房） [MWh]
#                     if LtAHUc(num,iAHU) == 0
#                         E_fan_c_hour(num,iAHU) = 0;
#                     else
#                         E_fan_c_hour(num,iAHU) = tmpEkW(LtAHUc(num,iAHU))/1000;   % ファンエネルギー消費量　MWh
#                     end
#                     % 空調機のエネルギー消費量（暖房） [MWh]
#                     if LtAHUh(num,iAHU) == 0
#                         E_fan_h_hour(num,iAHU) = 0;
#                     else
#                         E_fan_h_hour(num,iAHU) = tmpEkW(LtAHUh(num,iAHU))/1000;   % ファンエネルギー消費量　MWh
#                     end
                    
#                     E_fan_hour = E_fan_c_hour + E_fan_h_hour;
                    
#                     if LtAHUc(num,iAHU) > 0 || LtAHUh(num,iAHU) > 0
#                         E_AHUaex_hour(num,iAHU) = ahuaexE(iAHU)/1000;    % 全熱交換器エネルギー消費量　MWh
#                     end
                    
#                 end
#             end
            
#         case {1,2,3}
            
#             % エネルギー計算（空調機ファン） 出現時間 * 単位エネルギー [MWh]
#             MxAHUkW(iAHU,:) = tmpEkW;  % 結果出力用[kW]
#             MxAHUcE(iAHU,:) = MxAHUc(iAHU,:).* tmpEkW./1000;
#             MxAHUhE(iAHU,:) = MxAHUh(iAHU,:).* tmpEkW./1000;
            
#             % 全熱交換機のエネルギー消費量 [MWh] →　バイパスの影響は？
#             AHUaex(iAHU) = ahuaexE(iAHU).*sum(AHUsystemT(:,iAHU))./1000;
            
#         case {4}
            
#             MxAHUkW(iAHU,:) = tmpEkW;  % 結果出力用[kW]
            
#             for dd = 1:365
                
#                 % 空調機のエネルギー消費量（冷房） [MWh]
#                 if LdAHUc(dd,1,iAHU) > 0
#                     E_fan_c_day(dd,iAHU) = E_fan_c_day(dd,iAHU) + tmpEkW(LdAHUc(dd,1,iAHU))/1000.*TdAHUc(dd,1,iAHU);   % ファンエネルギー消費量　MWh
#                     TdAHUc_total(dd,iAHU) = TdAHUc_total(dd,iAHU) + TdAHUc(dd,1,iAHU);
#                 end
#                 if LdAHUc(dd,2,iAHU) > 0
#                     E_fan_c_day(dd,iAHU) = E_fan_c_day(dd,iAHU) + tmpEkW(LdAHUc(dd,2,iAHU))/1000.*TdAHUc(dd,2,iAHU);   % ファンエネルギー消費量　MWh
#                     TdAHUc_total(dd,iAHU) = TdAHUc_total(dd,iAHU) + TdAHUc(dd,2,iAHU);
#                 end
                
#                 % 空調機のエネルギー消費量（暖房） [MWh]
#                 if LdAHUh(dd,1,iAHU) > 0
#                     E_fan_h_day(dd,iAHU) = E_fan_h_day(dd,iAHU) + tmpEkW(LdAHUh(dd,1,iAHU))/1000.*TdAHUh(dd,1,iAHU);   % ファンエネルギー消費量　MWh
#                     TdAHUh_total(dd,iAHU) = TdAHUh_total(dd,iAHU) + TdAHUh(dd,1,iAHU);
#                 end
#                 if LdAHUh(dd,2,iAHU) > 0
#                     E_fan_h_day(dd,iAHU) = E_fan_h_day(dd,iAHU) + tmpEkW(LdAHUh(dd,2,iAHU))/1000.*TdAHUh(dd,2,iAHU);   % ファンエネルギー消費量　MWh
#                     TdAHUh_total(dd,iAHU) = TdAHUh_total(dd,iAHU) + TdAHUh(dd,2,iAHU);
#                 end
                
#                 if TdAHUc(dd,1,iAHU) > 0 || TdAHUh(dd,1,iAHU) > 0 || TdAHUc(dd,2,iAHU) > 0 || TdAHUh(dd,2,iAHU) > 0
#                     E_AHUaex_day(dd,iAHU) = ahuaexE(iAHU)/1000.*AHUsystemT(dd,iAHU);    % 全熱交換器エネルギー消費量　MWh
#                 end
                
#             end
            
#             E_fan_day = E_fan_c_day + E_fan_h_day;
            
#     end
    
# end

# % 空調機のエネルギー消費量 [MWh] 及び 積算運転時間(システム毎)
# switch MODE
#     case {0}
#         E_fan = sum(sum(E_fan_hour));
#         E_aex = sum(sum(E_AHUaex_hour));
#         TcAHU = sum(LtAHUc>0,1)';
#         ThAHU = sum(LtAHUh>0,1)';
        
#     case {1,2,3}
#         E_fan = sum(sum(MxAHUcE+MxAHUhE));
#         E_aex = sum(AHUaex);
#         TcAHU = sum(MxAHUc,2);
#         ThAHU = sum(MxAHUh,2);
        
#     case {4}
#         E_fan = sum(sum(E_fan_day));
#         E_aex = sum(sum(E_AHUaex_day));
#         TcAHU = sum(TdAHUc_total,1)';  % ファン発熱の計算に使う
#         ThAHU = sum(TdAHUh_total,1)';  % ファン発熱の計算に使う
#         MxAHUcE(:,1) = sum(E_fan_c_day,1)';  % ファン発熱の計算に使う
#         MxAHUhE(:,1) = sum(E_fan_h_day,1)';  % ファン発熱の計算に使う
# end




# %------------------------------
# % 二管式/四管式の処理（未処理負荷を0にする）

# % 未処理負荷 [MJ/day] の集計
# switch MODE
#     case {0,1}
        
#         Qahu_remainChour = zeros(8760,numOfAHUSET);
#         Qahu_remainHhour = zeros(8760,numOfAHUSET);
        
#         for iAHU = 1:numOfAHUSET
#             for dd = 1:365
#                 for hh = 1:24
                    
#                     num = 24*(dd-1)+hh;
                    
#                     if ModeOpe(dd,1) == -1  % 暖房モード
#                         if Qahu_hour(num,iAHU) > 0  && AHUCHmode_H(iAHU) == 0
#                             Qahu_remainChour(num,iAHU) = Qahu_remainChour(num,iAHU) + Qahu_hour(num,iAHU);
#                             Qahu_hour(num,iAHU) = 0;
#                         end
#                     elseif ModeOpe(dd,1) == 1  % 冷房モード
#                         if Qahu_hour(num,iAHU) < 0  && AHUCHmode_C(iAHU) == 0
#                             Qahu_remainHhour(num,iAHU) = Qahu_remainHhour(num,iAHU) + Qahu_hour(num,iAHU);
#                             Qahu_hour(num,iAHU) = 0;
#                         end
#                     else
#                         error('運転モード ModeOpe が不正です。')
#                     end
                    
#                 end
#             end
#         end
        
#     case {2,3,4}
        
#         Qahu_remainC = zeros(365,numOfAHUSET);
#         Qahu_remainH = zeros(365,numOfAHUSET);
        
#         for iAHU = 1:numOfAHUSET
#             for dd = 1:365
#                 if ModeOpe(dd,1) == -1  % 暖房モード
#                     if Qahu_c(dd,iAHU) > 0 && AHUCHmode_H(iAHU) == 0
#                         Qahu_remainC(dd,iAHU) = Qahu_remainC(dd,iAHU) + abs(Qahu_c(dd,iAHU));
#                         Qahu_c(dd,iAHU) = 0;
#                     end
#                     if Qahu_h(dd,iAHU) > 0 && AHUCHmode_H(iAHU) == 0
#                         Qahu_remainC(dd,iAHU) = Qahu_remainC(dd,iAHU) + abs(Qahu_h(dd,iAHU));
#                         Qahu_h(dd,iAHU) = 0;
#                     end
#                 elseif ModeOpe(dd,1) == 1  % 冷房モード
#                     if Qahu_c(dd,iAHU) < 0  && AHUCHmode_C(iAHU) == 0
#                         Qahu_remainH(dd,iAHU) = Qahu_remainH(dd,iAHU) + abs(Qahu_c(dd,iAHU));
#                         Qahu_c(dd,iAHU) = 0;
#                     end
#                     if Qahu_h(dd,iAHU) < 0   && AHUCHmode_C(iAHU) == 0
#                         Qahu_remainH(dd,iAHU) = Qahu_remainH(dd,iAHU) + abs(Qahu_h(dd,iAHU));
#                         Qahu_h(dd,iAHU) = 0;
#                     end
#                 else
#                     error('運転モード ModeOpe が不正です。')
#                 end
                
#             end
#         end
# end


# disp('空調エネルギー計算完了')
# toc


# %%-----------------------------------------------------------------------------------------------------------
# %% 二次搬送系の負荷計算

# switch MODE
    
#     case {0,1}
        
#         Qpsahu_fan_hour = zeros(8760,numOfPumps);  % ファン発熱量 [kW]
#         Qpsahu_hour     = zeros(8760,numOfPumps);  % ポンプ負荷 [kW]
        
#         for iPUMP = 1:numOfPumps
            
#             % ポンプ負荷の積算
#             for iAHU = 1:numOfAHUSET
#                 switch ahuSetName{iAHU}  % 属する空調機を見つける
#                     case PUMPahuSet{iPUMP}
                        
#                         % ポンプ負荷[kW]
#                         for num= 1:8760
                            
#                             if PUMPtype(iPUMP) == 1 % 冷水ポンプ
                                
#                                 % ファン発熱量 [kW]
#                                 fanHeatup = 0;
#                                 if ahuTypeNum(iAHU) == 1  % 空調機であれば
#                                     if Qahu_hour(num,iAHU) > 0
#                                         switch MODE
#                                             case {0}
#                                                 fanHeatup = E_fan_hour(num,iAHU) * k_heatup .* 1000;
#                                             case {1}
#                                                 fanHeatup = sum(MxAHUcE(iAHU,:))*(k_heatup)./TcAHU(iAHU,1).*1000;
#                                         end
                                        
#                                         Qpsahu_fan_hour(num,iPUMP) = Qpsahu_fan_hour(num,iPUMP) + fanHeatup;
#                                     end
#                                 end
                                
#                                 if Qahu_hour(num,iAHU) > 0
#                                     if ahuOAcool(iAHU) == 1 % 外冷あり
#                                         if abs(Qahu_hour(num,iAHU) - Qahu_oac_hour(num,iAHU)) < 1
#                                             Qpsahu_hour(num,iPUMP) = Qpsahu_hour(num,iPUMP) + 0;
#                                         else
#                                             Qpsahu_hour(num,iPUMP) = Qpsahu_hour(num,iPUMP) + Qahu_hour(num,iAHU) - Qahu_oac_hour(num,iAHU);
#                                         end
#                                     else
#                                         Qpsahu_hour(num,iPUMP) = Qpsahu_hour(num,iPUMP) + Qahu_hour(num,iAHU) - Qahu_oac_hour(num,iAHU) + fanHeatup;
#                                     end
#                                 end
                                
#                             elseif PUMPtype(iPUMP) == 2 % 温水ポンプ
                                
#                                 % ファン発熱量 [kW]
#                                 fanHeatup = 0;
#                                 if ahuTypeNum(iAHU) == 1  % 空調機であれば
#                                     if Qahu_hour(num,iAHU) < 0
#                                         switch MODE
#                                             case {0}
#                                                 fanHeatup = E_fan_hour(num,iAHU) * k_heatup .* 1000;
#                                             case {1}
#                                                 fanHeatup = sum(MxAHUhE(iAHU,:))*(k_heatup)./ThAHU(iAHU,1).*1000;
#                                         end
                                        
#                                         Qpsahu_fan_hour(num,iPUMP) = Qpsahu_fan_hour(num,iPUMP) + fanHeatup;
#                                     end
#                                 end
                                
#                                 if Qahu_hour(num,iAHU) < 0
#                                     Qpsahu_hour(num,iPUMP) = Qpsahu_hour(num,iPUMP) + (-1)*(Qahu_hour(num,iAHU)+fanHeatup);
#                                 end
#                             end
#                         end
#                 end
#             end
#         end
        
        
#     case {2,3,4}
        
#         Qpsahu_fan = zeros(365,numOfPumps);   % ファン発熱量 [MJ/day]
#         Qpsahu_fan_AHU_C = zeros(365,numOfAHUSET);   % ファン発熱量 [MJ/day]
#         Qpsahu_fan_AHU_H = zeros(365,numOfAHUSET);   % ファン発熱量 [MJ/day]
#         pumpTime_Start = zeros(365,numOfPumps);
#         pumpTime_Stop  = zeros(365,numOfPumps);
#         Qps = zeros(365,numOfPumps); % ポンプ負荷 [MJ/day]
#         Tps = zeros(365,numOfPumps);
        
#         for iPUMP = 1:numOfPumps
            
#             % ポンプ負荷の積算
#             for iAHU = 1:numOfAHUSET
                
#                 if isempty(PUMPahuSet{iPUMP}) == 0
                    
#                     switch ahuSetName{iAHU}
#                         case PUMPahuSet{iPUMP}
                            
#                             for dd = 1:365
                                
#                                 if PUMPtype(iPUMP) == 1 % 冷水ポンプ
                                    
#                                     % ファン発熱量 Qpsahu_fan [MJ/day] の算出
#                                     tmpC = 0;
#                                     tmpH = 0;
#                                     if ahuTypeNum(iAHU) == 1  % 空調機であれば
#                                         if Qahu_c(dd,iAHU) > 0
#                                             tmpC = sum(MxAHUcE(iAHU,:))*(k_heatup)./TcAHU(iAHU,1).*Tahu_c(dd,iAHU).*3600;
#                                             Qpsahu_fan(dd,iPUMP) = Qpsahu_fan(dd,iPUMP) + tmpC;
#                                             Qpsahu_fan_AHU_C(dd,iAHU) = Qpsahu_fan_AHU_C(dd,iAHU) + tmpC;
#                                         end
#                                         if Qahu_h(dd,iAHU) > 0
#                                             tmpH = sum(MxAHUhE(iAHU,:))*(k_heatup)./ThAHU(iAHU,1).*Tahu_h(dd,iAHU).*3600;
#                                             Qpsahu_fan(dd,iPUMP) = Qpsahu_fan(dd,iPUMP) + tmpH;
#                                             Qpsahu_fan_AHU_C(dd,iAHU) = Qpsahu_fan_AHU_C(dd,iAHU) + tmpH;
#                                         end
#                                     end
                                    
#                                     % 日積算ポンプ負荷 Qps [MJ/day] の算出
#                                     if Qahu_c(dd,iAHU) > 0
#                                         if Qahu_oac(dd,iAHU) > 0 % 外冷時はファン発熱量足さない　⇒　小さな負荷が出てしまう
#                                             if abs(Qahu_c(dd,iAHU) - Qahu_oac(dd,iAHU)) < 1  % 計算誤差まるめ
#                                                 Qps(dd,iPUMP) = Qps(dd,iPUMP) + 0;
#                                             else
#                                                 Qps(dd,iPUMP) = Qps(dd,iPUMP) + Qahu_c(dd,iAHU) - Qahu_oac(dd,iAHU);
#                                             end
#                                         else
#                                             Qps(dd,iPUMP) = Qps(dd,iPUMP) + Qahu_c(dd,iAHU) - Qahu_oac(dd,iAHU) + tmpC + tmpH;
#                                         end
#                                     end
#                                     if Qahu_h(dd,iAHU) > 0
#                                         Qps(dd,iPUMP) = Qps(dd,iPUMP) + Qahu_h(dd,iAHU) - Qahu_oac(dd,iAHU) + tmpC + tmpH;
#                                     end
                                    
#                                 elseif PUMPtype(iPUMP) == 2 % 温水ポンプ
                                    
#                                     % ファン発熱量 Qpsahu_fan [MJ/day] の算出
#                                     tmpC = 0;
#                                     tmpH = 0;
#                                     if ahuTypeNum(iAHU) == 1  % 空調機であれば
#                                         if Qahu_c(dd,iAHU) < 0
#                                             tmpC = sum(MxAHUcE(iAHU,:))*(k_heatup)./TcAHU(iAHU,1).*Tahu_c(dd,iAHU).*3600;
#                                             Qpsahu_fan(dd,iPUMP) = Qpsahu_fan(dd,iPUMP) + tmpC;
#                                             Qpsahu_fan_AHU_H(dd,iAHU) = Qpsahu_fan_AHU_H(dd,iAHU) + tmpC;
#                                         end
#                                         if Qahu_h(dd,iAHU) < 0
#                                             tmpH = sum(MxAHUhE(iAHU,:))*(k_heatup)./ThAHU(iAHU,1).*Tahu_h(dd,iAHU).*3600;
#                                             Qpsahu_fan(dd,iPUMP) = Qpsahu_fan(dd,iPUMP) + tmpH;
#                                             Qpsahu_fan_AHU_H(dd,iAHU) = Qpsahu_fan_AHU_H(dd,iAHU) + tmpH;
#                                         end
#                                     end
                                    
#                                     % 日積算ポンプ負荷 Qps [MJ/day] の算出<符号逆転させる>
#                                     if Qahu_c(dd,iAHU) < 0
#                                         Qps(dd,iPUMP) = Qps(dd,iPUMP) + (-1).*(Qahu_c(dd,iAHU) + tmpC + tmpH);
#                                     end
#                                     if Qahu_h(dd,iAHU) < 0
#                                         Qps(dd,iPUMP) = Qps(dd,iPUMP) + (-1).*(Qahu_h(dd,iAHU) + tmpC + tmpH);
#                                     end
                                    
#                                 end
#                             end
#                     end
                    
#                 end
#             end
            
#             % ポンプ運転時間
#             [Tps(:,iPUMP),pumpsystemOpeTime(iPUMP,:,:)]...
#                 = mytfunc_PUMPOpeTIME(Qps(:,iPUMP),ahuSetName,PUMPahuSet{iPUMP},AHUsystemOpeTime);
            
#         end
# end

# disp('ポンプ負荷計算完了')
# toc;


# %% ポンプエネルギー計算

# % 負荷マトリックス
# MxPUMP    = zeros(numOfPumps,length(mxL));
# % 運転台数マトリックス
# MxPUMPNum = zeros(numOfPumps,length(mxL));
# MxPUMPPower = zeros(numOfPumps,length(mxL));
# % 消費電力マトリックス
# MxPUMPE   = zeros(numOfPumps,length(mxL));
# % 部分負荷特性
# PUMPvwvfac = ones(numOfPumps,length(mxL));

# % 時刻別計算用（MODE = 0）
# LtPUMP = zeros(8760,numOfPumps);  % ポンプの負荷率区分
# E_pump_hour = zeros(8760,numOfPumps);  % ポンプのエネルギー消費量

# % 日別計算用（MODE = 4）
# LdPUMP = zeros(365,numOfPumps);  % ポンプの負荷率区分
# TdPUMP = zeros(365,numOfPumps);  % ポンプの運転時間
# E_pump_day = zeros(365,numOfPumps);  % ポンプのエネルギー消費量


# % ポンプ群i及び群に属するポンプjの仮想定格能力[kW]　（温度差×流量合計値）
# [Qpsr, Qpsr_sub] = func_PUMPCapacity(pumpdelT',pumpFlow,Cw);

# for iPUMP = 1:numOfPumps
    
#     if Qpsr(iPUMP) ~= 0 % ビルマル用仮想ポンプは除く
        
#         % ポンプ負荷マトリックス作成（仕様書 2.7.2.2 二次ポンプ群の負荷率）
#         switch MODE
#             case {0}
#                 [LtPUMP(:,iPUMP),~] = func_matrixPUMP(MODE,Qpsahu_hour(:,iPUMP),Qpsr(iPUMP),[],mxL);
#             case {1}
#                 [MxPUMP(iPUMP,:),~] = func_matrixPUMP(MODE,Qpsahu_hour(:,iPUMP),Qpsr(iPUMP),[],mxL);
#             case {2,3}
#                 [MxPUMP(iPUMP,:),~] = func_matrixPUMP(MODE,Qps(:,iPUMP),Qpsr(iPUMP),Tps(:,iPUMP),mxL);
#             case {4}
#                 [LdPUMP(:,iPUMP),TdPUMP(:,iPUMP)] = func_matrixPUMP(MODE,Qps(:,iPUMP),Qpsr(iPUMP),Tps(:,iPUMP),mxL);
#         end
        
        
#         % ポンプ運転台数 [台] と　消費電力 [kW]
#         if PUMPnumctr(iPUMP) == 0   % 台数制御なし
            
#             % 運転台数（全台運転）
#             MxPUMPNum(iPUMP,:)   = pumpsetPnum(iPUMP).*ones(1,length(mxL));
            
#             % 流量制御方式
#             if prod(PUMPvwv(iPUMP,1:pumpsetPnum(iPUMP))) == 1  % 全台VWVであれば
                
#                 for iL = 1:length(mxL)
#                     if aveL(iL) < max(pumpVWVmin(iPUMP,1:pumpsetPnum(iPUMP)))
#                         tmpL = max(pumpVWVmin(iPUMP,1:pumpsetPnum(iPUMP)));
#                     else
#                         tmpL = aveL(iL);
#                     end
                    
#                     % VWVの効果率曲線(1番目の特性を代表して使う)
#                     if iL == length(mxL)
#                         PUMPvwvfac(iPUMP,iL) = 1.2;
#                     else
#                         PUMPvwvfac(iPUMP,iL) = ...
#                             Pump_VWVcoeffi(iPUMP,1,1).*tmpL.^4 + ...
#                             Pump_VWVcoeffi(iPUMP,1,2).*tmpL.^3 + ...
#                             Pump_VWVcoeffi(iPUMP,1,3).*tmpL.^2 + ...
#                             Pump_VWVcoeffi(iPUMP,1,4).*tmpL + ...
#                             Pump_VWVcoeffi(iPUMP,1,5);
#                     end
                    
#                 end
#             else
#                 % 全台VWVでなければ、CWVとみなす
#                 PUMPvwvfac(iPUMP,:) = ones(1,11);
#                 PUMPvwvfac(iPUMP,end) = 1.2;
#             end
            
#             % 消費電力（部分負荷特性×定格消費電力）[kW]
#             MxPUMPPower(iPUMP,:) = PUMPvwvfac(iPUMP,:) .* sum(pumpPower(iPUMP,:),2);
            
            
#         elseif PUMPnumctr(iPUMP) == 1  % 台数制御あり
            
#             for iL = 1:length(mxL)
                
#                 % 負荷区分 iL における処理負荷 [kW]
#                 Qpsr_iL  = Qpsr(iPUMP)*aveL(iL);
                
#                 % 運転台数 MxPUMPNum
#                 for rr = 1:pumpsetPnum(iPUMP)
#                     % 1台～rr台までの最大能力合計値
#                     tmpQmax = sum(Qpsr_sub(iPUMP,1:rr),2);
                    
#                     if Qpsr_iL < tmpQmax
#                         break
#                     end
#                 end
#                 MxPUMPNum(iPUMP,iL) = rr;
                
#                 % 定流量ポンプの処理熱量合計、VWVポンプの台数
#                 Qtmp_CWV = 0;
#                 numVWV = MxPUMPNum(iPUMP,iL);
#                 for iPUMPSUB = 1:MxPUMPNum(iPUMP,iL)
#                     if PUMPvwv(iPUMP,iPUMPSUB) == 0  % 定流量ポンプであれば
#                         % 定流量ポンプの処理熱量合計
#                         Qtmp_CWV = Qtmp_CWV + Qpsr_sub(iPUMP,iPUMPSUB);
#                         % 全体台数から定流量ポンプの台数を差し引いていく
#                         numVWV = numVWV - 1;
#                     end
#                 end
                
#                 % 制御を加味した消費エネルギー MxPUMPPower [kW]
#                 for iPUMPSUB = 1:MxPUMPNum(iPUMP,iL)
                    
#                     if PUMPvwv(iPUMP,iPUMPSUB) == 0 % 定流量
                        
#                         if aveL(iL) > 1.0
#                             MxPUMPPower(iPUMP,iL) = MxPUMPPower(iPUMP,iL)  + pumpPower(iPUMP,iPUMPSUB)*1.2;
#                         else
#                             MxPUMPPower(iPUMP,iL) = MxPUMPPower(iPUMP,iL)  + pumpPower(iPUMP,iPUMPSUB);
#                         end
                        
#                     elseif PUMPvwv(iPUMP,iPUMPSUB) == 1 % 変流量
                        
#                         % 変流量ポンプjの負荷率 [-]
#                         tmpL = ( (Qpsr_iL - Qtmp_CWV)/numVWV ) / Qpsr_sub(iPUMP,iPUMPSUB);
                        
#                         % 最小流量の制限
#                         if tmpL < pumpMinValveOpening(iPUMP,iPUMPSUB)
#                             tmpL = pumpMinValveOpening(iPUMP,iPUMPSUB);
#                         end
                        
#                         % 変流量制御による省エネ効果
#                         if aveL(iL) > 1.0
#                             PUMPvwvfac(iPUMP,iL) = 1.2;
#                         else
#                             PUMPvwvfac(iPUMP,iL) = ...
#                                 Pump_VWVcoeffi(iPUMP,iPUMPSUB,1).*tmpL.^4 + ...
#                                 Pump_VWVcoeffi(iPUMP,iPUMPSUB,2).*tmpL.^3 + ...
#                                 Pump_VWVcoeffi(iPUMP,iPUMPSUB,3).*tmpL.^2 + ...
#                                 Pump_VWVcoeffi(iPUMP,iPUMPSUB,4).*tmpL + ...
#                                 Pump_VWVcoeffi(iPUMP,iPUMPSUB,5);
#                         end
                        
#                         MxPUMPPower(iPUMP,iL) = MxPUMPPower(iPUMP,iL)  + pumpPower(iPUMP,iPUMPSUB).*PUMPvwvfac(iPUMP,iL);
                        
#                     end
#                 end
#             end
            
#         end
        
        
#         % 二次ポンプ群の電力消費量（消費電力×運転時間）[MWh]
#         switch MODE
            
#             case {0}
                
#                 for dd = 1:365
#                     for hh = 1:24
                        
#                         % 1月1日0時からの時間数
#                         num = 24*(dd-1)+hh;
                        
#                         % ポンプのエネルギー消費量 [MWh]
#                         if LtPUMP(num,iPUMP) == 0
#                             E_pump_hour(num,iPUMP) = 0;
#                         else
#                             E_pump_hour(num,iPUMP) =  MxPUMPPower(iPUMP,LtPUMP(num,iPUMP))./1000;   % ポンプエネルギー消費量  MWh
#                         end
#                     end
#                 end
                
#             case {1,2,3}
#                 % ポンプエネルギー消費量 [MWh]
#                 MxPUMPE(iPUMP,:) = MxPUMP(iPUMP,:).*MxPUMPPower(iPUMP,:)./1000;
                
#             case {4}
                
#                 for dd = 1:365
                    
#                     % ポンプのエネルギー消費量 [MWh]
#                     if TdPUMP(dd,iPUMP) == 0
#                         E_pump_day(dd,iPUMP) = 0;
#                     else
#                         E_pump_day(dd,iPUMP) =  MxPUMPPower(iPUMP,LdPUMP(dd,iPUMP))./1000.*TdPUMP(dd,iPUMP);   % ポンプエネルギー消費量  MWh
#                     end
#                 end
                
#         end
        
#     end
# end

# % 二次ポンプのエネルギー消費量 [MWh] 及び 積算運転時間(システム毎)
# switch MODE
#     case {0}
#         E_pump = sum(sum(E_pump_hour));
#         TcPUMP = sum(E_pump_hour>0,1)';
#     case {1,2,3}
#         E_pump = sum(sum(MxPUMPE));  % エネルギー消費量 [MWh]
#         TcPUMP = sum(MxPUMP,2); % 積算運転時間(システム毎)
#     case {4}
#         E_pump = sum(sum(E_pump_day));  % エネルギー消費量 [MWh]
#         TcPUMP = sum(TdPUMP,1)'; % 積算運転時間(システム毎)
#         MxPUMPE = sum(E_pump_day,1)';
# end

# disp('ポンプエネルギー計算完了')
# toc

# %%-----------------------------------------------------------------------------------------------------------
# %% 熱源系統の計算

# xXratioMX  = ones(numOfRefs,3,3).*NaN;

# switch MODE
#     case {0,1}
        
#         Qref_hour = zeros(8760,numOfRefs);   % 時刻別熱源負荷 [kW]
#         Qref_OVER_hour = zeros(8760,numOfRefs);   % 過負荷 [MJ/h]
        
#         for iREF = 1:numOfRefs
            
#             % 日積算熱源負荷 [MJ/Day]
#             for iPUMP = 1:numOfPumps
#                 switch pumpName{iPUMP}
#                     case REFpumpSet{iREF}
                        
#                         for num=1:8760
                            
#                             % ポンプ発熱量 [kW]
#                             pumpHeatup = 0;
                            
#                             if TcPUMP(iPUMP,1) ~= 0
#                                 switch MODE
#                                     case {0}
#                                         pumpHeatup = E_pump_hour(num,iPUMP) .* k_heatup .*1000;
#                                     case {1}
#                                         pumpHeatup = sum(MxPUMPE(iPUMP,:)).*(k_heatup)./TcPUMP(iPUMP,1).*1000;
#                                 end
#                             else
#                                 pumpHeatup = 0;  % 仮想ポンプ用
#                             end
                            
                            
#                             if Qpsahu_hour(num,iPUMP) ~= 0  % 停止時除く
                                
#                                 if REFtype(iREF) == 1 % 冷房負荷→冷房熱源に
                                    
#                                     tmp = Qpsahu_hour(num,iPUMP) + pumpHeatup;
#                                     Qref_hour(num,iREF) = Qref_hour(num,iREF) + tmp;
                                    
#                                 elseif REFtype(iREF) == 2 % 暖房負荷→暖房熱源に
                                    
#                                     tmp = Qpsahu_hour(num,iPUMP) - pumpHeatup;
#                                     if tmp<0
#                                         tmp = 0;
#                                     end
#                                     Qref_hour(num,iREF) = Qref_hour(num,iREF) + tmp;
                                    
#                                 end
                                
#                             end
#                         end
#                 end
#             end
            
#             % 熱源運転時間を求める
#             opetimeTemp = zeros(365,1);
#             for dd = 1:365
#                 count = 0;
#                 for hh = 1:24
#                     if Qref_hour(24*(dd-1)+hh,iREF) > 0
#                         count = count + 1;
#                     end
#                 end
#                 opetimeTemp(dd) = count;
#             end
            
#             for dd = 1:365
#                 for hh = 1:24
#                     num = 24*(dd-1) + hh;
                    
#                     % 過負荷分を抜き出す [MJ/hour]
#                     if Qref_hour(num,iREF) > QrefrMax(iREF)
#                         Qref_OVER_hour(num,iREF) = (Qref_hour(num,iREF)-QrefrMax(iREF)) *3600/1000;
#                     end
                    
#                 end
#             end
#         end
        
#         % 蓄熱の処理(2016/01/11追加)
#         [Qref_hour,Qref_hour_discharge] = mytfunc_thermalstorage_Qrefhour(Qref_hour,REFstorage,storageEffratio,refsetStorageSize,numOfRefs,refset_Capacity,refsetID,QrefrMax);
        
#         % 放熱用熱交換器を削除
#         for iREF = 1:numOfRefs
#             if REFstorage(iREF) == -1  % 採熱＋追掛け
                
#                 % 放熱運転時の補機
#                 refset_PrimaryPumpPower_discharge(iREF,1) = refset_PrimaryPumpPower(iREF,1);
                
#                 % 熱交換器を削除
#                 refset_Count(iREF,1:10)       = [refset_Count(iREF,2:10),0];
#                 refset_Type(iREF,1:10)        = [refset_Type(iREF,2:10),0];
#                 refset_Capacity(iREF,1:10)    = [refset_Capacity(iREF,2:10),0];
#                 refset_MainPower(iREF,1:10)   = [refset_MainPower(iREF,2:10),0];
#                 refset_SubPower(iREF,1:10)    = [refset_SubPower(iREF,2:10),0];
#                 refset_PrimaryPumpPower(iREF,1:10) = [refset_PrimaryPumpPower(iREF,2:10),0];
#                 refset_CTCapacity(iREF,1:10)  = [refset_CTCapacity(iREF,2:10),0];
#                 refset_CTFanPower(iREF,1:10)  = [refset_CTFanPower(iREF,2:10),0];
#                 refset_CTPumpPower(iREF,1:10) = [refset_CTPumpPower(iREF,2:10),0];
#                 refset_SupplyTemp(iREF,1:10)  = [refset_SupplyTemp(iREF,2:10),0];
                
#                 for iREFSUB = 1:refsetRnum(iREF)
#                     if iREFSUB ~= refsetRnum(iREF)
                        
#                         refInputType(iREF,iREFSUB) = refInputType(iREF,iREFSUB+1);
#                         refset_MainPowerELE(iREF,iREFSUB) = refset_MainPowerELE(iREF,iREFSUB+1);
#                         refHeatSourceType(iREF,iREFSUB) = refHeatSourceType(iREF,iREFSUB+1);
                        
#                         xTALL(iREF,iREFSUB,:) =  xTALL(iREF,iREFSUB+1,:);
#                         xQratio(iREF,iREFSUB,:) = xQratio(iREF,iREFSUB+1,:);
#                         xPratio(iREF,iREFSUB,:) = xPratio(iREF,iREFSUB+1,:);
#                         xXratioMX(iREF,iREFSUB,:) = xXratioMX(iREF,iREFSUB+1,:);
                        
#                         RerPerC_x_min(iREF,iREFSUB,:) = RerPerC_x_min(iREF,iREFSUB+1,:);
#                         RerPerC_x_max(iREF,iREFSUB,:) = RerPerC_x_max(iREF,iREFSUB+1,:);
#                         RerPerC_x_coeffi(iREF,iREFSUB,:,:) = RerPerC_x_coeffi(iREF,iREFSUB+1,:,:);
                        
#                         RerPerC_w_min(iREF,iREFSUB,:) = RerPerC_w_min(iREF,iREFSUB+1,:);
#                         RerPerC_w_max(iREF,iREFSUB,:) = RerPerC_w_max(iREF,iREFSUB+1,:);
#                         RerPerC_w_coeffi(iREF,iREFSUB,:,:) = RerPerC_w_coeffi(iREF,iREFSUB+1,:,:);
                        
#                     else
                        
#                         refInputType(iREF,refsetRnum(iREF)) = 0;
#                         refset_MainPowerELE(iREF,refsetRnum(iREF)) = 0;
#                         refHeatSourceType(iREF,refsetRnum(iREF)) = 0;
                        
#                         xTALL(iREF,refsetRnum(iREF),:) = zeros(1,1,size(xTALL,3));
#                         xQratio(iREF,refsetRnum(iREF),:) = zeros(1,1,size(xQratio,3));
#                         xPratio(iREF,refsetRnum(iREF),:) = zeros(1,1,size(xPratio,3));
#                         xXratioMX(iREF,refsetRnum(iREF),:) = zeros(1,1,size(xXratioMX,3));
                        
#                         RerPerC_x_min(iREF,refsetRnum(iREF),:) = zeros(1,1,size(RerPerC_x_min,3));
#                         RerPerC_x_max(iREF,refsetRnum(iREF),:) = zeros(1,1,size(RerPerC_x_max,3));
#                         RerPerC_x_coeffi(iREF,refsetRnum(iREF),:,:) = zeros(1,1,size(RerPerC_x_max,3),size(RerPerC_x_max,4));
                        
#                         RerPerC_w_min(iREF,refsetRnum(iREF),:) = zeros(1,1,size(RerPerC_w_min,3));
#                         RerPerC_w_max(iREF,refsetRnum(iREF),:) = zeros(1,1,size(RerPerC_w_max,3));
#                         RerPerC_w_coeffi(iREF,refsetRnum(iREF),:,:) = zeros(1,1,size(RerPerC_w_coeffi,3),size(RerPerC_w_coeffi,4));
                        
#                     end
#                 end
                
#                 % 台数を減じる
#                 refsetRnum(iREF) = refsetRnum(iREF) - 1;
                
#             end
#         end
        
        
#     case {2,3,4}
        
#         Qref          = zeros(365,numOfRefs);    % 日積算熱源負荷 [MJ/day]
#         Qref_kW       = zeros(365,numOfRefs);    % 日平均熱源負荷 [kW]
#         Qref_OVER     = zeros(365,numOfRefs);    % 日積算過負荷 [MJ/day]
#         Qpsahu_pump   = zeros(1,numOfPumps);     % ポンプ発熱量 [kW]
#         Tref          = zeros(365,numOfRefs);
#         refTime_Start = zeros(365,numOfRefs);
#         refTime_Stop  = zeros(365,numOfRefs);
#         Qpsahu_pump_save =  zeros(365,numOfRefs); % ポンプ発熱量 保存 [MJ]
        
#         for iREF = 1:numOfRefs
            
#             % 日積算熱源負荷 [MJ/Day]
#             for iPUMP = 1:numOfPumps
#                 switch pumpName{iPUMP}
#                     case REFpumpSet{iREF}
                        
#                         % 二次ポンプ発熱量 [kW]
#                         if TcPUMP(iPUMP,1) > 0
#                             Qpsahu_pump(iPUMP) = sum(MxPUMPE(iPUMP,:)).*(k_heatup)./TcPUMP(iPUMP,1).*1000;
#                         end
                        
#                         for dd = 1:365
                            
#                             if REFtype(iREF) == 1  % 冷熱生成モード
#                                 % 日積算熱源負荷  [MJ/day]
#                                 if Qps(dd,iPUMP) > 0
#                                     Qref(dd,iREF)  = Qref(dd,iREF) + Qps(dd,iPUMP) + Qpsahu_pump(iPUMP).*Tps(dd,iPUMP).*3600/1000;
#                                     % ポンプ発熱保存
#                                     Qpsahu_pump_save(dd,iREF) = Qpsahu_pump_save(dd,iREF) + Qpsahu_pump(iPUMP).*Tps(dd,iPUMP).*3600/1000;
#                                 end
#                             elseif REFtype(iREF) == 2 % 温熱生成モード
#                                 % 日積算熱源負荷  [MJ/day] (Qpsの符号が変わっていることに注意)
#                                 if Qps(dd,iPUMP) + (-1).*Qpsahu_pump(iPUMP).*Tps(dd,iPUMP).*3600/1000 > 0
#                                     Qref(dd,iREF)  = Qref(dd,iREF) + Qps(dd,iPUMP) + (-1).*Qpsahu_pump(iPUMP).*Tps(dd,iPUMP).*3600/1000;
#                                     % ポンプ発熱保存
#                                     Qpsahu_pump_save(dd,iREF) = Qpsahu_pump_save(dd,iREF) - (-1).*Qpsahu_pump(iPUMP).*Tps(dd,iPUMP).*3600/1000;
#                                 end
#                             end
                            
#                         end
#                 end
#             end
            
#             % 熱源運転時間（ポンプ運転時間の和集合）
#             [Tref(:,iREF),refsystemOpeTime(iREF,:,:)] =...
#                 mytfunc_REFOpeTIME(Qref(:,iREF),pumpName,REFpumpSet{iREF},pumpsystemOpeTime);
            
            
#             % 平均負荷[kW]と過負荷量を求める。
#             for dd = 1:365
                
#                 % 蓄熱の場合: 熱損失量 [MJ/day] を足す。損失量は 蓄熱槽容量の3%。
#                 if Tref(dd,iREF) > 0  && REFstorage(iREF) == 1
#                     Qref(dd,iREF) = Qref(dd,iREF) + refsetStorageSize(iREF)*0.03;  % 2014/1/10修正
                    
#                     % 蓄熱処理追加（蓄熱槽容量以上の負荷を処理しないようにする） 2013/12/16
#                     if Qref(dd,iREF) > storageEffratio(iREF)*refsetStorageSize(iREF)
#                         Qref(dd,iREF) = storageEffratio(iREF)*refsetStorageSize(iREF);
#                     end
                    
#                 end
                
#                 % 平均負荷 [kW]
#                 if Tref(dd,iREF) == 0
#                     Qref_kW(dd,iREF) = 0;
#                 else
#                     Qref_kW(dd,iREF) = Qref(dd,iREF)./Tref(dd,iREF).*1000./3600;
#                 end
                
#                 % 過負荷分を集計 [MJ/day]
#                 if Qref_kW(dd,iREF) > QrefrMax(iREF)
#                     Qref_OVER(dd,iREF) = (Qref_kW(dd,iREF)-QrefrMax(iREF)).*Tref(dd,iREF)*3600/1000;
#                 end
#             end
            
#         end
        
# end

# disp('熱源負荷計算完了')
# toc


# %% 熱源特性を抜き出す

# switch MODE
#     case {2,3,4}
        
#         % 地中熱ヒートポンプ用係数
#         gshp_ah = [8.0278, 13.0253, 16.7424, 19.3145, 21.2833];   % 地盤モデル：暖房時パラメータa
#         gshp_bh = [-1.1462, -1.8689, -2.4651, -3.091, -3.8325];   % 地盤モデル：暖房時パラメータb
#         gshp_ch = [-0.1128, -0.1846, -0.2643, -0.2926, -0.3474];  % 地盤モデル：暖房時パラメータc
#         gshp_dh = [0.1256, 0.2023, 0.2623, 0.3085, 0.3629];       % 地盤モデル：暖房時パラメータd
#         gshp_ac = [8.0633, 12.6226, 16.1703, 19.6565, 21.8702];   % 地盤モデル：冷房時パラメータa
#         gshp_bc = [2.9083, 4.7711, 6.3128, 7.8071, 9.148];        % 地盤モデル：冷房時パラメータb
#         gshp_cc = [0.0613, 0.0568, 0.1027, 0.1984, 0.249];        % 地盤モデル：冷房時パラメータc
#         gshp_dc = [0.2178, 0.3509, 0.4697, 0.5903, 0.7154];       % 地盤モデル：冷房時パラメータd
        
#         ghspToa_ave = [5.8, 7.5, 10.2, 11.6, 13.3, 15.7, 17.4, 22.7]; % 地盤モデル：年平均外気温
#         gshpToa_h   = [-3, -0.8, 0, 1.1, 3.6, 6, 9.3, 17.5];          % 地盤モデル：暖房時平均外気温
#         gshpToa_c   = [16.8,17,18.9,19.6,20.5,22.4,22.1,24.6];        % 地盤モデル：冷房時平均外気温
        
#         % 冷房負荷と暖房負荷の比率（地中熱ヒートポンプ用）　← 冷房用と暖房用熱源は順に並んでいる
#         ghsp_Rq = zeros(1,numOfRefs);
#         for iREFc = 1:numOfRefs/2
#             Qcmax = abs( max(Qref(:,2*iREFc-1))); % 先に冷房
#             Qhmax = abs( max(Qref(:,2*iREFc)));   % 次に暖房
            
#             % 冷熱・温熱に分けて熱源群を作成したときの例外処理（2017/3/7）
#             if Qcmax == 0
#                 Qcmax = Qhmax;
#             elseif Qhmax == 0
#                 Qhmax = Qcmax;
#             end
            
#             ghsp_Rq(2*iREFc-1) = (Qcmax-Qhmax)/(Qcmax+Qhmax); % 冷房
#             ghsp_Rq(2*iREFc)   = (Qcmax-Qhmax)/(Qcmax+Qhmax); % 暖房
#         end
        
#         switch climateAREA
#             case {'Ia','1'}
#                 iAREA = 1;
#             case {'Ib','2'}
#                 iAREA = 2;
#             case {'II','3'}
#                 iAREA = 3;
#             case {'III','4'}
#                 iAREA = 4;
#             case {'IVa','5'}
#                 iAREA = 5;
#             case {'IVb','6'}
#                 iAREA = 6;
#             case {'V','7'}
#                 iAREA = 7;
#             case {'VI','8'}
#                 iAREA = 8;
#             otherwise
#                 error('地域区分が不正です')
#         end
        
# end

# for iREF = 1:numOfRefs
#     % 熱源機器別の設定
#     for iREFSUB = 1:refsetRnum(iREF)
        
#         % 熱源種類
#         tmprefset = refset_Type{iREF,iREFSUB};
        
#         if isempty( tmprefset ) == 0
            
#             % 冷却水変流量制御の有無
#             if endsWith(tmprefset, '_CTVWV')
#                 checkCTVWV(iREF,iREFSUB) = 1;
#             else
#                 checkCTVWV(iREF,iREFSUB) = 0;
#             end
            
#             % 発電機能の有無
#             switch tmprefset
#                 case {'GasHeatPumpAirConditioner_GE_CityGas','GasHeatPumpAirConditioner_GE_LPG'}
#                     checkGEGHP(iREF,iREFSUB) = 1;
#                 otherwise
#                     checkGEGHP(iREF,iREFSUB) = 0;
#             end
            
#             refmatch = 0; % チェック用
            
#             % データベースを検索
#             if isempty(tmprefset) == 0
                
#                 % 該当する箇所をすべて抜き出す
#                 refParaSetALL = {};
#                 for iDB = 2:size(perDB_refList,1)
#                     if strcmp(perDB_refList(iDB,1),tmprefset)
#                         refParaSetALL = [refParaSetALL;perDB_refList(iDB,:)];
#                     end
#                 end
                
#                 % データベースファイルに熱源機器の特性がない場合
#                 if isempty(refParaSetALL)
#                     error('熱源 %s の特性が見つかりません',tmprefset)
#                 end
                
#                 % 燃料種類＋一次エネルギー換算 [kW]
#                 switch refParaSetALL{1,3}
#                     case '電力'
#                         refInputType(iREF,iREFSUB) = 1;
#                         refset_MainPowerELE(iREF,iREFSUB) = (9760/3600)*refset_MainPower(iREF,iREFSUB);
#                     case 'ガス'
#                         refInputType(iREF,iREFSUB) = 2;
#                         % refset_MainPowerELE(iREF,iREFSUB) = (45000/3600)*refset_MainPower(iREF,iREFSUB);  % 20130607 燃料消費量に変更
#                         refset_MainPowerELE(iREF,iREFSUB) = refset_MainPower(iREF,iREFSUB);
#                     case '重油'
#                         refInputType(iREF,iREFSUB) = 3;
#                         % refset_MainPowerELE(iREF,iREFSUB) = (41000/3600)*refset_MainPower(iREF,iREFSUB);  % 20130607 燃料消費量に変更
#                         refset_MainPowerELE(iREF,iREFSUB) = refset_MainPower(iREF,iREFSUB);
#                     case '灯油'
#                         refInputType(iREF,iREFSUB) = 4;
#                         % refset_MainPowerELE(iREF,iREFSUB) = (37000/3600)*refset_MainPower(iREF,iREFSUB);  % 20130607 燃料消費量に変更
#                         refset_MainPowerELE(iREF,iREFSUB) = refset_MainPower(iREF,iREFSUB);
#                     case '液化石油ガス'
#                         refInputType(iREF,iREFSUB) = 5;
#                         % refset_MainPowerELE(iREF,iREFSUB) = (50000/3600)*refset_MainPower(iREF,iREFSUB);  % 20130607 燃料消費量に変更
#                         refset_MainPowerELE(iREF,iREFSUB) = refset_MainPower(iREF,iREFSUB);
#                     case '蒸気'
#                         refInputType(iREF,iREFSUB) = 6;
#                         % エネルギー消費量＝生成熱量とする。
#                         refset_MainPower(iREF,iREFSUB) = refset_Capacity(iREF,iREFSUB);
#                         refset_MainPowerELE(iREF,iREFSUB) = (copDHC_heating)*refset_MainPower(iREF,iREFSUB);
#                     case '温水'
#                         refInputType(iREF,iREFSUB) = 7;
#                         % エネルギー消費量＝生成熱量とする。
#                         refset_MainPower(iREF,iREFSUB) = refset_Capacity(iREF,iREFSUB);
#                         refset_MainPowerELE(iREF,iREFSUB) = (copDHC_heating)*refset_MainPower(iREF,iREFSUB);
#                     case '冷水'
#                         refInputType(iREF,iREFSUB) = 8;
#                         % エネルギー消費量＝生成熱量とする。
#                         refset_MainPower(iREF,iREFSUB) = refset_Capacity(iREF,iREFSUB);
#                         refset_MainPowerELE(iREF,iREFSUB) = (copDHC_cooling)*refset_MainPower(iREF,iREFSUB);
#                     otherwise
#                         error('熱源 %s の燃料種別が不正です',tmprefset)
#                 end
                
#                 % 冷却方式
#                 switch refParaSetALL{1,4}
#                     case '水'
#                         refHeatSourceType(iREF,iREFSUB) = 1;
#                     case '空気'
#                         refHeatSourceType(iREF,iREFSUB) = 2;
#                     case '不要'
#                         refHeatSourceType(iREF,iREFSUB) = 4;
#                     case {'地盤1'}
#                         refHeatSourceType(iREF,iREFSUB) = 3;
#                         igsType = 1;
#                     case {'地盤2'}
#                         refHeatSourceType(iREF,iREFSUB) = 3;
#                         igsType = 2;
#                     case {'地盤3'}
#                         refHeatSourceType(iREF,iREFSUB) = 3;
#                         igsType = 3;
#                     case {'地盤4'}
#                         refHeatSourceType(iREF,iREFSUB) = 3;
#                         igsType = 4;
#                     case {'地盤5'}
#                         refHeatSourceType(iREF,iREFSUB) = 3;
#                         igsType = 5;
#                     otherwise
#                         error('熱源 %s の冷却方式が不正です',tmprefset)
#                 end
                
#                 % 能力比、入力比の変数
#                 if refHeatSourceType(iREF,iREFSUB) == 1 && REFtype(iREF) == 1   % 水冷／冷房
#                     xT = TctwC;   % 冷却水温度
#                 elseif refHeatSourceType(iREF,iREFSUB) == 1 && REFtype(iREF) == 2   % 水冷／暖房
#                     xT = TctwH;   % 冷却水温度
                    
#                 elseif refHeatSourceType(iREF,iREFSUB) == 2 && REFtype(iREF) == 1   % 空冷／冷房
#                     xT = ToadbC;  % 乾球温度
#                 elseif refHeatSourceType(iREF,iREFSUB) == 2 && REFtype(iREF) == 2   % 空冷／暖房
#                     xT = ToawbH;  % 湿球温度
                    
#                 elseif refHeatSourceType(iREF,iREFSUB) == 4 && REFtype(iREF) == 1   % 不要／冷房
#                     xT = ToadbC;  % 乾球温度
#                 elseif refHeatSourceType(iREF,iREFSUB) == 4 && REFtype(iREF) == 2   % 不要／暖房
#                     xT = ToadbH;  % 乾球温度
                    
#                 elseif refHeatSourceType(iREF,iREFSUB) == 3 && REFtype(iREF) == 1   % 地中熱／冷房
                    
#                     % 地盤からの還り温度（冷房）
#                     xT = ( gshp_cc(igsType) * ghsp_Rq(iREF) + gshp_dc(igsType) ) .* ( ToadbC - gshpToa_c(iAREA) ) + ...
#                         (ghspToa_ave(iAREA) + gshp_ac(igsType) * ghsp_Rq(iREF) + gshp_bc(igsType));
                    
#                 elseif refHeatSourceType(iREF,iREFSUB) == 3 && REFtype(iREF) == 2   % 地中熱／暖房
                    
#                     % 地盤からの還り温度（暖房）
#                     xT = ( gshp_ch(igsType) * ghsp_Rq(iREF) + gshp_dh(igsType) ) .* ( ToadbH - gshpToa_h(iAREA) ) + ...
#                         (ghspToa_ave(iAREA) + gshp_ah(igsType) * ghsp_Rq(iREF) + gshp_bh(igsType));
                    
#                 else
#                     error('モードが不正です')
#                 end
                
#                 % 外気温度の軸（マトリックスの縦軸）
#                 xTALL(iREF,iREFSUB,:) = xT;
                
#                 % 能力比と入力比
#                 for iPQXW = 1:4
                    
#                     if iPQXW == 1
#                         PQname = '能力比';
#                         Vname  = 'xQratio';
#                     elseif iPQXW == 2
#                         PQname = '入力比';
#                         Vname  = 'xPratio';
#                     elseif iPQXW == 3
#                         PQname = '部分負荷特性';
#                     elseif iPQXW == 4
#                         PQname = '送水温度特性';
#                     end
                    
#                     % データベースから該当箇所を抜き出し（特性が2つ以上の式で表現されている場合、該当箇所が複数ある）
#                     paraQ = {};
#                     for iDB = 1:size(refParaSetALL,1)
#                         if strcmp(refParaSetALL(iDB,5),refsetMode{iREF}) && strcmp(refParaSetALL(iDB,6),PQname)
#                             paraQ = [paraQ;  refParaSetALL(iDB,:)];
#                         end
#                     end
                    
#                     % 値の抜き出し
#                     tmpdata   = [];
#                     tmpdataMX = [];
#                     if isempty(paraQ) == 0
#                         for iDBQ = 1:size(paraQ,1)
                            
#                             % 機器特性データベース perDB_refCurve を探査
#                             for iLIST = 2:size(perDB_refCurve,1)
#                                 if strcmp(paraQ(iDBQ,9),perDB_refCurve(iLIST,2))
#                                     % 最小値、最大値、基整促係数、パラメータ（x4,x3,x2,x1,a）
#                                     tmpdata = [tmpdata;str2double(paraQ(iDBQ,[7,8,10])),str2double(perDB_refCurve(iLIST,4:8))];
                                    
#                                     if iPQXW == 3
#                                         tmpdataMX = [tmpdataMX; str2double(paraQ(iDBQ,12))];  % 当該特性の冷却水温度適用最大値（該当機器のみ）
#                                     end
                                    
#                                 end
#                             end
#                         end
#                     end
                    
#                     % 係数（基整促係数込み）
#                     if iPQXW == 1 || iPQXW == 2
#                         for i = 1:length(ToadbC)
#                             eval(['',Vname,'(iREF,iREFSUB,i) = mytfunc_REFparaSET(tmpdata,xT(i));'])
#                         end
                        
#                     elseif iPQXW == 3
#                         if isempty(tmpdata) == 0
#                             for iX = 1:size(tmpdata,1)
#                                 RerPerC_x_min(iREF,iREFSUB,iX)    = tmpdata(iX,1);
#                                 RerPerC_x_max(iREF,iREFSUB,iX)    = tmpdata(iX,2);
#                                 RerPerC_x_coeffi(iREF,iREFSUB,iX,1)  = tmpdata(iX,4);
#                                 RerPerC_x_coeffi(iREF,iREFSUB,iX,2)  = tmpdata(iX,5);
#                                 RerPerC_x_coeffi(iREF,iREFSUB,iX,3)  = tmpdata(iX,6);
#                                 RerPerC_x_coeffi(iREF,iREFSUB,iX,4)  = tmpdata(iX,7);
#                                 RerPerC_x_coeffi(iREF,iREFSUB,iX,5)  = tmpdata(iX,8);
#                             end
#                         else
#                             disp('特性が見つからないため、デフォルト特性を適用')
#                             RerPerC_x_min(iREF,iREFSUB,1)    = 0;
#                             RerPerC_x_max(iREF,iREFSUB,1)    = 0;
#                             RerPerC_x_coeffi(iREF,iREFSUB,1,1)  = 0;
#                             RerPerC_x_coeffi(iREF,iREFSUB,1,2)  = 0;
#                             RerPerC_x_coeffi(iREF,iREFSUB,1,3)  = 0;
#                             RerPerC_x_coeffi(iREF,iREFSUB,1,4)  = 0;
#                             RerPerC_x_coeffi(iREF,iREFSUB,1,5)  = 1;
#                         end
#                         if isempty(tmpdataMX) == 0
#                             % 当該特性の冷却水温度適用最大値（該当機器のみ）
#                             for iMX = 1:length(tmpdataMX)
#                                 xXratioMX(iREF,iREFSUB,iMX) = tmpdataMX(iMX);
#                             end
#                         end
                        
#                     elseif iPQXW == 4
#                         if isempty(tmpdata) == 0
#                             RerPerC_w_min(iREF,iREFSUB)    = tmpdata(1,1);
#                             RerPerC_w_max(iREF,iREFSUB)    = tmpdata(1,2);
#                             RerPerC_w_coeffi(iREF,iREFSUB,1)  = tmpdata(1,4);
#                             RerPerC_w_coeffi(iREF,iREFSUB,2)  = tmpdata(1,5);
#                             RerPerC_w_coeffi(iREF,iREFSUB,3)  = tmpdata(1,6);
#                             RerPerC_w_coeffi(iREF,iREFSUB,4)  = tmpdata(1,7);
#                             RerPerC_w_coeffi(iREF,iREFSUB,5)  = tmpdata(1,8);
#                         else
#                             RerPerC_w_min(iREF,iREFSUB)       = 0;
#                             RerPerC_w_max(iREF,iREFSUB)       = 0;
#                             RerPerC_w_coeffi(iREF,iREFSUB,1)  = 0;
#                             RerPerC_w_coeffi(iREF,iREFSUB,2)  = 0;
#                             RerPerC_w_coeffi(iREF,iREFSUB,3)  = 0;
#                             RerPerC_w_coeffi(iREF,iREFSUB,4)  = 0;
#                             RerPerC_w_coeffi(iREF,iREFSUB,5)  = 1;
#                         end
                        
#                     end
                    
#                 end
                
#                 refmatch = 1; % 処理済みの証拠
                
#             end
            
#             if isempty(tmprefset)== 0 && refmatch == 0
#                 error('熱源名称 %s は不正です',tmprefset);
#             end
            
#         end
#     end
# end


# %% 熱源エネルギー計算

# MxREF     = zeros(length(ToadbC),length(mxL),numOfRefs);  % 熱源負荷の出現頻度マトリックス（縦軸：外気温度、横軸：負荷率）
# MxREFnum  = zeros(length(ToadbC),length(mxL),numOfRefs);
# MxREFxL   = zeros(length(ToadbC),length(mxL),numOfRefs);
# MxREFperE = zeros(length(ToadbC),length(mxL),numOfRefs);
# MxREF_E   = zeros(numOfRefs,length(mxL));

# MxREFSUBperE = zeros(length(ToadbC),length(mxL),numOfRefs,10);
# MxREFSUBperQ = zeros(length(ToadbC),length(mxL),numOfRefs,10);
# MxREFSUBE = zeros(numOfRefs,10,length(mxL));
# Qrefr_mod = zeros(numOfRefs,10,length(ToadbC));
# Erefr_mod = zeros(numOfRefs,10,length(ToadbC));

# hoseiStorage = ones(length(ToadbC),length(mxL),numOfRefs);  % 蓄熱槽があるシステムの追い掛け時の補正係数 2014/1/10

# % 時刻別計算用
# LtREF = zeros(8760,numOfRefs);  % 熱源の負荷率区分
# TtREF = zeros(8760,numOfRefs);  % 熱源の温度区分
# E_ref_hour = zeros(8760,numOfRefs);      % 熱源主機のエネルギー消費量
# E_ref_ACc_hour = zeros(8760,numOfRefs);  % 補機電力 [MWh]
# E_PPc_hour = zeros(8760,numOfRefs);      % 一次ポンプ電力 [MWh]
# E_CTfan_hour = zeros(8760,numOfRefs);    % 冷却塔ファン電力 [MWh]
# E_CTpump_hour = zeros(8760,numOfRefs);   % 冷却水ポンプ電力 [MWh]
# E_refsys_hour = zeros(8760,numOfRefs,max(refsetRnum));      % 熱源機器ごとのエネルギー消費量
# Q_refsys_hour = zeros(8760,numOfRefs,max(refsetRnum));      % 熱源機器ごとの処理熱量[kW]

# % 日別計算用
# LdREF = zeros(365,numOfRefs);  % 熱源の負荷率区分
# TdREF = zeros(365,numOfRefs);  % 熱源の温度区分
# TimedREF =  zeros(365,numOfRefs);  % 熱源の運転時間
# E_ref_day     =  zeros(365,numOfRefs);
# E_ref_ACc_day =  zeros(365,numOfRefs);   % 補機電力 [MWh]
# E_PPc_day     =  zeros(365,numOfRefs);   % 一次ポンプ電力 [MWh]
# E_CTfan_day   =  zeros(365,numOfRefs);   % 冷却塔ファン電力 [MWh]
# E_CTpump_day  =  zeros(365,numOfRefs);   % 冷却水ポンプ電力 [MWh]
# E_refsys_day  = zeros(365,numOfRefs,max(refsetRnum));      % 熱源機器ごとのエネルギー消費量
# Q_refsys_day  = zeros(365,numOfRefs,max(refsetRnum));      % 熱源機器ごとの処理熱量[kW]


# EctpumprALL = zeros(length(ToadbC),length(mxL),numOfRefs);
# ErefaprALL = zeros(length(ToadbC),length(mxL),numOfRefs);

# for iREF = 1:numOfRefs
    
#     % 蓄熱槽がある場合の放熱用熱交換器の容量の補正（mytstcript_readXML_Setting.mでは8時間を想定）
#     switch MODE
#         case {2,3,4}
#             tmpCapacityHEX = 0;
#             if REFstorage(iREF) == -1  && isempty(cell2mat(refset_Type(iREF,1))) == 0 % 放熱運転の場合
#                 if strcmp(refset_Type(iREF,1),'HEX') % 熱交換器は必ず1台目
#                     tmpCapacityHEX = refset_Capacity(iREF,1) *  (8/max(Tref(:,iREF)));  % 熱源運転時間の最大値で補正した容量
#                     QrefrMax(iREF) = QrefrMax(iREF) +  tmpCapacityHEX - refset_Capacity(iREF,1);  % 定格容量の合計値を修正
#                     refset_Capacity(iREF,1) = tmpCapacityHEX;   % 熱交換器の容量を修正
#                 else
#                     error('熱交換機が設定されていません')
#                 end
#             end
#     end
    
#     % 熱源負荷マトリックス
#     switch MODE
#         case {0}
            
#             % 時刻別の外気温度に変更（2016/2/3）
#             if REFtype(iREF) == 1
#                 [tmp,~] = mytfunc_matrixREF(MODE,Qref_hour(:,iREF),QrefrMax(iREF),[],OAdataHourly,mxTC,mxL);  % 冷房
#                 LtREF(:,iREF) = tmp(:,1);
#                 TtREF(:,iREF) = tmp(:,2);
#             else
#                 [tmp,~] = mytfunc_matrixREF(MODE,Qref_hour(:,iREF),QrefrMax(iREF),[],OAdataHourly,mxTH,mxL);  % 暖房
#                 LtREF(:,iREF) = tmp(:,1);
#                 TtREF(:,iREF) = tmp(:,2);
#             end
            
#         case {1}
#             if REFtype(iREF) == 1
#                 [MxREF(:,:,iREF),~]  = mytfunc_matrixREF(MODE,Qref_hour(:,iREF),QrefrMax(iREF),[],OAdataAll,mxTC,mxL);  % 冷房
#             else
#                 [MxREF(:,:,iREF),~]  = mytfunc_matrixREF(MODE,Qref_hour(:,iREF),QrefrMax(iREF),[],OAdataAll,mxTH,mxL);  % 暖房
#             end
            
#         case {2,3}
#             if REFtype(iREF) == 1
#                 [MxREF(:,:,iREF),~]  = mytfunc_matrixREF(MODE,Qref(:,iREF),QrefrMax(iREF),Tref(:,iREF),OAdataAll,mxTC,mxL);  % 冷房
#             else
#                 [MxREF(:,:,iREF),~]  = mytfunc_matrixREF(MODE,Qref(:,iREF),QrefrMax(iREF),Tref(:,iREF),OAdataAll,mxTH,mxL);  % 暖房
#             end
            
#         case {4}
#             if REFtype(iREF) == 1
#                 [tmp,TimedREF(:,iREF)]  = mytfunc_matrixREF(MODE,Qref(:,iREF),QrefrMax(iREF),Tref(:,iREF),OAdataAll,mxTC,mxL);  % 冷房
#                 LdREF(:,iREF) = tmp(:,1);
#                 TdREF(:,iREF) = tmp(:,2);
#             else
#                 [tmp,TimedREF(:,iREF)]  = mytfunc_matrixREF(MODE,Qref(:,iREF),QrefrMax(iREF),Tref(:,iREF),OAdataAll,mxTH,mxL);  % 暖房
#                 LdREF(:,iREF) = tmp(:,1);
#                 TdREF(:,iREF) = tmp(:,2);
#             end
#     end
    
    
#     % 最大能力、最大入力の設定
#     for iREFSUB = 1:refsetRnum(iREF)   % 熱源台数分だけ繰り返す
        
#         for iX = 1:length(ToadbC)
            
#             % 各外気温区分における最大能力 [kW]
#             Qrefr_mod(iREF,iREFSUB,iX) = refset_Capacity(iREF,iREFSUB) .* xQratio(iREF,iREFSUB,iX);
            
#             % 各外気温区分における最大入力 [kW]  (1次エネルギー換算値であることに注意）
#             Erefr_mod(iREF,iREFSUB,iX) = refset_MainPowerELE(iREF,iREFSUB) .* xPratio(iREF,iREFSUB,iX);
            
#             xqsave(iREF,iX) = xTALL(iREF,iREFSUB,iX);  % xTALL 外気温度の軸(結果表示用)
#             xpsave(iREF,iX) = xTALL(iREF,iREFSUB,iX);  % xTALL 外気温度の軸(結果表示用)
            
#         end
#     end
    
    
#     % 蓄熱の場合のマトリックス操作（負荷率１に集約＋外気温を１レベル変える）
#     switch MODE
#         case {0}
            
#             % 外気温をシフト（負荷率帯の集約は今後の課題）
#             if REFstorage(iREF) == 1
#                 for hh = 1:8760
#                     if TtREF(hh,iREF) > 1
#                         TtREF(hh,iREF) = TtREF(hh,iREF) - 1;
#                     end
#                 end
#             end
            
#         case {1,2,3}
#             if REFstorage(iREF) == 1
#                 for iX = 1:length(ToadbC)
#                     timeQmax = 0;
#                     for iY = 1:length(aveL)
#                         timeQmax = timeQmax + aveL(iY)*MxREF(iX,iY,iREF)*QrefrMax(iREF);
#                         MxREF(iX,iY,iREF) = 0;
#                     end
#                     % 全負荷相当運転時間 [hour] →　各外気温帯の最大能力で運転時間を出すように変更（H25.12.25）
#                     if iX ~=1
#                         MxREF(iX,length(aveL)-1,iREF) = timeQmax./( sum(Qrefr_mod(iREF,:,iX-1)) );
#                     else
#                         MxREF(iX,length(aveL)-1,iREF) = timeQmax./( sum(Qrefr_mod(iREF,:,iX)) );
#                     end
#                 end
                
#                 % 外気温をシフト
#                 for iX = 1:length(ToadbC)
#                     if iX == 1
#                         MxREF(iX,:,iREF) = MxREF(iX,:,iREF) + MxREF(iX+1,:,iREF);
#                     elseif iX == length(ToadbC)
#                         MxREF(iX,:,iREF) = zeros(1,length(aveL));
#                     else
#                         MxREF(iX,:,iREF) = MxREF(iX+1,:,iREF);
#                     end
#                 end
#             end
            
#         case {4}
            
#             if REFstorage(iREF) == 1
                
#                 for dd = 1:365
                    
#                     if LdREF(dd,iREF) > 0   % これを入れないと aveL(LdREF)でエラーとなる。
                        
#                         % 負荷率対 LdREF のときの熱負荷
#                         timeQmax =  aveL(LdREF(dd,iREF))*TimedREF(dd,iREF)*QrefrMax(iREF);
                        
#                         % 全負荷相当運転時間（熱負荷を最大負荷で除す）
#                         if TdREF(dd,iREF) > 1
#                             TimedREF(dd,iREF) = timeQmax./( sum(Qrefr_mod(iREF,:,TdREF(dd,iREF)-1)) );
#                         elseif TdREF(dd,iREF) == 1
#                             TimedREF(dd,iREF) = timeQmax./( sum(Qrefr_mod(iREF,:,TdREF(dd,iREF))) );
#                         end
                        
#                         if LdREF(dd,iREF) > 0
#                             LdREF(dd,iREF) = length(aveL)-1;   % 最大負荷率帯にする。
                            
#                             if TdREF(dd,iREF) > 1
#                                 TdREF(dd,iREF) = TdREF(dd,iREF) - 1; % 外気温帯を1つ下げる。
#                             elseif TdREF(dd,iREF) == 1
#                                 TdREF(dd,iREF) = TdREF(dd,iREF);
#                             end
#                         end
                        
#                     end
                    
#                 end
#             end
            
#     end
    
    
#     % 運転台数
#     if REFnumctr(iREF) == 0  % 台数制御なし
        
#         MxREFnum(:,:,iREF) = refsetRnum(iREF).*ones(length(ToadbC),length(mxL));
        
#     elseif REFnumctr(iREF) == 1 % 台数制御あり
#         for ioa = 1:length(ToadbC)
#             for iL = 1:length(mxL)
                
#                 % 処理負荷 [kW]
#                 tmpQ  = QrefrMax(iREF)*aveL(iL);
                
#                 % 運転台数 MxREFnum
#                 for rr = 1:refsetRnum(iREF)
#                     % 1台～rr台までの最大能力合計値
#                     tmpQmax = sum(Qrefr_mod(iREF,1:rr,ioa));
                    
#                     if tmpQ < tmpQmax
#                         break
#                     end
#                 end
#                 MxREFnum(ioa,iL,iREF) = rr;
                
#             end
#         end
#     end
    
    
#     % 部分負荷率
    
#     for ioa = 1:length(ToadbC)
#         for iL = 1:length(mxL)
            
#             % 処理負荷 [kW]
#             tmpQ  = QrefrMax(iREF)*aveL(iL);
            
#             % [ioa,iL]における負荷率
#             MxREFxL(ioa,iL,iREF) = tmpQ ./ sum(Qrefr_mod(iREF,1:MxREFnum(ioa,iL,iREF),ioa));
            
            
#             % 蓄熱の場合のマトリックス操作（蓄熱運転時は必ず負荷率＝１）（H25.12.25）
#             switch MODE
#                 case {1,2,3,4}
#                     if REFstorage(iREF) == 1
#                         MxREFxL(ioa,iL,iREF) = 1;
#                     end
#             end
            
            
#             % 部分負荷特性と送水温度特性（各負荷率・各温度帯について）
#             for iREFSUB = 1:MxREFnum(ioa,iL,iREF)
                
#                 % どの部分負荷特性を使うか（インバータターボなど、冷却水温度によって特性が異なる場合がある）
#                 if isnan(xXratioMX(iREF,iREFSUB)) == 0
#                     if xTALL(iREF,iREFSUB,ioa) <= xXratioMX(iREF,iREFSUB,1)
#                         xCurveNum = 1;
#                     elseif xTALL(iREF,iREFSUB,ioa) <= xXratioMX(iREF,iREFSUB,2)
#                         xCurveNum = 2;
#                     elseif xTALL(iREF,iREFSUB,ioa) <= xXratioMX(iREF,iREFSUB,3)
#                         xCurveNum = 3;
#                     else
#                         error('特性式の上限を超えています')
#                     end
#                 else
#                     xCurveNum = 1;
#                 end
                
#                 % 部分負荷特性の上下限
#                 MxREFxL_real(ioa,iL,iREF) = MxREFxL(ioa,iL,iREF);
                
#                 if MxREFxL(ioa,iL,iREF) < RerPerC_x_min(iREF,iREFSUB,xCurveNum)
#                     MxREFxL(ioa,iL,iREF) = RerPerC_x_min(iREF,iREFSUB,xCurveNum);
#                 elseif MxREFxL(ioa,iL,iREF) > RerPerC_x_max(iREF,iREFSUB,xCurveNum) || iL == length(mxL)
#                     MxREFxL(ioa,iL,iREF) = RerPerC_x_max(iREF,iREFSUB,xCurveNum);
#                 end
#                 tmpL = MxREFxL(ioa,iL,iREF);
                
                
#                 % 部分負荷特性
#                 coeff_x(iREFSUB) = ...
#                     RerPerC_x_coeffi(iREF,iREFSUB,xCurveNum,1).*tmpL.^4 + ...
#                     RerPerC_x_coeffi(iREF,iREFSUB,xCurveNum,2).*tmpL.^3 + ...
#                     RerPerC_x_coeffi(iREF,iREFSUB,xCurveNum,3).*tmpL.^2 + ...
#                     RerPerC_x_coeffi(iREF,iREFSUB,xCurveNum,4).*tmpL + ...
#                     RerPerC_x_coeffi(iREF,iREFSUB,xCurveNum,5);
                
#                 if iL == length(mxL)
#                     coeff_x(iREFSUB) = coeff_x(iREFSUB).* 1.2;  % 過負荷時のペナルティ（要検討）
#                 end
                
#                 % 送水温度特性の上下限
#                 if refset_SupplyTemp(iREF,iREFSUB) < RerPerC_w_min(iREF,iREFSUB)
#                     TCtmp = RerPerC_w_min(iREF,iREFSUB);
#                 elseif refset_SupplyTemp(iREF,iREFSUB) > RerPerC_w_max(iREF,iREFSUB)
#                     TCtmp = RerPerC_w_max(iREF,iREFSUB);
#                 else
#                     TCtmp = refset_SupplyTemp(iREF,iREFSUB);
#                 end
                
#                 % 送水温度特性
#                 coeff_tw(iREFSUB) = RerPerC_w_coeffi(iREF,iREFSUB,1).*TCtmp.^4 + ...
#                     RerPerC_w_coeffi(iREF,iREFSUB,2).*TCtmp.^3 + RerPerC_w_coeffi(iREF,iREFSUB,3).*TCtmp.^2 +...
#                     RerPerC_w_coeffi(iREF,iREFSUB,4).*TCtmp + RerPerC_w_coeffi(iREF,iREFSUB,5);
                
#             end
            
            
#             % エネルギー消費量 [kW] (1次エネルギー換算後の値であることに注意）
#             switch MODE
                
#                 case {0}
#                     for rr = 1:MxREFnum(ioa,iL,iREF)
#                         % エネルギー消費量
#                         MxREFSUBperE(ioa,iL,iREF,rr) = Erefr_mod(iREF,rr,ioa).*coeff_x(rr).*coeff_tw(rr);
#                         % 処理熱量
#                         MxREFSUBperQ(ioa,iL,iREF,rr) = Qrefr_mod(iREF,rr,ioa).* MxREFxL_real(ioa,iL,iREF);
#                     end
                    
#                 case {1,2,3,4}
#                     for rr = 1:MxREFnum(ioa,iL,iREF)
#                         % エネルギー消費量
#                         MxREFSUBperE(ioa,iL,iREF,rr) = Erefr_mod(iREF,rr,ioa).*coeff_x(rr).*coeff_tw(rr);
#                         MxREFperE(ioa,iL,iREF) = MxREFperE(ioa,iL,iREF) + MxREFSUBperE(ioa,iL,iREF,rr);
#                     end
                    
#             end
#         end
        
#     end
    
#     % 補機群のエネルギー消費量
#     for ioa = 1:length(ToadbC)
#         for iL = 1:length(mxL)
            
#             % 一台あたりの負荷率
#             aveLperU = MxREFxL_real(ioa,iL,iREF);
            
#             if iL == length(mxL)
#                 aveLperU = 1.2;
#             end
            
#             % 補機電力
#             if sum(checkGEGHP(iREF,:)) >= 1
                
#                 for iREFSUB = 1:MxREFnum(ioa,iL,iREF)
#                     if checkGEGHP(iREF,iREFSUB) == 1
                        
#                         % 発電機能ありの機種
#                         if REFtype(iREF) == 1  % 冷房
#                             E_nonGE = refset_Capacity(iREF,iREFSUB) * 0.017;  % 非発電時の消費電力 [kW]
#                         elseif REFtype(iREF) == 2  % 暖房
#                             E_nonGE = refset_Capacity(iREF,iREFSUB) * 0.012;  % 非発電時の消費電力 [kW]
#                         end
                        
#                         E_GE = refset_SubPower(iREF,iREFSUB); % 発電時の消費電力 [kW]
                        
#                         if aveLperU <= 0.3
#                             ErefaprALL(ioa,iL,iREF)  = ErefaprALL(ioa,iL,iREF) + ( 0.3 * E_nonGE - (E_nonGE - E_GE) * aveLperU );
#                         else
#                             ErefaprALL(ioa,iL,iREF)  = ErefaprALL(ioa,iL,iREF) + aveLperU * E_GE;
#                         end
                        
#                     else
#                         % 発電機能なしの機種
#                         if aveLperU <= 0.3
#                             ErefaprALL(ioa,iL,iREF)  = ErefaprALL(ioa,iL,iREF) + 0.3 * refset_SubPower(iREF,iREFSUB);
#                         else
#                             ErefaprALL(ioa,iL,iREF)  = ErefaprALL(ioa,iL,iREF) + aveLperU * refset_SubPower(iREF,iREFSUB);
#                         end
#                     end
#                 end
                
#             else
                
#                 % 負荷に比例させる（発電機能なし）
#                 if aveLperU <= 0.3
#                     ErefaprALL(ioa,iL,iREF)  = 0.3 * sum( refset_SubPower(iREF,1:MxREFnum(ioa,iL,iREF)));
#                 else
#                     ErefaprALL(ioa,iL,iREF)  = aveLperU * sum( refset_SubPower(iREF,1:MxREFnum(ioa,iL,iREF)));
#                 end
                
#             end
            
#             EpprALL(ioa,iL,iREF)     = sum( refset_PrimaryPumpPower(iREF,1:MxREFnum(ioa,iL,iREF)));  % 一次ポンプ
#             EctfanrALL(ioa,iL,iREF)  = sum( refset_CTFanPower(iREF,1:MxREFnum(ioa,iL,iREF)));        % 冷却塔ファン
            
#             % 冷却水ポンプ
#             if sum(checkCTVWV(iREF,:)) >= 1  % 変流量制御あり
                
#                 for iREFSUB = 1:MxREFnum(ioa,iL,iREF)
#                     if checkCTVWV(iREF,iREFSUB) == 1
#                         % 変流量ありの機種
#                         if aveLperU <= 0.5
#                             EctpumprALL(ioa,iL,iREF) = EctpumprALL(ioa,iL,iREF) + 0.5 * refset_CTPumpPower(iREF,iREFSUB);
#                         else
#                             EctpumprALL(ioa,iL,iREF) = EctpumprALL(ioa,iL,iREF) + aveLperU * refset_CTPumpPower(iREF,iREFSUB);
#                         end
#                     else
#                         % 変流量なしの機種
#                         EctpumprALL(ioa,iL,iREF) = EctpumprALL(ioa,iL,iREF) + refset_CTPumpPower(iREF,iREFSUB);
#                     end
#                 end
                
#             else
#                 EctpumprALL(ioa,iL,iREF) = sum( refset_CTPumpPower(iREF,1:MxREFnum(ioa,iL,iREF)));
#             end
            
#         end
#     end
    
#     % 蓄熱槽を持つシステムの追い掛け時運転時間補正（追い掛け運転開始時に蓄熱量がすべて使われない問題を解消） 2014/1/10
#     switch MODE
#         case {1,2,3,4}
#             if REFstorage(iREF) == -1 && refsetStorageSize(iREF)>0
#                 for ioa = 1:length(ToadbC)
#                     for iL = 1:length(mxL)
#                         if MxREFnum(ioa,iL,iREF) >= 2
#                             % hoseiStorage(ioa,iL,iREF) = 1 - ( Qrefr_mod(iREF,1,ioa)*(1-MxREFxL(ioa,iL,iREF)) / (MxREFxL(ioa,iL,iREF)*sum( Qrefr_mod(iREF,2:MxREFnum(ioa,iL,iREF),ioa) )) );
#                             hoseiStorage(ioa,iL,iREF) = 1 - ( Qrefr_mod(iREF,1,ioa)*(1-MxREFxL_real(ioa,iL,iREF)) / (MxREFxL_real(ioa,iL,iREF)*sum( Qrefr_mod(iREF,2:MxREFnum(ioa,iL,iREF),ioa) )) );
#                         else
#                             hoseiStorage(ioa,iL,iREF) = 1.0;
#                         end
#                     end
#                 end
                
#                 switch MODE
#                     case {1,2,3}
#                         MxREF(:,:,iREF) = MxREF(:,:,iREF) .* hoseiStorage(:,:,iREF);  % 運転時間を補正
#                     case {4}
#                         for dd = 1:365
#                             TimedREF(dd,iREF) = TimedREF(dd,iREF) .* hoseiStorage(TdREF(dd,iREF),LdREF(dd,iREF),iREF);  % 運転時間を補正
#                         end
#                 end
#             end
#     end
    
#     switch MODE
#         case {0}
            
#             for dd = 1:365
#                 for hh = 1:24
                    
#                     % 1月1日0時からの時間数
#                     num = 24*(dd-1)+hh;
                    
#                     % 熱源のエネルギー消費量 [MJ]（一次エネ換算値）
#                     if LtREF(num,iREF) == 0 && (REFstorage(iREF) == -1 && Qref_hour_discharge(num,iREF) > 0) % 放熱のみ
#                         E_ref_hour(num,iREF)     =  0;
#                         E_ref_ACc_hour(num,iREF) =  0;   % 補機電力 [MWh]
#                         E_PPc_hour(num,iREF)     =  refset_PrimaryPumpPower_discharge(iREF,1)./1000;   % 一次ポンプ電力 [MWh]
#                         E_CTfan_hour(num,iREF)   =  0;   % 冷却塔ファン電力 [MWh]
#                         E_CTpump_hour(num,iREF)  =  0;   % 冷却水ポンプ電力 [MWh]
                        
#                     elseif LtREF(num,iREF) == 0
#                         E_ref_hour(num,iREF)     =  0;
#                         E_ref_ACc_hour(num,iREF) =  0;   % 補機電力 [MWh]
#                         E_PPc_hour(num,iREF)     =  0;   % 一次ポンプ電力 [MWh]
#                         E_CTfan_hour(num,iREF)   =  0;   % 冷却塔ファン電力 [MWh]
#                         E_CTpump_hour(num,iREF)  =  0;   % 冷却水ポンプ電力 [MWh]
                        
#                     else
                        
#                         % サブ機器ごとに解くように変更　2016/02/04
#                         % 熱源群エネルギー消費量  MJ
#                         %  E_ref_hour(num,iREF)     =  MxREFperE(TtREF(num,iREF),LtREF(num,iREF),iREF).*3600/1000;
#                         for rr = 1:refsetRnum(iREF)
#                             E_refsys_hour(num,iREF,rr) = MxREFSUBperE(TtREF(num,iREF),LtREF(num,iREF),iREF,rr).*3600./1000;
#                             E_ref_hour(num,iREF)       = E_ref_hour(num,iREF) + E_refsys_hour(num,iREF,rr);
                            
#                             % サブ機器ごとの熱負荷　←　マトリックスを使っているので、厳密にQrefと一致しないので注意
#                             Q_refsys_hour(num,iREF,rr) = MxREFSUBperQ(TtREF(num,iREF),LtREF(num,iREF),iREF,rr);
#                         end
                        
#                         E_ref_ACc_hour(num,iREF) =  ErefaprALL(TtREF(num,iREF),LtREF(num,iREF),iREF)./1000;   % 補機電力 [MWh]
#                         E_PPc_hour(num,iREF) =  EpprALL(TtREF(num,iREF),LtREF(num,iREF),iREF)./1000;   % 一次ポンプ電力 [MWh]
                        
#                         if REFstorage(iREF) == -1 && Qref_hour_discharge(num,iREF) > 0  % 放熱運転時
#                             E_PPc_hour(num,iREF) =  E_PPc_hour(num,iREF) + refset_PrimaryPumpPower_discharge(iREF,1)./1000;  % 放熱用ポンプ
#                         end
                        
#                         E_CTfan_hour(num,iREF) =  EctfanrALL(TtREF(num,iREF),LtREF(num,iREF),iREF)./1000;   % 冷却塔ファン電力 [MWh]
#                         E_CTpump_hour(num,iREF) =  EctpumprALL(TtREF(num,iREF),LtREF(num,iREF),iREF)./1000;   % 冷却水ポンプ電力 [MWh]
#                     end
                    
                    
#                 end
#             end
            
            
#         case {1,2,3}
            
#             MxREF_E(iREF,:)   = nansum(MxREF(:,:,iREF) .* MxREFperE(:,:,iREF)).*3600/1000;  % 熱源群エネルギー消費量  [MJ]
#             MxREFACcE(iREF,:) = nansum(MxREF(:,:,iREF) .* ErefaprALL(:,:,iREF)./1000);  % 補機電力 [MWh]
#             MxPPcE(iREF,:)    = nansum(MxREF(:,:,iREF) .* EpprALL(:,:,iREF)./1000);     % 一次ポンプ電力 [MWh]
#             MxCTfan(iREF,:)   = nansum(MxREF(:,:,iREF) .* EctfanrALL(:,:,iREF)./1000);  % 冷却塔ファン電力 [MWh]
#             MxCTpump(iREF,:)  = nansum(MxREF(:,:,iREF) .* EctpumprALL(:,:,iREF)./1000); % 冷却水ポンプ電力 [MWh]
            
#             % 熱源別エネルギー消費量 [MJ]
#             for iREFSUB = 1:refsetRnum(iREF)
#                 MxREFSUBE(iREF,iREFSUB,:) = nansum(MxREF(:,:,iREF) .* MxREFSUBperE(:,:,iREF,iREFSUB).*3600)./1000;
#             end
            
#         case {4}
            
#             for dd = 1:365
                
#                 if LdREF(dd,iREF) == 0
                    
#                     E_ref_day(dd,iREF)     =  0;   % 熱源群エネルギー消費量 [MJ]
#                     E_ref_ACc_day(dd,iREF) =  0;   % 補機電力 [MWh]
#                     E_PPc_day(dd,iREF)     =  0;   % 一次ポンプ電力 [MWh]
#                     E_CTfan_day(dd,iREF)   =  0;   % 冷却塔ファン電力 [MWh]
#                     E_CTpump_day(dd,iREF)  =  0;   % 冷却水ポンプ電力 [MWh]
                    
#                 else
                    
#                     % E_ref_day(dd,iREF)     =  MxREFperE(TdREF(dd,iREF),LdREF(dd,iREF),iREF).*3600./1000 .* TimedREF(dd,iREF); % 熱源群エネルギー消費量 [MJ]
                    
#                     for rr = 1:refsetRnum(iREF)
#                         E_refsys_day(dd,iREF,rr) = MxREFSUBperE(TdREF(dd,iREF),LdREF(dd,iREF),iREF,rr).*3600./1000 .* TimedREF(dd,iREF);
#                         E_ref_day(dd,iREF)       = E_ref_day(dd,iREF) + E_refsys_day(dd,iREF,rr);
                        
#                         % サブ機器ごとの熱負荷　←　マトリックスを使っているので、厳密にQrefと一致しないので注意
#                         %                         Q_refsys_hour(num,iREF,rr) = MxREFSUBperQ(TtREF(num,iREF),LtREF(num,iREF),iREF,rr);
#                     end
                    
#                     E_ref_ACc_day(dd,iREF) =  ErefaprALL(TdREF(dd,iREF),LdREF(dd,iREF),iREF)./1000 .* TimedREF(dd,iREF);   % 補機電力 [MWh]
#                     E_PPc_day(dd,iREF)     =  EpprALL(TdREF(dd,iREF),LdREF(dd,iREF),iREF)./1000 .* TimedREF(dd,iREF);   % 一次ポンプ電力 [MWh]
#                     E_CTfan_day(dd,iREF)   =  EctfanrALL(TdREF(dd,iREF),LdREF(dd,iREF),iREF)./1000 .* TimedREF(dd,iREF);   % 冷却塔ファン電力 [MWh]
#                     E_CTpump_day(dd,iREF)  =  EctpumprALL(TdREF(dd,iREF),LdREF(dd,iREF),iREF)./1000 .* TimedREF(dd,iREF);   % 冷却水ポンプ電力 [MWh]
                    
#                 end
                
#             end
            
#     end
    
# end

# % 熱源群のエネルギー消費量
# switch MODE
#     case {0}
        
#         % 熱源主機のエネルギー消費量 [MJ]
#         E_refsysr = sum(E_ref_hour,1);
        
#         % 熱源主機のエネルギー消費量 [*] （各燃料の単位に戻す）
#         E_ref_source_hour = zeros(8760,8);
        
#         for iREF = 1:numOfRefs
#             for iREFSUB = 1:refsetRnum(iREF)
                
#                 if refInputType(iREF,iREFSUB) == 1
#                     E_ref_source_hour(:,refInputType(iREF,iREFSUB)) = E_ref_source_hour(:,refInputType(iREF,iREFSUB)) + E_refsys_hour(:,iREF,iREFSUB)./(9760);      % [MWh]
#                 elseif refInputType(iREF,iREFSUB) == 2
#                     E_ref_source_hour(:,refInputType(iREF,iREFSUB)) = E_ref_source_hour(:,refInputType(iREF,iREFSUB)) + E_refsys_hour(:,iREF,iREFSUB)./(45000/1000); % [m3/h]
#                 elseif refInputType(iREF,iREFSUB) == 3
#                     E_ref_source_hour(:,refInputType(iREF,iREFSUB)) = E_ref_source_hour(:,refInputType(iREF,iREFSUB)) + E_refsys_hour(:,iREF,iREFSUB)./(41000/1000);
#                 elseif refInputType(iREF,iREFSUB) == 4
#                     E_ref_source_hour(:,refInputType(iREF,iREFSUB)) = E_ref_source_hour(:,refInputType(iREF,iREFSUB)) + E_refsys_hour(:,iREF,iREFSUB)./(37000/1000);
#                 elseif refInputType(iREF,iREFSUB) == 5
#                     E_ref_source_hour(:,refInputType(iREF,iREFSUB)) = E_ref_source_hour(:,refInputType(iREF,iREFSUB)) + E_refsys_hour(:,iREF,iREFSUB)./(50000/1000);
#                 elseif refInputType(iREF,iREFSUB) == 6
#                     E_ref_source_hour(:,refInputType(iREF,iREFSUB)) = E_ref_source_hour(:,refInputType(iREF,iREFSUB)) + E_refsys_hour(:,iREF,iREFSUB)./(copDHC_heating);   % [MJ]
#                 elseif refInputType(iREF,iREFSUB) == 7
#                     E_ref_source_hour(:,refInputType(iREF,iREFSUB)) = E_ref_source_hour(:,refInputType(iREF,iREFSUB)) + E_refsys_hour(:,iREF,iREFSUB)./(copDHC_heating);   % [MJ]
#                 elseif refInputType(iREF,iREFSUB) == 8
#                     E_ref_source_hour(:,refInputType(iREF,iREFSUB)) = E_ref_source_hour(:,refInputType(iREF,iREFSUB)) + E_refsys_hour(:,iREF,iREFSUB)./(copDHC_cooling);   % [MJ]
#                 end
                
#             end
#         end
        
#         E_ref = sum(E_ref_source_hour,1); % 使わない
        
#         % 熱源補機電力消費量 [MWh]
#         E_refac = sum(sum(E_ref_ACc_hour));
#         % 一次ポンプ電力消費量 [MWh]
#         E_pumpP = sum(sum(E_PPc_hour));
#         % 冷却塔ファン電力消費量 [MWh]
#         E_ctfan = sum(sum(E_CTfan_hour));
#         % 冷却水ポンプ電力消費量 [MWh]
#         E_ctpump = sum(sum(E_CTpump_hour));
        
#     case {1,2,3}
        
#         % 熱源主機のエネルギー消費量 [MJ]
#         E_refsysr = sum(MxREF_E,2);
        
#         % 熱源主機のエネルギー消費量 [*] （各燃料の単位に戻す）
#         E_ref = zeros(1,8);
        
#         for iREF = 1:numOfRefs
#             for iREFSUB = 1:refsetRnum(iREF)
                
#                 if refInputType(iREF,iREFSUB) == 1
#                     E_ref(1,refInputType(iREF,iREFSUB)) = E_ref(1,refInputType(iREF,iREFSUB)) + sum(sum(MxREFSUBE(iREF,iREFSUB,:)))./(9760);      % [MWh]
#                 elseif refInputType(iREF,iREFSUB) == 2
#                     E_ref(1,refInputType(iREF,iREFSUB)) = E_ref(1,refInputType(iREF,iREFSUB)) + sum(sum(MxREFSUBE(iREF,iREFSUB,:)))./(45000/1000); % [m3/h]
#                 elseif refInputType(iREF,iREFSUB) == 3
#                     E_ref(1,refInputType(iREF,iREFSUB)) = E_ref(1,refInputType(iREF,iREFSUB)) + sum(sum(MxREFSUBE(iREF,iREFSUB,:)))./(41000/1000);
#                 elseif refInputType(iREF,iREFSUB) == 4
#                     E_ref(1,refInputType(iREF,iREFSUB)) = E_ref(1,refInputType(iREF,iREFSUB)) + sum(sum(MxREFSUBE(iREF,iREFSUB,:)))./(37000/1000);
#                 elseif refInputType(iREF,iREFSUB) == 5
#                     E_ref(1,refInputType(iREF,iREFSUB)) = E_ref(1,refInputType(iREF,iREFSUB)) + sum(sum(MxREFSUBE(iREF,iREFSUB,:)))./(50000/1000);
#                 elseif refInputType(iREF,iREFSUB) == 6
#                     E_ref(1,refInputType(iREF,iREFSUB)) = E_ref(1,refInputType(iREF,iREFSUB)) + sum(sum(MxREFSUBE(iREF,iREFSUB,:)))./(copDHC_heating);   % [MJ]
#                 elseif refInputType(iREF,iREFSUB) == 7
#                     E_ref(1,refInputType(iREF,iREFSUB)) = E_ref(1,refInputType(iREF,iREFSUB)) + sum(sum(MxREFSUBE(iREF,iREFSUB,:)))./(copDHC_heating);   % [MJ]
#                 elseif refInputType(iREF,iREFSUB) == 8
#                     E_ref(1,refInputType(iREF,iREFSUB)) = E_ref(1,refInputType(iREF,iREFSUB)) + sum(sum(MxREFSUBE(iREF,iREFSUB,:)))./(copDHC_cooling);   % [MJ]
#                 end
                
#             end
#         end
        
#         % 熱源補機電力消費量 [MWh]
#         E_refac = sum(sum(MxREFACcE));
#         % 一次ポンプ電力消費量 [MWh]
#         E_pumpP = sum(sum(MxPPcE));
#         % 冷却塔ファン電力消費量 [MWh]
#         E_ctfan = sum(sum(MxCTfan));
#         % 冷却水ポンプ電力消費量 [MWh]
#         E_ctpump = sum(sum(MxCTpump));
        
#     case {4}
        
#         % 熱源主機のエネルギー消費量 [MJ]
#         E_refsysr = sum(E_ref_day,1)';
        
#         % 熱源主機のエネルギー消費量 [*] （各燃料の単位に戻す）
#         E_ref_source_day = zeros(365,8);
#         E_ref_source_Ele_day = zeros(365,numOfRefs); % コジェネ計算用に熱源群単位で消費電力を集計する。
        
#         for iREF = 1:numOfRefs
#             for iREFSUB = 1:refsetRnum(iREF)
                
#                 if refInputType(iREF,iREFSUB) == 1
#                     E_ref_source_day(:,refInputType(iREF,iREFSUB)) = E_ref_source_day(:,refInputType(iREF,iREFSUB)) + E_refsys_day(:,iREF,iREFSUB)./(9760);      % [MWh]
#                     E_ref_source_Ele_day(:,iREF) = E_ref_source_Ele_day(:,iREF) + E_refsys_day(:,iREF,iREFSUB)./(9760);      % [MWh]
#                 elseif refInputType(iREF,iREFSUB) == 2
#                     E_ref_source_day(:,refInputType(iREF,iREFSUB)) = E_ref_source_day(:,refInputType(iREF,iREFSUB)) + E_refsys_day(:,iREF,iREFSUB)./(45000/1000); % [m3/h]
#                 elseif refInputType(iREF,iREFSUB) == 3
#                     E_ref_source_day(:,refInputType(iREF,iREFSUB)) = E_ref_source_day(:,refInputType(iREF,iREFSUB)) + E_refsys_day(:,iREF,iREFSUB)./(41000/1000);
#                 elseif refInputType(iREF,iREFSUB) == 4
#                     E_ref_source_day(:,refInputType(iREF,iREFSUB)) = E_ref_source_day(:,refInputType(iREF,iREFSUB)) + E_refsys_day(:,iREF,iREFSUB)./(37000/1000);
#                 elseif refInputType(iREF,iREFSUB) == 5
#                     E_ref_source_day(:,refInputType(iREF,iREFSUB)) = E_ref_source_day(:,refInputType(iREF,iREFSUB)) + E_refsys_day(:,iREF,iREFSUB)./(50000/1000);
#                 elseif refInputType(iREF,iREFSUB) == 6
#                     E_ref_source_day(:,refInputType(iREF,iREFSUB)) = E_ref_source_day(:,refInputType(iREF,iREFSUB)) + E_refsys_day(:,iREF,iREFSUB)./(copDHC_heating);   % [MJ]
#                 elseif refInputType(iREF,iREFSUB) == 7
#                     E_ref_source_day(:,refInputType(iREF,iREFSUB)) = E_ref_source_day(:,refInputType(iREF,iREFSUB)) + E_refsys_day(:,iREF,iREFSUB)./(copDHC_heating);   % [MJ]
#                 elseif refInputType(iREF,iREFSUB) == 8
#                     E_ref_source_day(:,refInputType(iREF,iREFSUB)) = E_ref_source_day(:,refInputType(iREF,iREFSUB)) + E_refsys_day(:,iREF,iREFSUB)./(copDHC_cooling);   % [MJ]
#                 end
                
#             end
            
#         end
        
#         E_ref = sum(E_ref_source_day);
        
#         % 熱源補機電力消費量 [MWh]
#         E_refac = sum(sum(E_ref_ACc_day));
#         % 一次ポンプ電力消費量 [MWh]
#         E_pumpP = sum(sum(E_PPc_day));
#         % 冷却塔ファン電力消費量 [MWh]
#         E_ctfan = sum(sum(E_CTfan_day));
#         % 冷却水ポンプ電力消費量 [MWh]
#         E_ctpump = sum(sum(E_CTpump_day));
        
# end

# disp('熱源エネルギー計算完了')
# toc


# %%-----------------------------------------------------------------------------------------------------------
# %% エネルギー消費量合計

# % 2次エネルギー
# E2nd_total =[E_aex,zeros(1,7);E_fan,zeros(1,7);E_pump,zeros(1,7);E_ref;E_refac,zeros(1,7);...
#     E_pumpP,zeros(1,7);E_ctfan,zeros(1,7);E_ctpump,zeros(1,7)];
# E2nd_total = [E2nd_total;sum(E2nd_total)];

# % 1次エネルギー [MJ]
# unitE = [9760,45,41,37,50,copDHC_heating,copDHC_heating,copDHC_cooling];
# for i=1:size(E2nd_total,1)
#     E1st_total(i,:) = E2nd_total(i,:) .* unitE;
# end
# E1st_total = [E1st_total,sum(E1st_total,2)];
# E1st_total = [E1st_total;E1st_total(end,:)/roomAreaTotal];



# %% 負荷集計

# Qctotal = 0;
# Qhtotal = 0;
# Qcpeak = 0;
# Qhpeak = 0;
# Qcover = 0;
# Qhover = 0;

# switch MODE
#     case {0}
#         tmpQcpeak = zeros(8760,1);
#         tmpQhpeak = zeros(8760,1);
#         for iREF = 1:numOfRefs
#             if REFtype(iREF) == 1 % 冷房 [kW]→[MJ/day]
#                 Qctotal = Qctotal + sum(Qref_hour(:,iREF)).*3600./1000;
#                 Qcover = Qcover + sum(Qref_OVER_hour(:,iREF));
#                 tmpQcpeak = tmpQcpeak + Qref_hour(:,iREF);
#             elseif REFtype(iREF) == 2
#                 Qhtotal = Qhtotal + sum(Qref_hour(:,iREF)).*3600./1000;
#                 Qhover = Qhover + sum(Qref_OVER_hour(:,iREF));
#                 tmpQhpeak = tmpQhpeak + Qref_hour(:,iREF);
#             end
#         end
        
#     case {1}
#         tmpQcpeak = zeros(8760,1);
#         tmpQhpeak = zeros(8760,1);
#         for iREF = 1:numOfRefs
#             if REFtype(iREF) == 1 &&  REFstorage(iREF) ~= -1 % 冷房 [kW]→[MJ/day]
#                 Qctotal = Qctotal + sum(Qref_hour(:,iREF)).*3600./1000;
#                 Qcover = Qcover + sum(Qref_OVER_hour(:,iREF));
#                 tmpQcpeak = tmpQcpeak + Qref_hour(:,iREF);
#             elseif REFtype(iREF) == 2 &&  REFstorage(iREF) ~= -1
#                 Qhtotal = Qhtotal + sum(Qref_hour(:,iREF)).*3600./1000;
#                 Qhover = Qhover + sum(Qref_OVER_hour(:,iREF));
#                 tmpQhpeak = tmpQhpeak + Qref_hour(:,iREF);
#             end
#         end
        
#     case {2,3,4}
        
#         tmpQcpeak = zeros(365,1);
#         tmpQhpeak = zeros(365,1);
        
#         for iREF = 1:numOfRefs
#             if REFtype(iREF) == 1 &&  REFstorage(iREF) ~= 1  % 冷房 [MJ/day] で蓄熱運転ではない場合（2014/1/10修正）
#                 Qctotal = Qctotal + sum(Qref(:,iREF));
#                 Qcover = Qcover + sum(Qref_OVER(:,iREF));
#                 tmpQcpeak = tmpQcpeak + Qref_kW(:,iREF);
#             elseif REFtype(iREF) == 2 &&  REFstorage(iREF) ~= 1  % 冷房 [MJ/day] で蓄熱運転ではない場合（2014/1/10修正）
#                 Qhtotal = Qhtotal + sum(Qref(:,iREF));
#                 Qhover = Qhover + sum(Qref_OVER(:,iREF));
#                 tmpQhpeak = tmpQhpeak + Qref_kW(:,iREF);
#             end
#         end
# end

# % ピーク負荷 [W/m2]
# Qcpeak = max(tmpQcpeak)./roomAreaTotal .*1000;
# Qhpeak = max(tmpQhpeak)./roomAreaTotal .*1000;

# % コンセント電力 [kW]
# E_OAapp = zeros(8760,numOfRoooms);
# P_Light = zeros(8760,numOfRoooms);
# for iROOM = 1:numOfRoooms
#     for dd = 1:365
#         for hh = 1:24
#             % コンセント電力 [kW]
#             E_OAapp(24*(dd-1)+hh,iROOM) = ...
#                 (roomEnergyOAappUnit(iROOM) .* roomScheduleOAapp(iROOM,roomDailyOpePattern(dd,iROOM),hh)).*roomArea(iROOM)./1000;
#             P_Light(24*(dd-1)+hh,iROOM) = roomScheduleLight(iROOM,roomDailyOpePattern(dd,iROOM),hh);
#         end
#     end
# end
# % コンセント電力 [MJ/年]
# E_OAapp_1st = sum(E_OAapp,2)*9760./1000;
# P_Light_ave = mean(P_Light,2);


# %% 基準値計算

# switch climateAREA
#     case {'Ia','1'}
#         stdLineNum = 1;
#     case {'Ib','2'}
#         stdLineNum = 2;
#     case {'II','3'}
#         stdLineNum = 3;
#     case {'III','4'}
#         stdLineNum = 4;
#     case {'IVa','5'}
#         stdLineNum = 5;
#     case {'IVb','6'}
#         stdLineNum = 6;
#     case {'V','7'}
#         stdLineNum = 7;
#     case {'VI','8'}
#         stdLineNum = 8;
# end

# % 基準値計算
# standardValue = mytfunc_calcStandardValue(buildingType,roomType,roomArea,stdLineNum)/sum(roomArea);



# %% 計算結果取りまとめ

# y(1)  = E1st_total(end,end);  % 一次エネルギー消費量合計 [MJ/m2]
# y(2)  = Qctotal/roomAreaTotal; % 年間冷房負荷[MJ/m2・年]
# y(3)  = Qhtotal/roomAreaTotal; % 年間暖房負荷[MJ/m2・年]
# y(4)  = E1st_total(1,end)/roomAreaTotal;  % 全熱交換機 [MJ/m2]
# y(5)  = E1st_total(2,end)/roomAreaTotal;  % 空調ファン [MJ/m2]
# y(6)  = E1st_total(3,end)/roomAreaTotal;  % 二次ポンプ [MJ/m2]
# y(7)  = E1st_total(4,end)/roomAreaTotal;  % 熱源主機 [MJ/m2]
# y(8)  = E1st_total(5,end)/roomAreaTotal;  % 熱源補機 [MJ/m2]
# y(9)  = E1st_total(6,end)/roomAreaTotal;  % 一次ポンプ [MJ/m2]
# y(10) = E1st_total(7,end)/roomAreaTotal;  % 冷却塔ファン [MJ/m2]
# y(11) = E1st_total(8,end)/roomAreaTotal;  % 冷却水ポンプ [MJ/m2]


# % CEC/ACのようなもの（未処理負荷は差し引く）
# switch MODE
#     case {0,1}
#         % 未処理負荷[MJ/m2]
#         y(12) = nansum(sum(abs(Qahu_remainChour)))./roomAreaTotal;
#         y(13) = nansum(sum(abs(Qahu_remainHhour)))./roomAreaTotal;
#         y(14) = nansum(Qcover)./roomAreaTotal;
#         y(15) = nansum(Qhover)./roomAreaTotal;
#         y(16) = y(1)./( ((sum(sum(Qahu_hour_CEC))))./roomAreaTotal -y(12) -y(13) );
#     case {2,3,4}
#         % 未処理負荷[MJ/m2]
#         y(12) = nansum(sum(abs(Qahu_remainC)))./roomAreaTotal;
#         y(13) = nansum(sum(abs(Qahu_remainH)))./roomAreaTotal;
#         y(14) = nansum(Qcover)./roomAreaTotal;
#         y(15) = nansum(Qhover)./roomAreaTotal;
#         y(16) = y(1)./( ((sum(sum(Qahu_CEC))))./roomAreaTotal -y(12) -y(13) );
# end

# y(17) = standardValue;
# y(18) = y(1)/y(17);

# % コンセント電力（一次エネルギー換算） [MJ/m2/年]
# y(19) = sum(E_OAapp_1st)./roomAreaTotal;
# y(20) = roomAreaTotal;

# % 熱損失係数 [W/m2K]
# y(21) = NaN; %sum(UAlist)/roomAreaTotal;
# % 日射取得係数 [-]
# y(22) = NaN; %sum(MAlist)/roomAreaTotal;


# % 熱源容量計算
# tmpREFQ_C = 0;
# tmpREFQ_H = 0;
# tmpREFS_C = 0;
# tmpREFS_H = 0;
# for iREF = 1:length(REFtype)
#     if REFtype(iREF) == 1
#         tmpREFQ_C = tmpREFQ_C + QrefrMax(iREF);
#         tmpREFS_C = tmpREFS_C + refS(iREF);
#     elseif REFtype(iREF) == 2
#         tmpREFQ_H = tmpREFQ_H + QrefrMax(iREF);
#         tmpREFS_H = tmpREFS_H + refS(iREF);
#     end
# end
# REFQperS_C = tmpREFQ_C/tmpREFS_C*1000;
# REFQperS_H = tmpREFQ_H/tmpREFS_H*1000;

# y(23) = REFQperS_C;
# y(24) = REFQperS_H;

# % ピーク負荷
# y(25) = Qcpeak;
# y(26) = Qhpeak;

# % 全負荷相当運転時間
# y(27) = y(2)/(y(23)/1000000*3600); % 冷房
# y(28) = y(3)/(y(24)/1000000*3600); % 暖房


# disp('計算結果取り纏め完了')
# toc


# %% 出力

# % switch MODE
# %     case {4}
# %         % コージェネレーション用
# %         if isfield(INPUT.CogenerationSystemsDetail,'CogenerationUnit')
# %
# %             % 様式7-3に記されている「熱源群」を探す
# %             CGS_refName_C = INPUT.CogenerationSystemsDetail.CogenerationUnit(1).ATTRIBUTE.REFc_name;
# %             CGS_refName_H = INPUT.CogenerationSystemsDetail.CogenerationUnit(1).ATTRIBUTE.REFh_name;
# %
# %             mytscript_result2csv_daily_for_CGS;
# %         end
# % end


# % 詳細出力
# if OutputOptionVar == 1
#     switch MODE
#         case {0}
#             mytscript_result2csv_hourly;
#             mytscript_result_for_GHSP;
            
#         case {2,3,4}
#             mytscript_result2csv;
            
#     end
# end

# % 簡易出力
# rfcS = {};
# rfcS = [rfcS;'---------'];
# eval(['rfcS = [rfcS;''一次エネルギー消費量 設計値： ', num2str(y(1)) ,'  MJ/m2・年''];'])
# eval(['rfcS = [rfcS;''一次エネルギー消費量 基準値： ', num2str(y(17)) ,'  MJ/m2・年''];'])
# rfcS = [rfcS;'---------'];
# eval(['rfcS = [rfcS;''年間冷房負荷  ： ', num2str(y(2)) ,'  MJ/m2・年''];'])
# eval(['rfcS = [rfcS;''年間暖房負荷  ： ', num2str(y(3)) ,'  MJ/m2・年''];'])
# rfcS = [rfcS;'---------'];
# eval(['rfcS = [rfcS;''BEI/Q        ： ', num2str((y(2)+y(3))/(y(17)*0.8)) ,'''];'])
# eval(['rfcS = [rfcS;''BEI/AC       ： ', num2str(y(18)) ,'''];'])
# eval(['rfcS = [rfcS;''CEC/AC*      ： ', num2str(y(16)) ,'''];'])
# rfcS = [rfcS;'---------'];
# eval(['rfcS = [rfcS;''全熱交換機Ｅ  ： ', num2str(y(4)) ,'  MJ/m2・年''];'])
# eval(['rfcS = [rfcS;''空調ファンＥ  ： ', num2str(y(5)) ,'  MJ/m2・年''];'])
# eval(['rfcS = [rfcS;''二次ポンプＥ  ： ', num2str(y(6)) ,'  MJ/m2・年''];'])
# eval(['rfcS = [rfcS;''熱源主機Ｅ    ： ', num2str(y(7)) ,'  MJ/m2・年''];'])
# eval(['rfcS = [rfcS;''熱源補機Ｅ    ： ', num2str(y(8)) ,'  MJ/m2・年''];'])
# eval(['rfcS = [rfcS;''一次ポンプＥ  ： ', num2str(y(9)) ,'  MJ/m2・年''];'])
# eval(['rfcS = [rfcS;''冷却塔ファンＥ： ', num2str(y(10)) ,'  MJ/m2・年''];'])
# eval(['rfcS = [rfcS;''冷却水ポンプＥ： ', num2str(y(11)) ,'  MJ/m2・年''];'])
# rfcS = [rfcS;'---------'];
# eval(['rfcS = [rfcS;''未処理負荷(冷)： ', num2str(y(12)) ,'  MJ/m2・年''];'])
# eval(['rfcS = [rfcS;''未処理負荷(温)： ', num2str(y(13)) ,'  MJ/m2・年''];'])
# eval(['rfcS = [rfcS;''熱源過負荷(冷)： ', num2str(y(14)) ,'  MJ/m2・年''];'])
# eval(['rfcS = [rfcS;''熱源過負荷(温)： ', num2str(y(15)) ,'  MJ/m2・年''];'])
# eval(['rfcS = [rfcS;''ピーク負荷(冷)： ', num2str(y(25)) ,'  W/m2''];'])
# eval(['rfcS = [rfcS;''ピーク負荷(温)： ', num2str(y(26)) ,'  W/m2''];'])
# eval(['rfcS = [rfcS;''全負荷相当運転時間(冷)： ', num2str(y(27)) ,'  時間''];'])
# eval(['rfcS = [rfcS;''全負荷相当運転時間(暖)： ', num2str(y(28)) ,'  時間''];'])
# rfcS = [rfcS;'---------'];
# eval(['rfcS = [rfcS;''熱損失係数*　 ： ', num2str(y(21)) ,'  W/m2・K''];'])
# eval(['rfcS = [rfcS;''夏季日射取得係数* ： ', num2str(y(22)) ,'  ''];'])
# eval(['rfcS = [rfcS;''熱源容量（冷）： ', num2str(y(23)) ,'  W/m2''];'])
# eval(['rfcS = [rfcS;''熱源容量（暖）： ', num2str(y(24)) ,'  W/m2''];'])
# rfcS = [rfcS;'---------'];
# eval(['rfcS = [rfcS;''計算モード： ', num2str(MODE) ,' ''];'])


# % 出力するファイル名
# if isempty(strfind(INPUTFILENAME,'/'))
#     eval(['resfilenameS = ''calcRES_AC_',INPUTFILENAME(1:end-4),'_',datestr(now,30),'.csv'';'])
# else
#     tmp = strfind(INPUTFILENAME,'/');
#     eval(['resfilenameS = ''calcRES_AC_',INPUTFILENAME(tmp(end)+1:end-4),'_',datestr(now,30),'.csv'';'])
# end
# fid = fopen(resfilenameS,'w+');
# for i=1:size(rfcS,1)
#     fprintf(fid,'%s\r\n',rfcS{i});
# end
# fclose(fid);


# disp('出力完了')
# disp(rfcS)

# toc




#     resultJson = []

#     return resultJson



# if __name__ == '__main__':

#     print('----- airconditioning.py -----')
#     filename = './sample/inputdata_AC.json'

#     # テンプレートjsonの読み込み
#     with open(filename, 'r') as f:
#         inputdata = json.load(f)

#     resultJson = airconditioning(inputdata)
#     print(resultJson)