"""
Service layer for handling ski station data and filtering operations.
"""
import json
import logging
from typing import List, Dict, Optional
from pathlib import Path
from ..models.station import Station

logger = logging.getLogger(__name__)

class StationService:
    def __init__(self, data_file: str = 'data/magic_pass_stations.json'):
        logger.debug(f"Initializing StationService with data file: {data_file}")
        self.data_file = data_file
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
    
    def filter_stations(self, criteria: List[str], priorities: Dict[str, int]) -> List[Station]:
        """Filter and sort stations based on user criteria and priorities."""
        logger.info(f"Filtering stations with criteria: {criteria}")
        logger.debug(f"Priority weights: {priorities}")
        
        try:
            stations = self.load_stations()
            filtered = stations.copy()
            
            # Apply filters
            if 'snow_sure' in criteria:
                logger.debug("Applying snow-sure filter (base altitude > 1500m)")
                filtered = [s for s in filtered if s.base_altitude > 1500]
            
            if 'km_of_pistes' in criteria:
                logger.debug("Applying piste length filter (> 50km)")
                filtered = [s for s in filtered if s.total_pistes_km > 50]
            
            if 'family_friendly' in criteria:
                logger.debug("Applying family-friendly filter (>30% easy slopes)")
                filtered = [s for s in filtered if (
                    s.difficulty_breakdown.easy_km > (s.total_pistes_km * 0.3)
                    if s.total_pistes_km > 0 else False
                )]
            
            # Score and sort stations
            logger.debug("Calculating station scores and sorting")
            scored_stations = [(station, self._calculate_station_score(station, priorities))
                            for station in filtered]
            scored_stations.sort(key=lambda x: x[1], reverse=True)
            
            result = [station for station, _ in scored_stations]
            logger.info(f"Found {len(result)} matching stations")
            if result:
                logger.debug(f"Top 3 matches: {', '.join(s.name for s in result[:3])}")
            return result
            
        except Exception as e:
            logger.error(f"Error filtering stations: {str(e)}", exc_info=True)
            raise
    
    def _calculate_station_score(self, station: Station, priorities: Dict[str, int]) -> float:
        """Calculate a score for a station based on user priorities."""
        try:
            score = 0
            for priority, weight in priorities.items():
                if priority == 'altitude':
                    score += station.base_altitude / 3000 * weight
                elif priority == 'piste_length':
                    score += station.total_pistes_km / 150 * weight
                elif priority == 'vertical_drop':
                    score += station.vertical_drop / 2000 * weight
            logger.debug(f"Calculated score {score:.2f} for station {station.name}")
            return score
        except Exception as e:
            logger.error(f"Error calculating score for station {station.name}: {str(e)}", exc_info=True)
            raise