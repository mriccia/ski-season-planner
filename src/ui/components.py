"""
Reusable UI components for the Streamlit application.
"""
from typing import List, Dict, Tuple
import streamlit as st
from datetime import datetime, timedelta
# Standard Streamlit imports are sufficient

from models.station import Station
from models.trip import Trip
from config import CRITERIA_OPTIONS
from . import state

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
        state.update_preferences(home_location, selected_criteria, priorities, transport_mode)

def render_trip_form(on_add_trip):
    """Render the form for adding a new trip."""
    with st.expander("Add a New Trip", expanded=True):
        st.write("Select trip dates:")
        col1, col2 = st.columns(2)
        
        # Set default dates to December 12-15
        default_start_date = datetime(2025, 12, 12)
        default_end_date = datetime(2025, 12, 15)
        
        with col1:
            start_date = st.date_input(
                "Start Date",
                value=default_start_date,
                key='trip_start_date'
            )
        with col2:
            end_date = st.date_input(
                "End Date",
                value=default_end_date,
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
        
        if st.button(f"Remove Trip {index+1}"):
            state.remove_trip(index)
            st.rerun()

def render_plan_tab(planner_service):
    """Render the plan generation tab."""
    if not st.session_state.preferences.home_location:
        st.warning("Please enter your home location in the sidebar.")
        return
    
    # Ollama model selection
    st.subheader("LLM Settings")
    
    # Check if we have available models
    if not st.session_state.available_models:
        st.warning("No Ollama models found. Please ensure Ollama is running with at least one model installed.")
        if st.button("Refresh Available Models"):
            from config import get_available_ollama_models
            st.session_state.available_models = get_available_ollama_models()
            st.rerun()
        return
    
    selected_model = st.selectbox(
        "Select Ollama model", 
        st.session_state.available_models,
        index=st.session_state.available_models.index(st.session_state.ollama_model) 
            if st.session_state.ollama_model in st.session_state.available_models else 0
    )
    
    if selected_model != st.session_state.ollama_model:
        st.session_state.ollama_model = selected_model
        state.reset_plan()
        
    if not st.session_state.plan_generated:
        if st.button("Generate Ski Plan"):
            with st.spinner("Generating your personalized ski plan..."):
                plan = planner_service.generate_ski_plan(
                    st.session_state.preferences,
                    st.session_state.trips,
                    model_name=st.session_state.ollama_model,
                    stations=st.session_state.stations
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
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("Edit Trips"):
            state.set_app_step("trips")
            st.rerun()
    with col2:
        if st.button("Regenerate Plan"):
            state.reset_plan()
            st.rerun()
    with col3:
        st.download_button(
            label="Download Plan",
            data=st.session_state.ski_plan,
            file_name="ski_season_plan.txt",
            mime="text/plain"
        )