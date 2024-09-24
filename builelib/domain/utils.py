import json
import os

database_directory = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/database/"


def read_json_file(file_name) -> dict:
    if not os.path.exists(file_name):
        raise FileNotFoundError(f"The file '{file_name}' does not exist.")
    try:
        with open(file_name, "r", encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Error decoding JSON from the file '{file_name}': {e}")
