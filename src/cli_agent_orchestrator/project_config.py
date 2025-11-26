"""Project-level configuration for CLI Agent Orchestrator.

Reads cao.config.json from the project directory to configure agents and teams.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from cli_agent_orchestrator.config import get_default_provider
from cli_agent_orchestrator.models.provider import ProviderType

logger = logging.getLogger(__name__)

# Project config file name
PROJECT_CONFIG_FILE = "cao.config.json"

# Valid providers
VALID_PROVIDERS = [p.value for p in ProviderType]


def find_project_config(start_dir: Optional[str] = None) -> Optional[Path]:
    """Find cao.config.json in the directory or parent directories.

    Args:
        start_dir: Directory to start searching from (default: current directory)

    Returns:
        Path to config file if found, None otherwise
    """
    if start_dir:
        current = Path(start_dir).resolve()
    else:
        current = Path.cwd()

    # Search up to root
    while current != current.parent:
        config_path = current / PROJECT_CONFIG_FILE
        if config_path.exists():
            return config_path
        current = current.parent

    # Check root
    config_path = current / PROJECT_CONFIG_FILE
    if config_path.exists():
        return config_path

    return None


def load_project_config(config_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Load project configuration from cao.config.json.

    Args:
        config_path: Path to config file (default: search from current directory)

    Returns:
        Configuration dict or None if not found
    """
    if config_path is None:
        config_path = find_project_config()

    if config_path is None or not config_path.exists():
        return None

    try:
        with open(config_path) as f:
            config = json.load(f)
            logger.info(f"Loaded project config from {config_path}")
            return config
    except Exception as e:
        logger.error(f"Failed to load project config: {e}")
        return None


def get_project_agents(cwd: Optional[str] = None) -> Optional[List[Dict[str, str]]]:
    """Get list of agents from project config.

    Args:
        cwd: Working directory to search for config

    Returns:
        List of agent configs [{"agent": "name", "provider": "provider"}] or None
    """
    config_path = find_project_config(cwd)
    config = load_project_config(config_path)

    if config is None:
        return None

    agents = config.get("agents", [])
    if not agents:
        return None

    # Normalize agent configs
    result = []
    default_provider = config.get("default_provider", get_default_provider())

    for agent in agents:
        if isinstance(agent, str):
            # Simple format: just agent name
            result.append({
                "agent": agent,
                "provider": default_provider,
            })
        elif isinstance(agent, dict):
            # Full format: {"agent": "name", "provider": "provider"}
            agent_name = agent.get("agent") or agent.get("name")
            provider = agent.get("provider", default_provider)

            if agent_name:
                # Validate provider
                if provider not in VALID_PROVIDERS:
                    logger.warning(
                        f"Invalid provider '{provider}' for agent '{agent_name}', using default"
                    )
                    provider = default_provider

                result.append({
                    "agent": agent_name,
                    "provider": provider,
                })

    return result if result else None


def create_default_config(path: Path, agents: Optional[List[Dict[str, str]]] = None) -> bool:
    """Create a default cao.config.json file.

    Args:
        path: Directory to create config in
        agents: Optional list of agents to include

    Returns:
        True if successful
    """
    if agents is None:
        agents = [
            {"agent": "code_supervisor", "provider": "claude_code"},
            {"agent": "frontend_developer", "provider": "claude_code"},
            {"agent": "backend_developer", "provider": "codex_cli"},
            {"agent": "reviewer", "provider": "claude_code"},
        ]

    config = {
        "$schema": "https://raw.githubusercontent.com/awslabs/cli-agent-orchestrator/main/cao.config.schema.json",
        "name": path.name,
        "agents": agents,
    }

    config_path = path / PROJECT_CONFIG_FILE
    try:
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Failed to create config: {e}")
        return False


def get_config_path_for_display(cwd: Optional[str] = None) -> Optional[str]:
    """Get config file path for display purposes."""
    config_path = find_project_config(cwd)
    return str(config_path) if config_path else None

