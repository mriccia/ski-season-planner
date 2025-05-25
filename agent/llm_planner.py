"""
LLM-based ski season planner module.
This module handles the interaction with language models to generate personalized ski plans.
"""

import os
import requests
from typing import List, Dict, Any

# Check if we're in a development environment with required packages
try:
    from langchain.prompts import PromptTemplate
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

def is_ollama_running():
    """Check if Ollama is running locally"""
    try:
        response = requests.get("http://localhost:11434/api/tags")
        return response.status_code == 200
    except:
        return False

def is_llm_configured():
    """Check if LLM is available and configured"""
    if not LANGCHAIN_AVAILABLE:
        return False
    return is_ollama_running()

def generate_ski_plan(
    home_location: str, 
    trips: List[Dict[str, Any]], 
    criteria: List[str], 
    priorities: Dict[str, int],
    model_name: str = "llama3"
) -> str:
    """
    Generate a personalized ski season plan using Ollama.
    
    Args:
        home_location: User's home location
        trips: List of planned trips with dates and matching stations
        criteria: List of selected criteria
        priorities: Dictionary of priorities with weights
        model_name: Name of the Ollama model to use
        
    Returns:
        A string containing the generated ski plan
    """
    if not LANGCHAIN_AVAILABLE:
        return "LangChain is not available. Please install langchain."
    
    if not is_ollama_running():
        return "Ollama is not running. Please start Ollama service."
    
    # Create the prompt content
    trips_text = ""
    for i, trip in enumerate(trips):
        stations_text = ", ".join([s['name'] for s in trip['matching_stations'][:5]])
        trips_text += f"Trip {i+1}: {trip['start_date'].strftime('%Y-%m-%d')} to {trip['end_date'].strftime('%Y-%m-%d')}\n"
        trips_text += f"Matching stations: {stations_text}\n\n"
    
    priorities_text = ", ".join([f"{k} (weight: {v})" for k, v in priorities.items()])
    
    prompt = f"""
    You are a ski trip planner. Create a personalized ski season plan for a person living in {home_location}.
    
    They have the following trips planned:
    {trips_text}
    
    Their skiing preferences and priorities are:
    - Criteria: {', '.join(criteria)}
    - Priorities: {priorities_text}
    
    Please create a detailed ski season plan that:
    1. Recommends specific resorts for each trip date
    2. Explains why each resort is a good match for their preferences
    3. Suggests any adjustments to their trip dates if it would improve their experience
    4. Provides tips for each resort (best runs, facilities to check out, etc.)
    
    Ski Season Plan:
    """
    
    # Call Ollama API directly
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
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
    home_location: str, 
    trips: List[Dict[str, Any]], 
    criteria: List[str], 
    priorities: Dict[str, int]
) -> str:
    """
    Generate a mock ski plan when LLM is not available.
    This function provides a fallback when the LLM is not configured.
    
    Args:
        Same as generate_ski_plan
        
    Returns:
        A string containing a mock ski plan
    """
    plan = f"# Personalized Ski Season Plan for {home_location}\n\n"
    
    plan += "## Your Preferences\n"
    plan += f"- Selected criteria: {', '.join(criteria)}\n"
    plan += "- Priorities:\n"
    for k, v in priorities.items():
        plan += f"  * {k.replace('_', ' ').title()}: {v}/10\n"
    
    plan += "\n## Trip Recommendations\n\n"
    
    for i, trip in enumerate(trips):
        plan += f"### Trip {i+1}: {trip['start_date'].strftime('%Y-%m-%d')} to {trip['end_date'].strftime('%Y-%m-%d')}\n\n"
        
        if trip['matching_stations']:
            top_station = trip['matching_stations'][0]
            plan += f"**Primary Recommendation: {top_station['name']}**\n\n"
            plan += "Why this resort:\n"
            plan += f"- Located in the {top_station.get('region', 'unknown')} region\n"
            
            if 'base_altitude' in top_station:
                plan += f"- Base altitude: {top_station['base_altitude']}m\n"
            if 'top_altitude' in top_station:
                plan += f"- Top altitude: {top_station['top_altitude']}m\n"
            if 'total_pistes_km' in top_station:
                plan += f"- Total pistes: {top_station['total_pistes_km']}km\n"
            
            plan += "\nAlternative options:\n"
            for station in trip['matching_stations'][1:3]:  # Next 2 alternatives
                plan += f"- {station['name']} ({station.get('region', 'unknown')})\n"
        else:
            plan += "No matching stations found for your criteria. Consider adjusting your preferences.\n"
        
        plan += "\n"
    
    plan += "\n## Note\n"
    plan += "This is a mock ski plan. For a more detailed and personalized plan, please configure the LLM integration."
    
    return plan