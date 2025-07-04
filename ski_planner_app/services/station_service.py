"""
Service layer for handling ski station data and filtering operations.
"""
import json
import logging
import os
from typing import List, Optional, Dict, Any
from pathlib import Path
from ski_planner_app.models.station import Station
from ski_planner_app.services.singleton import singleton_session
from ski_planner_app.services.database_service import DatabaseService
from ski_planner_app.config import STATIONS_FILE_PATH

logger = logging.getLogger(__name__)


@singleton_session("service")
class StationService:
    """
    Service for managing ski station data.
    
    This service handles loading and caching ski station data from a JSON file
    and/or the SQLite database. It uses the singleton pattern to ensure only 
    one instance exists per session.
    """
    
    def __init__(self):
        """
        Initialize the StationService with the path to the stations data file.
        """
        self.data_file = STATIONS_FILE_PATH
        logger.debug(
            f"Initializing StationService with data file: {self.data_file}")
        self._stations: Optional[List[Station]] = None
        self.db_service = DatabaseService()
        
        # Ensure stations are loaded into the database
        self._ensure_stations_in_db()
    
    def _ensure_stations_in_db(self):
        """
        Ensure stations are loaded into the database.
        
        If the stations table in the database is empty, this method will
        import the stations from the JSON file.
        """
        if not self.db_service.is_stations_table_populated():
            logger.info("Stations table is empty, importing from JSON")
            count = self.db_service.import_stations_from_json(self.data_file)
            logger.info(f"Imported {count} stations into the database")

    def load_stations(self) -> List[Station]:
        """
        Load stations from the database or JSON data file.
        
        This method first tries to load stations from the database.
        If that fails, it falls back to loading from the JSON file.
        The loaded data is cached for future use.
        
        Returns:
            List[Station]: List of Station objects
            
        Raises:
            RuntimeError: If there's an error loading the station data
        """
        if self._stations is None:
            try:
                # Try to load from database first
                db_stations = self.db_service.get_all_stations()
                if db_stations:
                    logger.info(f"Loaded {len(db_stations)} stations from database")
                    self._stations = [self._dict_to_station(s) for s in db_stations]
                else:
                    raise RuntimeError("No stations found in the database")
            except Exception as e:
                logger.error(f"Error loading stations from database: {str(e)}", exc_info=True)
                
        return self._stations
    
    def _dict_to_station(self, station_dict: Dict[str, Any]) -> Station:
        """
        Convert a dictionary from the database to a Station object.
        
        Args:
            station_dict: Dictionary containing station data from the database
            
        Returns:
            Station: A Station object
        """
            
        # Create station object with flattened structure
        return Station(
            name=station_dict.get('name'),
            region=station_dict.get('region'),
            base_altitude=station_dict.get('base_altitude'),
            top_altitude=station_dict.get('top_altitude'),
            vertical_drop=station_dict.get('vertical_drop'),
            total_pistes_km=station_dict.get('total_pistes_km'),
            longitude=station_dict.get('longitude'),
            latitude=station_dict.get('latitude'),
            magic_pass_url=station_dict.get('magic_pass_url')
        )
    
    def get_all_stations(self) -> List[Station]:
        """
        Get all stations.
        
        Returns:
            List[Station]: List of all Station objects
        """
        return self.load_stations()
    
    def get_all_locations_with_coordinates(self) -> List[Dict[str, Any]]:
        """
        Get all station locations with their coordinates.
        
        Returns:
            List[Dict]: List of dictionaries with station name and coordinates
        """
        stations = self.load_stations()
        result = []
        
        for station in stations:
            station_data = {
                'name': station.name,
                'coordinates': station.get_coordinates()
            }
            
            # Only include stations that have valid coordinates
            if station.longitude != 0.0 and station.latitude != 0.0:
                result.append(station_data)
            else:
                logger.warning(f"Station {station.name} has no coordinates and will be skipped for distance calculations")
                
        if not result:
            logger.error("No stations with valid coordinates found")
            
        return result
