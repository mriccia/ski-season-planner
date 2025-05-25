"""
Service layer for handling ski plan generation using LLM.
"""
from typing import List, Dict, Any, Optional
import requests
from ..models.trip import Trip, UserPreferences

class PlannerService:
    def __init__(self, ollama_url: str = "http://localhost:11434"):
        self.ollama_url = ollama_url
        self._langchain_available = self._check_langchain()
    
    def _check_langchain(self) -> bool:
        """Check if LangChain is available."""
        try:
            from langchain.prompts import PromptTemplate
            return True
        except ImportError:
            return False
    
    def is_llm_configured(self) -> bool:
        """Check if LLM is available and configured."""
        if not self._langchain_available:
            return False
        return self._is_ollama_running()
    
    def _is_ollama_running(self) -> bool:
        """Check if Ollama is running locally."""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags")
            return response.status_code == 200
        except:
            return False
    
    def generate_ski_plan(
        self,
        preferences: UserPreferences,
        trips: List[Trip],
        model_name: str = "llama3"
    ) -> str:
        """Generate a personalized ski season plan using Ollama."""
        if not self._langchain_available:
            return self.mock_generate_ski_plan(preferences, trips)
        
        if not self._is_ollama_running():
            return "Ollama is not running. Please start Ollama service."
        
        prompt = self._create_prompt(preferences, trips)
        
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": model_name,
                    "prompt": prompt,
                    "stream": False
                }
            )
            
            if response.status_code == 200:
                return response.json().get("response", "Error: No response from Ollama")
            else:
                return f"Error: Ollama returned status code {response.status_code}"
        except Exception as e:
            return f"Error calling Ollama API: {str(e)}"
    
    def mock_generate_ski_plan(
        self,
        preferences: UserPreferences,
        trips: List[Trip]
    ) -> str:
        """Generate a mock ski plan when LLM is not available."""
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
                plan += "No matching stations found for your criteria. Consider adjusting your preferences.\n"
            
            plan += "\n"
        
        plan += "\n## Note\n"
        plan += "This is a mock ski plan. For a more detailed and personalized plan, please configure the LLM integration."
        
        return plan
    
    def _create_prompt(self, preferences: UserPreferences, trips: List[Trip]) -> str:
        """Create the prompt for the LLM."""
        trips_text = ""
        for i, trip in enumerate(trips):
            stations_text = ", ".join([s.name for s in trip.matching_stations[:5]])
            trips_text += f"Trip {i+1}: {trip.start_date.strftime('%Y-%m-%d')} to {trip.end_date.strftime('%Y-%m-%d')}\n"
            trips_text += f"Matching stations: {stations_text}\n\n"
        
        priorities_text = ", ".join([f"{k} (weight: {v})" for k, v in preferences.priorities.items()])
        
        return f"""
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