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
        model_name: str
    ) -> str:
        """
        Generate a personalised ski season plan.

        Args:
            preferences: User preferences including home location and criteria
            trips: List of planned trips
            model_name: Name of the LLM model to use

        Returns:
            str: Generated ski plan
        """
        logger.info(
            f"Generating ski plan for {len(trips)} trips using model {model_name}")
        logger.debug(f"User preferences: {preferences}")
        
        # Use the agent service to execute the prompt with the enriched stations
        response = self.agent_service.get_plan(preferences, trips, model_name)
        return response
        
    async def generate_ski_plan_streaming(
        self,
        preferences: UserPreferences,
        trips: List[Trip],
        model_name: str
    ):
        """
        Generate a personalised ski season plan with streaming output.

        Args:
            preferences: User preferences including home location and criteria
            trips: List of planned trips
            model_name: Name of the LLM model to use

        Yields:
            dict: Streaming events from the agent
        """
        logger.info(
            f"Generating streaming ski plan for {len(trips)} trips using model {model_name}")
        logger.debug(f"User preferences: {preferences}")
        
        # Use the agent service to execute the prompt with streaming
        async for event in self.agent_service.get_plan_streaming(preferences, trips, model_name):
            yield event


def get_planner_service():
    """Get a singleton instance of PlannerService."""
    return PlannerService()
