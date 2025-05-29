"""
Application configuration and constants.
"""
import os
import logging.config
from typing import Dict, List
from pathlib import Path
import logging

# Configure the root strands logger
logging.getLogger("strands").setLevel(logging.DEBUG)

# Add a handler to see the logs
logging.basicConfig(
    format="%(levelname)s | %(name)s | %(message)s", 
    handlers=[logging.StreamHandler()]
)
# Paths
STATIONS_FILE = "./data/magic_pass_stations.json"

# Ollama configuration
OLLAMA_URL = "http://localhost:11434"
DEFAULT_MODEL = "llama3.2:3b"
AVAILABLE_MODELS = ["deepseek-r1:7b", "llama3.2:3b"]

# Skiing criteria options
CRITERIA_OPTIONS: Dict[str, str] = {
    "snow_sure": "Snow-sure resorts (Base altitude > 1500m)",
    "km_of_pistes": "Large ski areas (> 50km of pistes)",
    "family_friendly": "Family-friendly (More easy slopes)"
}

# Default priorities
DEFAULT_PRIORITIES: Dict[str, int] = {
    'altitude': 5,
    'piste_length': 5,
    'vertical_drop': 5,
    'resort_distance': 5
}