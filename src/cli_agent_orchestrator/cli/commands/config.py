"""Config command for CLI Agent Orchestrator CLI."""

import click

from cli_agent_orchestrator.config import (
    get_config,
    get_config_path,
    get_default_provider,
    get_provider_for_agent,
    remove_provider_for_agent,
    set_default_provider,
    set_provider_for_agent,
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
    """Show current global configuration."""
    cfg = get_config()
    config_path = get_config_path()

    click.echo(f"\nGlobal config: {config_path}")
    click.echo("=" * 50)

    # Default provider
    click.echo(f"\n{click.style('Default Provider:', bold=True)}")
    click.echo(f"  {click.style(cfg.get('default_provider', 'q_cli'), fg='cyan')}")

    # Agent-specific providers
    agent_providers = cfg.get("agent_providers", {})
    click.echo(f"\n{click.style('Agent-Specific Providers:', bold=True)}")
    if agent_providers:
        for agent, provider in agent_providers.items():
            click.echo(f"  {agent}: {click.style(provider, fg='cyan')}")
    else:
        click.echo("  (none configured - all use default)")

    click.echo(f"\n{click.style('Note:', fg='bright_black')} Project teams are configured in cao.config.json")
    click.echo()


@config.command("set-provider")
@click.argument("provider", type=click.Choice(VALID_PROVIDERS))
@click.option("--agent", "-a", help="Set provider for specific agent only")
def set_provider(provider: str, agent: str):
    """Set the default provider (or provider for a specific agent).

    Examples:

        # Set global default provider
        cao config set-provider claude_code

        # Set provider for specific agent
        cao config set-provider claude_code --agent frontend_developer
        cao config set-provider codex_cli --agent backend_developer
    """
    try:
        if agent:
            set_provider_for_agent(agent, provider)
            click.echo(
                f"Provider for {click.style(agent, fg='cyan')} set to: "
                f"{click.style(provider, fg='green', bold=True)}"
            )
        else:
            set_default_provider(provider)
            click.echo(f"Default provider set to: {click.style(provider, fg='green', bold=True)}")
    except ValueError as e:
        raise click.ClickException(str(e))
    except Exception as e:
        raise click.ClickException(f"Failed to save config: {e}")


@config.command("get-provider")
@click.option("--agent", "-a", help="Get provider for specific agent")
def get_provider(agent: str):
    """Show the default provider (or provider for a specific agent)."""
    if agent:
        provider = get_provider_for_agent(agent)
        click.echo(f"Provider for {agent}: {click.style(provider, fg='cyan', bold=True)}")
    else:
        provider = get_default_provider()
        click.echo(f"Default provider: {click.style(provider, fg='cyan', bold=True)}")


@config.command("reset-agent")
@click.argument("agent")
def reset_agent_provider(agent: str):
    """Reset an agent to use the default provider.

    Example:
        cao config reset-agent frontend_developer
    """
    remove_provider_for_agent(agent)
    default = get_default_provider()
    click.echo(f"Agent '{agent}' reset to use default provider ({default})")

