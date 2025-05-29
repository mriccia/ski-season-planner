import streamlit as st
import requests
from strands import Agent, tool
import logging

logger = logging.getLogger(__name__)

api_key = st.secrets.get("OPENROUTE_API_KEY")


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
        
        # Log response details
        response_details = {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "response_time": response.elapsed.total_seconds(),
            "content_size": len(response.content),
            "features_count": len(data.get("features", [])),
            "full_response": data  # Store the full response
        }
        
        # Extract coordinates from the first feature
        if data.get('features') and len(data['features']) > 0:
            coordinates = data['features'][0]['geometry']['coordinates']
            return coordinates  # [longitude, latitude]
        else:
            logger.warning(f"Could not find coordinates for {location_name}")
            return None
    except requests.exceptions.RequestException as e:
        logger.warning(f"Error geocoding location: {e}")
        raise e  # Re-raise the exception to be handled by the caller
@tool
def get_directions(start_location, end_location):
    """
    Get driving directions between two locations using OpenRoute Service API.
    
    Args:
        start_location (str): Starting location (e.g., "Geneva,Switzerland")
        end_location (str): Destination location (e.g., "Zermatt,Switzerland")
        
    Returns:
        dict: Response containing route information including duration
    """
    # First, geocode the locations to get coordinates
    start_coords = geocode_location(start_location, api_key)
    end_coords = geocode_location(end_location, api_key)
    
    if not start_coords or not end_coords:
        return None
    
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
        
        # Log response details
        response_details = {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "response_time": response.elapsed.total_seconds(),
            "content_size": len(response.content),
            "response_summary": {
                "routes": len(response_data.get("routes", [])),
                "summary": response_data.get("routes", [{}])[0].get("summary", {}) if response_data.get("routes") else {}
            },
            "full_response": response_data  # Store the full response
        }
        
        return response_data
    except requests.exceptions.RequestException as e:
        logger.warning(f"Error fetching directions: {e}")
        raise e  # Re-raise the exception to be handled by the caller
