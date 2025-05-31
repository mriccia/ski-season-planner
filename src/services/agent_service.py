"""
Service for handling Strands Agent configuration, prompt creation, and execution.
"""
import logging
from typing import List, Any, Optional

import streamlit as st
from strands import Agent
from strands.models.openai import OpenAIModel
from strands.tools.mcp import MCPClient
from mcp import stdio_client, StdioServerParameters
from strands_tools import calculator

from services.openrouteservice_tool import get_directions
from models.trip import Trip, UserPreferences
from services.prompt import format_prompt

logger = logging.getLogger(__name__)

class AgentService:
    """Service for managing Strands Agent interactions."""
    
    def __init__(self):
        """Initialise the agent service with required configurations and agent."""
        logger.debug("Initialising AgentService")
        self._setup_openai_model()
        self._setup_mcp_client()
        self._initialise_agent()
        
    def _setup_openai_model(self):
        """Set up the OpenAI model configuration."""
        self.openai_model = OpenAIModel(
            client_args={
                "api_key": st.secrets.get("OPENAI_API_KEY"),
            },
            model_id="gpt-4o"
        )
        logger.debug("OpenAI model configured")
        
    def _setup_mcp_client(self):
        """Set up the MCP client for additional tools."""
        self.mcp_client = MCPClient(
            lambda: stdio_client(
                StdioServerParameters(
                    command="uvx",
                    args=["mcp-server-fetch"]
                )
            )
        )
        logger.debug("MCP client configured")
    
    def _initialise_agent(self):
        """Initialise the agent with all tools during service instantiation."""
        # Get the tools list once during initialisation
        with self.mcp_client:
            mcp_tools = self.mcp_client.list_tools_sync()
            
        # Create the agent with all tools
        self._agent = Agent(
            tools=[calculator, get_directions] + mcp_tools,
            model=self.openai_model,
        )
        logger.debug("Agent successfully initialised with all tools")
            
    def get_plan(self,
                 preferences: UserPreferences,
                 trips: List[Trip],
                 model_name: str,   
                 stations: List[object]
                 ) -> str:
        """
        Execute a prompt using the Strands Agent.
        
        Args:
            prompt (str): The prompt to send to the agent
            
        Returns:
            str: The agent's response
        """
        try:
            
            prompt = format_prompt(preferences, trips, stations)
            logger.debug(f"Executing prompt of length {len(prompt)}")
            # Use the MCP client within a context manager only for the execution
            with self.mcp_client:
                response = self._agent(prompt)
                
            logger.debug("Agent response received")
            return response.__str__()
        except Exception as e:
            error_msg = f"Error executing agent prompt: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise e
