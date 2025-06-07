"""
Service layer for handling ski station data and filtering operations.
"""
import json
import logging
import os
from typing import List, Optional, Dict, Any
from pathlib import Path
from ski_planner_app.models.station import Station, DifficultyBreakdown, Coordinates
from ski_planner_app.services.singleton import singleton_session
from ski_planner_app.services.database_service import DatabaseService

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
        CURR_DIR = Path(__file__).parent
        STATIONS_FILE = f"{CURR_DIR}/data/magic_pass_stations.json"
        logger.debug(
            f"Initializing StationService with data file: {STATIONS_FILE}")
        self.data_file = STATIONS_FILE
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
                    # Fall back to JSON file
                    logger.info(f"No stations in database, loading from {self.data_file}")
                    self._load_from_json()
            except Exception as e:
                logger.error(f"Error loading stations from database: {str(e)}", exc_info=True)
                # Fall back to JSON file
                logger.info(f"Falling back to loading from {self.data_file}")
                self._load_from_json()
                
        return self._stations
    
    def _load_from_json(self):
        """Load stations from the JSON file."""
        try:
            with open(self.data_file, 'r') as f:
                data = json.load(f)
            self._stations = [Station.from_dict(s) for s in data['stations']]
            logger.info(f"Successfully loaded {len(self._stations)} stations from JSON")
        except FileNotFoundError as e:
            logger.error(f"Station data file not found: {self.data_file}", exc_info=True)
            raise RuntimeError(f"Error loading station data: {str(e)}")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in station data file: {self.data_file}", exc_info=True)
            raise RuntimeError(f"Error loading station data: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error loading stations: {str(e)}", exc_info=True)
            raise RuntimeError(f"Error loading station data: {str(e)}")
    
    def _dict_to_station(self, station_dict: Dict[str, Any]) -> Station:
        """
        Convert a dictionary from the database to a Station object.
        
        Args:
            station_dict: Dictionary containing station data from the database
            
        Returns:
            Station: A Station object
        """
        # Create difficulty breakdown
        difficulty = DifficultyBreakdown(
            easy_km=station_dict.get('difficulty_breakdown', {}).get('easy_km', 0),
            intermediate_km=station_dict.get('difficulty_breakdown', {}).get('intermediate_km', 0),
            difficult_km=station_dict.get('difficulty_breakdown', {}).get('difficult_km', 0)
        )
        
        # Extract coordinates if available
        coordinates = None
        if 'coordinates' in station_dict and station_dict['coordinates']:
            coords = station_dict['coordinates']
            if isinstance(coords, dict) and all(k in coords for k in ('longitude', 'latitude')):
                coordinates = Coordinates(
                    longitude=coords['longitude'],
                    latitude=coords['latitude']
                )
        
        # Create station object
        return Station(
            name=station_dict.get('name', ''),
            region=station_dict.get('region', ''),
            base_altitude=station_dict.get('base_altitude', 0),
            top_altitude=station_dict.get('top_altitude', 0),
            vertical_drop=station_dict.get('vertical_drop', 0),
            total_pistes_km=station_dict.get('total_pistes_km', 0),
            difficulty_breakdown=difficulty,
            coordinates=coordinates
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
                'coordinates': station.coordinates.to_list() if station.coordinates else None
            }
            
            # Only include stations that have valid coordinates
            if station_data['coordinates']:
                result.append(station_data)
            else:
                logger.warning(f"Station {station.name} has no coordinates and will be skipped for distance calculations")
                
        if not result:
            logger.error("No stations with valid coordinates found")
            
        return result
