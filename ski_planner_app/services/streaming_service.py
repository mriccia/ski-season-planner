"""
Service for handling streaming responses from the planner service.
"""
import asyncio
import json
import logging
from typing import Dict, Any, Optional, Callable, AsyncGenerator, List, Tuple

from ski_planner_app.models.streaming import (
    TextChunk, 
    ToolCall, 
    ToolResult, 
    StatusUpdate, 
    StreamingState,
    StreamEvent
)

logger = logging.getLogger(__name__)

class StreamingService:
    """
    Service for handling streaming responses from the planner service.
    Maps complex SDK events to simplified domain models.
    """
    
    def __init__(self):
        """Initialize the streaming service."""
        self.state = StreamingState()
    
    def _map_event(self, event: Dict[str, Any]) -> List[StreamEvent]:
        """
        Map a raw SDK event to our domain model events.
        
        Args:
            event: Raw event from the SDK
            
        Returns:
            List of mapped StreamEvent objects
        """
        mapped_events = []
        
        # Handle direct data events (legacy format)
        if "data" in event:
            chunk = event["data"]
            mapped_events.append(StreamEvent(
                event_type="text",
                data=TextChunk(content=chunk)
            ))
            return mapped_events
        
        # Handle event-based updates
        if "event" in event:
            event_data = event["event"]
            
            # Handle message start
            if "messageStart" in event_data:
                mapped_events.append(StreamEvent(
                    event_type="status",
                    data=StatusUpdate(status="start", details="Agent is generating a response")
                ))
            
            # Handle content block start
            if "contentBlockStart" in event_data and "start" in event_data["contentBlockStart"]:
                start_data = event_data["contentBlockStart"]["start"]
                
                # Check if this is a tool use block
                if start_data and "toolUse" in start_data:
                    tool_info = start_data["toolUse"]
                    tool_name = tool_info.get("name")
                    tool_id = tool_info.get("toolUseId")
                    
                    if tool_name:
                        mapped_events.append(StreamEvent(
                            event_type="tool_call",
                            data=ToolCall(
                                tool_id=tool_id,
                                tool_name=tool_name
                            )
                        ))
            
            # Handle content block delta
            if "contentBlockDelta" in event_data and "delta" in event_data["contentBlockDelta"]:
                delta = event_data["contentBlockDelta"]["delta"]
                
                if "toolUse" in delta and "input" in delta["toolUse"]:
                    input_chunk = delta["toolUse"]["input"]
                    if input_chunk:
                        mapped_events.append(StreamEvent(
                            event_type="tool_input",
                            data=TextChunk(content=str(input_chunk))
                        ))
            
            # Handle tool result block
            if "toolResultBlock" in event_data:
                result_data = event_data["toolResultBlock"]
                tool_id = result_data.get("toolUseId")
                result = result_data.get("result", {})
                
                if tool_id and result:
                    # Find the tool name from our state
                    tool_name = ""
                    for tool_call in self.state.tool_calls:
                        if tool_call.tool_id == tool_id:
                            tool_name = tool_call.tool_name
                            break
                    
                    mapped_events.append(StreamEvent(
                        event_type="tool_result",
                        data=ToolResult(
                            tool_id=tool_id,
                            tool_name=tool_name,
                            result_data=result
                        )
                    ))
            
            # Handle message stop
            if "messageStop" in event_data:
                stop_reason = event_data["messageStop"].get("stopReason", "end_turn")
                mapped_events.append(StreamEvent(
                    event_type="status",
                    data=StatusUpdate(status="complete", details=f"Generation complete: {stop_reason}")
                ))
            
            # Handle redact content
            if "redactContent" in event_data:
                redact_data = event_data["redactContent"]
                if "redactAssistantContentMessage" in redact_data:
                    redact_msg = redact_data["redactAssistantContentMessage"]
                    mapped_events.append(StreamEvent(
                        event_type="status",
                        data=StatusUpdate(status="warning", details="Some content was redacted")
                    ))
        
        return mapped_events
    
    def _update_state(self, event: StreamEvent) -> None:
        """
        Update the streaming state based on an event.
        
        Args:
            event: The event to process
        """
        if event.event_type == "text":
            text_chunk = event.data
            self.state.add_text(text_chunk.content)
        
        elif event.event_type == "tool_call":
            tool_call = event.data
            self.state.add_tool_call(tool_call)
        
        elif event.event_type == "tool_input":
            text_chunk = event.data
            if self.state.current_tool_call:
                self.state.current_tool_call.update_input(text_chunk.content)
        
        elif event.event_type == "tool_result":
            tool_result = event.data
            self.state.add_tool_result(tool_result)
        
        elif event.event_type == "status":
            status_update = event.data
            self.state.add_status_update(status_update)
    
    async def process_stream(
        self,
        async_gen: AsyncGenerator,
        on_event: Optional[Callable[[StreamEvent], None]] = None,
        on_state_change: Optional[Callable[[StreamingState], None]] = None,
        on_complete: Optional[Callable[[str], None]] = None
    ) -> str:
        """
        Process events from an async generator, map them to our domain model,
        and update the state.
        
        Args:
            async_gen: Async generator producing events
            on_event: Optional callback for each mapped event
            on_state_change: Optional callback for state changes
            on_complete: Optional callback function to call with the final plan
            
        Returns:
            The complete generated plan as a string
        """
        # Reset state
        self.state = StreamingState()
        
        try:
            # Process events from the async generator
            async for raw_event in async_gen:
                # Skip initialization events
                if any(key in raw_event for key in ["init_event_loop", "start", "start_event_loop"]):
                    continue
                
                # Map the raw event to our domain model
                mapped_events = self._map_event(raw_event)
                
                # Process each mapped event
                for event in mapped_events:
                    # Update our state
                    self._update_state(event)
                    
                    # Call the event callback if provided
                    if on_event:
                        on_event(event)
                    
                    # Call the state change callback if provided
                    if on_state_change:
                        on_state_change(self.state)
        
        except Exception as e:
            logger.error(f"Error in stream processing: {str(e)}")
            raise e
        
        # Call the completion callback if provided
        if on_complete:
            on_complete(self.state.text_content)
            
        return self.state.text_content
