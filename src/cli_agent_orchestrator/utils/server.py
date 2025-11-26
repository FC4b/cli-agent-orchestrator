"""Utilities for managing the cao-server process."""

import logging
import subprocess
import sys
import time
from pathlib import Path

import requests

from cli_agent_orchestrator.constants import API_BASE_URL, SERVER_HOST, SERVER_PORT

logger = logging.getLogger(__name__)


def is_server_running() -> bool:
    """Check if cao-server is running by attempting to connect to it.

    Returns:
        bool: True if server is reachable, False otherwise
    """
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=2)
        return response.status_code == 200
    except (requests.exceptions.RequestException, requests.exceptions.Timeout):
        return False


def start_server_background() -> bool:
    """Start cao-server in the background if it's not already running.

    Returns:
        bool: True if server was started or already running, False if failed to start
    """
    if is_server_running():
        logger.debug("cao-server is already running")
        return True

    try:
        # Start server as a detached background process
        # Use same Python interpreter as current process
        python_executable = sys.executable

        # Start server with nohup-like behavior (detached from terminal)
        subprocess.Popen(
            [python_executable, "-m", "cli_agent_orchestrator.api.main"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,  # Detach from parent process
        )

        # Wait for server to be ready (with timeout)
        max_wait = 10  # seconds
        wait_interval = 0.5
        elapsed = 0

        while elapsed < max_wait:
            time.sleep(wait_interval)
            if is_server_running():
                logger.info("cao-server started successfully")
                return True
            elapsed += wait_interval

        logger.error("cao-server failed to start within timeout")
        return False

    except Exception as e:
        logger.error(f"Failed to start cao-server: {e}")
        return False


def ensure_server_running(silent: bool = False) -> bool:
    """Ensure cao-server is running, starting it if necessary.

    Args:
        silent: If True, don't print messages to stdout

    Returns:
        bool: True if server is running, False otherwise
    """
    if is_server_running():
        return True

    if not silent:
        print("Starting cao-server...")

    success = start_server_background()

    if success and not silent:
        print(f"cao-server started successfully on {SERVER_HOST}:{SERVER_PORT}")

    return success
