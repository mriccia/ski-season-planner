# Ski Season Planner

## Overview
The Ski Season Planner is a Streamlit application designed to help users plan their ski trips efficiently. This application allows users to manage their ski season activities, including tracking locations, dates, and preferences to generate personalized ski trip recommendations.

## Features
- Set user preferences including home location and skiing criteria
- Add multiple ski trips with specific dates
- Generate personalized ski resort recommendations based on user preferences
- Get travel distance and time estimates using OpenRouteService API
- View detailed information about ski resorts including piste lengths and difficulty levels
- Real-time streaming of plan generation with tool call visibility

## Project Structure
```
ski-season-planner
├── data/                # Directory for SQLite database file
├── docs/                # Documentation files
│   ├── database_design.md       # Database schema and query documentation
│   ├── db_feature.md            # Database integration implementation plan
│   ├── mcp_usage.md             # MCP server usage documentation
│   └── streaming_events_structure.md  # Streaming events documentation
├── ski_planner_app
│   ├── __init__.py
│   ├── app.py              # Main Streamlit application
│   ├── config.py           # Application configuration
│   ├── models
│   │   ├── __init__.py
│   │   ├── station.py      # Ski station data models
│   │   ├── streaming.py    # Streaming event models
│   │   └── trip.py         # Trip and user preferences models
│   ├── services
│   │   ├── __init__.py
│   │   ├── agent_service.py       # LLM agent service
│   │   ├── data
│   │   │   └── magic_pass_stations.json  # Ski resort data
│   │   ├── database_service.py    # SQLite database service
│   │   ├── distance_service.py    # Distance calculation service
│   │   ├── planner_service.py     # LLM-based plan generation service
│   │   ├── singleton.py           # Singleton pattern implementation
│   │   ├── station_service.py     # Service for handling ski station data
│   │   ├── streaming_service.py   # Service for handling streaming events
│   │   └── tools
│   │       └── openrouteservice_tool.py  # Integration with OpenRouteService API
│   └── ui
│       ├── __init__.py
│       ├── components.py          # Reusable UI components
│       ├── main.py                # Main UI layout
│       ├── state.py               # Streamlit session state management
│       └── streaming_components.py # UI components for streaming
├── observations.md       # Code review observations
├── TODO.md               # Todo list
├── pyproject.toml        # Project dependencies and metadata
├── poetry.lock           # Locked dependencies
├── Dockerfile            # Docker configuration
├── .dockerignore
└── README.md
```

## Setup Instructions

### Prerequisites
- Python 3.12 or higher
- Poetry for dependency management
- Docker for containerization (optional)
- OpenRouteService API key (for distance calculations)
- OpenAI API key (for LLM-based recommendations)

### Installation
1. Clone the repository:
   ```
   git clone <repository-url>
   cd ski-season-planner
   ```

2. Install dependencies using Poetry:
   ```
   poetry install
   ```

3. Set up your environment variables:
   Create a `.streamlit/secrets.toml` file with your API keys:
   ```toml
   OPENROUTE_API_KEY = "your_openroute_api_key"
   OPENAI_API_KEY = "your_openai_api_key"
   ```

### Running the Application
To run the application locally, use the following command:
```
poetry run streamlit run ski_planner_app/app.py
```

### Docker Setup
To build and run the application using Docker, follow these steps:

1. Build the Docker image:
   ```
   docker build -t ski-season-planner .
   ```

2. Run the Docker container:
   ```
   docker run -p 8501:8501 ski-season-planner
   ```

3. Access the application in your web browser at `http://localhost:8501`.

## Usage
1. **Set Preferences**: Enter your home location, preferred transportation mode, and skiing criteria in the sidebar.
2. **Add Trips**: Plan your ski trips by selecting dates for each trip.
3. **Generate Plan**: Get personalized resort recommendations based on your preferences and trip dates.

## Architecture

### Key Components

1. **UI Layer**
   - Streamlit components for user interaction
   - Session state management for application flow
   - Streaming UI components for real-time plan generation

2. **Service Layer**
   - Agent service for LLM integration
   - Distance service for travel calculations
   - Station service for ski resort data
   - Planner service for generating recommendations
   - Streaming service for handling event streams

3. **Data Layer**
   - SQLite database for persistent storage
   - JSON data source for ski resort information
   - Distance caching for performance optimization

4. **Model Layer**
   - Trip and user preference models
   - Station data models
   - Streaming event models

### Design Patterns

- **Singleton Pattern**: Used for service instances to ensure consistent state
- **Service Pattern**: Separation of business logic into dedicated services
- **Repository Pattern**: Data access abstraction through service classes
- **Domain Model Pattern**: Rich models representing business entities

## Dependencies
- Streamlit: Web application framework
- Strands Agents: LLM integration for personalized recommendations
- OpenRouteService: API for distance and travel time calculations
- Pandas: Data manipulation and analysis
- SQLite: Lightweight database for storing station data and caching distances

## Contributing
Contributions are welcome! Please submit a pull request or open an issue for any suggestions or improvements.

## License
This project is licensed under the MIT License. See the LICENSE file for more details.
