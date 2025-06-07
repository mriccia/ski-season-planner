"""
Module for generating prompts for the LLM-based planner.
"""
from typing import List, Dict, Any
import logging
import json
from ski_planner_app.models.trip import Trip, UserPreferences

logger = logging.getLogger(__name__)


def format_prompt(preferences: UserPreferences, trips: List[Trip], stations: List[object]) -> str:
    """
    Create the prompt for the LLM to generate a ski plan.

    This function formats all the user preferences, trip details, and available
    ski stations into a structured prompt for the LLM to generate personalized
    ski trip recommendations.

    Args:
        preferences (UserPreferences): User's skiing preferences and priorities
        trips (List[Trip]): List of planned trips with dates
        stations (List[object]): List of available ski stations/resorts with distance data

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
    
    # Format stations with their pre-calculated distances
    # Create a more compact representation to avoid token limits
    stations_data = []
    for station in stations:
        try:
            station_dict = {
                'name': getattr(station, 'name', 'Unknown'),
                'region': getattr(station, 'region', ''),
                'base_altitude': getattr(station, 'base_altitude', 0),
                'top_altitude': getattr(station, 'top_altitude', 0),
                'vertical_drop': getattr(station, 'vertical_drop', 0),
                'total_pistes_km': getattr(station, 'total_pistes_km', 0),
            }
            
            # Add difficulty breakdown if available
            if hasattr(station, 'difficulty_breakdown'):
                difficulty = station.difficulty_breakdown
                station_dict['easy_km'] = getattr(difficulty, 'easy_km', 0)
                station_dict['intermediate_km'] = getattr(difficulty, 'intermediate_km', 0)
                station_dict['difficult_km'] = getattr(difficulty, 'difficult_km', 0)
            
            # Add distance and duration if available
            if hasattr(station, 'distance') and station.distance is not None:
                station_dict['distance_km'] = station.distance
            if hasattr(station, 'duration') and station.duration is not None:
                station_dict['duration_minutes'] = station.duration
                
            stations_data.append(station_dict)
        except Exception as e:
            logger.warning(f"Error formatting station data for {getattr(station, 'name', 'Unknown')}: {str(e)}")
    
    # Count stations with distance data
    stations_with_distance = sum(1 for s in stations_data if 'distance_km' in s)
    logger.info(f"{stations_with_distance} out of {len(stations_data)} stations have distance data")
    
    # Create a more compact representation of stations
    # For very large datasets, we might need to limit the number of stations
    MAX_STATIONS = 50  # Limit to avoid token limits
    if len(stations_data) > MAX_STATIONS:
        logger.warning(f"Limiting stations in prompt from {len(stations_data)} to {MAX_STATIONS}")
        stations_data = stations_data[:MAX_STATIONS]
        stations_text = json.dumps(stations_data, indent=2)
        stations_text += f"\n\n(Note: Only showing {MAX_STATIONS} out of {len(stations)} stations due to size constraints)"
    else:
        stations_text = json.dumps(stations_data, indent=2)

    prompt = f"""
You are a ski trip planner. Your task is to create a personalised ski season plan for a person living in {preferences.home_location}.

**Trips Planned:**
The user has {len(trips)} trips planned:
{trips_text}

**Available Resorts with Pre-calculated Distances:**
The following resorts are available, with distances and travel times already calculated from {preferences.home_location}:
{stations_text}

**Preferences:**
- Criteria: {', '.join(preferences.criteria)}
- Priorities (between 1 and 10): {priorities_text}
- Mode of Transport: {preferences.transport_mode}

**Tasks:**
1. Create a comprehensive comparison table of ALL resorts with their distances, travel times, and key features.
2. Based on this data, recommend one specific resort for each of the {len(trips)} trips.
3. Explain why each resort matches their preferences.
4. Suggest any adjustments to trip dates for a better experience.
5. Provide tips for each resort (best runs, facilities, etc.).
6. Include transport recommendations based on their preferred mode of transport.

**Guidelines:**
- Use the pre-calculated distances and travel times provided in the resort data.
- Consider the following factors when making recommendations: altitude, piste length, vertical drop, and distance from home.
- Only use the information provided in the trips and preferences. Do not make assumptions.
- Do not include information about the Magic Pass or its benefits.

**Format:**
1. Introduction
2. Complete Resort Comparison Table (including ALL resorts with distances and travel times)
3. Trip Overview with Recommendations
4. Tips and Recommendations

**Steps to Follow:**
1. **Create Comparison Table:** Compile all data into a comprehensive comparison table.
2. **Filter Resorts:** Filter the resorts based on the user's criteria and priorities.
3. **Recommend Resorts:** Recommend one specific resort for each of the {len(trips)} trips based on the complete data.
4. **Provide Details:** Explain why each resort is a good match, provide tips, and include transport recommendations.

Please ensure you have all the necessary data available to complete this task. Only return your response once the plan is fully generated and all steps are completed.
"""

    logger.debug(f"Created prompt of length {len(prompt)}")
    return prompt
