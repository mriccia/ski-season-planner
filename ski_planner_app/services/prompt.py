"""
Module for generating improved prompts for the LLM-based planner with better SQLite guidance.
"""
from typing import List, Dict, Any
import logging
import json
from ski_planner_app.models.trip import Trip, UserPreferences

logger = logging.getLogger(__name__)


def format_prompt(preferences: UserPreferences, trips: List[Trip]) -> str:
    """
    Create the prompt for the LLM to generate a ski plan with detailed SQLite query guidance.

    This function formats all the user preferences, trip details, and provides
    specific instructions on how to query the SQLite database for ski station data
    and distance calculations.

    Args:
        preferences (UserPreferences): User's skiing preferences and priorities
        trips (List[Trip]): List of planned trips with dates

    Returns:
        str: Formatted prompt for the LLM with detailed instructions and SQLite query examples
    """
    logger.debug("Creating LLM prompt with SQLite query guidance")
    
    # Format trip dates
    trips_text = ""
    for i, trip in enumerate(trips):
        trips_text += f"Trip {i+1}: {trip.start_date.strftime('%Y-%m-%d')} to {trip.end_date.strftime('%Y-%m-%d')}\n"

    # Format priorities
    priorities_text = ", ".join(
        [f"{k} (weight: {v})" for k, v in preferences.priorities.items()])
    transport = 'driving-car' if preferences.transport_mode == 'Car' else 'public-transport'
    prompt = f"""
You are a ski trip planner. Your task is to create a personalised ski season plan for a person living in {preferences.home_location}.

**Trips Planned:**
The user has {len(trips)} trips planned:
{trips_text}

**Database Schema Information:**
The SQLite database contains the following key tables:
1. `stations` - Information about ski resorts with columns:
   - id: Primary key
   - name: Resort name
   - region: Geographic region (e.g., "Valais", "Vaud", "Bern", "France")
   - base_altitude: Altitude at the base of the resort in meters
   - top_altitude: Highest altitude of the resort in meters
   - vertical_drop: Difference between top and base altitude in meters
   - total_pistes_km: Total length of ski pistes in kilometers
   - longitude: Geographic longitude coordinate
   - latitude: Geographic latitude coordinate

2. `distances` - Pre-calculated travel distances and times:
   - id: Primary key
   - origin: Starting location (e.g., "{preferences.home_location}")
   - destination: Destination ski resort name
   - transport_mode: Mode of transportation (e.g., "{transport}")
   - distance: Distance in kilometers
   - duration: Travel duration in minutes
   - timestamp: When the calculation was performed

**Example SQLite Queries:**
Use these queries as templates to access the data you need:

1. To find resorts with specific characteristics:
```sql
SELECT name, region, base_altitude, top_altitude, vertical_drop, total_pistes_km, magic_pass_url
FROM stations
WHERE total_pistes_km > 50
ORDER BY total_pistes_km DESC;
```

2. To get travel information from the user's home location:
```sql
SELECT s.name, s.region, s.total_pistes_km, s.vertical_drop, s.magic_pass_url, d.distance, d.duration
FROM stations s
JOIN distances d ON s.name = d.destination
WHERE d.origin = '{preferences.home_location}'
AND d.transport_mode = '{transport}'
ORDER BY d.duration ASC;
```

3. To find resorts with good snow conditions (higher altitude):
```sql
SELECT name, region, base_altitude, top_altitude, total_pistes_km, magic_pass_url
FROM stations
WHERE top_altitude > 2500
ORDER BY top_altitude DESC;
```

4. To find resorts that match specific criteria and are within reasonable travel time:
```sql
SELECT s.name, s.region, s.total_pistes_km, s.vertical_drop, s.magic_pass_url, d.distance, d.duration
FROM stations s
JOIN distances d ON s.name = d.destination
WHERE d.origin = '{preferences.home_location}'
AND d.transport_mode = '{transport}'
AND s.total_pistes_km > 40
AND d.duration < 180
ORDER BY s.total_pistes_km DESC;
```

**Preferences:**
- Criteria: {', '.join(preferences.criteria)}
- User Priorities, defining how important a each aspect is for the user (between 1 and 10. 1=least important, 10=most important): {priorities_text}
- Mode of Transport: {transport}

**Tasks:**
1. First, use the SQLite MCP to query the database and find suitable resorts based on the user's preferences.
2. Recommend one specific resort for each of the {len(trips)} trips.
3. For EACH recommended resort, use the Fetch MCP tool to check the resort link in the field `magic_pass_url` for additional information. Inlcude this information and reference using the format: [Magic Pass - Resort Name](magic_pass_url).
4. Include key data points in your recommendations: resort name, region, total piste length, vertical drop, distance from home, and travel duration.
5. Explain why each resort matches their preferences, using specific data from the database and Magic Pass website data.
6. When multiple trips are planned, ensure each trip has a unique recommendation based on the date and user preferences.

**Guidelines for Using SQLite MCP:**
1. Start by exploring the available data with basic queries to understand what's available.
2. Use the `mcp_server_sqlite___read_query` function to execute SELECT queries.
3. Always join the stations and distances tables to get both resort information and travel times.
4. Filter by the user's home location: `d.origin = '{preferences.home_location}'`
5. Filter by the user's transport mode: `d.transport_mode = '{transport}'`
6. Consider the user's priorities when ordering results (e.g., if they prioritize short travel time, order by duration).
7. Use multiple queries to gather different perspectives on the data before making recommendations.

**Format:**
1. Introduction
2. Trip x of {len(trips)}: Resort Name
2a. Overview with Recommendations (include dates, specific data points and Magic Pass link)
2b. Tips and Recommendations


Please ensure you have all the necessary data available to complete this task. Only return your response once the plan is fully generated and all steps are completed.
"""

    logger.debug(f"Created prompt of length {len(prompt)}")
    return prompt
