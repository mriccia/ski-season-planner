"""
Streamlit session state management.
"""
from typing import Dict, List, Optional
import streamlit as st
from models.trip import Trip, UserPreferences
from config import DEFAULT_PRIORITIES, DEFAULT_MODEL
from services.station_service import StationService

def initialize_session_state():
    """Initialize or get session state variables."""
    if 'stations' not in st.session_state:
        station_service = StationService() 
        st.session_state.stations= station_service.load_stations()
        
    if 'trips' not in st.session_state:
        st.session_state.trips: List[Trip] = []
    
    if 'preferences' not in st.session_state:
        st.session_state.preferences = UserPreferences(
            criteria=[],
            priorities=DEFAULT_PRIORITIES.copy(),
            home_location="",
            transport_mode="Car"
        )
    
    if 'plan_generated' not in st.session_state:
        st.session_state.plan_generated = False
    
    if 'ski_plan' not in st.session_state:
        st.session_state.ski_plan = ""
    
    if 'ollama_model' not in st.session_state:
        st.session_state.ollama_model = DEFAULT_MODEL
        
    # Add app flow state
    if 'app_step' not in st.session_state:
        st.session_state.app_step = "preferences"  # Options: preferences, trips, plan

def update_preferences(home_location: str, criteria: List[str], priorities: Dict[str, int], transport_mode: str = "Car"):
    """Update user preferences in session state."""
    st.session_state.preferences.home_location = home_location
    st.session_state.preferences.criteria = criteria
    st.session_state.preferences.priorities = priorities
    st.session_state.preferences.transport_mode = transport_mode
    
def set_app_step(step: str):
    """Set the current step in the guided experience."""
    st.session_state.app_step = step

def add_trip(trip: Trip):
    """Add a new trip to session state."""
    st.session_state.trips.append(trip)
    st.session_state.plan_generated = False

def remove_trip(index: int):
    """Remove a trip from session state."""
    st.session_state.trips.pop(index)
    st.session_state.plan_generated = False

def update_ski_plan(plan: str):
    """Update the generated ski plan."""
    st.session_state.ski_plan = plan
    st.session_state.plan_generated = True

def reset_plan():
    """Reset the generated plan."""
    st.session_state.plan_generated = False