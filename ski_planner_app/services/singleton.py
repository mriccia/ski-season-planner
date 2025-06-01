"""
Singleton utilities for Streamlit services.
"""
import streamlit as st
from functools import wraps


def singleton_session(key_prefix):
    """
    Decorator to create a singleton instance stored in session state.
    Use this for services that need to maintain state during a user session.

    Args:
        key_prefix (str): Prefix for the session state key

    Returns:
        Decorated class that behaves as a singleton within the session
    """
    def decorator(cls):
        @wraps(cls)
        def wrapped_class(*args, **kwargs):
            key = f"{key_prefix}_{cls.__name__}"
            if key not in st.session_state:
                st.session_state[key] = cls(*args, **kwargs)
            return st.session_state[key]
        return wrapped_class
    return decorator
