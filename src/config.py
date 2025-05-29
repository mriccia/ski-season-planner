"""
Application configuration and constants.
"""
import os
import logging.config
from typing import Dict, List
from pathlib import Path
import logging
import requests

# Configure the root strands logger
logging.getLogger("strands").setLevel(logging.DEBUG)
logging.getLogger(__name__).setLevel(logging.DEBUG)

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
FALLBACK_MODELS = ["deepseek-r1:7b", "llama3.2:3b"]

def get_available_ollama_models() -> List[str]:
    """Query Ollama API to get available models."""
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags")
        if response.status_code == 200:
            models = [model["name"] for model in response.json().get("models", [])]
            logging.info(f"Found {len(models)} available Ollama models: {models}")
            return models
        else:
            logging.warning(f"Failed to get Ollama models: status code {response.status_code}")
            return FALLBACK_MODELS
    except Exception as e:
        logging.error(f"Error fetching Ollama models: {e}")
        return FALLBACK_MODELS

# Get available models dynamically
AVAILABLE_MODELS = get_available_ollama_models()

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