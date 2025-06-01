"""
Service layer for handling ski station data and filtering operations.
"""
import json
import logging
from typing import List, Optional
from pathlib import Path
from ski_planner_app.models.station import Station
from ski_planner_app.services.singleton import singleton_session

logger = logging.getLogger(__name__)


@singleton_session("service")
class StationService:
    """
    Service for managing ski station data.
    
    This service handles loading and caching ski station data from a JSON file.
    It uses the singleton pattern to ensure only one instance exists per session.
    """
    
    def __init__(self):
        """
        Initialize the StationService with the path to the stations data file.
        """
        CURR_DIR = Path(__file__).parent
        STATIONS_FILE = f"{CURR_DIR}/data/magic_pass_stations.json"
        logger.debug(
            f"Initializing StationService with data file: {STATIONS_FILE}")
        self.data_file = STATIONS_FILE
        self._stations: Optional[List[Station]] = None

    def load_stations(self) -> List[Station]:
        """
        Load stations from the JSON data file.
        
        This method loads the station data from the JSON file and caches it
        for future use. If the data is already loaded, it returns the cached data.
        
        Returns:
            List[Station]: List of Station objects
            
        Raises:
            RuntimeError: If there's an error loading the station data
        """
        if self._stations is None:
            logger.info(f"Loading stations data from {self.data_file}")
            try:
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                self._stations = [Station.from_dict(
                    s) for s in data['stations']]
                logger.info(
                    f"Successfully loaded {len(self._stations)} stations")
            except FileNotFoundError as e:
                logger.error(
                    f"Station data file not found: {self.data_file}", exc_info=True)
                raise RuntimeError(f"Error loading station data: {str(e)}")
            except json.JSONDecodeError as e:
                logger.error(
                    f"Invalid JSON in station data file: {self.data_file}", exc_info=True)
                raise RuntimeError(f"Error loading station data: {str(e)}")
            except Exception as e:
                logger.error(
                    f"Unexpected error loading stations: {str(e)}", exc_info=True)
                raise RuntimeError(f"Error loading station data: {str(e)}")
        return self._stations
