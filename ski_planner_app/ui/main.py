
import logging

import streamlit as st
from datetime import datetime

from ski_planner_app.models.trip import Trip
from ski_planner_app.services.planner_service import PlannerService
from ski_planner_app.services.station_service import StationService
from ski_planner_app.services.distance_service import DistanceService
from ski_planner_app.ui import components, state

logger = logging.getLogger(__name__)


def main():
    logger.info("Starting Ski Season Planner application")
    st.title("Ski Season Planner")
    st.write("Plan your perfect ski season with personalized recommendations!")

    try:
        # Initialize services using singleton pattern
        logger.debug("Getting service instances")
        planner_service = PlannerService()
        station_service = StationService()
        distance_service = DistanceService()

        # Initialize session state
        logger.debug("Initializing session state")
        state.initialize_session_state()

        # Render preferences in sidebar
        logger.debug("Rendering preferences sidebar")
        components.render_preferences_sidebar()

        # Step indicator
        steps = ["1. Set Preferences", "2. Add Trips", "3. Generate Plan"]
        current_step = 0

        if st.session_state.app_step == "preferences":
            current_step = 0
        elif st.session_state.app_step == "trips":
            current_step = 1
        elif st.session_state.app_step == "plan":
            current_step = 2

        st.progress(float(current_step) / 2)
        st.write(f"**Current step: {steps[current_step]}**")

        # Step 1: Preferences
        if st.session_state.app_step == "preferences":
            st.subheader("1. Set Your Preferences")

            # Check if preferences are set
            preferences_complete = (
                st.session_state.preferences.home_location != "" and st.session_state.preferences.criteria
            )

            if not preferences_complete:
                st.info(
                    "Please complete your profile and preferences in the sidebar before continuing.")
            else:
                # Check if we need to calculate distances
                if not st.session_state.get('distances_calculated', False):
                    home_location = st.session_state.preferences.home_location
                    transport_mode = "driving-car" if st.session_state.preferences.transport_mode == "Car" else "public-transport"
                    
                    # Get all station locations with coordinates
                    all_stations = station_service.get_all_locations_with_coordinates()
                    
                    # Show progress for distance calculations
                    with st.spinner(f"Calculating distances from {home_location} to all ski resorts..."):
                        result = distance_service.prefetch_all_distances(
                            home_location, 
                            all_stations, 
                            transport_mode
                        )
                        
                        if result["status"] == "completed":
                            st.success(f"✅ Calculated distances to {result['newly_calculated']} new resorts!")
                        elif result["status"] == "already_calculated":
                            st.success("✅ Distances already calculated!")
                        else:
                            st.error(f"❌ Error calculating distances: {result.get('error', 'Unknown error')}")
                            logger.error(f"Distance calculation failed: {result}")
                        
                        # Mark as calculated regardless of result to avoid repeated failures
                        st.session_state['distances_calculated'] = True
                
                # Display the distances table
                components.render_distances_table(distance_service)
                
                st.success("✅ Preferences set successfully!")
                if st.button("Continue to Add Trips"):
                    state.set_app_step("trips")
                    st.rerun()

        # Step 2: Trip Planning
        elif st.session_state.app_step == "trips":
            st.subheader("2. Plan Your Trips")

            def on_add_trip(start_date: datetime, end_date: datetime):
                """Callback for when a new trip is added."""
                logger.info(f"Adding new trip from {start_date} to {end_date}")
                
                # Create and add new trip
                trip = Trip(
                    start_date=start_date,
                    end_date=end_date,
                    criteria=st.session_state.preferences.criteria.copy(),
                    priorities=st.session_state.preferences.priorities.copy()
                )
                state.add_trip(trip)
                logger.info(f"Successfully added trip matching stations")

            # Add new trip form
            components.render_trip_form(on_add_trip)

            # Display planned trips
            st.subheader("Your Planned Trips")

            if not st.session_state.trips:
                logger.debug("No trips found in session state")
                st.info("No trips planned yet. Use the form above to add a trip!")
            else:
                logger.debug(
                    f"Displaying {len(st.session_state.trips)} planned trips")
                for i, trip in enumerate(st.session_state.trips):
                    components.render_trip_details(trip, i)

                col1, col2 = st.columns([1, 1])
                with col1:
                    if st.button("Back to Preferences"):
                        state.set_app_step("preferences")
                        st.rerun()
                with col2:
                    if st.button("Continue to Generate Plan"):
                        state.set_app_step("plan")
                        st.rerun()

        # Step 3: Generate Plan
        elif st.session_state.app_step == "plan":
            st.subheader("3. Generate Your Ski Season Plan")

            if not st.session_state.trips:
                st.warning(
                    "Please add at least one trip before generating a plan.")
                if st.button("Back to Add Trips"):
                    state.set_app_step("trips")
                    st.rerun()
            else:
                # Display trip snapshot
                with st.expander("Your Trips Summary", expanded=True):
                    for i, trip in enumerate(st.session_state.trips):
                        st.write(
                            f"**Trip {i+1}:** {trip.start_date.strftime('%Y-%m-%d')} to {trip.end_date.strftime('%Y-%m-%d')} ({trip.duration_days} days)")

                components.render_plan_tab(planner_service)

                if not st.session_state.plan_generated:
                    if st.button("Back to Trips"):
                        state.set_app_step("trips")
                        st.rerun()

    except Exception as e:
        logger.critical(
            f"Critical error in main application: {str(e)}", exc_info=True)
        st.error("An unexpected error occurred. Please try refreshing the page.")
