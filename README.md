# Ski Season Planner

## Overview
The Ski Season Planner is a Streamlit application designed to help users plan their ski trips efficiently. This application allows users to manage their ski season activities, including tracking locations, dates, and other relevant information.

## Project Structure
```
ski-season-planner
├── agent
│   └── __init__.py
├── src
│   └── app.py
├── pyproject.toml
├── Dockerfile
├── .dockerignore
└── README.md
```

## Setup Instructions

### Prerequisites
- Python 3.13 or higher
- Poetry for dependency management
- Docker for containerization

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

### Running the Application
To run the application locally, use the following command:
```
poetry run streamlit run src/app.py
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
Once the application is running, you can interact with the user interface to plan your ski trips. Follow the on-screen instructions to navigate through the features.

## Contributing
Contributions are welcome! Please submit a pull request or open an issue for any suggestions or improvements.

## License
This project is licensed under the MIT License. See the LICENSE file for more details.