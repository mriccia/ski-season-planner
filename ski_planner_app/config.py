"""
Application configuration and constants.

This module contains all the configuration values and constants used throughout
the application. Centralizing these values makes the application more maintainable
and easier to modify.
"""
from typing import Dict
from datetime import datetime

# File paths
STATIONS_FILE_PATH = "data/magic_pass_stations.json"
DB_FILE_PATH = "data/ski_planner.db"

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

# Default trip dates
DEFAULT_TRIP_START_DATE = datetime(2025, 12, 12)
DEFAULT_TRIP_END_DATE = datetime(2025, 12, 15)

# Ski season months (1-based, January=1, December=12)
SKI_SEASON_START_MONTH = 11  # November
SKI_SEASON_END_MONTH = 4     # April

# API endpoints
OLLAMA_DEFAULT_URL = "http://localhost:11434"

# Default OpenAI models
DEFAULT_OPENAI_MODELS = ["gpt-4o", "gpt-3.5-turbo"]

# API retry configuration
MAX_API_RETRIES = 5
INITIAL_RETRY_DELAY = 10  # seconds
RETRY_JITTER_FACTOR = 0.1  # Add randomness to avoid thundering herd

# UI configuration
UI_DOWNLOAD_FILENAME = "ski_season_plan.txt"
UI_DOWNLOAD_MIME_TYPE = "text/plain"
