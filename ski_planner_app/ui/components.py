"""
Reusable UI components for the Streamlit application.
"""
import streamlit as st
import asyncio
import json
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
        
        # Add a checkbox for streaming mode
        use_streaming = st.checkbox("Show real-time generation", value=True, 
                                   help="See the plan being generated in real-time")
        
        if st.button("Generate Plan"):
            # Initialize debug information
            if "debug_info" not in st.session_state:
                st.session_state.debug_info = {
                    "tool_calls": [],
                    "tool_responses": [],
                    "events": []
                }
            
            if use_streaming:
                # Create placeholders for streaming content
                status_container = st.empty()
                status_container.info("Starting plan generation...")
                
                # Create tool container first so it appears above the text
                tool_container = st.container()
                
                # Create text placeholder last so it appears at the bottom
                stream_placeholder = st.empty()
                
                try:
                    # Initialize the full plan text
                    full_plan = ""
                    current_tool = None
                    current_tool_id = None
                    
                    # Create text placeholder last so it appears at the bottom
                    text_placeholder = stream_placeholder.empty()
                    
                    # Dictionary to track tool inputs for updating
                    tool_input_placeholders = {}
                    
                    # Define an async function to process the stream
                    async def process_stream():
                        nonlocal full_plan, current_tool, current_tool_id
                        async_gen = planner_service.generate_ski_plan_streaming(
                            st.session_state.preferences,
                            st.session_state.trips,
                            model_name
                        )
                        
                        # Initialize state following SDK's approach
                        state = {
                            "message": {"role": "assistant", "content": []},
                            "text": "",
                            "current_tool_use": {},
                            "reasoningText": "",
                            "signature": "",
                            "content": []  # Will be set to message["content"]
                        }
                        state["content"] = state["message"]["content"]
                        
                        # Process events from the async generator
                        try:
                            async for event in async_gen:
                                # Store event for debugging
                                st.session_state.debug_info["events"].append(event)
                                
                                # Handle initialization events
                                if "init_event_loop" in event or "start" in event or "start_event_loop" in event:
                                    continue
                                
                                # Handle direct data events (legacy format)
                                if "data" in event:
                                    chunk = event["data"]
                                    full_plan += chunk
                                    text_placeholder.markdown(full_plan)
                                    continue
                                
                                # Handle event-based updates
                                if "event" in event:
                                    event_data = event["event"]
                                    
                                    # Handle message start
                                    if "messageStart" in event_data:
                                        state["message"]["role"] = event_data["messageStart"].get("role", "assistant")
                                        status_container.info("Agent is generating a response...")
                                        continue
                                    
                                    # Handle content block start
                                    if "contentBlockStart" in event_data and "start" in event_data["contentBlockStart"]:
                                        start_data = event_data["contentBlockStart"]["start"]
                                        
                                        # Reset current text accumulation
                                        state["text"] = ""
                                        
                                        # Check if this is a tool use block
                                        if start_data and "toolUse" in start_data:
                                            tool_info = start_data["toolUse"]
                                            tool_name = tool_info.get("name")
                                            tool_id = tool_info.get("toolUseId")
                                            
                                            if tool_name:
                                                current_tool = tool_name
                                                current_tool_id = tool_id
                                                
                                                # Initialize tool use state
                                                state["current_tool_use"] = {
                                                    "toolUseId": tool_id,
                                                    "name": tool_name,
                                                    "input": ""
                                                }
                                                
                                                status_container.info(f"Using tool: {current_tool}...")
                                                
                                                # Add to debug info
                                                st.session_state.debug_info["tool_calls"].append({
                                                    "name": tool_name,
                                                    "id": tool_id,
                                                    "input": ""
                                                })
                                                
                                                # Display in tool container
                                                with tool_container:
                                                    st.info(f"🔧 **Tool Call**: {tool_name}")
                                                    # Create a placeholder for the tool input that we'll update
                                                    input_placeholder = st.empty()
                                                    # Store the input placeholder for this tool
                                                    tool_input_placeholders[tool_id] = input_placeholder
                                    
                                    # Handle content block delta
                                    if "contentBlockDelta" in event_data and "delta" in event_data["contentBlockDelta"]:
                                        delta = event_data["contentBlockDelta"]["delta"]
                                        
                                        if "toolUse" in delta and "input" in delta["toolUse"]:
                                            input_chunk = delta["toolUse"]["input"]
                                            if input_chunk:
                                                state["current_tool_use"]["input"] += str(input_chunk)
                                                
                                                # Update the tool input in debug info
                                                for tool_info in st.session_state.debug_info["tool_calls"]:
                                                    if tool_info.get("id") == current_tool_id:
                                                        tool_info["input"] = state["current_tool_use"]["input"]
                                                
                                                # Update the tool input placeholder for this specific tool call
                                                if tool_id in tool_input_placeholders:
                                                    input_placeholder = tool_input_placeholders[tool_id]
                                                    input_placeholder.code(f"Input: {state['current_tool_use']['input']}")
                                        
                                        # Handle reasoning content delta
                                        elif "reasoningContent" in delta:
                                            reasoning_content = delta["reasoningContent"]
                                            
                                            # Handle reasoning text
                                            if "text" in reasoning_content:
                                                reasoning_chunk = reasoning_content["text"]
                                                if "reasoningText" not in state:
                                                    state["reasoningText"] = ""
                                                state["reasoningText"] += reasoning_chunk
                                                
                                            # Handle reasoning signature
                                            elif "signature" in reasoning_content:
                                                signature_chunk = reasoning_content["signature"]
                                                if "signature" not in state:
                                                    state["signature"] = ""
                                                state["signature"] += signature_chunk
                                    
                                    # Handle content block stop - finalize the current block
                                    if "contentBlockStop" in event_data:
                                        # If we have a tool use, finalize it
                                        if state["current_tool_use"]:
                                            # Try to parse the input as JSON
                                            try:
                                                parsed_input = json.loads(state["current_tool_use"]["input"])
                                                state["current_tool_use"]["input"] = parsed_input
                                            except (ValueError, json.JSONDecodeError):
                                                # If parsing fails, keep as string
                                                pass
                                            
                                            # Add to finalized content
                                            state["content"].append({
                                                "toolUse": state["current_tool_use"]
                                            })
                                            
                                            # Reset current tool use
                                            state["current_tool_use"] = {}
                                        
                                        # If we have text, finalize it
                                        elif state["text"]:
                                            # Add to finalized content
                                            state["content"].append({
                                                "text": state["text"]
                                            })
                                            # Reset text accumulation
                                            state["text"] = ""
                                        
                                        # If we have reasoning text, finalize it
                                        elif state.get("reasoningText"):
                                            # Add to finalized content
                                            state["content"].append({
                                                "reasoningContent": {
                                                    "reasoningText": {
                                                        "text": state["reasoningText"],
                                                        "signature": state.get("signature", "")
                                                    }
                                                }
                                            })
                                            # Reset reasoning text and signature
                                            state["reasoningText"] = ""
                                            state["signature"] = ""
                                    
                                    # Handle tool result block
                                    if "toolResultBlock" in event_data:
                                        result_data = event_data["toolResultBlock"]
                                        tool_id = result_data.get("toolUseId")
                                        result = result_data.get("result", {})
                                        
                                        if tool_id and result:
                                            # Add to debug info
                                            st.session_state.debug_info["tool_responses"].append(result)
                                            
                                            # Display result directly in the tool container
                                            with tool_container:
                                                st.success(f"Tool {current_tool} completed")
                                                content = result.get("content", [])
                                                for item in content:
                                                    if item.get("type") == "text":
                                                        st.code(f"Result: {item.get('text')}", language="json")
                                            
                                            status_container.success(f"Tool {current_tool} completed")
                                    
                                    # Handle message stop
                                    if "messageStop" in event_data:
                                        stop_reason = event_data["messageStop"].get("stopReason", "end_turn")
                                        status_container.success(f"Generation complete: {stop_reason}")
                                    
                                    # Handle metadata
                                    if "metadata" in event_data:
                                        metadata = event_data["metadata"]
                                        if "usage" in metadata:
                                            usage = metadata["usage"]
                                    
                                    # Handle redact content
                                    if "redactContent" in event_data:
                                        redact_data = event_data["redactContent"]
                                        if "redactAssistantContentMessage" in redact_data:
                                            redact_msg = redact_data["redactAssistantContentMessage"]
                                            state["message"]["content"] = [{"text": redact_msg}]
                                            status_container.warning("Some content was redacted")
                                                
                        except Exception as e:
                            status_container.error(f"Error in stream processing: {str(e)}")
                            raise e
                    
                    # Run the async function
                    asyncio.run(process_stream())
                    
                    # Store the complete plan in session state
                    st.session_state.plan = full_plan
                    st.session_state.plan_generated = True
                    
                    # Update status
                    status_container.success("Plan generation complete!")
                        
                except Exception as e:
                    status_container.error(f"Error generating plan: {str(e)}")
            else:
                # Use the original non-streaming approach
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
