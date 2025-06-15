# Ski Season Planner

## Overview
The Ski Season Planner is a Streamlit application designed to help users plan their ski trips efficiently. This application allows users to manage their ski season activities, including tracking locations, dates, and preferences to generate personalised ski trip recommendations using AI.

## Demo
Here a demo of the solution.

https://github.com/user-attachments/assets/02af48ad-88a9-4e05-806d-073b4392139e


## Features
- Set user preferences including home location and skiing criteria
- Add multiple ski trips with specific dates
- Generate personalised ski resort recommendations based on user preferences using AI
- Get travel distance and time estimates using OpenRouteService API
- View detailed information about ski resorts including piste lengths and difficulty levels
- Real-time streaming of plan generation with tool call visibility
- SQLite database for caching distance calculations and storing resort data
- Modular architecture with clear separation of concerns

## Project Structure
```
ski-season-planner/
├── data/                          # Directory for SQLite database and data files
│   ├── ski_planner.db             # SQLite database 
│   └── magic_pass_stations.json   # Ski resort data
├── docs/                          # Documentation files
│   └── database_design.md         # Database schema and query documentation
├── ski_planner_app/               # Main application package
│   ├── __init__.py
│   ├── app.py                     # Main Streamlit application entry point
│   ├── config.py                  # Application configuration and constants
│   ├── models/                    # Data models and domain objects
│   │   ├── __init__.py
│   │   ├── station.py             # Ski station data models
│   │   ├── streaming.py           # Streaming event models
│   │   └── trip.py                # Trip and user preferences models
│   ├── services/                  # Business logic and external integrations
│   │   ├── __init__.py
│   │   ├── agent_service.py       # LLM agent service for AI recommendations
│   │   ├── database_service.py    # SQLite database operations
│   │   ├── distance_service.py    # Distance calculation and caching
│   │   ├── planner_service.py     # Trip planning orchestration
│   │   ├── prompt.py              # LLM prompt templates
│   │   ├── singleton.py           # Singleton pattern implementation
│   │   ├── station_service.py     # Ski station data management
│   │   └── streaming_service.py   # Real-time streaming event handling
│   └── ui/                        # User interface components
│       ├── __init__.py
│       ├── components.py          # Reusable UI components
│       ├── main.py                # Main UI layout and navigation
│       ├── state.py               # Streamlit session state management
│       └── streaming_components.py # UI components for streaming events
├── .dockerignore                  # Docker ignore file
├── .gitignore                     # Git ignore file
├── .gitattributes                 # Git attributes
├── Dockerfile                     # Docker configuration
├── LICENSE                        # MIT License
├── README.md                      # This file
└── pyproject.toml                 # Project metadata and dependencies
```

## Setup Instructions

### Prerequisites
- Python 3.12 or higher
- Poetry for dependency management
- Docker for containerisation (optional)
- OpenRouteService API key (for distance calculations)
- At least one of: OpenAI API key or Ollama running locally (for local LLM inference)
  - If both are available, you can choose between them in the application

### Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/mriccia/ski-season-planner.git
   cd ski-season-planner
   ```

2. Install dependencies using Poetry:
   ```bash
   poetry install
   ```

3. Set up your environment variables:
   Create a `.streamlit/secrets.toml` file with your API keys:
   ```toml
   OPENROUTE_API_KEY = "your_openroute_api_key"
   OPENAI_API_KEY = "your_openai_api_key"  # Optional if using Ollama
   ```
   
   **Note**: You need either the OpenAI API key or Ollama running locally. If you have both, you can choose between them in the application.

### Running the Application
To run the application locally, use the following command:
```bash
poetry run python -m streamlit run ski_planner_app/app.py
```

The application will be available at `http://localhost:8501`.

### Docker Setup
To build and run the application using Docker:

1. Build the Docker image:
   ```bash
   docker build -t ski-season-planner .
   ```

2. Run the Docker container:
   ```bash
   docker run -p 8501:8501 -v $(pwd)/data:/app/data ski-season-planner
   ```

3. Access the application in your web browser at `http://localhost:8501`.

**Note**: The `-v $(pwd)/data:/app/data` flag mounts the local data directory to persist the SQLite database between container runs.

## Usage
1. **Set Preferences**: Enter your home location, preferred transportation mode, and skiing criteria in the sidebar.
2. **Add Trips**: Plan your ski trips by selecting dates for each trip.
3. **Generate Plan**: Get personalised resort recommendations based on your preferences and trip dates.

**Note on Distance Calculations**: The application has pre-computed distances for "Basel, Switzerland", "Bern, Switzerland", "Geneva, Switzerland", "Lausanne, Switzerland", "Sion, Switzerland", and "Zurich, Switzerland" to all 88 ski resorts, providing instant results. If you enter any other location, the system will calculate distances in real-time using the OpenRouteService API, which may take several minutes due to API rate limiting.

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
   - Distance caching for performance optimisation

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
- **Streamlit**: Web application framework
- **Strands Agents**: LLM integration for personalised recommendations
- **Pandas**: Data manipulation and analysis
- **Ollama**: Local LLM support
- **OpenRouteService API**: Distance and travel time calculations (via HTTP requests)
- **SQLite**: Lightweight database for storing station data and caching distances

## Contributing
Contributions are welcome! Please submit a pull request or open an issue for any suggestions or improvements.

## License
This project is licensed under the MIT License. See the LICENSE file for more details.
