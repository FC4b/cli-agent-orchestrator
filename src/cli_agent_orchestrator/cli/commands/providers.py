"""Providers command for CLI Agent Orchestrator CLI."""

import click

from cli_agent_orchestrator.models.provider import ProviderType
from cli_agent_orchestrator.utils.cli_check import check_cli_available, get_cli_path


# Provider metadata: command name, description, install instructions
PROVIDER_INFO = {
    ProviderType.Q_CLI: {
        "command": "q",
        "description": "Amazon Q Developer CLI",
        "install": "brew install amazon-q",
        "docs": "https://docs.aws.amazon.com/amazonq/latest/qdeveloper-ug/command-line-getting-started-installing.html",
    },
    ProviderType.KIRO_CLI: {
        "command": "kiro-cli",
        "description": "Kiro CLI",
        "install": "npm install -g @anthropic-ai/kiro-cli",
        "docs": "https://kiro.dev/docs/cli",
    },
    ProviderType.CLAUDE_CODE: {
        "command": "claude",
        "description": "Claude Code CLI (Anthropic)",
        "install": "npm install -g @anthropic-ai/claude-code",
        "docs": "https://docs.anthropic.com/en/docs/claude-code",
    },
    ProviderType.CODEX_CLI: {
        "command": "codex",
        "description": "Codex CLI (OpenAI)",
        "install": "npm install -g @openai/codex",
        "docs": "https://github.com/openai/codex",
    },
    ProviderType.GEMINI_CLI: {
        "command": "gemini",
        "description": "Gemini CLI (Google)",
        "install": "npm install -g @anthropic-ai/gemini-cli",
        "docs": "https://geminicli.com/docs/",
    },
}


@click.command()
@click.option("--verbose", "-v", is_flag=True, help="Show detailed information including paths")
def providers(verbose: bool):
    """List available CLI providers and their installation status.

    Shows which CLI tools are installed on the current machine and can be
    used as providers for CAO agent sessions.
    """
    click.echo("\n" + click.style("CLI Agent Orchestrator - Provider Status", bold=True))
    click.echo("=" * 50 + "\n")

    installed_count = 0
    total_count = len(PROVIDER_INFO)

    for provider_type, info in PROVIDER_INFO.items():
        command = info["command"]
        is_available = check_cli_available(command)

        if is_available:
            installed_count += 1
            status = click.style("✓ installed", fg="green")
            path_info = ""
            if verbose:
                path = get_cli_path(command)
                path_info = click.style(f" ({path})", fg="bright_black")
        else:
            status = click.style("✗ not found", fg="red")
            path_info = ""

        # Provider name and status
        provider_name = click.style(provider_type.value, fg="cyan", bold=True)
        click.echo(f"  {provider_name}")
        click.echo(f"    Command: {command} [{status}]{path_info}")
        click.echo(f"    {info['description']}")

        if verbose or not is_available:
            if not is_available:
                click.echo(f"    Install: {click.style(info['install'], fg='yellow')}")
            click.echo(f"    Docs: {info['docs']}")

        click.echo()

    # Summary
    click.echo("-" * 50)
    if installed_count == total_count:
        summary = click.style(f"All {total_count} providers available!", fg="green", bold=True)
    elif installed_count == 0:
        summary = click.style(
            f"No providers installed. Install at least one CLI tool to use CAO.",
            fg="red",
        )
    else:
        summary = f"{click.style(str(installed_count), fg='green', bold=True)} of {total_count} providers available"

    click.echo(f"  {summary}\n")

