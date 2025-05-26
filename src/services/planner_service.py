"""
Service layer for handling ski plan generation using LLM.
"""
from typing import List, Dict, Any, Optional
import logging
import requests
from ..models.trip import Trip, UserPreferences

from strands.tools.mcp import MCPClient
from mcp import stdio_client, StdioServerParameters
from strands.models.ollama import OllamaModel

from strands import Agent
from strands.tools.mcp import MCPClient



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
        
        playwright = MCPClient(
            lambda: stdio_client(
                StdioServerParameters(
                    command="npx",
                    args=["@playwright/mcp@latest"]
                )
            )
        )
        
        ollama_model = OllamaModel(
            host=self.ollama_url,
            model_id=model_name
        )
        with playwright:
            agent = Agent(
                tools=playwright.list_tools_sync(),
                model=ollama_model
            )
            
            logger.debug(f"Agent for model {model_name} retrieved")
            return agent
    
    def generate_ski_plan(
        self,
        preferences: UserPreferences,
        trips: List[Trip],
        model_name: str
    ) -> str:
        """Generate a personalized ski season plan using Ollama."""
        logger.info(f"Generating ski plan for {len(trips)} trips using model {model_name}")
        logger.debug(f"User preferences: {preferences}")
        
        if not self._is_ollama_running():
            logger.error("Cannot generate plan: Ollama service is not running")
            return "Ollama is not running. Please start Ollama service."
        
        prompt = self._create_prompt(preferences, trips)
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
    
    def _create_prompt(self, preferences: UserPreferences, trips: List[Trip]) -> str:
        """Create the prompt for the LLM."""
        logger.debug("Creating LLM prompt")
        try:
            trips_text = ""
            for i, trip in enumerate(trips):
                stations_text = ", ".join([s.name for s in trip.matching_stations[:5]])
                trips_text += f"Trip {i+1}: {trip.start_date.strftime('%Y-%m-%d')} to {trip.end_date.strftime('%Y-%m-%d')}\n"
                trips_text += f"Matching stations: {stations_text}\n\n"
            
            priorities_text = ", ".join([f"{k} (weight: {v})" for k, v in preferences.priorities.items()])
            
            prompt = f"""
            You are a ski trip planner. Create a personalized ski season plan for a person living in {preferences.home_location}.
            
            They have the following trips planned:
            {trips_text}
            
            Their skiing preferences and priorities are:
            - Criteria: {', '.join(preferences.criteria)}
            - Priorities: {priorities_text}
            - Mode of Transport: {preferences.transport_mode}
            
            Please create a detailed ski season plan that:
            1. Recommends specific resorts for each trip date
            2. Explains why each resort is a good match for their preferences
            3. Suggests any adjustments to their trip dates if it would improve their experience
            4. Provides tips for each resort (best runs, facilities to check out, etc.)
            5. Includes transport recommendations based on their preferred mode of transport ({preferences.transport_mode})
            
            Ski Season Plan:
            """
            
            logger.debug(f"Created prompt of length {len(prompt)}")
            return prompt
            
        except Exception as e:
            logger.error(f"Error creating prompt: {str(e)}", exc_info=True)
            raise