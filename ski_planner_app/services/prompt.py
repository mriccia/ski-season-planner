"""
Module for generating prompts for the LLM-based planner.
"""
from typing import List, Dict, Any
import logging
import json
from ski_planner_app.models.trip import Trip, UserPreferences

logger = logging.getLogger(__name__)


def format_prompt(preferences: UserPreferences, trips: List[Trip]) -> str:
    """
    Create the prompt for the LLM to generate a ski plan.

    This function formats all the user preferences, trip details, and available
    ski stations into a structured prompt for the LLM to generate personalized
    ski trip recommendations.

    Args:
        preferences (UserPreferences): User's skiing preferences and priorities
        trips (List[Trip]): List of planned trips with dates

    Returns:
        str: Formatted prompt for the LLM with detailed instructions
    """
    logger.debug("Creating LLM prompt")
    
    # Format trip dates
    trips_text = ""
    for i, trip in enumerate(trips):
        trips_text += f"Trip {i+1}: {trip.start_date.strftime('%Y-%m-%d')} to {trip.end_date.strftime('%Y-%m-%d')}\n"

    # Format priorities
    priorities_text = ", ".join(
        [f"{k} (weight: {v})" for k, v in preferences.priorities.items()])
    
    prompt = f"""
You are a ski trip planner. Your task is to create a personalised ski season plan for a person living in {preferences.home_location}.

**Trips Planned:**
The user has {len(trips)} trips planned:
{trips_text}

**Available Resorts with Pre-calculated Distances:**
The resorts and distances from {preferences.home_location} are calculated and provided in the data in the SQLite Database.
Use the SQLite MCP to access the resort data, as well as the pre-calculated distances and travel times.

**Preferences:**
- Criteria: {', '.join(preferences.criteria)}
- Priorities (between 1 and 10): {priorities_text}
- Mode of Transport: {preferences.transport_mode}

**Tasks:**
1. Recommend one specific resort for each of the {len(trips)} trips.
3. Explain why each resort matches their preferences.
4. Suggest any adjustments to trip dates for a better experience.
5. Provide tips for each resort (best runs, facilities, etc.).
6. Include transport recommendations based on their preferred mode of transport.

**Guidelines:**
- Use the pre-calculated distances and travel times provided in the SQLite database.
- Use the SQLite MCP to access the resort data, slope information, etc.
- Consider the following factors when making recommendations: altitude, piste length, vertical drop, and distance from home.
- Only use the information provided in the trips and preferences. Do not make assumptions.
- If you want to include additional information, find the resort using the Fetch MCP tool at https://www.magicpass.ch/en/stations and include relevant details.

**Format:**
1. Introduction
2. Trip Overview with Recommendations
3. Tips and Recommendations

Please ensure you have all the necessary data available to complete this task. Only return your response once the plan is fully generated and all steps are completed.
"""

    logger.debug(f"Created prompt of length {len(prompt)}")
    return prompt
