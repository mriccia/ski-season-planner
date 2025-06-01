
from typing import List
import logging
from ski_planner_app.models.trip import Trip, UserPreferences

logger = logging.getLogger(__name__)


def format_prompt(preferences: UserPreferences, trips: List[Trip], stations: List[object]) -> str:
    """
    Create the prompt for the LLM.

    Args:
        preferences: User preferences
        trips: List of planned trips
        stations: List of ski stations/resorts

    Returns:
        str: Formatted prompt for the LLM
    """
    logger.debug("Creating LLM prompt")
    trips_text = ""
    for i, trip in enumerate(trips):
        trips_text += f"Trip {i+1}: {trip.start_date.strftime('%Y-%m-%d')} to {trip.end_date.strftime('%Y-%m-%d')}\n"

    priorities_text = ", ".join(
        [f"{k} (weight: {v})" for k, v in preferences.priorities.items()])

    prompt = f"""
        
You are a ski trip planner. Your task is to create a personalised ski season plan for a person living in {preferences.home_location}.

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
