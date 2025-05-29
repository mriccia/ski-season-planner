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
from strands.models.openai import OpenAIModel

from strands import Agent
from strands.tools.mcp import MCPClient

from strands_tools import calculator, shell
import streamlit as st
from services.openrouteservice_tool import get_directions

openai_model = OpenAIModel(
    client_args={
        "api_key": st.secrets.get("OPENAI_API_KEY"),
    },
    model_id="gpt-4o"
)

mcp_fetch = MCPClient(
    lambda: stdio_client(
        StdioServerParameters(
            command="uvx",
            args=["mcp-server-fetch"]
        )
    )
)

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
                # Update available models in session state if needed
                if 'available_models' not in st.session_state or not st.session_state.available_models:
                    models = [model["name"] for model in response.json().get("models", [])]
                    st.session_state.available_models = models
                    logger.info(f"Updated available models in session state: {models}")
            else:
                logger.warning(f"Ollama service returned status code {response.status_code}")
            return is_running
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to connect to Ollama service: {str(e)}")
            return False
        
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
            with mcp_fetch:
                agent = Agent(
                    tools=[calculator, get_directions] + mcp_fetch.list_tools_sync(),
                    model=openai_model,
                )
                logger.debug(f"Agent for model {model_name} retrieved")
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
            
You are a ski trip planner. Your task is to create a personalized ski season plan for a person living in {preferences.home_location}.

**Trips Planned:**
The user has {len(trips)} trips planned:
{trips_text}

**Available Resorts:**
{stations}

**CRITICAL INSTRUCTION:**
You MUST calculate the distance and travel time from {preferences.home_location} to EVERY resort in the list using the `get_directions` tool. This is mandatory before making any recommendations. The tool now returns a simplified response with only distance_km and duration_minutes.

**Preferences:**
- Criteria: {', '.join(preferences.criteria)}
- Priorities (between 1 and 10): {priorities_text}
- Mode of Transport: {preferences.transport_mode}

**Tasks:**
1. First, calculate the distance and travel time from {preferences.home_location} to EVERY resort using the `get_directions` tool.
2. Create a comprehensive comparison table of ALL resorts with their distances, travel times, and key features.
3. Based on this complete data, recommend one specific resort for each of the {len(trips)} trips.
4. Explain why each resort matches their preferences.
5. Suggest any adjustments to trip dates for a better experience.
6. Provide tips for each resort (best runs, facilities, etc.).
7. Include transport recommendations based on their preferred mode of transport.

**Guidelines:**
- The `get_directions` tool must be used for EVERY resort to calculate distance and travel time from {preferences.home_location}. Use it like this: `get_directions("{preferences.home_location}", "Resort Name, Region")`.
- Consider the following factors when making recommendations: altitude, piste length, vertical drop, and distance from home.
- Only use the information provided in the trips and preferences. Do not make assumptions.
- Do not include information about the Magic Pass or its benefits.
- Include a `<worklog>` section detailing the steps taken and tools used.
- If you need to access additional information, use the fetch tool.
-- For magic pass resorts, use https://www.magicpass.ch/en/stations
-- For directions, you must use the `get_directions` tool to get the distance and estimated travel time from the home location to each resort.

**Format:**
1. Introduction
2. Complete Resort Comparison Table (including ALL resorts with distances and travel times)
3. Trip Overview with Recommendations
4. Tips and Recommendations
5. Worklog (must include evidence of calculating distances for ALL resorts)

**Steps to Follow:**
1. **Calculate ALL Distances:** Use the `get_directions` tool to calculate the distance and travel time from {preferences.home_location} to EVERY resort.
2. **Create Comparison Table:** Compile all data into a comprehensive comparison table.
3. **Filter Resorts:** Filter the resorts based on the user's criteria and priorities.
4. **Recommend Resorts:** Recommend one specific resort for each of the {len(trips)} trips based on the complete data.
5. **Provide Details:** Explain why each resort is a good match, provide tips, and include transport recommendations.
6. **Document Steps:** Document all the steps taken and tools used in the `<worklog>` section, including evidence that ALL resorts were evaluated.

Please ensure you have all the necessary tools and data available to complete this task. Only return your response once the plan is fully generated and all steps are completed.
            """
            
            logger.debug(f"Created prompt of length {len(prompt)}")
            return prompt
            
        except Exception as e:
            logger.error(f"Error creating prompt: {str(e)}", exc_info=True)
            raise