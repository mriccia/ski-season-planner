"""
Models for representing ski trips and user preferences.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict

@dataclass
class UserPreferences:
    """
    Represents user preferences for ski trips.
    
    Attributes:
        criteria (List[str]): List of criteria for selecting ski resorts
        priorities (Dict[str, int]): Dictionary mapping priority factors to their importance (1-10)
        home_location (str): User's home location for distance calculations
        transport_mode (str): Preferred mode of transport (Car or Public Transport)
    """
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
    """
    Represents a planned ski trip.
    
    Attributes:
        start_date (datetime): Start date of the trip
        end_date (datetime): End date of the trip
        criteria (List[str]): Specific criteria for this trip
        priorities (Dict[str, int]): Specific priorities for this trip
    
    Properties:
        duration_days (int): Duration of the trip in days
    """
    start_date: datetime
    end_date: datetime
    criteria: List[str]
    priorities: Dict[str, int]
    
    @property
    def duration_days(self) -> int:
        """
        Calculate the duration of the trip in days.
        
        Returns:
            int: Number of days for the trip (inclusive of start and end dates)
        """
        return (self.end_date - self.start_date).days + 1
    
    def to_dict(self) -> Dict:
        """
        Convert the Trip instance to a dictionary.
        
        Returns:
            Dict: Dictionary representation of the Trip
        """
        return {
            'start_date': self.start_date,
            'end_date': self.end_date,
            'criteria': self.criteria,
            'priorities': self.priorities
        }