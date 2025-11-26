"""Launch command for CLI Agent Orchestrator CLI."""

import os
import subprocess

import click
import requests

from cli_agent_orchestrator.constants import DEFAULT_PROVIDER, PROVIDERS, SERVER_HOST, SERVER_PORT


@click.command()
@click.option("--agents", required=True, help="Agent profile to launch")
@click.option("--session-name", help="Name of the session (default: auto-generated)")
@click.option("--headless", is_flag=True, help="Launch in detached mode")
@click.option(
    "--provider", default=DEFAULT_PROVIDER, help=f"Provider to use (default: {DEFAULT_PROVIDER})"
)
@click.option(
    "--cwd",
    "-C",
    type=click.Path(exists=True, file_okay=False, resolve_path=True),
    help="Working directory for the agent (default: current directory)",
)
def launch(agents, session_name, headless, provider, cwd):
    """Launch cao session with specified agent profile.

    The agent will start in the specified working directory (--cwd),
    making it ideal for working with VS Code workspaces or specific project folders.

    Examples:

        # Launch in current directory
        cao launch --agents developer

        # Launch in a specific project folder
        cao launch --agents developer --cwd /path/to/my-project

        # Launch in current VS Code workspace (from terminal)
        cao launch --agents developer --cwd .
    """
    try:
        # Validate provider
        if provider not in PROVIDERS:
            raise click.ClickException(
                f"Invalid provider '{provider}'. Available providers: {', '.join(PROVIDERS)}"
            )

        # Use current directory if cwd not specified
        working_dir = cwd if cwd else os.getcwd()

        # Call API to create session
        url = f"http://{SERVER_HOST}:{SERVER_PORT}/sessions"
        params = {
            "provider": provider,
            "agent_profile": agents,
            "cwd": working_dir,
        }
        if session_name:
            params["session_name"] = session_name

        response = requests.post(url, params=params)
        response.raise_for_status()

        terminal = response.json()

        click.echo(f"Session created: {terminal['session_name']}")
        click.echo(f"Terminal created: {terminal['name']}")
        click.echo(f"Working directory: {working_dir}")

        # Attach to tmux session unless headless
        if not headless:
            subprocess.run(["tmux", "attach-session", "-t", terminal["session_name"]])

    except requests.exceptions.RequestException as e:
        raise click.ClickException(f"Failed to connect to cao-server: {str(e)}")
    except Exception as e:
        raise click.ClickException(str(e))
