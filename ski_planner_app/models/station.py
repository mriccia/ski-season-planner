"""
Models for representing ski stations and related data structures.
"""
from dataclasses import dataclass
from typing import Dict, Optional, List

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
        longitude (float): Longitude coordinate
        latitude (float): Latitude coordinate
        magic_pass_url (str): URL to the Magic Pass page for this station
    """
    name: str
    region: str
    base_altitude: int
    top_altitude: int
    vertical_drop: int
    total_pistes_km: float
    longitude: float
    latitude: float
    magic_pass_url: str
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Station':
        """
        Create a Station instance from a dictionary.
        
        Args:
            data (Dict): Dictionary containing station data
            
        Returns:
            Station: A new Station instance populated with the data
        """
        return cls(
            name=data['name'],
            region=data.get('region'),
            base_altitude=data.get('base_altitude'),
            top_altitude=data.get('top_altitude'),
            vertical_drop=data.get('vertical_drop'),
            total_pistes_km=data.get('total_pistes_km'),
            longitude=data.get('longitude'),
            latitude=data.get('latitude'),
            magic_pass_url=data['magic_pass_url']
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
            'longitude': self.longitude,
            'latitude': self.latitude,
            'magic_pass_url': self.magic_pass_url
        }
    
    def get_coordinates(self) -> List[float]:
        """Return coordinates as [longitude, latitude] list for API calls."""
        return [self.longitude, self.latitude]
