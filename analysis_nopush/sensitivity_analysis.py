from SALib.sample import saltelli
from SALib.analyze import sobol
import numpy as np
import subprocess
import json

# モデルの入力パラメータの定義（パラメータとその範囲）
problem = {
    'num_vars': 10,  # パラメータの数
    'names': ['wall_u_value', 'glass_u_value', 'glass_eta_value', 'Qref_rated_cool', 'Qref_rated_heat',
              'AirHeatExchangeRateCooling', 'AirHeatExchangeRateHeating', 'Fan_air_volume', 'Lighting_rated_power', 'Hot_water_rated_capacity'],
    'bounds': [
        [0.05, 1],       # wall_u_valueの範囲
        [0.1, 5],       # glass_u_valueの範囲
        [0.1, 10],       # glass_eta_valueの範囲
        [1200, 1600],     # Qref_rated_coolの範囲
        [1000, 1300],     # Qref_rated_heatの範囲
        [40, 60],         # AirHeatExchangeRateCoolingの範囲
        [20, 40],         # AirHeatExchangeRateHeatingの範囲
        [2000, 3000],     # Fan_air_volumeの範囲
        [4000, 5500],      # Lighting_rated_powerの範囲
        [15.0, 25.0]
    ]
}

# Saltelliサンプリングで入力サンプルを生成
param_values = saltelli.sample(problem, 1024)

# モデルの実行とBEI値の取得
def run_model(params):
    # param.datファイルに新しいパラメータ値を書き込む
    with open("param.dat", "w") as f:
        f.write(f"wall_u_value = {params[0]}\n")
        f.write(f"glass_u_value = {params[1]}\n")
        f.write(f"glass_eta_value = {params[2]}\n")
        f.write(f"Qref_rated_cool = {params[3]}\n")
        f.write(f"Qref_rated_heat = {params[4]}\n")
        f.write(f"AirHeatExchangeRateCooling = {params[5]}\n")
        f.write(f"AirHeatExchangeRateHeating = {params[6]}\n")
        f.write(f"Fan_air_volume = {params[7]}\n")
        f.write(f"Lighting_rated_power = {params[8]}\n")
        f.write(f"Hot_water_rated_capacity = {params[8]}\n")

    # 外部のPythonスクリプトを実行
    subprocess.run(["python3", "generate_input_zebopt_for_sensitivity.py", "param.dat", "input_zebopt.json"])
    subprocess.run(["python3", "../builelib_zebopt_run.py", "input_zebopt.json", "zebopt"])

    # 実行結果のBEI値をJSONから取得
    with open("zebopt_result.json", "r") as f:
        output_data = json.load(f)
        return output_data["BEI"]

# 各サンプルに対してモデルを実行し、BEI値を取得
Y = np.array([run_model(params) for params in param_values])

# Sobol感度分析を実行
Si = sobol.analyze(problem, Y, print_to_console=True)

# 結果の表示
print("一次Sobol指数 (S1):", Si['S1'])
print("全順序Sobol指数 (ST):", Si['ST'])
