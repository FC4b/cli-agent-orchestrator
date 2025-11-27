"""Simplified tmux client as module singleton."""

import logging
import os
import re
import time
from typing import Dict, List, Optional

import libtmux
from libtmux.constants import PaneDirection

from cli_agent_orchestrator.constants import TMUX_HISTORY_LINES

logger = logging.getLogger(__name__)

# Delay between chunks when sending long key strings
SEND_KEYS_CHUNK_INTERVAL = 0.5


class TmuxClient:
    """Simplified tmux client for basic operations."""

    def __init__(self) -> None:
        self.server = libtmux.Server()

    def create_session(
        self,
        session_name: str,
        window_name: str,
        terminal_id: str,
        start_directory: Optional[str] = None,
    ) -> str:
        """Create detached tmux session with initial window and return window name.

        Args:
            session_name: Name for the tmux session
            window_name: Name for the initial window
            terminal_id: CAO terminal ID to set as environment variable
            start_directory: Working directory for the session (default: current directory)
        """
        try:
            environment = os.environ.copy()
            environment["CAO_TERMINAL_ID"] = terminal_id

            session = self.server.new_session(
                session_name=session_name,
                window_name=window_name,
                detach=True,
                environment=environment,
                start_directory=start_directory,
            )
            logger.info(
                f"Created tmux session: {session_name} with window: {window_name}"
                + (f" in {start_directory}" if start_directory else "")
            )
            window_name_result = session.windows[0].name
            if window_name_result is None:
                raise ValueError(f"Window name is None for session {session_name}")
            return window_name_result
        except Exception as e:
            logger.error(f"Failed to create session {session_name}: {e}")
            raise

    def create_window(
        self,
        session_name: str,
        window_name: str,
        terminal_id: str,
        start_directory: Optional[str] = None,
    ) -> str:
        """Create window in session and return window name.

        Args:
            session_name: Name of the tmux session
            window_name: Name for the new window
            terminal_id: CAO terminal ID to set as environment variable
            start_directory: Working directory for the window (default: session's directory)
        """
        try:
            session = self.server.sessions.get(session_name=session_name)
            if not session:
                raise ValueError(f"Session '{session_name}' not found")

            window = session.new_window(
                window_name=window_name,
                environment={"CAO_TERMINAL_ID": terminal_id},
                start_directory=start_directory,
            )

            logger.info(
                f"Created window '{window.name}' in session '{session_name}'"
                + (f" in {start_directory}" if start_directory else "")
            )
            window_name_result = window.name
            if window_name_result is None:
                raise ValueError(f"Window name is None for session {session_name}")
            return window_name_result
        except Exception as e:
            logger.error(f"Failed to create window in session {session_name}: {e}")
            raise

    def send_keys(self, session_name: str, window_name: str, keys: str) -> None:
        """Send keys to window with chunking for long messages."""
        try:
            logger.info(f"send_keys: {session_name}:{window_name} - keys: {keys}")

            session = self.server.sessions.get(session_name=session_name)
            if not session:
                raise ValueError(f"Session '{session_name}' not found")

            window = session.windows.get(window_name=window_name)
            if not window:
                raise ValueError(f"Window '{window_name}' not found in session '{session_name}'")

            pane = window.active_pane
            if pane:
                # Split keys into chunks of ~100 characters at whitespace boundaries
                chunks = []
                start = 0

                while start < len(keys):
                    target_pos = start + 100

                    if target_pos >= len(keys):
                        chunks.append(keys[start:])
                        break

                    # Look forward from target position to find next whitespace
                    match = re.search(r"\s", keys[target_pos:])

                    if match:
                        split_pos = target_pos + match.start()
                        chunks.append(keys[start:split_pos])
                        start = split_pos
                    else:
                        chunks.append(keys[start:])
                        break

                # Send chunks with delay between them
                for chunk in chunks:
                    pane.send_keys(chunk, enter=False)
                    time.sleep(SEND_KEYS_CHUNK_INTERVAL)

                # Send carriage return as separate command
                pane.send_keys("C-m", enter=False)
                logger.debug(f"Sent keys to {session_name}:{window_name}")
        except Exception as e:
            logger.error(f"Failed to send keys to {session_name}:{window_name}: {e}")
            raise

    def get_history(
        self, session_name: str, window_name: str, tail_lines: Optional[int] = None
    ) -> str:
        """Get window history.

        Args:
            session_name: Name of tmux session
            window_name: Name of window in session
            tail_lines: Number of lines to capture from end (default: TMUX_HISTORY_LINES)
        """
        try:
            session = self.server.sessions.get(session_name=session_name)
            if not session:
                raise ValueError(f"Session '{session_name}' not found")

            window = session.windows.get(window_name=window_name)
            if not window:
                raise ValueError(f"Window '{window_name}' not found in session '{session_name}'")

            # Use cmd to run capture-pane with -e (escape sequences) and -p (print) flags
            pane = window.panes[0]
            lines = tail_lines if tail_lines is not None else TMUX_HISTORY_LINES
            result = pane.cmd("capture-pane", "-e", "-p", "-S", f"-{lines}")
            # Join all lines with newlines to get complete output
            return "\n".join(result.stdout) if result.stdout else ""
        except Exception as e:
            logger.error(f"Failed to get history from {session_name}:{window_name}: {e}")
            raise

    def list_sessions(self) -> List[Dict[str, str]]:
        """List all tmux sessions."""
        try:
            sessions: List[Dict[str, str]] = []
            for session in self.server.sessions:
                # Check if session has attached clients
                is_attached = len(getattr(session, "attached_sessions", [])) > 0

                session_name = session.name if session.name is not None else ""
                sessions.append(
                    {
                        "id": session_name,
                        "name": session_name,
                        "status": "active" if is_attached else "detached",
                    }
                )

            return sessions
        except Exception as e:
            logger.error(f"Failed to list sessions: {e}")
            return []

    def get_session_windows(self, session_name: str) -> List[Dict[str, str]]:
        """Get all windows in a session."""
        try:
            session = self.server.sessions.get(session_name=session_name)
            if not session:
                return []

            windows: List[Dict[str, str]] = []
            for window in session.windows:
                window_name = window.name if window.name is not None else ""
                windows.append({"name": window_name, "index": str(window.index)})

            return windows
        except Exception as e:
            logger.error(f"Failed to get windows for session {session_name}: {e}")
            return []

    def kill_session(self, session_name: str) -> bool:
        """Kill tmux session."""
        try:
            session = self.server.sessions.get(session_name=session_name)
            if session:
                session.kill_session()
                logger.info(f"Killed tmux session: {session_name}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to kill session {session_name}: {e}")
            return False

    def session_exists(self, session_name: str) -> bool:
        """Check if session exists."""
        try:
            session = self.server.sessions.get(session_name=session_name)
            return session is not None
        except Exception:
            return False

    def pipe_pane(self, session_name: str, window_name: str, file_path: str) -> None:
        """Start piping pane output to file.

        Args:
            session_name: Tmux session name
            window_name: Tmux window name
            file_path: Absolute path to log file
        """
        try:
            session = self.server.sessions.get(session_name=session_name)
            if not session:
                raise ValueError(f"Session '{session_name}' not found")

            window = session.windows.get(window_name=window_name)
            if not window:
                raise ValueError(f"Window '{window_name}' not found in session '{session_name}'")

            pane = window.active_pane
            if pane:
                pane.cmd("pipe-pane", "-o", f"cat >> {file_path}")
                logger.info(f"Started pipe-pane for {session_name}:{window_name} to {file_path}")
        except Exception as e:
            logger.error(f"Failed to start pipe-pane for {session_name}:{window_name}: {e}")
            raise

    def stop_pipe_pane(self, session_name: str, window_name: str) -> None:
        """Stop piping pane output.

        Args:
            session_name: Tmux session name
            window_name: Tmux window name
        """
        try:
            session = self.server.sessions.get(session_name=session_name)
            if not session:
                raise ValueError(f"Session '{session_name}' not found")

            window = session.windows.get(window_name=window_name)
            if not window:
                raise ValueError(f"Window '{window_name}' not found in session '{session_name}'")

            pane = window.active_pane
            if pane:
                pane.cmd("pipe-pane")
                logger.info(f"Stopped pipe-pane for {session_name}:{window_name}")
        except Exception as e:
            logger.error(f"Failed to stop pipe-pane for {session_name}:{window_name}: {e}")
            raise

    def create_pane(
        self,
        session_name: str,
        window_name: str,
        terminal_id: str,
        vertical: bool = True,
        start_directory: Optional[str] = None,
        target_pane_id: Optional[str] = None,
        size: Optional[int] = None,
    ) -> str:
        """Create a new pane by splitting an existing pane.

        Args:
            session_name: Name of the tmux session
            window_name: Name of the window containing the pane
            terminal_id: CAO terminal ID to set as environment variable
            vertical: If True, split vertically (side by side). If False, split horizontally (top/bottom).
            start_directory: Working directory for the pane
            target_pane_id: Optional specific pane ID to split. If None, splits the active pane.
            size: Optional percentage size for the new pane (1-100).

        Returns:
            The pane ID of the newly created pane.
        """
        try:
            session = self.server.sessions.get(session_name=session_name)
            if not session:
                raise ValueError(f"Session '{session_name}' not found")

            window = session.windows.get(window_name=window_name)
            if not window:
                raise ValueError(f"Window '{window_name}' not found in session '{session_name}'")

            # Get target pane
            if target_pane_id:
                target_pane = None
                for pane in window.panes:
                    if pane.pane_id == target_pane_id:
                        target_pane = pane
                        break
                if not target_pane:
                    raise ValueError(f"Pane '{target_pane_id}' not found")
            else:
                target_pane = window.active_pane

            if not target_pane:
                raise ValueError("No active pane found")

            # Determine split direction:
            # vertical=True means side-by-side (Right), vertical=False means top/bottom (Below)
            direction = PaneDirection.Right if vertical else PaneDirection.Below

            # Build size parameter (percentage string like "50%")
            size_param = f"{size}%" if size else None

            # Split the pane
            new_pane = target_pane.split(
                direction=direction,
                start_directory=start_directory,
                environment={"CAO_TERMINAL_ID": terminal_id},
                size=size_param,
            )

            pane_id = new_pane.pane_id
            if pane_id is None:
                raise ValueError("Failed to get pane ID for new pane")

            logger.info(
                f"Created pane {pane_id} in {session_name}:{window_name}"
                + (f" in {start_directory}" if start_directory else "")
                + (f" with size {size}%" if size else "")
            )
            return pane_id

        except Exception as e:
            logger.error(f"Failed to create pane in {session_name}:{window_name}: {e}")
            raise

    def get_pane_id(self, session_name: str, window_name: str, pane_index: int = 0) -> str:
        """Get pane ID by index in a window.

        Args:
            session_name: Name of the tmux session
            window_name: Name of the window
            pane_index: Index of the pane (0-based)

        Returns:
            The pane ID.
        """
        try:
            session = self.server.sessions.get(session_name=session_name)
            if not session:
                raise ValueError(f"Session '{session_name}' not found")

            window = session.windows.get(window_name=window_name)
            if not window:
                raise ValueError(f"Window '{window_name}' not found in session '{session_name}'")

            if pane_index >= len(window.panes):
                raise ValueError(f"Pane index {pane_index} out of range")

            pane_id = window.panes[pane_index].pane_id
            if pane_id is None:
                raise ValueError(f"Pane ID is None for pane index {pane_index}")
            return pane_id

        except Exception as e:
            logger.error(f"Failed to get pane ID: {e}")
            raise

    def send_keys_to_pane(
        self, session_name: str, window_name: str, pane_id: str, keys: str
    ) -> None:
        """Send keys to a specific pane."""
        try:
            logger.info(f"send_keys_to_pane: {session_name}:{window_name}:{pane_id} - keys: {keys}")

            session = self.server.sessions.get(session_name=session_name)
            if not session:
                raise ValueError(f"Session '{session_name}' not found")

            window = session.windows.get(window_name=window_name)
            if not window:
                raise ValueError(f"Window '{window_name}' not found in session '{session_name}'")

            # Find the specific pane
            target_pane = None
            for pane in window.panes:
                if pane.pane_id == pane_id:
                    target_pane = pane
                    break

            if not target_pane:
                raise ValueError(f"Pane '{pane_id}' not found in window '{window_name}'")

            # Split keys into chunks (same logic as send_keys)
            chunks = []
            start = 0

            while start < len(keys):
                target_pos = start + 100

                if target_pos >= len(keys):
                    chunks.append(keys[start:])
                    break

                match = re.search(r"\s", keys[target_pos:])

                if match:
                    split_pos = target_pos + match.start()
                    chunks.append(keys[start:split_pos])
                    start = split_pos
                else:
                    chunks.append(keys[start:])
                    break

            # Send chunks with delay
            for chunk in chunks:
                target_pane.send_keys(chunk, enter=False)
                time.sleep(SEND_KEYS_CHUNK_INTERVAL)

            # Send carriage return
            target_pane.send_keys("C-m", enter=False)
            logger.debug(f"Sent keys to {session_name}:{window_name}:{pane_id}")

        except Exception as e:
            logger.error(f"Failed to send keys to pane: {e}")
            raise

    def get_pane_history(
        self, session_name: str, window_name: str, pane_id: str, tail_lines: Optional[int] = None
    ) -> str:
        """Get history from a specific pane.

        Args:
            session_name: Name of tmux session
            window_name: Name of window in session
            pane_id: Pane ID
            tail_lines: Number of lines to capture from end (default: TMUX_HISTORY_LINES)
        """
        try:
            session = self.server.sessions.get(session_name=session_name)
            if not session:
                raise ValueError(f"Session '{session_name}' not found")

            window = session.windows.get(window_name=window_name)
            if not window:
                raise ValueError(f"Window '{window_name}' not found in session '{session_name}'")

            # Find the specific pane
            target_pane = None
            for pane in window.panes:
                if pane.pane_id == pane_id:
                    target_pane = pane
                    break

            if not target_pane:
                raise ValueError(f"Pane '{pane_id}' not found")

            lines = tail_lines if tail_lines is not None else TMUX_HISTORY_LINES
            result = target_pane.cmd("capture-pane", "-e", "-p", "-S", f"-{lines}")
            return "\n".join(result.stdout) if result.stdout else ""

        except Exception as e:
            logger.error(f"Failed to get pane history: {e}")
            raise

    def pipe_pane_by_id(self, session_name: str, window_name: str, pane_id: str, file_path: str) -> None:
        """Start piping specific pane output to file.

        Args:
            session_name: Tmux session name
            window_name: Tmux window name
            pane_id: Pane ID
            file_path: Absolute path to log file
        """
        try:
            session = self.server.sessions.get(session_name=session_name)
            if not session:
                raise ValueError(f"Session '{session_name}' not found")

            window = session.windows.get(window_name=window_name)
            if not window:
                raise ValueError(f"Window '{window_name}' not found in session '{session_name}'")

            # Find the specific pane
            target_pane = None
            for pane in window.panes:
                if pane.pane_id == pane_id:
                    target_pane = pane
                    break

            if not target_pane:
                raise ValueError(f"Pane '{pane_id}' not found")

            target_pane.cmd("pipe-pane", "-o", f"cat >> {file_path}")
            logger.info(f"Started pipe-pane for {session_name}:{window_name}:{pane_id} to {file_path}")

        except Exception as e:
            logger.error(f"Failed to start pipe-pane for pane {pane_id}: {e}")
            raise

    def select_layout(self, session_name: str, window_name: str, layout: str) -> None:
        """Apply a tmux layout to a window.

        Args:
            session_name: Tmux session name
            window_name: Tmux window name
            layout: Layout name ('even-horizontal', 'even-vertical', 'main-horizontal',
                   'main-vertical', 'tiled') or custom layout string
        """
        try:
            session = self.server.sessions.get(session_name=session_name)
            if not session:
                raise ValueError(f"Session '{session_name}' not found")

            window = session.windows.get(window_name=window_name)
            if not window:
                raise ValueError(f"Window '{window_name}' not found in session '{session_name}'")

            window.cmd("select-layout", layout)
            logger.info(f"Applied layout '{layout}' to {session_name}:{window_name}")

        except Exception as e:
            logger.error(f"Failed to apply layout: {e}")
            raise

    def resize_pane(
        self,
        session_name: str,
        window_name: str,
        pane_id: str,
        height: Optional[int] = None,
        width: Optional[int] = None,
        percentage: Optional[int] = None,
    ) -> None:
        """Resize a specific pane.

        Args:
            session_name: Tmux session name
            window_name: Tmux window name
            pane_id: Pane ID to resize
            height: Absolute height in lines
            width: Absolute width in columns
            percentage: Resize to percentage of window
        """
        try:
            session = self.server.sessions.get(session_name=session_name)
            if not session:
                raise ValueError(f"Session '{session_name}' not found")

            window = session.windows.get(window_name=window_name)
            if not window:
                raise ValueError(f"Window '{window_name}' not found in session '{session_name}'")

            # Find the specific pane
            target_pane = None
            for pane in window.panes:
                if pane.pane_id == pane_id:
                    target_pane = pane
                    break

            if not target_pane:
                raise ValueError(f"Pane '{pane_id}' not found")

            args = []
            if height is not None:
                args.extend(["-y", str(height)])
            if width is not None:
                args.extend(["-x", str(width)])
            if percentage is not None:
                args.extend(["-p", str(percentage)])

            if args:
                target_pane.cmd("resize-pane", *args)
                logger.info(f"Resized pane {pane_id} with args: {args}")

        except Exception as e:
            logger.error(f"Failed to resize pane: {e}")
            raise


# Module-level singleton
tmux_client = TmuxClient()
