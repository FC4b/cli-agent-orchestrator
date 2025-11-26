"""CLI availability validation utilities."""

import shutil
from typing import Optional


class CLINotFoundError(Exception):
    """Exception raised when a CLI tool is not found in PATH."""

    def __init__(self, command: str, install_instructions: str):
        self.command = command
        self.install_instructions = install_instructions
        super().__init__(
            f"CLI tool '{command}' not found in PATH.\n\n"
            f"Install instructions:\n{install_instructions}"
        )


def check_cli_available(command: str) -> bool:
    """Check if a CLI command is available in PATH.

    Args:
        command: The CLI command to check (e.g., 'claude', 'codex', 'gemini')

    Returns:
        bool: True if the command is found in PATH, False otherwise
    """
    return shutil.which(command) is not None


def get_cli_path(command: str) -> Optional[str]:
    """Get the full path to a CLI command if available.

    Args:
        command: The CLI command to find (e.g., 'claude', 'codex', 'gemini')

    Returns:
        Optional[str]: Full path to the command if found, None otherwise
    """
    return shutil.which(command)


def validate_cli_or_raise(command: str, install_instructions: str) -> None:
    """Validate that a CLI command is available, or raise a helpful error.

    Args:
        command: The CLI command to validate
        install_instructions: Human-readable installation instructions

    Raises:
        CLINotFoundError: If the CLI command is not found in PATH
    """
    if not check_cli_available(command):
        raise CLINotFoundError(command, install_instructions)

