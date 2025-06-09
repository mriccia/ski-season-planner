"""
Distance service for the Ski Season Planner application.
Handles bulk distance calculations and caching using the database.
"""
import logging
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Optional, Callable
from ski_planner_app.services.database_service import DatabaseService
import requests
import streamlit as st

logger = logging.getLogger(__name__)

def get_api_key():
    return st.secrets.get("OPENROUTE_API_KEY")

def retry_with_backoff(max_retries=3, initial_delay=10, jitter_factor=0.1):
    """
    Decorator to retry a function with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        jitter_factor: Factor to add randomness to delay
        
    Returns:
        Decorator function
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            retries = 0
            delay = initial_delay
            
            while True:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    if retries >= max_retries:
                        logger.error(f"Max retries reached for {func.__name__}. Giving up.")
                        raise
                    
                    # Calculate backoff with jitter
                    jitter = delay * jitter_factor * random.uniform(-1, 1)
                    wait_time = delay + jitter
                    
                    logger.warning(f"Error in {func.__name__}, retrying in {wait_time:.2f} seconds (attempt {retries}/{max_retries})")
                    time.sleep(wait_time)
                    
                    # Exponential backoff
                    delay *= 2
        
        return wrapper
    return decorator

class DistanceService:
    """Service for handling distance calculations and caching."""
    
    def __init__(self):
        """Initialize the distance service."""
        self.db_service = DatabaseService()
        self.api_key = get_api_key()
    
    def is_origin_calculated(self, origin: str, transport_mode: str) -> bool:
        """
        Check if all distances from an origin have been calculated.
        
        Args:
            origin: Origin location
            transport_mode: Mode of transport
            
        Returns:
            bool: True if the origin has been fully calculated, False otherwise
        """
        return self.db_service.check_origin_calculated(origin, transport_mode)
    
    def get_cached_distance(self, origin: str, destination: str, transport_mode: str) -> Optional[Dict[str, Any]]:
        """
        Get cached distance data if available.
        
        Args:
            origin: Origin location
            destination: Destination location
            transport_mode: Mode of transport
            
        Returns:
            Dict with distance and duration if found, None otherwise
        """
        return self.db_service.get_distance(origin, destination, transport_mode)
    
    @retry_with_backoff(max_retries=3, initial_delay=60)
    def _calculate_route(self, origin_coords: List[float], dest_coords: List[float], transport_mode: str) -> Dict[str, Any]:
        """
        Calculate route between two sets of coordinates.
        
        Args:
            origin_coords: Origin coordinates [longitude, latitude]
            dest_coords: Destination coordinates [longitude, latitude]
            transport_mode: Mode of transport
            
        Returns:
            Dict with distance and duration information
        """
        url = f"https://api.openrouteservice.org/v2/directions/{transport_mode}"
        
        headers = {
            'Accept': 'application/json, application/geo+json, application/gpx+xml',
            'Authorization': self.api_key,
            'Content-Type': 'application/json'
        }
        
        body = {
            "coordinates": [origin_coords, dest_coords],
            "format": "json"
        }
        
        response = requests.post(url, json=body, headers=headers)
        response.raise_for_status()
        response_data = response.json()
        
        if response_data.get("routes") and len(response_data["routes"]) > 0:
            summary = response_data["routes"][0].get("summary", {})
            
            # Convert distance from meters to kilometers and duration from seconds to minutes
            distance_km = round(summary.get("distance", 0) / 1000, 1)  # Convert m to km
            duration_minutes = round(summary.get("duration", 0) / 60)   # Convert seconds to minutes
            
            return {
                "distance_km": distance_km,
                "duration_minutes": duration_minutes
            }
        else:
            raise ValueError("No routes found in the response")
    
    def geocode_location(self, location_name: str) -> Optional[List[float]]:
        """
        Convert a location name to coordinates using OpenRoute Service Geocoding API.
        
        Args:
            location_name (str): Location name (e.g., "Geneva,Switzerland")
            
        Returns:
            list: [longitude, latitude] coordinates or None if geocoding failed
        """
        url = "https://api.openrouteservice.org/geocode/search"
        
        headers = {
            'Accept': 'application/json, application/geo+json, application/gpx+xml',
            'Authorization': self.api_key
        }
        
        params = {
            'text': location_name,
            'size': 1  # Get only the top result
        }
        
        try:
            response = requests.get(url, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            # Extract coordinates from the first feature
            if data.get('features') and len(data['features']) > 0:
                coordinates = data['features'][0]['geometry']['coordinates']
                logger.info(f"Successfully geocoded {location_name} to coordinates {coordinates}")
                return coordinates  # [longitude, latitude]
            
            logger.warning(f"Could not find coordinates for {location_name}")
            return None
        except requests.exceptions.RequestException as e:
            logger.warning(f"Error geocoding location: {e}")
            raise e  # Re-raise the exception to be handled by the retry decorator
    @retry_with_backoff(max_retries=3, initial_delay=60)
    def _geocode_origin(self, origin: str) -> Optional[List[float]]:
        """
        Geocode the origin location with built-in retry logic.
        
        Args:
            origin: Origin location to geocode
            
        Returns:
            List[float]: Coordinates as [longitude, latitude] or None if geocoding failed
        """
        try:
            return self.geocode_location(origin)
        except Exception as e:
            logger.error(f"Failed to geocode origin {origin}: {e}")
            return None
            
    def _process_destinations_in_parallel(
        self, 
        origin: str, 
        origin_coords: List[float], 
        destinations: List[Dict[str, Any]], 
        transport_mode: str,
        results: Dict[str, Any]
    ) -> None:
        """
        Process destinations in parallel using ThreadPoolExecutor.
        
        Args:
            origin: Origin location
            origin_coords: Origin coordinates [longitude, latitude]
            destinations: List of dictionaries with station name and coordinates
            transport_mode: Mode of transport
            results: Dictionary to update with results
        """
        def process_destination(station_data: Dict[str, Any]) -> Dict[str, Any]:
            """Process a single destination."""
            station_name = station_data['name']
            station_coords = station_data['coordinates']
            
            # Skip if no coordinates available
            if not station_coords:
                return {
                    "success": False, 
                    "destination": station_name, 
                    "error": "No coordinates available for station"
                }
            
            try:
                # Calculate route using coordinates
                route_result = self._calculate_route_with_retry(origin_coords, station_coords, transport_mode)
                
                # Save to database
                self.db_service.save_distance(
                    origin, 
                    station_name,
                    transport_mode, 
                    route_result["distance_km"], 
                    route_result["duration_minutes"]
                )
                
                return {
                    "success": True, 
                    "destination": station_name,
                    "distance_km": route_result["distance_km"],
                    "duration_minutes": route_result["duration_minutes"]
                }
            except Exception as e:
                logger.error(f"Error calculating route to {station_name}: {e}")
                return {"success": False, "destination": station_name, "error": str(e)}
        
        # Use ThreadPoolExecutor to process destinations in parallel
        # Limit concurrency to avoid overwhelming the API
        max_workers = min(10, len(destinations))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_station = {
                executor.submit(process_destination, station): station 
                for station in destinations
            }
            
            # Process results as they complete
            for future in as_completed(future_to_station):
                station = future_to_station[future]
                try:
                    result = future.result()
                    if result["success"]:
                        results["newly_calculated"] += 1
                        logger.info(f"Successfully calculated distance to {station['name']}: {result.get('distance_km')} km, {result.get('duration_minutes')} min")
                    else:
                        results["failed"] += 1
                        logger.warning(f"Failed to calculate distance to {station['name']}: {result.get('error')}")
                except Exception as e:
                    logger.error(f"Exception processing {station['name']}: {str(e)}")
                    results["failed"] += 1
                    
    def _calculate_route_with_retry(self, origin_coords: List[float], dest_coords: List[float], transport_mode: str) -> Dict[str, Any]:
        """
        Calculate route between two sets of coordinates with retry logic.
        
        Args:
            origin_coords: Origin coordinates [longitude, latitude]
            dest_coords: Destination coordinates [longitude, latitude]
            transport_mode: Mode of transport
            
        Returns:
            Dict with distance and duration information
        """
        @retry_with_backoff(max_retries=3, initial_delay=60)
        def calculate_with_retry():
            return self._calculate_route(origin_coords, dest_coords, transport_mode)
            
        return calculate_with_retry()
    
    def prefetch_all_distances(self, origin: str, stations_with_coords: List[Dict[str, Any]], transport_mode: str = "driving-car") -> Dict[str, Any]:
        """
        Prefetch distances for all destinations from a given origin using parallel processing.
        
        Args:
            origin: Origin location
            stations_with_coords: List of dictionaries with station name and coordinates
            transport_mode: Mode of transport
            
        Returns:
            Dict with results summary
        """
        # Check if already calculated
        if self.is_origin_calculated(origin, transport_mode):
            logger.info(f"Distances from {origin} already calculated, skipping prefetch")
            return {
                "status": "already_calculated",
                "origin": origin,
                "transport_mode": transport_mode
            }
        
        # Get destinations that already have data
        existing_destinations = self.db_service.get_all_destinations_with_distances(origin, transport_mode)
        
        # Filter out destinations that need to be fetched
        destinations_to_fetch = [
            station for station in stations_with_coords 
            if station['name'] not in existing_destinations and station['coordinates']
        ]
        
        if not destinations_to_fetch:
            logger.info(f"No new destinations to fetch for {origin}")
            return {
                "status": "completed",
                "origin": origin,
                "transport_mode": transport_mode,
                "total_destinations": len(stations_with_coords),
                "already_cached": len(existing_destinations),
                "newly_calculated": 0,
                "failed": 0
            }
        
        logger.info(f"Prefetching distances from {origin} to {len(destinations_to_fetch)} destinations in parallel")
        
        results = {
            "status": "completed",
            "origin": origin,
            "transport_mode": transport_mode,
            "total_destinations": len(stations_with_coords),
            "already_cached": len(existing_destinations),
            "newly_calculated": 0,
            "failed": 0
        }
        
        # Geocode origin once with retry
        origin_coords = self._geocode_origin(origin)
        if not origin_coords:
            return {
                "status": "failed",
                "error": "Could not geocode origin location",
                "origin": origin,
                "transport_mode": transport_mode
            }
        
        # Process destinations in parallel
        self._process_destinations_in_parallel(
            origin, origin_coords, destinations_to_fetch, transport_mode, results
        )
        
        # Mark origin as calculated if we have at least some successful calculations
        if results["newly_calculated"] > 0:
            self.db_service.mark_origin_calculated(origin, transport_mode, True)
        
        return results
    
    def get_all_distances(self, origin: str, transport_mode: str) -> List[Dict[str, Any]]:
        """
        Get all calculated distances from an origin.
        
        Args:
            origin: Origin location
            transport_mode: Mode of transport
            
        Returns:
            List of dictionaries with destination, distance, and duration information
        """
        # Get all stations with their distances
        return self.db_service.get_all_stations_with_distances(origin, transport_mode)
