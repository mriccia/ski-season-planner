FROM python:3.12-slim

# Set the working directory
WORKDIR /app

# Install Poetry
RUN pip install poetry uv

# Copy the application code
COPY . /app

# Install dependencies
RUN poetry install --no-root

# Create volume for database persistence
VOLUME ["/app/data"]

# Expose the port the app runs on
EXPOSE 8501

# Command to run the application
CMD ["poetry", "run", "python", "-m", "streamlit", "run", "ski_planner_app/app.py"]
