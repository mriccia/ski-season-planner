"""
UI components for handling streaming responses.
"""
import streamlit as st
from typing import Dict, Any, Optional, Callable

from ski_planner_app.models.streaming import (
    StreamEvent, 
    StreamingState,
    TextChunk,
    ToolCall,
    ToolResult,
    StatusUpdate
)

class StreamingUI:
    """UI components for handling streaming responses."""
    
    def __init__(self):
        """Initialize the streaming UI components."""
        self.status_container = None
        self.tool_container = None
        self.text_placeholder = None
        self.tool_input_placeholders: Dict[str, Any] = {}
    
    def setup_ui_containers(self):
        """Set up the UI containers for streaming content."""
        self.status_container = st.empty()
        self.status_container.info("Starting plan generation...")
        
        # Create tool container first so it appears above the text
        self.tool_container = st.container()
        
        # Create text placeholder last so it appears at the bottom
        stream_placeholder = st.empty()
        self.text_placeholder = stream_placeholder.empty()
        
        return self
    
    def handle_event(self, event: StreamEvent) -> None:
        """
        Handle a streaming event and update the UI accordingly.
        
        Args:
            event: The event to handle
        """
        if event.event_type == "text":
            text_chunk = event.data
            self.text_placeholder.markdown(text_chunk.content)
        
        elif event.event_type == "tool_call":
            tool_call = event.data
            self.status_container.info(f"Using tool: {tool_call.tool_name}...")
            
            # Display in tool container
            with self.tool_container:
                st.info(f"🔧 **Tool Call**: {tool_call.tool_name}")
                # Create a placeholder for the tool input that we'll update
                input_placeholder = st.empty()
                # Store the input placeholder for this tool
                self.tool_input_placeholders[tool_call.tool_id] = input_placeholder
        
        elif event.event_type == "tool_input":
            text_chunk = event.data
            # This event is handled in handle_state_change to ensure we have the current tool context
        
        elif event.event_type == "tool_result":
            tool_result = event.data
            
            # Display result directly in the tool container
            with self.tool_container:
                st.success(f"Tool {tool_result.tool_name} completed")
                content = tool_result.result_data.get("content", [])
                for item in content:
                    if item.get("type") == "text":
                        st.code(f"Result: {item.get('text')}", language="json")
            
            self.status_container.success(f"Tool {tool_result.tool_name} completed")
        
        elif event.event_type == "status":
            status_update = event.data
            if status_update.status == "start":
                self.status_container.info(status_update.details)
            elif status_update.status == "complete":
                self.status_container.success(status_update.details)
            elif status_update.status == "warning":
                self.status_container.warning(status_update.details)
            elif status_update.status == "error":
                self.status_container.error(status_update.details)
    
    def handle_state_change(self, state: StreamingState) -> None:
        """
        Handle state changes and update the UI accordingly.
        
        Args:
            state: The current streaming state
        """
        # Update the text content
        self.text_placeholder.markdown(state.text_content)
        
        # Update tool input if there's a current tool call
        if state.current_tool_call:
            tool_id = state.current_tool_call.tool_id
            if tool_id in self.tool_input_placeholders:
                input_placeholder = self.tool_input_placeholders[tool_id]
                input_placeholder.code(f"Input: {state.current_tool_call.input_data}")
    
    def update_debug_info(self, state: StreamingState) -> None:
        """
        Update the debug information in the session state.
        
        Args:
            state: The current streaming state
        """
        if "debug_info" not in st.session_state:
            st.session_state.debug_info = {
                "tool_calls": [],
                "tool_responses": [],
                "events": []
            }
        
        # Update tool calls
        st.session_state.debug_info["tool_calls"] = [
            {
                "name": tool.tool_name,
                "id": tool.tool_id,
                "input": tool.input_data
            }
            for tool in state.tool_calls
        ]
        
        # Update tool responses
        st.session_state.debug_info["tool_responses"] = [
            result.result_data
            for result in state.tool_results
        ]
