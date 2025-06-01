FROM python:3.12-slim

# Set the working directory
WORKDIR /app

# Copy the pyproject.toml and poetry.lock files
COPY pyproject.toml poetry.lock* /app/

# Install Poetry
RUN pip install poetry


# Copy the rest of the application code
COPY . /app

# Install dependencies
RUN poetry install --no-root

# Expose the port the app runs on
EXPOSE 8501

# Command to run the application
CMD ["poetry", "run", "streamlit", "run", "src/app.py"]