"""Shutdown command for CLI Agent Orchestrator."""

import os
import signal
import subprocess

import click

from cli_agent_orchestrator.constants import SERVER_HOST, SERVER_PORT
from cli_agent_orchestrator.services.session_service import delete_session, list_sessions


def stop_server() -> bool:
    """Stop the cao-server process.

    Returns:
        True if server was stopped, False if not running or failed.
    """
    try:
        # Find and kill process listening on the server port
        result = subprocess.run(
            ["lsof", "-ti", f":{SERVER_PORT}"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0 and result.stdout.strip():
            pids = result.stdout.strip().split("\n")
            for pid in pids:
                try:
                    os.kill(int(pid), signal.SIGTERM)
                except (ProcessLookupError, ValueError):
                    pass
            return True
        return False
    except Exception:
        return False


@click.command()
@click.option("--all", "shutdown_all", is_flag=True, help="Shutdown all cao sessions and stop server")
@click.option("--session", help="Shutdown specific session")
@click.option("--server", "stop_server_flag", is_flag=True, help="Also stop the cao-server")
def shutdown(shutdown_all, session, stop_server_flag):
    """Shutdown tmux sessions and cleanup terminal records.

    Examples:

        # Shutdown all sessions and stop server
        cao shutdown --all

        # Shutdown specific session
        cao shutdown --session cao-abc123

        # Only stop the server (keep sessions)
        cao shutdown --server
    """

    # If only --server flag, just stop the server
    if stop_server_flag and not shutdown_all and not session:
        if stop_server():
            click.echo(f"✓ Stopped cao-server (port {SERVER_PORT})")
        else:
            click.echo(f"cao-server not running or already stopped")
        return

    if not shutdown_all and not session:
        raise click.ClickException("Must specify --all, --session, or --server")

    if shutdown_all and session:
        raise click.ClickException("Cannot use --all and --session together")

    # Determine sessions to shutdown
    sessions_to_shutdown = []

    if shutdown_all:
        sessions = list_sessions()
        sessions_to_shutdown = [s["id"] for s in sessions]
    else:
        sessions_to_shutdown = [session]

    if not sessions_to_shutdown and not shutdown_all:
        click.echo("No cao sessions found to shutdown")
    else:
        # Shutdown each session
        for session_name in sessions_to_shutdown:
            try:
                delete_session(session_name)
                click.echo(f"✓ Shutdown session '{session_name}'")
            except Exception as e:
                click.echo(f"Error shutting down session '{session_name}': {e}", err=True)

        if not sessions_to_shutdown:
            click.echo("No cao sessions found to shutdown")

    # Stop server if --all or --server flag is set
    if shutdown_all or stop_server_flag:
        if stop_server():
            click.echo(f"✓ Stopped cao-server (port {SERVER_PORT})")
        else:
            click.echo(f"cao-server not running or already stopped")
