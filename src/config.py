"""
Application configuration and constants.
"""
import os
import logging.config
from typing import Dict, List
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
STATIONS_FILE = DATA_DIR / "magic_pass_stations.json"
LOGS_DIR = PROJECT_ROOT / "logs"

# Create logs directory if it doesn't exist
LOGS_DIR.mkdir(exist_ok=True)

# Logging Configuration
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        },
        'detailed': {
            'format': '%(asctime)s [%(levelname)s] %(name)s:%(lineno)d: %(message)s'
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'INFO',
            'formatter': 'standard',
            'stream': 'ext://sys.stdout'
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'DEBUG',
            'formatter': 'detailed',
            'filename': LOGS_DIR / 'ski_planner.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5
        },
        'error_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'ERROR',
            'formatter': 'detailed',
            'filename': LOGS_DIR / 'error.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5
        }
    },
    'loggers': {
        '': {  # Root logger
            'handlers': ['console', 'file', 'error_file'],
            'level': os.getenv('LOG_LEVEL', 'INFO'),
            'propagate': True
        },
        'src.services': {  # Services logger
            'handlers': ['console', 'file', 'error_file'],
            'level': 'DEBUG',
            'propagate': False
        }
    }
}

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
    'vertical_drop': 5
}