"""
Service layer for handling ski plan generation using LLM.
"""
from typing import List, Dict, Any, Optional
import logging
import requests
from models.trip import Trip, UserPreferences

import streamlit as st
from services.agent_service import get_agent_service
from services.singleton import singleton_session

logger = logging.getLogger(__name__)

@singleton_session("service")
class PlannerService:
    def __init__(self):
        """
        Initialise the PlannerService.
        """
        self.agent_service = get_agent_service()
        
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
        logger.info(f"Generating ski plan for {len(trips)} trips using model {model_name}")
        logger.debug(f"User preferences: {preferences}")
        
        # Use the agent service to execute the prompt
        response = self.agent_service.get_plan(preferences, trips, model_name, stations)
        return response

# Function to get a singleton instance of PlannerService
def get_planner_service():
    return PlannerService()
    