#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

PARAM_FILENAME="param.dat"
INPUT_FILENAME="input_zebopt.json"
OUTPUT_FILENAME_BASE="zebopt"

python3 "$SCRIPT_DIR/generate_input_zebopt_for_sensitivity.py" "$PARAM_FILENAME" "$INPUT_FILENAME"
echo "Generated file: $INPUT_FILENAME"

python3 "$SCRIPT_DIR/../builelib_zebopt_run.py" "$INPUT_FILENAME" "$OUTPUT_FILENAME_BASE"

echo "Successfully ran builelib_zebopt_run.py with $INPUT_FILENAME" "$OUTPUT_FILENAME_BASE"

# Define the output JSON file (assuming it's the result of builelib_zebopt_run.py)
OUTPUT_JSON_FILE="${OUTPUT_FILENAME_BASE}_result.json"

# Check if the output file exists
if [ -f "$OUTPUT_JSON_FILE" ]; then
    # Extract the "BEI" value from the output JSON file using jq
    BEI=$(jq '.BEI' "$OUTPUT_JSON_FILE")
    echo "BEI value from $OUTPUT_JSON_FILE: $BEI"
else
    echo "Error: Output file $OUTPUT_JSON_FILE not found."
fi
