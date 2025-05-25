"""
Models for representing ski stations and related data structures.
"""
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class DifficultyBreakdown:
    easy_km: float = 0
    intermediate_km: float = 0
    difficult_km: float = 0

@dataclass
class Station:
    name: str
    region: str
    base_altitude: int
    top_altitude: int
    vertical_drop: int
    total_pistes_km: float
    difficulty_breakdown: DifficultyBreakdown
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Station':
        """Create a Station instance from a dictionary."""
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
        """Convert the Station instance to a dictionary."""
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