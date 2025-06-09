"""
Reusable UI components for the Streamlit application.
"""
import streamlit as st
import asyncio
import json
from datetime import datetime
from typing import Callable, Dict, List, Any, Optional

from ski_planner_app.models.trip import Trip
from ski_planner_app.config import (
    CRITERIA_OPTIONS, 
    DEFAULT_TRIP_START_DATE, 
    DEFAULT_TRIP_END_DATE,
    UI_DOWNLOAD_FILENAME,
    UI_DOWNLOAD_MIME_TYPE,
    SKI_SEASON_START_MONTH,
    SKI_SEASON_END_MONTH
)
from ski_planner_app.ui import state
from ski_planner_app.services.station_service import StationService
from ski_planner_app.services.distance_service import DistanceService
from ski_planner_app.services.streaming_service import StreamingService
from ski_planner_app.ui.streaming_components import StreamingUI

def render_preferences_sidebar() -> None:
    """
    Render the user preferences in the sidebar.
    
    Updates the session state with the user's preferences.
    """
    with st.sidebar:
        st.header("Your Profile")

        # Home location input
        home_location = st.text_input(
            "Your Home Location (City, Country)",
            value=st.session_state.preferences.home_location
        )

        # Transport mode selection
        transport_mode = st.radio(
            "Mode of Transport",
            options=["Car", "Public Transport"],
            index=0 if st.session_state.preferences.transport_mode == "Car" else 1,
            horizontal=True
        )

        st.header("Your Skiing Preferences")

        # Criteria selection
        selected_criteria = []
        st.write("Select your skiing criteria:")

        criteria_items = list(CRITERIA_OPTIONS.items())
        for key, label in criteria_items:
            if st.checkbox(label, key=f"criteria_{key}",
                           value=key in st.session_state.preferences.criteria):
                selected_criteria.append(key)

        # Priorities sliders
        st.write("Set your priorities (1 = low, 10 = high):")
        priorities = {}

        priorities['altitude'] = st.slider(
            "High Altitude", 1, 10,
            value=st.session_state.preferences.priorities['altitude'],
            help="Prioritize resorts with higher base altitude"
        )
        priorities['piste_length'] = st.slider(
            "Total Piste Length", 1, 10,
            value=st.session_state.preferences.priorities['piste_length'],
            help="Prioritize resorts with more kilometers of pistes"
        )
        priorities['vertical_drop'] = st.slider(
            "Vertical Drop", 1, 10,
            value=st.session_state.preferences.priorities['vertical_drop'],
            help="Prioritize resorts with more vertical meters"
        )
        priorities['resort_distance'] = st.slider(
            "Resort Distance", 1, 10,
            value=st.session_state.preferences.priorities['resort_distance'],
            help="Prioritize resorts that are closer to your home location"
        )

        # Update preferences in session state
        state.update_preferences(
            home_location, selected_criteria, priorities, transport_mode)
        
        # If home location has changed, trigger distance calculation
        if home_location and home_location != st.session_state.get('last_home_location', ''):
            st.session_state['last_home_location'] = home_location
            st.session_state['distances_calculated'] = False


def render_trip_form(on_add_trip: Callable[[datetime, datetime], None]) -> None:
    """
    Render the form for adding a new trip.
    
    Args:
        on_add_trip: Callback function to call when a trip is added
    """
    with st.expander("Add a New Trip", expanded=True):
        st.write("Select trip dates:")
        col1, col2 = st.columns(2)

        # Set default dates from config
        with col1:
            start_date = st.date_input(
                "Start Date",
                value=DEFAULT_TRIP_START_DATE,
                key='trip_start_date'
            )
        with col2:
            end_date = st.date_input(
                "End Date",
                value=DEFAULT_TRIP_END_DATE,
                key='trip_end_date'
            )

        # Validate dates
        if start_date > end_date:
            st.error("End date must be after start date.")
        else:
            if st.button("Add Trip"):
                on_add_trip(start_date, end_date)


def render_trip_details(trip: Trip, index: int) -> None:
    """
    Render details for a single trip.
    
    Args:
        trip: The trip to render
        index: The index of the trip in the list
    """
    with st.container():
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            st.write(f"**Trip {index+1}**")
            st.write(f"From: {trip.start_date.strftime('%Y-%m-%d')}")
            st.write(f"To: {trip.end_date.strftime('%Y-%m-%d')}")
        with col2:
            st.write(f"**Duration: {trip.duration_days} days**")
            criteria_labels = [CRITERIA_OPTIONS[c] for c in trip.criteria]
            st.write(f"Criteria: {', '.join(criteria_labels)}")
        with col3:
            if st.button("Remove", key=f"remove_trip_{index}"):
                state.remove_trip(index)
                st.rerun()
        st.divider()


def render_plan_tab(planner_service: Any) -> None:
    """
    Render the plan generation tab.
    
    Args:
        planner_service: The planner service instance
    """
    if not st.session_state.plan_generated:
        st.write("Generate a personalized ski season plan based on your preferences and trips.")
        
        # Model selection
        model_options = st.session_state.available_models
        model_name = st.selectbox("Select AI Model", model_options, index=0)
        
        # Add a checkbox for streaming mode
        use_streaming = st.checkbox("Show real-time generation", value=True, 
                                   help="See the plan being generated in real-time")
        
        if st.button("Generate Plan"):
            # Always reset debug information before generating a new plan
            st.session_state.debug_info = {
                "tool_calls": [],
                "tool_responses": [],
                "events": []
            }
            
            if use_streaming:
                # Use the new streaming approach with proper separation of concerns
                handle_streaming_generation(planner_service, model_name)
            else:
                # Use the original non-streaming approach
                handle_non_streaming_generation(planner_service, model_name)
    else:
        # Show debug information if available
        if "debug_info" in st.session_state and st.session_state.debug_info["tool_calls"]:
            with st.expander("Tool Calls Log", expanded=False):
                for i, tool_info in enumerate(st.session_state.debug_info["tool_calls"]):
                    st.write(f"**Tool {i+1}:** {tool_info['name']}")
                    st.code(f"Input: {tool_info['input']}")
                    if i < len(st.session_state.debug_info["tool_responses"]):
                        st.code(f"Response: {st.session_state.debug_info['tool_responses'][i]}")
        
        # Display the generated plan
        st.markdown(st.session_state.plan)
        
        # Download button
        st.download_button(
            label="Download Plan",
            data=st.session_state.plan,
            file_name=UI_DOWNLOAD_FILENAME,
            mime=UI_DOWNLOAD_MIME_TYPE
        )
        
        # Reset button
        if st.button("Generate New Plan"):
            st.session_state.plan_generated = False
            st.session_state.plan = None
            
            # Reset debug information
            st.session_state.debug_info = {
                "tool_calls": [],
                "tool_responses": [],
                "events": []
            }
            
            st.rerun()


def handle_streaming_generation(planner_service: Any, model_name: str) -> None:
    """
    Handle streaming generation of the ski plan.
    
    Args:
        planner_service: The planner service instance
        model_name: The name of the model to use
    """
    # Set up the streaming UI components
    streaming_ui = StreamingUI().setup_ui_containers()
    
    # Create the streaming service
    streaming_service = StreamingService()
    
    try:
        # Define the completion callback
        def on_complete(final_plan: str) -> None:
            st.session_state.plan = final_plan
            st.session_state.plan_generated = True
        
        # Run the async function to process the stream
        asyncio.run(
            streaming_service.process_stream(
                planner_service.generate_ski_plan_streaming(
                    st.session_state.preferences,
                    st.session_state.trips,
                    model_name
                ),
                on_event=streaming_ui.handle_event,
                on_state_change=streaming_ui.handle_state_change,
                on_complete=on_complete
            )
        )
        
        # Update debug info
        streaming_ui.update_debug_info(streaming_service.state)
        
        # Update status
        streaming_ui.status_container.success("Plan generation complete!")
            
    except Exception as e:
        streaming_ui.status_container.error(f"Error generating plan: {str(e)}")


def handle_non_streaming_generation(planner_service: Any, model_name: str) -> None:
    """
    Handle non-streaming generation of the ski plan.
    
    Args:
        planner_service: The planner service instance
        model_name: The name of the model to use
    """
    with st.spinner("Generating your personalized ski season plan..."):
        try:
            # Generate plan
            plan = planner_service.generate_ski_plan(
                st.session_state.preferences,
                st.session_state.trips,
                model_name
            )
            
            # Store plan in session state
            st.session_state.plan = plan
            st.session_state.plan_generated = True
            
            # Rerun to display the plan
            st.rerun()
        except Exception as e:
            st.error(f"Error generating plan: {str(e)}")
            
def render_distances_table(distance_service: DistanceService) -> None:
    """
    Render a table showing all resorts with their distances and travel times.
    
    Args:
        distance_service: The distance service instance
    """
    st.subheader("Resort Distances")
    
    origin = st.session_state.preferences.home_location
    transport_mode = "driving-car" if st.session_state.preferences.transport_mode == "Car" else "public-transport"
    
    # Get all distances
    stations_with_distances = distance_service.get_all_distances(origin, transport_mode)
    
    if stations_with_distances:
        # Display the table directly using Streamlit's built-in functionality
        st.dataframe(stations_with_distances)
    else:
        st.info("No distance data available.")
