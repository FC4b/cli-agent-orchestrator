"""Main CLI entry point for CLI Agent Orchestrator."""

import click

from cli_agent_orchestrator.cli.commands.config import config
from cli_agent_orchestrator.cli.commands.flow import flow
from cli_agent_orchestrator.cli.commands.init import init
from cli_agent_orchestrator.cli.commands.install import install
from cli_agent_orchestrator.cli.commands.launch import launch
from cli_agent_orchestrator.cli.commands.providers import providers
from cli_agent_orchestrator.cli.commands.shutdown import shutdown
from cli_agent_orchestrator.cli.commands.team import team

# Version info from pyproject.toml
__version__ = "0.1.2"


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(version=__version__, prog_name="cao")
def cli():
    """CLI Agent Orchestrator."""


# Register commands
cli.add_command(launch)
cli.add_command(init)
cli.add_command(install)
cli.add_command(shutdown)
cli.add_command(flow)
cli.add_command(providers)
cli.add_command(config)
cli.add_command(team)


if __name__ == "__main__":
    cli()
