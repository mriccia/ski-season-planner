"""
Models for representing ski stations and related data structures.
"""
from dataclasses import dataclass
from typing import Dict

@dataclass
class DifficultyBreakdown:
    """
    Represents the breakdown of ski slopes by difficulty level.
    
    Attributes:
        easy_km (float): Length of easy/beginner slopes in kilometers
        intermediate_km (float): Length of intermediate slopes in kilometers
        difficult_km (float): Length of difficult/expert slopes in kilometers
    """
    easy_km: float = 0
    intermediate_km: float = 0
    difficult_km: float = 0

@dataclass
class Station:
    """
    Represents a ski resort/station with its key characteristics.
    
    Attributes:
        name (str): Name of the ski resort
        region (str): Geographic region where the resort is located
        base_altitude (int): Altitude of the resort base in meters
        top_altitude (int): Altitude of the highest point in meters
        vertical_drop (int): Vertical distance between top and base in meters
        total_pistes_km (float): Total length of all ski slopes in kilometers
        difficulty_breakdown (DifficultyBreakdown): Breakdown of slopes by difficulty
    """
    name: str
    region: str
    base_altitude: int
    top_altitude: int
    vertical_drop: int
    total_pistes_km: float
    difficulty_breakdown: DifficultyBreakdown
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Station':
        """
        Create a Station instance from a dictionary.
        
        Args:
            data (Dict): Dictionary containing station data
            
        Returns:
            Station: A new Station instance populated with the data
        """
        difficulty = DifficultyBreakdown(
            easy_km=data.get('difficulty_breakdown', {}).get('easy_km', 0),
            intermediate_km=data.get('difficulty_breakdown', {}).get('intermediate_km', 0),
            difficult_km=data.get('difficulty_breakdown', {}).get('difficult_km', 0)
        )
        
        return cls(
            name=data['name'],
            region=data.get('region', ''),
            base_altitude=data.get('base_altitude', 0),
            top_altitude=data.get('top_altitude', 0),
            vertical_drop=data.get('vertical_drop', 0),
            total_pistes_km=data.get('total_pistes_km', 0),
            difficulty_breakdown=difficulty
        )
    
    def to_dict(self) -> Dict:
        """
        Convert the Station instance to a dictionary.
        
        Returns:
            Dict: Dictionary representation of the Station
        """
        return {
            'name': self.name,
            'region': self.region,
            'base_altitude': self.base_altitude,
            'top_altitude': self.top_altitude,
            'vertical_drop': self.vertical_drop,
            'total_pistes_km': self.total_pistes_km,
            'difficulty_breakdown': {
                'easy_km': self.difficulty_breakdown.easy_km,
                'intermediate_km': self.difficulty_breakdown.intermediate_km,
                'difficult_km': self.difficulty_breakdown.difficult_km
            }
        }