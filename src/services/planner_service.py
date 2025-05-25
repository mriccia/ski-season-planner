"""
Service layer for handling ski plan generation using LLM.
"""
from typing import List, Dict, Any, Optional
import logging
import requests
from ..models.trip import Trip, UserPreferences

logger = logging.getLogger(__name__)

class PlannerService:
    def __init__(self, ollama_url: str = "http://localhost:11434"):
        logger.debug(f"Initializing PlannerService with Ollama URL: {ollama_url}")
        self.ollama_url = ollama_url
        self._langchain_available = self._check_langchain()
        if self._langchain_available:
            logger.info("LangChain is available")
        else:
            logger.warning("LangChain is not available - will use mock responses")
    
    def _check_langchain(self) -> bool:
        """Check if LangChain is available."""
        try:
            from langchain.prompts import PromptTemplate
            return True
        except ImportError as e:
            logger.warning(f"LangChain import failed: {str(e)}")
            return False
    
    def is_llm_configured(self) -> bool:
        """Check if LLM is available and configured."""
        if not self._langchain_available:
            logger.debug("LLM not configured: LangChain unavailable")
            return False
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
    
    def generate_ski_plan(
        self,
        preferences: UserPreferences,
        trips: List[Trip],
        model_name: str = "llama3"
    ) -> str:
        """Generate a personalized ski season plan using Ollama."""
        logger.info(f"Generating ski plan for {len(trips)} trips using model {model_name}")
        logger.debug(f"User preferences: {preferences}")
        
        if not self._langchain_available:
            logger.warning("Using mock plan generation due to missing LangChain")
            return self.mock_generate_ski_plan(preferences, trips)
        
        if not self._is_ollama_running():
            logger.error("Cannot generate plan: Ollama service is not running")
            return "Ollama is not running. Please start Ollama service."
        
        prompt = self._create_prompt(preferences, trips)
        logger.debug(f"Generated prompt of length {len(prompt)}")
        
        try:
            logger.debug(f"Sending request to Ollama API with model {model_name}")
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": model_name,
                    "prompt": prompt,
                    "stream": False
                }
            )
            
            if response.status_code == 200:
                plan = response.json().get("response", "Error: No response from Ollama")
                logger.info(f"Successfully generated plan of length {len(plan)}")
                return plan
            else:
                error_msg = f"Error: Ollama returned status code {response.status_code}"
                logger.error(error_msg)
                return error_msg
        except requests.exceptions.RequestException as e:
            error_msg = f"Error calling Ollama API: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return error_msg
        except Exception as e:
            error_msg = f"Unexpected error in plan generation: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return error_msg
    
    def mock_generate_ski_plan(
        self,
        preferences: UserPreferences,
        trips: List[Trip]
    ) -> str:
        """Generate a mock ski plan when LLM is not available."""
        logger.info("Generating mock ski plan")
        logger.debug(f"Mock plan for {len(trips)} trips with preferences: {preferences}")
        
        try:
            plan = f"# Personalized Ski Season Plan for {preferences.home_location}\n\n"
            
            plan += "## Your Preferences\n"
            plan += f"- Selected criteria: {', '.join(preferences.criteria)}\n"
            plan += "- Priorities:\n"
            for k, v in preferences.priorities.items():
                plan += f"  * {k.replace('_', ' ').title()}: {v}/10\n"
            
            plan += "\n## Trip Recommendations\n\n"
            
            for i, trip in enumerate(trips):
                plan += f"### Trip {i+1}: {trip.start_date.strftime('%Y-%m-%d')} to {trip.end_date.strftime('%Y-%m-%d')}\n\n"
                
                if trip.matching_stations:
                    top_station = trip.matching_stations[0]
                    plan += f"**Primary Recommendation: {top_station.name}**\n\n"
                    plan += "Why this resort:\n"
                    plan += f"- Located in the {top_station.region} region\n"
                    plan += f"- Base altitude: {top_station.base_altitude}m\n"
                    plan += f"- Top altitude: {top_station.top_altitude}m\n"
                    plan += f"- Total pistes: {top_station.total_pistes_km}km\n"
                    
                    plan += "\nAlternative options:\n"
                    for station in trip.matching_stations[1:3]:
                        plan += f"- {station.name} ({station.region})\n"
                else:
                    logger.warning(f"No matching stations found for trip {i+1}")
                    plan += "No matching stations found for your criteria. Consider adjusting your preferences.\n"
                
                plan += "\n"
            
            plan += "\n## Note\n"
            plan += "This is a mock ski plan. For a more detailed and personalized plan, please configure the LLM integration."
            
            logger.info(f"Successfully generated mock plan of length {len(plan)}")
            return plan
            
        except Exception as e:
            error_msg = f"Error generating mock plan: {str(e)}"
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
            
            Please create a detailed ski season plan that:
            1. Recommends specific resorts for each trip date
            2. Explains why each resort is a good match for their preferences
            3. Suggests any adjustments to their trip dates if it would improve their experience
            4. Provides tips for each resort (best runs, facilities to check out, etc.)
            
            Ski Season Plan:
            """
            
            logger.debug(f"Created prompt of length {len(prompt)}")
            return prompt
            
        except Exception as e:
            logger.error(f"Error creating prompt: {str(e)}", exc_info=True)
            raise