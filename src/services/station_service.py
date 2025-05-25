"""
Service layer for handling ski station data and filtering operations.
"""
import json
from typing import List, Dict, Optional
from pathlib import Path
from ..models.station import Station

class StationService:
    def __init__(self, data_file: str = 'data/magic_pass_stations.json'):
        self.data_file = data_file
        self._stations: Optional[List[Station]] = None
    
    def load_stations(self) -> List[Station]:
        """Load stations from the JSON data file."""
        if self._stations is None:
            try:
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                self._stations = [Station.from_dict(s) for s in data['stations']]
            except (FileNotFoundError, json.JSONDecodeError) as e:
                raise RuntimeError(f"Error loading station data: {str(e)}")
        return self._stations
    
    def filter_stations(self, criteria: List[str], priorities: Dict[str, int]) -> List[Station]:
        """Filter and sort stations based on user criteria and priorities."""
        stations = self.load_stations()
        filtered = stations.copy()
        
        # Apply filters
        if 'snow_sure' in criteria:
            filtered = [s for s in filtered if s.base_altitude > 1500]
        
        if 'km_of_pistes' in criteria:
            filtered = [s for s in filtered if s.total_pistes_km > 50]
        
        if 'family_friendly' in criteria:
            filtered = [s for s in filtered if (
                s.difficulty_breakdown.easy_km > (s.total_pistes_km * 0.3)
                if s.total_pistes_km > 0 else False
            )]
        
        # Score and sort stations
        scored_stations = [(station, self._calculate_station_score(station, priorities))
                          for station in filtered]
        scored_stations.sort(key=lambda x: x[1], reverse=True)
        
        return [station for station, _ in scored_stations]
    
    def _calculate_station_score(self, station: Station, priorities: Dict[str, int]) -> float:
        """Calculate a score for a station based on user priorities."""
        score = 0
        for priority, weight in priorities.items():
            if priority == 'altitude':
                score += station.base_altitude / 3000 * weight
            elif priority == 'piste_length':
                score += station.total_pistes_km / 150 * weight
            elif priority == 'vertical_drop':
                score += station.vertical_drop / 2000 * weight
        return score