import streamlit as st
import sys
import os

# Add the frontend directory to sys.path so modules like config_frontend and api_client work
current_dir = os.path.dirname(os.path.abspath(__file__))
frontend_dir = os.path.join(current_dir, "streamlit_frontend")
sys.path.append(frontend_dir)

# NOTE: For Streamlit Cloud to recognize multi-page apps, the 'pages' directory 
# must be in the same directory as the main script. 
# We recommend setting the "Main file path" in Streamlit Cloud to:
# streamlit_frontend/streamlit_frontend.py
#
# However, this file is provided as a convenience wrapper.

try:
    from streamlit_frontend import streamlit_frontend
except ImportError:
    # If standard import fails, try running it directly
    with open(os.path.join(frontend_dir, "streamlit_frontend.py"), encoding="utf-8") as f:
        code = compile(f.read(), "streamlit_frontend.py", "exec")
        exec(code, globals())
