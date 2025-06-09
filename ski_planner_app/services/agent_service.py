"""
Service for handling Strands Agent configuration, prompt creation, and execution.
"""
import logging
import requests
from typing import List
from abc import ABC

import streamlit as st
from strands import Agent
from strands.models.openai import OpenAIModel
from strands.models.ollama import OllamaModel
from strands.tools.mcp import MCPClient
from mcp import stdio_client, StdioServerParameters
from strands_tools import calculator

from ski_planner_app.models.trip import Trip, UserPreferences
from ski_planner_app.services.singleton import singleton_session
from ski_planner_app.config import OLLAMA_DEFAULT_URL, DEFAULT_OPENAI_MODELS, DB_FILE_PATH
from ski_planner_app.services.prompt import format_prompt

logger = logging.getLogger(__name__)

# Fix typo in secrets key and use config default
OLLAMA_URL = st.secrets.get("OLLAMA_URL", OLLAMA_DEFAULT_URL)


class BaseAgent(ABC):
    """Base class for all agent implementations."""

    def __init__(self, mcp_clients, model_id: str):
        """Initialise the base agent with MCP client."""
        self.mcp_clients = mcp_clients
        self.model_id = model_id
        self._agent = None

    def initialise(self):
        """
        Initialise the agent with tools.
        
        Note: The get_directions tool is intentionally excluded as we pre-calculate
        all distances between the user's home location and ski resorts.
        """
        try:
            # Get the tools list
            mcp_tools = []
            for client in self.mcp_clients:
                mcp_tools += client.list_tools_sync()
            
            # Create the agent with tools, excluding get_directions
            self._agent = Agent(
                tools=[calculator] + mcp_tools,
                model=self.model,
            )
            logger.debug(f"Agent successfully initialised: {self.model_id}")
        except Exception as e:
            logger.error(
                f"Failed to initialise {self.model_id} agent: {str(e)}")
            raise e

    def get_plan(self, preferences: UserPreferences, trips: List[Trip]) -> str:
        """
        Generate a plan using the agent.
        
        Args:
            preferences: User preferences including home location and criteria
            trips: List of planned trips
            
        Returns:
            str: The generated plan
        """
        try:
            # Format the prompt
            prompt = format_prompt(preferences, trips)
            logger.debug(f"Executing prompt of length {len(prompt)}")

            response = self._agent(prompt)

            logger.debug("Agent response received")
            return response.__str__()
        except Exception as e:
            error_msg = f"Error executing agent prompt: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise e
            
    async def get_plan_streaming(self, preferences: UserPreferences, trips: List[Trip]):
        """
        Generate a plan using the agent with streaming output.
        
        Args:
            preferences: User preferences including home location and criteria
            trips: List of planned trips
            
        Yields:
            dict: Streaming events from the agent
        """
        try:
            # Format the prompt
            prompt = format_prompt(preferences, trips)
            logger.debug(f"Executing streaming prompt of length {len(prompt)}")

            # Use stream_async method for streaming
            async for event in self._agent.stream_async(prompt):
                yield event
                
        except Exception as e:
            error_msg = f"Error executing streaming agent prompt: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise e


class OpenAIAgent(BaseAgent):
    """Agent implementation using OpenAI models."""

    def __init__(self, mcp_clients, model_id):
        """Initialise the OpenAI agent."""
        super().__init__(mcp_clients, model_id)

        if not st.secrets.get("OPENAI_API_KEY"):
            logger.warning("OPENAI_API_KEY not found in secrets")
            raise ValueError(
                "OpenAI API key is required to initialise the agent")
        # Configure OpenAI model
        openai_model = OpenAIModel(
            client_args={
                "api_key": st.secrets.get("OPENAI_API_KEY"),
            },
            model_id=self.model_id,
        )
        logger.debug(f"OpenAI model configured: {self.model_id}")
        self.model = openai_model
        self.initialise()


class OllamaAgent(BaseAgent):
    """Agent implementation using Ollama models."""

    def __init__(self, mcp_clients, model_id):
        """Initialise the Ollama agent."""
        super().__init__(mcp_clients, model_id)

        # Configure Ollama model
        ollama_model = OllamaModel(
            host=OLLAMA_URL,
            model_id=self.model_id
        )

        logger.debug(f"Ollama model configured: {self.model_id}")
        self.model = ollama_model
        self.initialise()


@singleton_session("service")
class AgentService:
    """Service for managing Strands Agent interactions."""

    def __init__(self):
        """Initialise the agent service with required configurations and agents."""
        logger.debug("Initialising AgentService")
        self.agents = {}

        # Setup MCP client (shared across agents)
        self._setup_mcp_clients()

        # Initialise agents
        self._initialise_agents()

    def _setup_mcp_clients(self):
        """Set up the MCP client for additional tools."""
        self.mcp_clients = [MCPClient(
            lambda: stdio_client(
                StdioServerParameters(
                    command="uvx",
                    args=["mcp-server-fetch"]
                )
            )
        ), MCPClient(
            lambda: stdio_client(
                StdioServerParameters(
                    command="uvx",
                    args=[
                        "mcp-server-sqlite", 
                        "--db", 
                        DB_FILE_PATH]
                )
            )
        )]
        for client in self.mcp_clients:
            client.start()
                
        logger.debug("MCP clients configured")

    def _initialise_agents(self):
        """Initialise all available agents."""
        # Initialise OpenAI agents
        self._initialise_openai_agents()

        # Initialise Ollama agents
        self._initialise_ollama_agents()

    def _initialise_openai_agents(self):
        """Initialise OpenAI agents."""
        try:
            openai_api_key = st.secrets.get("OPENAI_API_KEY")
            if not openai_api_key:
                logger.warning(
                    "OpenAI API key not found, skipping OpenAI agent setup")
                return

            for model in DEFAULT_OPENAI_MODELS:
                self.agents[model] = OpenAIAgent(
                    mcp_clients=self.mcp_clients,
                    model_id=model
                )

            logger.info("OpenAI agents initialised successfully")
        except Exception as e:
            logger.error(f"Failed to initialise OpenAI agents: {str(e)}")

    def _is_ollama_running(self) -> tuple:
        """Check if Ollama is running locally."""
        try:
            logger.debug("Checking Ollama service status")
            response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
            is_running = response.status_code == 200
            if is_running:
                logger.info("Ollama service is running")
                # Get available models
                models = [model["name"]
                          for model in response.json().get("models", [])]
                return True, models
            else:
                logger.warning(
                    f"Ollama service returned status code {response.status_code}")
                return False, []
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to connect to Ollama service: {str(e)}")
            return False, []

    def _initialise_ollama_agents(self):
        """Initialise Ollama agents if available."""
        is_running, models = self._is_ollama_running()
        if not is_running:
            logger.warning(
                "Ollama service not running, skipping Ollama agent setup")
            return

        try:
            # Create an agent for each available Ollama model
            for model_id in models:
                try:
                    self.agents[model_id] = OllamaAgent(
                        mcp_clients=self.mcp_clients,
                        model_id=model_id
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to initialise Ollama agent for model {model_id}: {str(e)}")

            logger.info(
                f"Ollama agents initialised successfully for models: {models}")
        except Exception as e:
            logger.error(f"Failed to initialise Ollama agents: {str(e)}")
            return

    def get_available_models(self) -> List[str]:
        """Get list of all available models."""
        return list(self.agents.keys())

    def get_plan(self,
                 preferences: UserPreferences,
                 trips: List[Trip],
                 model_id: str
                 ) -> str:
        """
        Execute a prompt using the specified agent.

        Args:
            preferences: User preferences including home location and criteria
            trips: List of planned trips
            model_id: Name of the LLM model to use

        Returns:
            str: The agent's response
        """
        try:
            # Check if the requested model is available
            if model_id not in self.agents:
                available_models = self.get_available_models()
                if not available_models:
                    raise ValueError("No AI models are available")

                logger.warning(
                    f"Model {model_id} not available, falling back to {available_models[0]}")
                model_id = available_models[0]

            # Get the appropriate agent
            agent = self.agents[model_id]
            logger.info(f"Using agent for model: {model_id}")

            # Generate the plan using the selected agent
            return agent.get_plan(preferences, trips)
        except Exception as e:
            error_msg = f"Error executing agent prompt with model {model_id}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise e
            
    async def get_plan_streaming(self,
                         preferences: UserPreferences,
                         trips: List[Trip],
                         model_id: str
                         ):
        """
        Execute a prompt using the specified agent with streaming output.

        Args:
            preferences: User preferences including home location and criteria
            trips: List of planned trips
            model_id: Name of the LLM model to use

        Yields:
            dict: Streaming events from the agent
        """
        try:
            # Check if the requested model is available
            if model_id not in self.agents:
                available_models = self.get_available_models()
                if not available_models:
                    raise ValueError("No AI models are available")

                logger.warning(
                    f"Model {model_id} not available, falling back to {available_models[0]}")
                model_id = available_models[0]

            # Get the appropriate agent
            agent = self.agents[model_id]
            logger.info(f"Using agent for streaming with model: {model_id}")

            # Generate the plan using the selected agent with streaming
            async for event in agent.get_plan_streaming(preferences, trips):
                yield event
                
        except Exception as e:
            error_msg = f"Error executing streaming agent prompt with model {model_id}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise e
