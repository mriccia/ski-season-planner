"""
Service layer for handling ski plan generation using LLM.
"""
from typing import List, Dict, Any, Optional
import logging
import requests
from models.trip import Trip, UserPreferences

from strands.tools.mcp import MCPClient
from mcp import stdio_client, StdioServerParameters
from strands.models.ollama import OllamaModel

from strands import Agent
from strands.tools.mcp import MCPClient
import streamlit as st



logger = logging.getLogger(__name__)

class PlannerService:
    def __init__(self, ollama_url: str = "http://localhost:11434"):
        logger.debug(f"Initializing PlannerService with Ollama URL: {ollama_url}")
        self.ollama_url = ollama_url
    
    def is_llm_configured(self) -> bool:
        """Check if LLM is available and configured."""
        return self._is_ollama_running()
    
    def _is_ollama_running(self) -> bool:
        """Check if Ollama is running locally."""
        try:
            logger.debug("Checking Ollama service status")
            response = requests.get(f"{self.ollama_url}/api/tags")
            is_running = response.status_code == 200
            if is_running:
                logger.info("Ollama service is running")
            else:
                logger.warning(f"Ollama service returned status code {response.status_code}")
            return is_running
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to connect to Ollama service: {str(e)}")
            return False
    def _get_agent(self, model_name: str) -> MCPClient:
        """Get the agent for the given model."""
        logger.debug(f"Getting agent for model {model_name}")
        
        mcp_fetch = MCPClient(
            lambda: stdio_client(
                StdioServerParameters(
                    command="uvx",
                    args=["mcp-server-fetch"]
                )
            )
        )
        
        ollama_model = OllamaModel(
            host=self.ollama_url,
            model_id=model_name
        )
        with mcp_fetch:
            agent = Agent(
                tools=mcp_fetch.list_tools_sync(),
                model=ollama_model
            )
            
            logger.debug(f"Agent for model {model_name} retrieved")
            return agent
    
    def generate_ski_plan(
        self,
        preferences: UserPreferences,
        trips: List[Trip],
        model_name: str,
        stations: List[object]
    ) -> str:
        """Generate a personalized ski season plan using Ollama."""
        logger.info(f"Generating ski plan for {len(trips)} trips using model {model_name}")
        logger.debug(f"User preferences: {preferences}")
        
        if not self._is_ollama_running():
            logger.error("Cannot generate plan: Ollama service is not running")
            return "Ollama is not running. Please start Ollama service."
        
        prompt = self._create_prompt(preferences, trips, stations)
        logger.debug(f"Generated prompt of length {len(prompt)}")
        
        try:
            logger.debug(f"Sending request to Ollama API with model {model_name}")
            agent = self._get_agent(model_name)
            response = agent(prompt)
            logger.debug(f"Response: {response}")
            return response.__str__()
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Error calling Ollama API: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return error_msg
        except Exception as e:
            error_msg = f"Unexpected error in plan generation: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return error_msg
    
    def _create_prompt(self, preferences: UserPreferences, trips: List[Trip], stations: List[object]) -> str:
        """Create the prompt for the LLM."""
        logger.debug("Creating LLM prompt")
        try:
            trips_text = ""
            for i, trip in enumerate(trips):
                trips_text += f"Trip {i+1}: {trip.start_date.strftime('%Y-%m-%d')} to {trip.end_date.strftime('%Y-%m-%d')}\n"
            
            priorities_text = ", ".join([f"{k} (weight: {v})" for k, v in preferences.priorities.items()])
            
            prompt = f"""
You are a ski trip planner. Create a personalized ski season plan for a person living in {preferences.home_location}.

They have the following trips planned:
{trips_text}

Here are all the resorts that are part of the Magic Pass:
{stations}

Their skiing preferences and priorities are:

Criteria: {', '.join(preferences.criteria)}
Priorities: {priorities_text}
Mode of Transport: {preferences.transport_mode}
Please create a detailed ski season plan that:

Recommends a specific resort for each trip date.
Explains why each resort is a good match for their preferences.
Suggests any adjustments to their trip dates if it would improve their experience.
Provides tips for each resort (best runs, facilities to check out, etc.).
Includes transport recommendations based on their preferred mode of transport ({preferences.transport_mode}).
Please use the mcp_fetch tool to access direction information. In your suggestions, include the distance and estimated travel time from their home location ({preferences.home_location}) to each resort.

Make sure to consider the altitude, piste length, vertical drop, and distance from home when making recommendations.

Format your response as a detailed ski season plan, including the following sections:

Introduction
Trip Overview
Resort Recommendations
Tips and Recommendations
Worklog
Please provide the plan in a clear and structured format, suitable for a ski enthusiast to follow.

Guidelines:

Only use the information provided in the trips and preferences.
Do not make assumptions about other trips or resorts.
Only use information from the context provided and from the tools.
If you need to access additional information, use the mcp_fetch tool.
For Magic Pass resorts, use https://www.magicpass.ch/en/stations.
For directions, use the mcp_fetch tool to get the distance and estimated travel time from the home location to each resort. You can leverage the OpenRouteService API for this purpose. The API Key is {st.secrets.get("OPENROUTE_API_KEY")}, and the endpoint is https://api.openrouteservice.org/v2/directions/.
Do not include any information about the Magic Pass or its benefits, as this is not relevant to the ski season plan.
Select only ONE destination for each trip.
Do not make up numbers, facts, or information about the resort.
The aim is to help the human decide which resort to go to on which trip, based on the criteria.
Include a <worklog> section in the output, detailing all the steps taken, which tools were called, and why.

Ski Season Plan:
            """
            
            logger.debug(f"Created prompt of length {len(prompt)}")
            return prompt
            
        except Exception as e:
            logger.error(f"Error creating prompt: {str(e)}", exc_info=True)
            raise