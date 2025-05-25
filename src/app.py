"""
Main Streamlit application for the Ski Season Planner.
"""
import sys
import os
import logging
import logging.config
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
from src.config import OLLAMA_URL, LOGGING_CONFIG

# Initialize logging
logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)

def main():
    logger.info("Starting Ski Season Planner application")
    st.title("Ski Season Planner")
    st.write("Plan your perfect ski season with personalized recommendations!")
    
    try:
        # Initialize services
        logger.debug("Initializing services")
        station_service = StationService()
        planner_service = PlannerService(OLLAMA_URL)
        
        # Initialize session state
        logger.debug("Initializing session state")
        state.initialize_session_state()
        
        # Create tabs for different sections
        tab1, tab2, tab3 = st.tabs(["Profile & Preferences", "Plan Trips", "Generate Ski Plan"])
        
        # Tab 1: User Profile and Preferences
        with tab1:
            logger.debug("Rendering preferences tab")
            components.render_preferences_tab()
        
        # Tab 2: Trip Planning
        with tab2:
            logger.debug("Rendering trip planning tab")
            st.header("Plan Your Trips")
            
            def on_add_trip(start_date: datetime, end_date: datetime):
                """Callback for when a new trip is added."""
                logger.info(f"Adding new trip from {start_date} to {end_date}")
                try:
                    # Filter stations based on current preferences
                    logger.debug("Filtering stations based on user preferences")
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
                    logger.info(f"Successfully added trip with {len(matching_stations)} matching stations")
                except Exception as e:
                    logger.error(f"Error adding trip: {str(e)}", exc_info=True)
                    st.error("An error occurred while adding the trip. Please try again.")
            
            # Add new trip form
            components.render_trip_form(on_add_trip)
            
            # Display planned trips
            st.header("Your Planned Trips")
            
            if not st.session_state.trips:
                logger.debug("No trips found in session state")
                st.info("No trips planned yet. Use the form above to add a trip!")
            else:
                logger.debug(f"Displaying {len(st.session_state.trips)} planned trips")
                for i, trip in enumerate(st.session_state.trips):
                    components.render_trip_details(trip, i)
        
        # Tab 3: Generate Plan
        with tab3:
            logger.debug("Rendering plan generation tab")
            components.render_plan_tab(planner_service)
            
    except Exception as e:
        logger.critical(f"Critical error in main application: {str(e)}", exc_info=True)
        st.error("An unexpected error occurred. Please try refreshing the page.")

if __name__ == "__main__":
    main()