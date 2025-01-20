#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

PARAM_FILENAME="param.dat"
INPUT_FILENAME="input_zebopt.json"
OUTPUT_FILENAME_BASE="zebopt"

# Parameters and their ranges
params=("wall_u_value" "glass_u_value" "glass_eta_value" "Qref_rated_cool" "Qref_rated_heat" "AirHeatExchangeRateCooling" "AirHeatExchangeRateHeating" "Fan_air_volume" "Motor_rated_power" "Lighting_rated_power" "Hot_water_rated_capacity")
values_min=("0.4" "0.4" "2.5" "1200" "1000" "40" "20" "2000" "0.45" "4000" "15.0")
values_max=("0.6" "0.6" "3.5" "1600" "1300" "60" "40" "3000" "0.65" "5500" "25.0")

# Load initial parameters from param.dat
function load_params() {
    cp "$PARAM_FILENAME" "${PARAM_FILENAME}.bak" # Backup original param file
}

# Modify a specific parameter in the param.dat file
function modify_param() {
    param_name=$1
    param_value=$2
    sed -i "" "s/^$param_name = .*/$param_name = $param_value/" "$PARAM_FILENAME"
}

# Restore the original param.dat file
function restore_params() {
    mv "${PARAM_FILENAME}.bak" "$PARAM_FILENAME"
}

# Function to run the simulation and extract BEI
function run_simulation() {
    python3 "$SCRIPT_DIR/generate_input_zebopt_for_sensitivity.py" "$PARAM_FILENAME" "$INPUT_FILENAME"
    python3 "$SCRIPT_DIR/../builelib_zebopt_run.py" "$INPUT_FILENAME" "$OUTPUT_FILENAME_BASE"

    OUTPUT_JSON_FILE="${OUTPUT_FILENAME_BASE}_result.json"

    if [ -f "$OUTPUT_JSON_FILE" ]; then
        BEI=$(jq '.BEI' "$OUTPUT_JSON_FILE")
        echo "$BEI"
    else
        echo "Error: Output file $OUTPUT_JSON_FILE not found."
        exit 1
    fi
}

# Run sensitivity analysis
load_params

for i in "${!params[@]}"; do
    param=${params[$i]}

    # Test min and max values for each parameter
    for value in "${values_min[$i]}" "${values_max[$i]}"; do
        echo "Modifying $param to $value"
        modify_param "$param" "$value"

        BEI=$(run_simulation)
        echo "For $param = $value, BEI = $BEI"

        # Log the result
        echo "$param = $value, BEI = $BEI" >> sensitivity_results.txt
    done
done

# restore_params
echo "Sensitivity analysis complete. Results saved to sensitivity_results.txt."
