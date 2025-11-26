"""User configuration for CLI Agent Orchestrator."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from cli_agent_orchestrator.models.provider import ProviderType

logger = logging.getLogger(__name__)

# Config file location
CONFIG_DIR = Path.home() / ".aws" / "cli-agent-orchestrator"
CONFIG_FILE = CONFIG_DIR / "config.json"

# Default configuration
DEFAULT_CONFIG: Dict[str, Any] = {
    "default_provider": ProviderType.Q_CLI.value,
    # Agent-specific provider overrides
    "agent_providers": {
        # Example: "frontend_developer": "claude_code"
    },
}


def _load_config() -> Dict[str, Any]:
    """Load configuration from file."""
    if not CONFIG_FILE.exists():
        return DEFAULT_CONFIG.copy()

    try:
        with open(CONFIG_FILE) as f:
            user_config = json.load(f)
            # Merge with defaults
            config = DEFAULT_CONFIG.copy()
            config.update(user_config)
            return config
    except Exception as e:
        logger.warning(f"Failed to load config file: {e}. Using defaults.")
        return DEFAULT_CONFIG.copy()


def _save_config(config: Dict[str, Any]) -> bool:
    """Save configuration to file."""
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Failed to save config file: {e}")
        return False


def get_default_provider() -> str:
    """Get the default provider from config."""
    config = _load_config()
    provider = config.get("default_provider", DEFAULT_CONFIG["default_provider"])

    # Validate provider
    valid_providers = [p.value for p in ProviderType]
    if provider not in valid_providers:
        logger.warning(f"Invalid provider '{provider}' in config. Using default.")
        return DEFAULT_CONFIG["default_provider"]

    return provider


def set_default_provider(provider: str) -> bool:
    """Set the default provider in config.

    Args:
        provider: Provider name (e.g., 'claude_code', 'codex_cli')

    Returns:
        True if successful, False otherwise
    """
    # Validate provider
    valid_providers = [p.value for p in ProviderType]
    if provider not in valid_providers:
        raise ValueError(f"Invalid provider '{provider}'. Valid options: {', '.join(valid_providers)}")

    config = _load_config()
    config["default_provider"] = provider
    return _save_config(config)


def get_config() -> Dict[str, Any]:
    """Get the full configuration."""
    return _load_config()


def get_config_path() -> Path:
    """Get the config file path."""
    return CONFIG_FILE


def get_provider_for_agent(agent_profile: str) -> str:
    """Get the provider for a specific agent (falls back to default).

    Args:
        agent_profile: Agent profile name (e.g., 'frontend_developer')

    Returns:
        Provider name for this agent
    """
    config = _load_config()
    agent_providers = config.get("agent_providers", {})

    # Check for agent-specific override
    if agent_profile in agent_providers:
        provider = agent_providers[agent_profile]
        valid_providers = [p.value for p in ProviderType]
        if provider in valid_providers:
            return provider

    # Fall back to default
    return get_default_provider()


def set_provider_for_agent(agent_profile: str, provider: str) -> bool:
    """Set the provider for a specific agent.

    Args:
        agent_profile: Agent profile name
        provider: Provider name

    Returns:
        True if successful
    """
    valid_providers = [p.value for p in ProviderType]
    if provider not in valid_providers:
        raise ValueError(f"Invalid provider '{provider}'. Valid: {', '.join(valid_providers)}")

    config = _load_config()
    if "agent_providers" not in config:
        config["agent_providers"] = {}

    config["agent_providers"][agent_profile] = provider
    return _save_config(config)


def remove_provider_for_agent(agent_profile: str) -> bool:
    """Remove agent-specific provider (will use default).

    Args:
        agent_profile: Agent profile name

    Returns:
        True if successful
    """
    config = _load_config()
    if "agent_providers" in config and agent_profile in config["agent_providers"]:
        del config["agent_providers"][agent_profile]
        return _save_config(config)
    return True

