"""
Application configuration and constants.
"""
from typing import Dict, List
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
STATIONS_FILE = DATA_DIR / "magic_pass_stations.json"

# Ollama configuration
OLLAMA_URL = "http://localhost:11434"
DEFAULT_MODEL = "llama3"
AVAILABLE_MODELS = ["llama3", "mistral", "gemma", "phi"]

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
    'vertical_drop': 5
}