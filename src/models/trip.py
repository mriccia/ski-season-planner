"""
Models for representing ski trips and user preferences.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional
from .station import Station

@dataclass
class UserPreferences:
    criteria: List[str] = field(default_factory=list)
    priorities: Dict[str, int] = field(default_factory=lambda: {
        'altitude': 5,
        'piste_length': 5,
        'vertical_drop': 5,
        'resort_distance': 5
    })
    home_location: str = ""
    transport_mode: str = "Car"  # Default to Car

@dataclass
class Trip:
    start_date: datetime
    end_date: datetime
    criteria: List[str]
    priorities: Dict[str, int]
    matching_stations: List[Station] = field(default_factory=list)
    
    @property
    def duration_days(self) -> int:
        """Calculate the duration of the trip in days."""
        return (self.end_date - self.start_date).days + 1
    
    def to_dict(self) -> Dict:
        """Convert the Trip instance to a dictionary."""
        return {
            'start_date': self.start_date,
            'end_date': self.end_date,
            'criteria': self.criteria,
            'priorities': self.priorities,
            'matching_stations': [s.to_dict() for s in self.matching_stations]
        }