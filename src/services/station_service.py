"""
Service layer for handling ski station data and filtering operations.
"""
import json
import logging
from typing import List, Dict, Optional
from pathlib import Path
from models.station import Station
import streamlit as st
from services.singleton import singleton_session

logger = logging.getLogger(__name__)

@singleton_session("service")
class StationService:
    def __init__(self):
        CURR_DIR = Path(__file__).parent
        STATIONS_FILE = f"{CURR_DIR}/data/magic_pass_stations.json"
        logger.debug(f"Initializing StationService with data file: {STATIONS_FILE}")
        self.data_file = STATIONS_FILE
        self._stations: Optional[List[Station]] = None
    
    def load_stations(self) -> List[Station]:
        """Load stations from the JSON data file."""
        if self._stations is None:
            logger.info(f"Loading stations data from {self.data_file}")
            try:
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                self._stations = [Station.from_dict(s) for s in data['stations']]
                logger.info(f"Successfully loaded {len(self._stations)} stations")
            except FileNotFoundError as e:
                logger.error(f"Station data file not found: {self.data_file}", exc_info=True)
                raise RuntimeError(f"Error loading station data: {str(e)}")
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in station data file: {self.data_file}", exc_info=True)
                raise RuntimeError(f"Error loading station data: {str(e)}")
            except Exception as e:
                logger.error(f"Unexpected error loading stations: {str(e)}", exc_info=True)
                raise RuntimeError(f"Error loading station data: {str(e)}")
        return self._stations

# Function to get a singleton instance of StationService
def get_station_service():
    return StationService()