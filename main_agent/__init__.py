import logging

# Silence verbose ADK framework DEBUG logs while keeping our own
logging.getLogger("adk_web_server").setLevel(logging.INFO)
logging.getLogger("google.adk").setLevel(logging.INFO)

from . import agent
