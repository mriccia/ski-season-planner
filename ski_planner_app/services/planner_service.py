"""
Service layer for handling ski plan generation using LLM.
"""
from typing import List
import logging
from ski_planner_app.models.trip import Trip, UserPreferences

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
        
        # Get station locations
        station_locations = [station.location for station in stations]
        
        # Check if distances are already calculated
        if not self.distance_service.is_origin_calculated(home_location, transport_mode):
            logger.info(f"Calculating distances from {home_location} to all stations")
            self.distance_service.prefetch_all_distances(home_location, station_locations, transport_mode)

        # Use the agent service to execute the prompt
        response = self.agent_service.get_plan(
            preferences, trips, model_name, stations)
        return response

# Function to get a singleton instance of PlannerService


def get_planner_service():
    return PlannerService()
