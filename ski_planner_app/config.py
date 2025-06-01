"""
Application configuration and constants.
"""
from typing import Dict


STATIONS_FILE = "./data/magic_pass_stations.json"

# Skiing criteria options
CRITERIA_OPTIONS: Dict[str, str] = {
    "snow_sure_1500m_min": "Snow-sure resorts (Base altitude > 1500m)",
    "km_of_pistes_50km_min": "Large ski areas (> 50km of pistes)",
    "family_friendly": "Family-friendly (More easy slopes)"
}

# Default priorities
DEFAULT_PRIORITIES: Dict[str, int] = {
    'altitude': 5,
    'piste_length': 5,
    'vertical_drop': 5,
    'resort_distance': 5
}
