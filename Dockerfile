FROM python:3.12-slim

# Set the working directory
WORKDIR /app

# Copy the pyproject.toml and poetry.lock files
COPY pyproject.toml poetry.lock* /app/

# Install Poetry
RUN pip install poetry

# Create data directory for SQLite database
RUN mkdir -p /app/data

# Copy the rest of the application code
COPY . /app

# Install dependencies
RUN poetry install --no-root

# Create volume for database persistence
VOLUME ["/app/data"]

# Expose the port the app runs on
EXPOSE 8501

# Command to run the application
CMD ["poetry", "run", "streamlit", "run", "ski_planner_app/app.py"]
