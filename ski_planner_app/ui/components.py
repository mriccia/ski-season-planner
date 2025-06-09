"""
Reusable UI components for the Streamlit application.
"""
import streamlit as st
from datetime import datetime

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

def render_preferences_sidebar():
    """Render the user preferences in the sidebar."""
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


def render_trip_form(on_add_trip):
    """Render the form for adding a new trip."""
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


def render_trip_details(trip, index):
    """Render details for a single trip."""
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


def render_plan_tab(planner_service):
    """Render the plan generation tab."""
    if not st.session_state.plan_generated:
        st.write("Generate a personalized ski season plan based on your preferences and trips.")
        
        # Model selection
        model_options = st.session_state.available_models
        model_name = st.selectbox("Select AI Model", model_options, index=0)
        
        if st.button("Generate Plan"):
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
    else:
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
            st.rerun()
            
def render_distances_table(distance_service):
    """Render a table showing all resorts with their distances and travel times."""
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

def render_distances_table(distance_service):
    """
    Render a table showing all resorts with their distances and travel times.
    
    Args:
        distance_service: The distance service instance
    """
    st.subheader("Resort Distances")
    
    if not st.session_state.preferences.home_location:
        st.info("Please set your home location in the preferences to see distances.")
        return
    
    origin = st.session_state.preferences.home_location
    transport_mode = "driving-car" if st.session_state.preferences.transport_mode == "Car" else "public-transport"
    
    # Check if distances have been calculated
    if not distance_service.is_origin_calculated(origin, transport_mode):
        st.warning("Distances have not been calculated yet. Please complete the preferences step.")
        return
    
    # Get all distances
    stations_with_distances = distance_service.get_all_distances(origin, transport_mode)
    
    if not stations_with_distances:
        st.info("No distance data available.")
        return
    
    # Create a DataFrame for better display
    import pandas as pd
    
    df = pd.DataFrame(stations_with_distances)
    
    # Select and rename columns for display
    display_columns = ['name', 'region', 'total_pistes_km', 'base_altitude', 'top_altitude', 'distance', 'duration']
    available_columns = [col for col in display_columns if col in df.columns]
    
    if not available_columns:
        st.error("No valid data columns found.")
        return
        
    display_df = df[available_columns].copy()
    
    # Create a mapping for column renaming
    column_names = {
        'name': 'Resort',
        'region': 'Region',
        'total_pistes_km': 'Total Pistes (km)',
        'base_altitude': 'Base Altitude (m)',
        'top_altitude': 'Top Altitude (m)',
        'distance': 'Distance (km)',
        'duration': 'Travel Time (min)'
    }
    
    # Rename only the columns that exist
    rename_map = {col: column_names[col] for col in available_columns if col in column_names}
    display_df = display_df.rename(columns=rename_map)
    
    # Add sorting options
    sort_options = [column_names[col] for col in available_columns if col in column_names]
    if sort_options:
        sort_by = st.selectbox(
            "Sort by:",
            options=sort_options,
            index=sort_options.index('Distance (km)') if 'Distance (km)' in sort_options else 0
        )
        
        # Sort the DataFrame
        display_df = display_df.sort_values(by=sort_by)
    
    # Display the table
    st.dataframe(display_df, use_container_width=True)
    
    # Add download button
    csv = display_df.to_csv(index=False)
    st.download_button(
        label="Download as CSV",
        data=csv,
        file_name="resort_distances.csv",
        mime="text/csv",
    )
