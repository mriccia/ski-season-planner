"""
Main Streamlit application for the Ski Season Planner.
"""
import sys
import os
from pathlib import Path

# Add the project root directory to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import streamlit as st
from datetime import datetime

from src.models.trip import Trip
from src.services.station_service import StationService
from src.services.planner_service import PlannerService
from src.ui import components, state
from src.config import OLLAMA_URL

def main():
    st.title("Ski Season Planner")
    st.write("Plan your perfect ski season with personalized recommendations!")
    
    # Initialize services
    station_service = StationService()
    planner_service = PlannerService(OLLAMA_URL)
    
    # Initialize session state
    state.initialize_session_state()
    
    # Create tabs for different sections
    tab1, tab2, tab3 = st.tabs(["Profile & Preferences", "Plan Trips", "Generate Ski Plan"])
    
    # Tab 1: User Profile and Preferences
    with tab1:
        components.render_preferences_tab()
    
    # Tab 2: Trip Planning
    with tab2:
        st.header("Plan Your Trips")
        
        def on_add_trip(start_date: datetime, end_date: datetime):
            """Callback for when a new trip is added."""
            # Filter stations based on current preferences
            matching_stations = station_service.filter_stations(
                st.session_state.preferences.criteria,
                st.session_state.preferences.priorities
            )
            
            # Create and add new trip
            trip = Trip(
                start_date=start_date,
                end_date=end_date,
                criteria=st.session_state.preferences.criteria.copy(),
                priorities=st.session_state.preferences.priorities.copy(),
                matching_stations=matching_stations
            )
            state.add_trip(trip)
        
        # Add new trip form
        components.render_trip_form(on_add_trip)
        
        # Display planned trips
        st.header("Your Planned Trips")
        
        if not st.session_state.trips:
            st.info("No trips planned yet. Use the form above to add a trip!")
        else:
            for i, trip in enumerate(st.session_state.trips):
                components.render_trip_details(trip, i)
    
    # Tab 3: Generate Plan
    with tab3:
        components.render_plan_tab(planner_service)

if __name__ == "__main__":
    main()