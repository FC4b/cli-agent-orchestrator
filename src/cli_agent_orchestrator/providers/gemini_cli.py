"""Gemini CLI provider implementation.

Based on Google Gemini CLI documentation:
https://geminicli.com/docs/

Gemini CLI is a REPL (Read-Eval-Print Loop) environment for interacting with
Google's Gemini models. It supports:
- Interactive REPL mode
- File system tools (read_file, write_file)
- Shell tool (run_shell_command)
- Web fetch and search tools
- Memory and todo tools
- MCP server integration
- Custom themes and settings
"""

import logging
import re
from typing import Optional

from cli_agent_orchestrator.clients.tmux import tmux_client
from cli_agent_orchestrator.models.terminal import TerminalStatus
from cli_agent_orchestrator.providers.base import BaseProvider
from cli_agent_orchestrator.utils.terminal import wait_for_shell, wait_until_status

logger = logging.getLogger(__name__)

# Regex patterns for Gemini CLI output analysis
# NOTE: These patterns are preliminary and should be refined based on actual
# Gemini CLI terminal output once installed and tested.
ANSI_CODE_PATTERN = r"\x1b\[[0-9;]*m"
ESCAPE_SEQUENCE_PATTERN = r"\[[?0-9;]*[a-zA-Z]"
CONTROL_CHAR_PATTERN = r"[\x00-\x1f\x7f-\x9f]"

# Gemini CLI prompt pattern - typically shows a prompt indicator
# Common patterns include `>`, `❯`, or custom themed prompts
IDLE_PROMPT_PATTERN = r"[>❯]\s*$"
IDLE_PROMPT_PATTERN_LOG = r"[>❯]\s*"

# Processing indicator - Gemini shows progress during model inference
PROCESSING_PATTERN = r"[⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏●○◐◑◒◓⣾⣽⣻⢿⡿⣟⣯⣷]|thinking|Thinking|\.{3,}"

# Error indicators
ERROR_INDICATORS = [
    "Error:",
    "error:",
    "failed",
    "Failed",
    "Unable to",
    "Cannot",
    "API error",
]

# CLI installation instructions
GEMINI_CLI_INSTALL_INSTRUCTIONS = """Gemini CLI can be installed via npm:

    npm install -g @anthropic-ai/gemini-cli

Or using the official installer. For more information, visit:
https://geminicli.com/docs/"""


class GeminiCliProvider(BaseProvider):
    """Provider for Google Gemini CLI tool integration.

    Gemini CLI provides a REPL environment for working with Gemini models.
    It supports MCP servers for extended functionality and tool integration.
    """

    def __init__(
        self,
        terminal_id: str,
        session_name: str,
        window_name: str,
        agent_profile: Optional[str] = None,
    ):
        super().__init__(terminal_id, session_name, window_name)
        self._initialized = False
        self._agent_profile = agent_profile

    def get_cli_command(self) -> str:
        """Return the Gemini CLI command name."""
        return "gemini"

    def get_install_instructions(self) -> str:
        """Return Gemini CLI installation instructions."""
        return GEMINI_CLI_INSTALL_INSTRUCTIONS

    def initialize(self) -> bool:
        """Initialize Gemini CLI provider by starting gemini command.

        Gemini CLI starts in interactive REPL mode by default.
        Configuration can be done via settings and MCP server configuration.
        """
        # Validate CLI is installed before attempting to start
        self.validate_cli_installed()

        # Wait for shell to be ready first
        if not wait_for_shell(tmux_client, self.session_name, self.window_name, timeout=10.0):
            raise TimeoutError("Shell initialization timed out after 10 seconds")

        # Build command - Gemini CLI base command
        # Agent profiles can be configured via MCP servers
        command = "gemini"

        tmux_client.send_keys(self.session_name, self.window_name, command)

        if not wait_until_status(self, TerminalStatus.IDLE, timeout=30.0):
            raise TimeoutError("Gemini CLI initialization timed out after 30 seconds")

        self._initialized = True
        return True

    def get_status(self, tail_lines: Optional[int] = None) -> TerminalStatus:
        """Get Gemini CLI status by analyzing terminal output."""
        logger.debug(f"get_status: tail_lines={tail_lines}")
        output = tmux_client.get_history(self.session_name, self.window_name, tail_lines=tail_lines)

        if not output:
            return TerminalStatus.ERROR

        # Strip ANSI codes for pattern matching
        clean_output = re.sub(ANSI_CODE_PATTERN, "", output)

        # Check for error indicators
        if any(indicator.lower() in clean_output.lower() for indicator in ERROR_INDICATORS):
            # Only return ERROR if we also don't have an idle prompt
            if not re.search(IDLE_PROMPT_PATTERN, clean_output):
                return TerminalStatus.ERROR

        # Check for processing state (spinner or thinking indicators)
        if re.search(PROCESSING_PATTERN, clean_output, re.IGNORECASE):
            # If we see processing indicators without idle prompt, still processing
            if not re.search(IDLE_PROMPT_PATTERN, clean_output):
                return TerminalStatus.PROCESSING

        # Check for idle prompt
        has_idle_prompt = re.search(IDLE_PROMPT_PATTERN, clean_output)

        if not has_idle_prompt:
            return TerminalStatus.PROCESSING

        # Check for completed state (has response content + idle prompt)
        # Look for any substantial content before the prompt
        lines = clean_output.strip().split("\n")
        if len(lines) > 1:
            # Has content before the prompt line
            logger.debug("get_status: returning COMPLETED")
            return TerminalStatus.COMPLETED

        # Just idle prompt, no response
        return TerminalStatus.IDLE

    def extract_last_message_from_script(self, script_output: str) -> str:
        """Extract agent's final response message from Gemini output.

        Gemini output format is similar to other REPL-based CLI agents -
        content followed by an idle prompt.
        """
        # Strip ANSI codes for pattern matching
        clean_output = re.sub(ANSI_CODE_PATTERN, "", script_output)

        # Find the last idle prompt
        idle_prompts = list(re.finditer(IDLE_PROMPT_PATTERN, clean_output))

        if not idle_prompts:
            raise ValueError("Incomplete Gemini CLI response - no final prompt detected")

        # Get content before the last prompt
        end_pos = idle_prompts[-1].start()

        # Find the start of the response (after any previous prompt or command)
        lines = clean_output[:end_pos].strip().split("\n")

        # Filter out command lines and empty lines to get response
        response_lines = []
        skip_first = True  # Skip the initial command line
        for line in lines:
            stripped = line.strip()
            if skip_first and (stripped.startswith("gemini") or stripped.startswith("$")):
                skip_first = False
                continue
            if stripped:
                response_lines.append(stripped)
                skip_first = False

        if not response_lines:
            raise ValueError("Empty Gemini CLI response - no content found")

        final_answer = "\n".join(response_lines)

        # Clean up the message
        final_answer = re.sub(ANSI_CODE_PATTERN, "", final_answer)
        final_answer = re.sub(ESCAPE_SEQUENCE_PATTERN, "", final_answer)
        final_answer = re.sub(CONTROL_CHAR_PATTERN, "", final_answer)

        return final_answer.strip()

    def get_idle_pattern_for_log(self) -> str:
        """Return Gemini CLI IDLE prompt pattern for log files."""
        return IDLE_PROMPT_PATTERN_LOG

    def exit_cli(self) -> str:
        """Get the command to exit Gemini CLI.

        Gemini CLI can be exited with /exit command or Ctrl+C.
        """
        return "/exit"

    def cleanup(self) -> None:
        """Clean up Gemini CLI provider."""
        self._initialized = False

