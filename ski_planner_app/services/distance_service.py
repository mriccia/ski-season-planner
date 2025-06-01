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
from ski_planner_app.services.tools.openrouteservice_tool import geocode_location, get_api_key
import requests

logger = logging.getLogger(__name__)

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
    
    def calculate_distance(self, origin: str, destination: str, transport_mode: str = "driving-car") -> Dict[str, Any]:
        """
        Calculate distance between two locations, using cache if available.
        
        Args:
            origin: Origin location
            destination: Destination location
            transport_mode: Mode of transport
            
        Returns:
            Dict with distance and duration information
        """
        # Check cache first
        cached_data = self.get_cached_distance(origin, destination, transport_mode)
        if cached_data:
            return {
                "start": origin,
                "destination": destination,
                "distance_km": cached_data["distance"],
                "duration_minutes": cached_data["duration"],
                "cached": True
            }
        
        # If not in cache, calculate using the API
        try:
            # Geocode locations
            start_coords = geocode_location(origin, self.api_key)
            end_coords = geocode_location(destination, self.api_key)
            
            if not start_coords or not end_coords:
                logger.warning(f"Could not geocode {origin} or {destination}")
                return {
                    "error": "Could not geocode one or both locations",
                    "distance_km": None,
                    "duration_minutes": None
                }
            
            # Calculate route
            route_result = self._calculate_route(start_coords, end_coords, transport_mode)
            
            # Save to database
            self.db_service.save_distance(
                origin, 
                destination, 
                transport_mode, 
                route_result["distance_km"], 
                route_result["duration_minutes"]
            )
            
            return {
                "start": origin,
                "destination": destination,
                "distance_km": route_result["distance_km"],
                "duration_minutes": route_result["duration_minutes"],
                "cached": False
            }
                
        except Exception as e:
            logger.error(f"Error calculating distance: {e}")
            return {
                "error": str(e),
                "distance_km": None,
                "duration_minutes": None
            }
    
    def prefetch_all_distances(self, origin: str, destinations: List[str], transport_mode: str = "driving-car") -> Dict[str, Any]:
        """
        Prefetch distances for all destinations from a given origin using parallel processing.
        
        Args:
            origin: Origin location
            destinations: List of destination locations
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
        destinations_to_fetch = [d for d in destinations if d not in existing_destinations]
        
        logger.info(f"Prefetching distances from {origin} to {len(destinations_to_fetch)} destinations in parallel")
        
        results = {
            "status": "completed",
            "origin": origin,
            "transport_mode": transport_mode,
            "total_destinations": len(destinations),
            "already_cached": len(existing_destinations),
            "newly_calculated": 0,
            "failed": 0
        }
        
        # Get station details to access region information
        stations = self.db_service.get_all_stations()
        station_regions = {station['name']: station.get('region', '') for station in stations}
        
        # Geocode origin once with retry
        @retry_with_backoff(max_retries=3, initial_delay=60)
        def geocode_origin():
            return geocode_location(origin, self.api_key)
        
        try:
            origin_coords = geocode_origin()
            if not origin_coords:
                logger.error(f"Could not geocode origin: {origin}")
                return {
                    "status": "failed",
                    "error": "Could not geocode origin location",
                    "origin": origin,
                    "transport_mode": transport_mode
                }
        except Exception as e:
            logger.error(f"Failed to geocode origin after retries: {e}")
            return {
                "status": "failed",
                "error": f"Failed to geocode origin: {str(e)}",
                "origin": origin,
                "transport_mode": transport_mode
            }
        
        # Function to process a single destination
        def process_destination(destination):
            # Apply retry with backoff to the destination processing
            @retry_with_backoff(max_retries=3, initial_delay=60)
            def process_with_retry(dest):
                # Try with just the station name first
                dest_coords = geocode_location(dest, self.api_key)
                
                # If that fails, try with region appended
                if not dest_coords and dest in station_regions and station_regions[dest]:
                    region = station_regions[dest]
                    enhanced_dest = f"{dest}, {region}"
                    logger.info(f"Trying with region: {enhanced_dest}")
                    dest_coords = geocode_location(enhanced_dest, self.api_key)
                
                if not dest_coords:
                    return {"success": False, "destination": dest, "error": "Could not geocode destination"}
                
                # Calculate route using already geocoded coordinates
                try:
                    route_result = self._calculate_route(origin_coords, dest_coords, transport_mode)
                    
                    # Save to database
                    self.db_service.save_distance(
                        origin, 
                        dest,  # Use original name in database
                        transport_mode, 
                        route_result["distance_km"], 
                        route_result["duration_minutes"]
                    )
                    
                    return {
                        "success": True, 
                        "destination": dest,
                        "distance_km": route_result["distance_km"],
                        "duration_minutes": route_result["duration_minutes"]
                    }
                except Exception as e:
                    logger.error(f"Error calculating route to {dest}: {e}")
                    return {"success": False, "destination": dest, "error": str(e)}
            
            try:
                return process_with_retry(destination)
            except Exception as e:
                logger.error(f"All retries failed for {destination}: {str(e)}")
                return {"success": False, "destination": destination, "error": str(e)}
        
        # Use ThreadPoolExecutor to process destinations in parallel
        # Limit concurrency to avoid overwhelming the API
        max_workers = min(10, len(destinations_to_fetch))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_destination = {
                executor.submit(process_destination, dest): dest 
                for dest in destinations_to_fetch
            }
            
            # Process results as they complete
            for future in as_completed(future_to_destination):
                destination = future_to_destination[future]
                try:
                    result = future.result()
                    if result["success"]:
                        results["newly_calculated"] += 1
                        logger.info(f"Successfully calculated distance to {destination}: {result.get('distance_km')} km, {result.get('duration_minutes')} min")
                    else:
                        results["failed"] += 1
                        logger.warning(f"Failed to calculate distance to {destination}: {result.get('error')}")
                except Exception as e:
                    logger.error(f"Exception processing {destination}: {str(e)}")
                    results["failed"] += 1
        
        # Mark origin as calculated if we have at least some successful calculations
        if results["newly_calculated"] > 0:
            self.db_service.mark_origin_calculated(origin, transport_mode, True)
        
        return results
    
    def get_closest_stations(self, origin: str, transport_mode: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get the closest stations to an origin location.
        
        Args:
            origin: Origin location
            transport_mode: Mode of transport
            limit: Maximum number of results
            
        Returns:
            List of station dictionaries with distance information
        """
        return self.db_service.get_closest_stations(origin, transport_mode, limit)
    
    def get_stations_by_date(self, origin: str, transport_mode: str, date: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get stations open on a specific date, sorted by distance.
        
        Args:
            origin: Origin location
            transport_mode: Mode of transport
            date: Date in format YYYY-MM-DD
            limit: Maximum number of results
            
        Returns:
            List of station dictionaries with distance information
        """
        return self.db_service.get_stations_by_date(origin, transport_mode, date, limit)
    
    def get_stations_by_piste_length(self, origin: str, transport_mode: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get stations sorted by piste length and then by distance.
        
        Args:
            origin: Origin location
            transport_mode: Mode of transport
            limit: Maximum number of results
            
        Returns:
            List of station dictionaries with distance information
        """
        return self.db_service.get_stations_by_piste_length(origin, transport_mode, limit)
        
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
