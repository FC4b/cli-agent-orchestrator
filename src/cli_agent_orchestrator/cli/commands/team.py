"""Team command for CLI Agent Orchestrator CLI."""

import json
import os
import subprocess
from pathlib import Path

import click
import requests

from cli_agent_orchestrator.constants import PROVIDERS, SERVER_HOST, SERVER_PORT
from cli_agent_orchestrator.project_config import (
    PROJECT_CONFIG_FILE,
    create_default_config,
    find_project_config,
    get_config_path_for_display,
    get_project_agents,
)
from cli_agent_orchestrator.utils.workspace import (
    get_workspace_root,
    parse_workspace_file,
    write_workspace_context_file,
)


@click.group()
def team():
    """Manage and launch agent teams from cao.config.json."""
    pass


@team.command("init")
@click.option(
    "--cwd",
    "-C",
    type=click.Path(exists=True, file_okay=False, resolve_path=True),
    help="Directory to create config in (default: current directory)",
)
@click.option("--force", "-f", is_flag=True, help="Overwrite existing config")
def init_config(cwd: str, force: bool):
    """Create a cao.config.json file in the project directory.

    Example:

        cao team init
        cao team init --cwd /path/to/project
    """
    target_dir = Path(cwd) if cwd else Path.cwd()
    config_path = target_dir / PROJECT_CONFIG_FILE

    if config_path.exists() and not force:
        raise click.ClickException(
            f"Config already exists: {config_path}\nUse --force to overwrite."
        )

    if create_default_config(target_dir):
        click.echo(f"Created {click.style(str(config_path), fg='green')}")
        click.echo("\nEdit this file to configure your agent team.")
    else:
        raise click.ClickException("Failed to create config file")


@team.command("show")
@click.option(
    "--cwd",
    "-C",
    type=click.Path(exists=True, file_okay=False, resolve_path=True),
    help="Working directory (default: current directory)",
)
def show_config(cwd: str):
    """Show the current project's cao.config.json."""
    working_dir = cwd if cwd else os.getcwd()
    config_path = find_project_config(working_dir)

    if not config_path:
        raise click.ClickException(
            f"No {PROJECT_CONFIG_FILE} found.\n"
            f"Run 'cao team init' to create one."
        )

    click.echo(f"\nConfig: {click.style(str(config_path), fg='cyan')}")
    click.echo("-" * 50)

    agents = get_project_agents(working_dir)
    if agents:
        click.echo(f"\n{click.style('Agents:', bold=True)}")
        for agent in agents:
            click.echo(
                f"  - {agent['agent']} ({click.style(agent['provider'], fg='bright_black')})"
            )
    else:
        click.echo("\nNo agents configured.")

    click.echo()


@team.command("start")
@click.option(
    "--cwd",
    "-C",
    type=click.Path(exists=True, file_okay=False, resolve_path=True),
    help="Working directory (default: current directory)",
)
@click.option(
    "--workspace",
    "-W",
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    help="VS Code workspace file (.code-workspace) to use",
)
@click.option("--session-name", help="Name of the session (default: auto-generated)")
@click.option("--headless", is_flag=True, help="Launch in detached mode (don't attach)")
def start_team(cwd: str, workspace: str, session_name: str, headless: bool):
    """Start all agents defined in cao.config.json.

    Reads the cao.config.json from the project directory and launches
    all configured agents in a single tmux session.

    Supports VS Code workspace files (.code-workspace) for multi-folder projects.
    When using --workspace, agents will be aware of all folders in the workspace.

    Examples:

        # Start team from current directory's config
        cao team start

        # Start team from specific project
        cao team start --cwd /path/to/my-project

        # Start with VS Code workspace (multi-folder support)
        cao team start --workspace ./my-project.code-workspace

        # Start with custom session name
        cao team start --session-name my-feature
    """
    # Handle VS Code workspace file
    workspace_context_file = None
    if workspace:
        workspace_path = Path(workspace)
        try:
            workspace_data = parse_workspace_file(workspace_path)
            working_dir = str(get_workspace_root(workspace_path))

            # Create workspace context file for agents
            workspace_context_file = write_workspace_context_file(
                workspace_path, Path(working_dir)
            )

            click.echo(f"\n{click.style('Workspace:', bold=True)} {workspace_path}")
            click.echo(f"{click.style('Folders:', bold=True)}")
            for folder in workspace_data.folders:
                resolved = folder.resolve(workspace_path.parent)
                status = "✓" if resolved.exists() else "✗"
                click.echo(f"  {status} {folder.name or resolved.name} ({resolved})")
        except (FileNotFoundError, ValueError) as e:
            raise click.ClickException(str(e))
    else:
        working_dir = cwd if cwd else os.getcwd()

    config_path = get_config_path_for_display(working_dir)

    if not config_path:
        raise click.ClickException(
            f"No {PROJECT_CONFIG_FILE} found in {working_dir}\n"
            f"Run 'cao team init' to create one."
        )

    agents = get_project_agents(working_dir)
    if not agents:
        raise click.ClickException(
            f"No agents defined in {config_path}\n"
            f"Add agents to your config file."
        )

    click.echo(f"\n{click.style('Config:', bold=True)} {config_path}")
    click.echo(f"{click.style('Working directory:', bold=True)} {working_dir}")
    click.echo(f"{click.style('Agents:', bold=True)} {len(agents)}")
    click.echo("-" * 50)

    created_session = None
    terminals = []

    try:
        for i, agent_config in enumerate(agents):
            agent = agent_config["agent"]
            provider = agent_config["provider"]

            # Validate provider
            if provider not in PROVIDERS:
                raise click.ClickException(
                    f"Invalid provider '{provider}' for agent '{agent}'"
                )

            if i == 0:
                # First agent - create new session
                url = f"http://{SERVER_HOST}:{SERVER_PORT}/sessions"
                params = {
                    "provider": provider,
                    "agent_profile": agent,
                    "cwd": working_dir,
                }
                if session_name:
                    params["session_name"] = session_name

                response = requests.post(url, params=params)
                response.raise_for_status()
                terminal = response.json()
                created_session = terminal["session_name"]
                terminals.append(terminal)
                click.echo(
                    f"  ✓ {agent} ({provider}) - {click.style('session created', fg='green')}"
                )
            else:
                # Subsequent agents - add to existing session
                url = f"http://{SERVER_HOST}:{SERVER_PORT}/sessions/{created_session}/terminals"
                params = {
                    "provider": provider,
                    "agent_profile": agent,
                    "cwd": working_dir,
                }

                response = requests.post(url, params=params)
                response.raise_for_status()
                terminal = response.json()
                terminals.append(terminal)
                click.echo(f"  ✓ {agent} ({provider})")

        click.echo("-" * 50)
        click.echo(f"\n{click.style('Session:', fg='green', bold=True)} {created_session}")
        click.echo(f"{click.style('Terminals created:', fg='green')} {len(terminals)}")

        # Attach to tmux session unless headless
        if not headless:
            click.echo(f"\nAttaching to session... (use Ctrl+b, d to detach)\n")
            subprocess.run(["tmux", "attach-session", "-t", created_session])

    except requests.exceptions.RequestException as e:
        raise click.ClickException(f"Failed to connect to cao-server: {str(e)}")
    except Exception as e:
        raise click.ClickException(str(e))
