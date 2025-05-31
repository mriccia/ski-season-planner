import streamlit as st
import requests
import time
import random
from strands import Agent, tool
import logging
from requests.exceptions import RequestException, HTTPError, Timeout

logger = logging.getLogger(__name__)

# Use a function to get the API key to avoid issues with Streamlit's execution flow
def get_api_key():
    return st.secrets.get("OPENROUTE_API_KEY")

def retry_with_backoff(func):
    """
    Decorator to retry a function with exponential backoff when API throttling occurs.
    
    Args:
        func: The function to retry
        
    Returns:
        The decorated function with retry logic
    """
    def get_direction_wrapper(start_location: str, end_location: str):
        """
        Calculate the driving distance and time between two locations.
        
        This tool calculates the driving route between a starting location and a destination,
        returning the distance in kilometers and travel time in minutes.
        
        Example usage:
        ```
        get_directions("Geneva, Switzerland", "Verbier, Switzerland")
        ```
        
        Args:
            start_location (str): Starting location as a string (city, country)
            end_location (str): Destination location as a string (city, country)
            
        Returns:
            dict: Contains keys:
                - start: The starting location
                - destination: The destination location
                - distance_km: Distance in kilometers (float)
                - duration_minutes: Travel time in minutes (int)
                - error: Error message if any (or None if successful)
        """
        max_retries = 5
        retry_delay = 1  # Initial delay in seconds
        jitter_factor = 0.1  # Add randomness to avoid thundering herd
        
        for attempt in range(max_retries):
            try:
                return func(start_location, end_location)
            except (HTTPError, Timeout) as e:
                # Check if it's a rate limit error (429) or server error (5xx)
                if hasattr(e, 'response') and (e.response.status_code == 429 or 500 <= e.response.status_code < 600):
                    if attempt == max_retries - 1:  # Last attempt
                        logger.error(f"Max retries reached for {func.__name__}. Giving up.")
                        raise
                    
                    # Calculate backoff with jitter
                    delay = retry_delay * (2 ** attempt)
                    jitter = delay * jitter_factor * random.uniform(-1, 1)
                    wait_time = delay + jitter
                    
                    logger.warning(f"API throttling detected. Retrying {func.__name__} in {wait_time:.2f} seconds (attempt {attempt+1}/{max_retries})")
                    time.sleep(wait_time)
                else:
                    # Not a throttling error, re-raise
                    raise
            except Exception as e:
                # For other exceptions, don't retry
                logger.error(f"Non-retryable error in {func.__name__}: {str(e)}")
                raise
                
    return get_direction_wrapper

def geocode_location(location_name, api_key):
    """
    Convert a location name to coordinates using OpenRoute Service Geocoding API.
    
    Args:
        location_name (str): Location name (e.g., "Geneva,Switzerland")
        api_key (str): Your OpenRoute Service API key
        
    Returns:
        list: [longitude, latitude] coordinates
    """
    url = f"https://api.openrouteservice.org/geocode/search"
    
    headers = {
        'Accept': 'application/json, application/geo+json, application/gpx+xml',
        'Authorization': api_key
    }
    
    params = {
        'text': location_name,
        'size': 1  # Get only the top result
    }
    
    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        # Extract coordinates from the first feature
        if data.get('features') and len(data['features']) > 0:
            coordinates = data['features'][0]['geometry']['coordinates']
            return coordinates  # [longitude, latitude]
        else:
            logger.warning(f"Could not find coordinates for {location_name}")
            return None
    except requests.exceptions.RequestException as e:
        logger.warning(f"Error geocoding location: {e}")
        raise e  # Re-raise the exception to be handled by the retry decorator
@tool
@retry_with_backoff
def get_directions(start_location, end_location):
    """
    Calculate the driving distance and time between two locations.
    
    This tool calculates the driving route between a starting location and a destination,
    returning the distance in kilometers and travel time in minutes.
    
    Example usage:
    ```
    get_directions("Geneva, Switzerland", "Verbier, Switzerland")
    ```
    
    Args:
        start_location (str): Starting location as a string (city, country)
        end_location (str): Destination location as a string (city, country)
        
    Returns:
        dict: Contains keys:
            - start: The starting location
            - destination: The destination location
            - distance_km: Distance in kilometers (float)
            - duration_minutes: Travel time in minutes (int)
            - error: Error message if any (or None if successful)
    """
    # Get API key at runtime
    api_key = get_api_key()
    
    # First, geocode the locations to get coordinates
    start_coords = geocode_location(start_location, api_key)
    end_coords = geocode_location(end_location, api_key)
    
    if not start_coords or not end_coords:
        return {
            "error": "Could not geocode one or both locations",
            "distance_km": None,
            "duration_minutes": None
        }
    
    # Prepare the directions request
    url = "https://api.openrouteservice.org/v2/directions/driving-car"
    
    headers = {
        'Accept': 'application/json, application/geo+json, application/gpx+xml',
        'Authorization': api_key,
        'Content-Type': 'application/json'
    }
    
    body = {
        "coordinates": [start_coords, end_coords],
        "format": "json"
    }
    
    try:
        response = requests.post(url, json=body, headers=headers)
        response.raise_for_status()
        response_data = response.json()
        
        # Extract only the distance and duration information
        if response_data.get("routes") and len(response_data["routes"]) > 0:
            summary = response_data["routes"][0].get("summary", {})
            
            # Convert distance from meters to kilometers and duration from seconds to minutes
            distance_km = round(summary.get("distance", 0) / 1000, 1)  # Convert m to km
            duration_minutes = round(summary.get("duration", 0) / 60)   # Convert seconds to minutes
            
            # Log simplified response
            logger.info(f"Route from {start_location} to {end_location}: {distance_km} km, {duration_minutes} min")
            
            return {
                "start": start_location,
                "destination": end_location,
                "distance_km": distance_km,
                "duration_minutes": duration_minutes
            }
        else:
            logger.warning(f"No routes found from {start_location} to {end_location}")
            return {
                "start": start_location,
                "destination": end_location,
                "distance_km": None,
                "duration_minutes": None,
                "error": "No routes found"
            }
    except requests.exceptions.RequestException as e:
        logger.warning(f"Error fetching directions: {e}")
        # Don't handle the error here, let the retry decorator handle it
        raise
