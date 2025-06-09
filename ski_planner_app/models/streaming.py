"""
Domain models for streaming events.
"""
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Union


@dataclass
class TextChunk:
    """A chunk of text from the streaming response."""
    content: str


@dataclass
class ToolCall:
    """A tool call event from the streaming response."""
    tool_id: str
    tool_name: str
    input_data: str = ""
    
    def update_input(self, new_input: str) -> None:
        """Update the input data for this tool call."""
        self.input_data += new_input


@dataclass
class ToolResult:
    """A tool result event from the streaming response."""
    tool_id: str
    tool_name: str
    result_data: Dict[str, Any]


@dataclass
class StatusUpdate:
    """A status update event from the streaming response."""
    status: str
    details: Optional[str] = None


@dataclass
class StreamingState:
    """The current state of the streaming response."""
    text_content: str = ""
    current_tool_call: Optional[ToolCall] = None
    tool_calls: List[ToolCall] = None
    tool_results: List[ToolResult] = None
    status_updates: List[StatusUpdate] = None
    
    def __post_init__(self):
        """Initialize empty lists if not provided."""
        if self.tool_calls is None:
            self.tool_calls = []
        if self.tool_results is None:
            self.tool_results = []
        if self.status_updates is None:
            self.status_updates = []
    
    def add_text(self, text: str) -> None:
        """Add text to the content."""
        self.text_content += text
    
    def add_tool_call(self, tool_call: ToolCall) -> None:
        """Add a tool call to the state."""
        self.current_tool_call = tool_call
        self.tool_calls.append(tool_call)
    
    def add_tool_result(self, tool_result: ToolResult) -> None:
        """Add a tool result to the state."""
        self.tool_results.append(tool_result)
        # Clear current tool call as it's now complete
        self.current_tool_call = None
    
    def add_status_update(self, status_update: StatusUpdate) -> None:
        """Add a status update to the state."""
        self.status_updates.append(status_update)


@dataclass
class StreamEvent:
    """A single event from the streaming response."""
    event_type: str  # "text", "tool_call", "tool_result", "status"
    data: Union[TextChunk, ToolCall, ToolResult, StatusUpdate]
