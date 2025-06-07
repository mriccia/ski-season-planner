"""
Service layer for handling ski plan generation using LLM.
"""
from typing import List, Dict
import logging
import copy
from ski_planner_app.models.trip import Trip, UserPreferences
from ski_planner_app.services.station_service import StationService
from ski_planner_app.services.agent_service import AgentService
from ski_planner_app.services.singleton import singleton_session
from ski_planner_app.services.distance_service import DistanceService

logger = logging.getLogger(__name__)


@singleton_session("service")
class PlannerService:
    def __init__(self):
        """
        Initialise the PlannerService.
        """
        self.agent_service = AgentService()
        self.distance_service = DistanceService()
        self.station_service = StationService()

    def generate_ski_plan(
        self,
        preferences: UserPreferences,
        trips: List[Trip],
        model_name: str,
        stations: List[object]
    ) -> str:
        """
        Generate a personalised ski season plan.

        Args:
            preferences: User preferences including home location and criteria
            trips: List of planned trips
            model_name: Name of the LLM model to use
            stations: List of ski stations/resorts

        Returns:
            str: Generated ski plan
        """
        logger.info(
            f"Generating ski plan for {len(trips)} trips using model {model_name}")
        logger.debug(f"User preferences: {preferences}")
        
        # Ensure distances are calculated before generating plan
        home_location = preferences.home_location
        transport_mode = "driving-car" if preferences.transport_mode == "Car" else "public-transport"
        
        # Get station locations with coordinates
        station_locations = self.station_service.get_all_locations_with_coordinates()
        
        # Check if distances are already calculated
        if not self.distance_service.is_origin_calculated(home_location, transport_mode):
            logger.info(f"Calculating distances from {home_location} to all stations")
            result = self.distance_service.prefetch_all_distances(
                home_location, station_locations, transport_mode
            )
            if result["status"] != "completed" and result["status"] != "already_calculated":
                logger.error(f"Failed to calculate distances: {result}")
                raise RuntimeError(f"Failed to calculate distances: {result.get('error', 'Unknown error')}")
        
        # Get all stations with their distances
        stations_with_distances = self.distance_service.get_all_distances(
            home_location, transport_mode
        )
        
        # Create a lookup dictionary for quick access to distance data
        distance_lookup = {
            station.get('name'): {
                'distance': station.get('distance'),
                'duration': station.get('duration')
            }
            for station in stations_with_distances
            if station.get('name') and station.get('distance') is not None
        }
        
        # Create a copy of stations to avoid modifying the original objects
        enriched_stations = []
        for station in stations:
            # Create a copy of the station object to avoid modifying the original
            station_copy = copy.deepcopy(station)
            
            # Add distance and duration if available in the lookup
            if station.name in distance_lookup:
                station_copy.distance = distance_lookup[station.name]['distance']
                station_copy.duration = distance_lookup[station.name]['duration']
            else:
                # If no distance data is available, log a warning
                logger.warning(f"No distance data available for station: {station.name}")
                # Set default values to avoid None errors
                station_copy.distance = None
                station_copy.duration = None
                
            enriched_stations.append(station_copy)
        
        # Log how many stations have distance data
        stations_with_data = sum(1 for s in enriched_stations if hasattr(s, 'distance') and s.distance is not None)
        logger.info(f"Enriched {stations_with_data} out of {len(enriched_stations)} stations with distance data")

        # Use the agent service to execute the prompt with the enriched stations
        response = self.agent_service.get_plan(
            preferences, trips, model_name, enriched_stations)
        return response


def get_planner_service():
    """Get a singleton instance of PlannerService."""
    return PlannerService()
