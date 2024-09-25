from dataclasses import dataclass

from builelib.domain.utils import read_json_file, database_directory


# This class map key are 定風量制御, 回転数制御,回転数制御_2乗, 回転数制御_3乗, 定流量制御
@dataclass
class FlowControl:
    type: str
    a4: int
    a3: int
    a2: int
    a1: int
    a0: int

    def __init__(self, flow_control_file_name):
        self.flow_control_map = read_json_file(database_directory + flow_control_file_name)

    def get_keys(self):
        return self.flow_control_map.keys()

    def get_a4(self, key):
        return self.flow_control_map[key]['a4']

    def get_a3(self, key):
        return self.flow_control_map[key]['a3']

    def get_a2(self, key):
        return self.flow_control_map[key]['a2']

    def get_a1(self, key):
        return self.flow_control_map[key]['a1']

    def get_a0(self, key):
        return self.flow_control_map[key]['a0']
