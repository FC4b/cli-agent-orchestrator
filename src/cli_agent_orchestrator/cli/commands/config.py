"""Config command for CLI Agent Orchestrator CLI."""

import click

from cli_agent_orchestrator.config import (
    get_config,
    get_config_path,
    get_default_provider,
    set_default_provider,
)
from cli_agent_orchestrator.models.provider import ProviderType

# Valid providers list
VALID_PROVIDERS = [p.value for p in ProviderType]


@click.group()
def config():
    """Manage CAO configuration."""
    pass


@config.command("show")
def show_config():
    """Show current configuration."""
    cfg = get_config()
    config_path = get_config_path()

    click.echo(f"\nConfig file: {config_path}")
    click.echo("-" * 50)

    for key, value in cfg.items():
        click.echo(f"  {key}: {click.style(str(value), fg='cyan')}")

    click.echo()


@config.command("set-provider")
@click.argument("provider", type=click.Choice(VALID_PROVIDERS))
def set_provider(provider: str):
    """Set the default provider.

    PROVIDER is one of: q_cli, kiro_cli, claude_code, codex_cli, gemini_cli
    """
    try:
        set_default_provider(provider)
        click.echo(f"Default provider set to: {click.style(provider, fg='green', bold=True)}")
    except ValueError as e:
        raise click.ClickException(str(e))
    except Exception as e:
        raise click.ClickException(f"Failed to save config: {e}")


@config.command("get-provider")
def get_provider():
    """Show the current default provider."""
    provider = get_default_provider()
    click.echo(f"Default provider: {click.style(provider, fg='cyan', bold=True)}")

