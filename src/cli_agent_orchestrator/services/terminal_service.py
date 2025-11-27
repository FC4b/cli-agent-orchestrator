"""Terminal service with workflow functions."""

import logging
from datetime import datetime
from enum import Enum
from typing import Dict, Optional

from cli_agent_orchestrator.clients.database import create_terminal as db_create_terminal
from cli_agent_orchestrator.clients.database import delete_terminal as db_delete_terminal
from cli_agent_orchestrator.clients.database import (
    get_terminal_metadata,
    update_last_active,
)
from cli_agent_orchestrator.clients.tmux import tmux_client
from cli_agent_orchestrator.constants import SESSION_PREFIX, TERMINAL_LOG_DIR
from cli_agent_orchestrator.models.provider import ProviderType
from cli_agent_orchestrator.models.terminal import Terminal, TerminalStatus
from cli_agent_orchestrator.providers.manager import provider_manager
from cli_agent_orchestrator.utils.terminal import (
    generate_session_name,
    generate_terminal_id,
    generate_window_name,
)

logger = logging.getLogger(__name__)


class OutputMode(str, Enum):
    """Output mode for terminal history."""

    FULL = "full"
    LAST = "last"


def create_terminal(
    provider: str,
    agent_profile: str,
    session_name: Optional[str] = None,
    new_session: bool = False,
    cwd: Optional[str] = None,
    wait_for_ready: bool = True,
) -> Terminal:
    """Create terminal, optionally creating new session with it.

    Args:
        provider: Provider type (e.g., 'q_cli', 'claude_code')
        agent_profile: Agent profile name
        session_name: Optional session name (auto-generated if not provided)
        new_session: Whether to create a new session
        cwd: Working directory for the terminal (default: current directory)
        wait_for_ready: If True, block until provider is ready. If False, return immediately.
    """
    try:
        terminal_id = generate_terminal_id()

        # Generate session name if not provided
        if not session_name:
            session_name = generate_session_name()

        window_name = generate_window_name(agent_profile)

        if new_session:
            # Apply SESSION_PREFIX if not already present
            if not session_name.startswith(SESSION_PREFIX):
                session_name = f"{SESSION_PREFIX}{session_name}"

            # Check if session already exists
            if tmux_client.session_exists(session_name):
                raise ValueError(f"Session '{session_name}' already exists")

            # Create new tmux session with this terminal as the initial window
            tmux_client.create_session(session_name, window_name, terminal_id, start_directory=cwd)
        else:
            # Add window to existing session
            if not tmux_client.session_exists(session_name):
                raise ValueError(f"Session '{session_name}' not found")
            window_name = tmux_client.create_window(
                session_name, window_name, terminal_id, start_directory=cwd
            )

        # Save terminal metadata to database
        db_create_terminal(terminal_id, session_name, window_name, provider, agent_profile, cwd)

        # Initialize provider (optionally non-blocking)
        provider_instance = provider_manager.create_provider(
            provider, terminal_id, session_name, window_name, agent_profile
        )
        provider_instance.initialize(wait_for_ready=wait_for_ready)

        # Create log file and start pipe-pane
        log_path = TERMINAL_LOG_DIR / f"{terminal_id}.log"
        log_path.touch()  # Ensure file exists before watching
        tmux_client.pipe_pane(session_name, window_name, str(log_path))

        terminal = Terminal(
            id=terminal_id,
            name=window_name,
            provider=ProviderType(provider),
            session_name=session_name,
            agent_profile=agent_profile,
            status=TerminalStatus.IDLE if wait_for_ready else TerminalStatus.PROCESSING,
            last_active=datetime.now(),
            pane_id=None,
        )

        logger.info(
            f"Created terminal: {terminal_id} in session: {session_name} (new_session={new_session}, wait_for_ready={wait_for_ready})"
        )
        return terminal

    except Exception as e:
        logger.error(f"Failed to create terminal: {e}")
        if new_session and session_name:
            try:
                tmux_client.kill_session(session_name)
            except:
                pass
        raise


def create_terminal_as_pane(
    provider: str,
    agent_profile: str,
    session_name: str,
    window_name: str,
    target_pane_id: Optional[str] = None,
    vertical: bool = True,
    cwd: Optional[str] = None,
    wait_for_ready: bool = True,
    size: Optional[int] = None,
) -> tuple[Terminal, str]:
    """Create terminal as a pane by splitting an existing pane.

    Args:
        provider: Provider type (e.g., 'q_cli', 'claude_code')
        agent_profile: Agent profile name
        session_name: Session name (must exist)
        window_name: Window name containing the pane to split
        target_pane_id: Optional specific pane ID to split. If None, splits the active pane.
        vertical: If True, split vertically (side by side). If False, split horizontally (top/bottom).
        cwd: Working directory for the terminal (default: current directory)
        wait_for_ready: If True, block until provider is ready. If False, return immediately.
        size: Optional percentage size for the new pane (1-100).

    Returns:
        Tuple of (Terminal, pane_id)
    """
    try:
        terminal_id = generate_terminal_id()

        if not tmux_client.session_exists(session_name):
            raise ValueError(f"Session '{session_name}' not found")

        # Create pane by splitting
        pane_id = tmux_client.create_pane(
            session_name,
            window_name,
            terminal_id,
            vertical=vertical,
            start_directory=cwd,
            target_pane_id=target_pane_id,
            size=size,
        )

        # Set pane title and agent name for identification
        tmux_client.set_pane_title(session_name, window_name, pane_id, agent_profile)
        tmux_client.set_pane_agent_name(session_name, window_name, pane_id, agent_profile)

        # Save terminal metadata to database (use pane_id as part of identifier)
        db_create_terminal(terminal_id, session_name, window_name, provider, agent_profile, cwd, pane_id=pane_id)

        # Initialize provider (optionally non-blocking)
        provider_instance = provider_manager.create_provider(
            provider, terminal_id, session_name, window_name, agent_profile, pane_id=pane_id
        )
        provider_instance.initialize(wait_for_ready=wait_for_ready)

        # Create log file and start pipe-pane for this specific pane
        log_path = TERMINAL_LOG_DIR / f"{terminal_id}.log"
        log_path.touch()
        tmux_client.pipe_pane_by_id(session_name, window_name, pane_id, str(log_path))

        terminal = Terminal(
            id=terminal_id,
            name=f"{window_name}:{pane_id}",
            provider=ProviderType(provider),
            session_name=session_name,
            agent_profile=agent_profile,
            status=TerminalStatus.IDLE if wait_for_ready else TerminalStatus.PROCESSING,
            last_active=datetime.now(),
            pane_id=pane_id,
        )

        logger.info(
            f"Created terminal as pane: {terminal_id} ({pane_id}) in session: {session_name}:{window_name}"
        )
        return terminal, pane_id

    except Exception as e:
        logger.error(f"Failed to create terminal as pane: {e}")
        raise


def apply_team_layout(
    session_name: str,
    window_name: str,
    supervisor_pane_id: Optional[str] = None,
    supervisor_agent_profile: Optional[str] = None,
) -> None:
    """Apply the team layout: supervisor on top, rest evenly split at bottom.

    Args:
        session_name: Tmux session name
        window_name: Tmux window name
        supervisor_pane_id: Optional pane ID of the supervisor (will be placed on top). If None, uses first pane.
        supervisor_agent_profile: Optional agent profile name for the supervisor pane title.
    """
    try:
        # Get session and window for setting options
        session = tmux_client.server.sessions.get(session_name=session_name)
        if not session:
            raise ValueError(f"Session '{session_name}' not found")

        window = session.windows.get(window_name=window_name)
        if not window:
            raise ValueError(f"Window '{window_name}' not found")

        # Set main-pane-height to 40% before applying layout
        window.cmd("set-window-option", "main-pane-height", "40%")

        # Apply main-horizontal layout: first pane on top, rest evenly distributed at bottom
        tmux_client.select_layout(session_name, window_name, "main-horizontal")

        # Enable pane borders to show agent names
        tmux_client.enable_pane_borders(session_name, window_name)

        # Set supervisor pane title and agent name if provided
        if supervisor_pane_id and supervisor_agent_profile:
            tmux_client.set_pane_title(session_name, window_name, supervisor_pane_id, supervisor_agent_profile)
            tmux_client.set_pane_agent_name(session_name, window_name, supervisor_pane_id, supervisor_agent_profile)

        logger.info(f"Applied team layout to {session_name}:{window_name}")
    except Exception as e:
        logger.error(f"Failed to apply team layout: {e}")
        raise


def wait_for_terminal_ready(terminal_id: str, timeout: float = 30.0, polling_interval: float = 0.5) -> bool:
    """Wait for a terminal's provider to become ready.

    Args:
        terminal_id: The terminal ID to wait for
        timeout: Maximum time to wait in seconds
        polling_interval: Time between status checks

    Returns:
        bool: True if provider became ready, False if timeout
    """
    provider = provider_manager.get_provider(terminal_id)
    if provider is None:
        raise ValueError(f"Provider not found for terminal {terminal_id}")

    return provider.wait_for_ready(timeout=timeout, polling_interval=polling_interval)


def get_terminal(terminal_id: str) -> Dict:
    """Get terminal data."""
    try:
        metadata = get_terminal_metadata(terminal_id)
        if not metadata:
            raise ValueError(f"Terminal '{terminal_id}' not found")

        # Get status from provider
        provider = provider_manager.get_provider(terminal_id)
        if provider is None:
            raise ValueError(f"Provider not found for terminal {terminal_id}")
        status = provider.get_status().value

        return {
            "id": metadata["id"],
            "name": metadata["tmux_window"],
            "provider": metadata["provider"],
            "session_name": metadata["tmux_session"],
            "agent_profile": metadata["agent_profile"],
            "cwd": metadata["cwd"],
            "status": status,
            "last_active": metadata["last_active"],
        }

    except Exception as e:
        logger.error(f"Failed to get terminal {terminal_id}: {e}")
        raise


def send_input(terminal_id: str, message: str) -> bool:
    """Send input to terminal."""
    try:
        metadata = get_terminal_metadata(terminal_id)
        if not metadata:
            raise ValueError(f"Terminal '{terminal_id}' not found")

        # Use pane-specific method if terminal has a pane_id
        pane_id = metadata.get("pane_id")
        if pane_id:
            tmux_client.send_keys_to_pane(
                metadata["tmux_session"], metadata["tmux_window"], pane_id, message
            )
        else:
            tmux_client.send_keys(metadata["tmux_session"], metadata["tmux_window"], message)

        update_last_active(terminal_id)
        logger.info(f"Sent input to terminal: {terminal_id}" + (f" (pane: {pane_id})" if pane_id else ""))
        return True

    except Exception as e:
        logger.error(f"Failed to send input to terminal {terminal_id}: {e}")
        raise


def get_output(terminal_id: str, mode: OutputMode = OutputMode.FULL) -> str:
    """Get terminal output."""
    try:
        metadata = get_terminal_metadata(terminal_id)
        if not metadata:
            raise ValueError(f"Terminal '{terminal_id}' not found")

        # Use pane-specific method if terminal has a pane_id
        pane_id = metadata.get("pane_id")
        if pane_id:
            full_output = tmux_client.get_pane_history(
                metadata["tmux_session"], metadata["tmux_window"], pane_id
            )
        else:
            full_output = tmux_client.get_history(metadata["tmux_session"], metadata["tmux_window"])

        if mode == OutputMode.FULL:
            return full_output
        elif mode == OutputMode.LAST:
            provider = provider_manager.get_provider(terminal_id)
            if provider is None:
                raise ValueError(f"Provider not found for terminal {terminal_id}")
            return provider.extract_last_message_from_script(full_output)

    except Exception as e:
        logger.error(f"Failed to get output from terminal {terminal_id}: {e}")
        raise


def delete_terminal(terminal_id: str) -> bool:
    """Delete terminal."""
    try:
        # Get metadata before deletion
        metadata = get_terminal_metadata(terminal_id)

        # Stop pipe-pane
        if metadata:
            try:
                tmux_client.stop_pipe_pane(metadata["tmux_session"], metadata["tmux_window"])
            except Exception as e:
                logger.warning(f"Failed to stop pipe-pane for {terminal_id}: {e}")

        # Existing cleanup
        provider_manager.cleanup_provider(terminal_id)
        deleted = db_delete_terminal(terminal_id)
        logger.info(f"Deleted terminal: {terminal_id}")
        return deleted

    except Exception as e:
        logger.error(f"Failed to delete terminal {terminal_id}: {e}")
        raise
