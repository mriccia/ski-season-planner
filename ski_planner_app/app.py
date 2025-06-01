"""
Main Streamlit application for the Ski Season Planner.
"""
import logging
from ski_planner_app.ui.main import main

# Add a handler
logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler()]
)

# Configure the root strands logger
logging.getLogger("strands").setLevel(logging.DEBUG)
logging.getLogger("ski_planner_app").setLevel(logging.DEBUG)

if __name__ == "__main__":
    main()
