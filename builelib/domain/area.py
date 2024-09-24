from dataclasses import dataclass

from builelib.domain.utils import read_json_file, database_directory


@dataclass
class Area:
    region_number: str
    representative_city: str
    latitude: float
    longitude: float
    weather_data_filename: str
    weather_data_filename_hot_water: str
    air_conditioning_mode_type: str
    heating_outdoor_temp_lower_limit: int
    heating_outdoor_temp_upper_limit: int
    cooling_outdoor_temp_lower_limit: int
    cooling_outdoor_temp_upper_limit: int
    wet_bulb_temp_coeff_heating_a1: float
    wet_bulb_temp_coeff_heating_a0: float
    wet_bulb_temp_coeff_cooling_a1: float
    wet_bulb_temp_coeff_cooling_a0: float

    def __init__(self, area_file_name, region_number: str):
        self.area_map = read_json_file(database_directory + area_file_name)
        self.selected_area = self.area_map[region_number]

    def get_representative_city(self):
        return self.selected_area['代表都市']

    def get_latitude(self):
        return self.selected_area['緯度']

    def get_longitude(self):
        return self.selected_area['経度']

    def get_weather_data_file_name(self):
        return self.selected_area['気象データファイル名']

    def get_weather_data_filename_hot_water(self):
        return self.selected_area['気象データファイル名_給湯']

    def get_air_conditioning_mode_type(self):
        return self.selected_area['空調運転モードタイプ']

    def get_heating_outdoor_temp_lower_limit(self):
        return self.selected_area['暖房時外気温下限']

    def get_heating_outdoor_temp_upper_limit(self):
        return self.selected_area['暖房時外気温上限']

    def get_cooling_outdoor_temp_lower_limit(self):
        return self.selected_area['冷房時外気温下限']

    def get_cooling_outdoor_temp_upper_limit(self):
        return self.selected_area['冷房時外気温上限']

    def get_wet_bulb_temp_coeff_heating_a1(self):
        return self.selected_area['湿球温度係数_暖房a1']

    def get_wet_bulb_temp_coeff_heating_a0(self):
        return self.selected_area['湿球温度係数_暖房a0']

    def get_wet_bulb_temp_coeff_cooling_a1(self):
        return self.selected_area['湿球温度係数_冷房a1']

    def get_wet_bulb_temp_coeff_cooling_a0(self):
        return self.selected_area['湿球温度係数_冷房a0']
