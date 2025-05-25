"""
Reusable UI components for the Streamlit application.
"""
from typing import List, Dict, Tuple
import streamlit as st
from datetime import datetime, timedelta
# Standard Streamlit imports are sufficient

from ..models.station import Station
from ..models.trip import Trip
from ..config import CRITERIA_OPTIONS
from . import state

def render_preferences_tab():
    """Render the user preferences tab."""
    st.header("Your Profile")
    
    # Home location input
    home_location = st.text_input(
        "Your Home Location (City, Country)", 
        value=st.session_state.preferences.home_location
    )
    
    st.header("Your Skiing Preferences")
    
    # Criteria selection
    selected_criteria = []
    st.write("Select your skiing criteria:")
    col1, col2 = st.columns(2)
    
    criteria_items = list(CRITERIA_OPTIONS.items())
    mid_point = len(criteria_items) // 2 + 1
    
    with col1:
        for key, label in criteria_items[:mid_point]:
            if st.checkbox(label, key=f"criteria_{key}", 
                         value=key in st.session_state.preferences.criteria):
                selected_criteria.append(key)
    
    with col2:
        for key, label in criteria_items[mid_point:]:
            if st.checkbox(label, key=f"criteria_{key}", 
                         value=key in st.session_state.preferences.criteria):
                selected_criteria.append(key)
    
    # Priorities sliders
    st.write("Set your priorities (1 = low, 10 = high):")
    priorities = {}
    
    col1, col2 = st.columns(2)
    with col1:
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
    
    with col2:
        priorities['vertical_drop'] = st.slider(
            "Vertical Drop", 1, 10, 
            value=st.session_state.preferences.priorities['vertical_drop'],
            help="Prioritize resorts with more vertical meters"
        )
    
    # Update preferences in session state
    state.update_preferences(home_location, selected_criteria, priorities)

def render_trip_form(on_add_trip):
    """Render the form for adding a new trip."""
    with st.expander("Add a New Trip", expanded=True):
        st.write("Select trip dates:")
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input(
                "Start Date",
                value=datetime.now(),
                min_value=datetime.now(),
                key='trip_start_date'
            )
        with col2:
            end_date = st.date_input(
                "End Date",
                value=datetime.now() + timedelta(days=7),
                min_value=start_date,
                key='trip_end_date'
            )
        
        if st.button("Add Trip"):
            if start_date and end_date and start_date <= end_date:
                on_add_trip(start_date, end_date)
                st.success("Trip added successfully!")
            else:
                st.error("Please select valid dates")

def render_trip_details(trip: Trip, index: int):
    """Render the details of a single trip."""
    with st.expander(f"Trip {index+1}: {trip.start_date.strftime('%Y-%m-%d')} to {trip.end_date.strftime('%Y-%m-%d')}"):
        st.write(f"**Duration:** {trip.duration_days} days")
        
        st.write("**Selected Criteria:**")
        if trip.criteria:
            for criterion in trip.criteria:
                st.write(f"- {criterion}")
        else:
            st.write("- No specific criteria selected")
        
        st.write("**Top Matching Stations:**")
        if trip.matching_stations:
            for station in trip.matching_stations[:5]:  # Show top 5
                st.write(f"- {station.name}")
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"  * Total pistes: {station.total_pistes_km} km")
                    st.write(f"  * Base altitude: {station.base_altitude} m")
                with col2:
                    st.write(f"  * Top altitude: {station.top_altitude} m")
                    st.write(f"  * Vertical drop: {station.vertical_drop} m")
        else:
            st.write("No stations match the selected criteria")
        
        if st.button(f"Remove Trip {index+1}"):
            state.remove_trip(index)
            st.rerun()

def render_plan_tab(planner_service):
    """Render the plan generation tab."""
    st.header("Generate Your Ski Season Plan")
    
    if not st.session_state.trips:
        st.warning("Please add at least one trip before generating a plan.")
        return
    
    if not st.session_state.preferences.home_location:
        st.warning("Please enter your home location in the Profile tab.")
        return
    
    # Ollama model selection
    st.subheader("LLM Settings")
    selected_model = st.selectbox(
        "Select Ollama model", 
        ["llama3", "mistral", "gemma", "phi"],
        index=["llama3", "mistral", "gemma", "phi"].index(st.session_state.ollama_model)
    )
    
    if selected_model != st.session_state.ollama_model:
        st.session_state.ollama_model = selected_model
        state.reset_plan()
    
    # Show LLM status
    if planner_service.is_llm_configured():
        st.success(f"Ollama is running and will use the {st.session_state.ollama_model} model.")
    else:
        st.warning("Ollama integration is not available or not running. A simplified plan will be generated.")
    
    if not st.session_state.plan_generated:
        if st.button("Generate Ski Plan"):
            with st.spinner("Generating your personalized ski plan..."):
                plan = planner_service.generate_ski_plan(
                    st.session_state.preferences,
                    st.session_state.trips,
                    model_name=st.session_state.ollama_model
                )
                state.update_ski_plan(plan)
                st.rerun()
    else:
        render_generated_plan()

def render_generated_plan():
    """Render the generated ski plan and related controls."""
    st.subheader("Your Personalized Ski Season Plan")
    st.markdown(st.session_state.ski_plan)
    
    # Allow user to modify the plan
    st.subheader("Modify Your Plan")
    modified_plan = st.text_area("Edit your plan", value=st.session_state.ski_plan, height=300)
    
    if modified_plan != st.session_state.ski_plan:
        if st.button("Save Changes"):
            state.update_ski_plan(modified_plan)
            st.success("Changes saved!")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Regenerate Plan"):
            state.reset_plan()
            st.rerun()
    
    with col2:
        st.download_button(
            label="Download Plan",
            data=st.session_state.ski_plan,
            file_name="ski_season_plan.txt",
            mime="text/plain"
        )