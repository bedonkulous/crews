"""CLI entry point for crewai-dev-teams using Typer."""

from __future__ import annotations

from typing import Optional

import typer
import yaml

from core.crew_factory import CrewFactory
from core.env_manager import ENVManager
from core.exceptions import (
    CrewAlreadyExistsError,
    CrewNotFoundError,
    MissingEnvVarError,
)
from core.git_manager import GitManager
from core.deployment_scaffold import DeploymentScaffold
from integrations.slack import SlackIntegration

# Required ENV vars for crew commands
CREW_REQUIRED_KEYS = ["SLACK_BOT_TOKEN", "SLACK_APP_TOKEN", "OPENAI_API_KEY"]

app = typer.Typer(help="crewai-dev-teams: manage AI-powered development crews.")
env_app = typer.Typer(help="Manage environment variables.")
project_app = typer.Typer(help="Manage crew projects.")

app.add_typer(env_app, name="env")
app.add_typer(project_app, name="project")


def _env_manager() -> ENVManager:
    return ENVManager()


# ---------------------------------------------------------------------------
# crew commands (top-level)
# ---------------------------------------------------------------------------

@app.command("create")
def crew_create(
    name: str = typer.Argument(..., help="Name of the crew to create."),
    model: Optional[str] = typer.Option(None, "--model", help="LLM model override for all agents."),
    slack_channel: Optional[str] = typer.Option(None, "--slack-channel", help="Slack channel name override."),
) -> None:
    """Create a new crew with smart defaults."""
    env = _env_manager()
    try:
        env.validate_required(CREW_REQUIRED_KEYS)
    except MissingEnvVarError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1)

    overrides: dict = {}
    if model:
        from core.agent_factory import ROLES
        for role in ROLES:
            overrides.setdefault(role, {})["model"] = model

    factory = CrewFactory()
    try:
        config = factory.create(name, overrides)
    except CrewAlreadyExistsError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1)

    typer.echo(f"Crew '{config.name}' created successfully.")
    typer.echo(f"  Slack channel: {config.slack_channel_name} ({config.slack_channel_id})")
    typer.echo(f"  Project path:  {config.project_path}")


@app.command("list")
def crew_list() -> None:
    """List all existing crews."""
    factory = CrewFactory()
    crews = factory.load_all()

    if not crews:
        typer.echo("No crews found.")
        return

    header = f"{'NAME':<20} {'SLACK CHANNEL':<25} {'CREATED AT':<25}"
    typer.echo(header)
    typer.echo("-" * len(header))
    for crew in crews:
        typer.echo(f"{crew.name:<20} {crew.slack_channel_name:<25} {crew.created_at:<25}")


@app.command("show")
def crew_show(
    name: str = typer.Argument(..., help="Name of the crew to show."),
) -> None:
    """Show the configuration for a named crew."""
    factory = CrewFactory()
    try:
        config = factory.load(name)
    except CrewNotFoundError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1)

    typer.echo(yaml.dump(config.to_dict(), default_flow_style=False, allow_unicode=True))


@app.command("start")
def crew_start(
    name: str = typer.Argument(..., help="Name of the crew to start the Slack listener for."),
) -> None:
    """Start the Slack listener for a crew (blocks until interrupted)."""
    env = _env_manager()
    try:
        env.validate_required(CREW_REQUIRED_KEYS)
    except MissingEnvVarError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1)

    factory = CrewFactory()
    try:
        config = factory.load(name)
    except CrewNotFoundError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1)

    typer.echo(f"Starting Slack listener for crew '{name}' (channel: {config.slack_channel_name})...")
    slack = SlackIntegration()
    slack.start_listener(crew_configs=[config])


# ---------------------------------------------------------------------------
# project subcommands
# ---------------------------------------------------------------------------

@project_app.command("init")
def project_init(
    name: str = typer.Argument(..., help="Name of the crew whose project to re-initialize."),
) -> None:
    """Re-run GitManager and DeploymentScaffold for an existing crew."""
    env = _env_manager()
    try:
        env.validate_required(CREW_REQUIRED_KEYS)
    except MissingEnvVarError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1)

    factory = CrewFactory()
    try:
        config = factory.load(name)
    except CrewNotFoundError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1)

    from pathlib import Path
    project_path = Path(config.project_path)
    GitManager().init_repo(project_path)
    DeploymentScaffold().generate(project_path, name)
    typer.echo(f"Project for crew '{name}' re-initialized at {project_path}.")


# ---------------------------------------------------------------------------
# env subcommands
# ---------------------------------------------------------------------------

@env_app.command("setup")
def env_setup() -> None:
    """Interactively set up all required environment variables."""
    _env_manager().setup_interactive()
    typer.echo("Environment setup complete.")


@env_app.command("set")
def env_set(
    key: str = typer.Argument(..., help="Environment variable name."),
    value: str = typer.Argument(..., help="Value to set."),
) -> None:
    """Set an environment variable in the .env file."""
    _env_manager().set(key, value)
    typer.echo(f"Set {key}.")


@env_app.command("get")
def env_get(
    key: str = typer.Argument(..., help="Environment variable name."),
) -> None:
    """Get the value of an environment variable."""
    value = _env_manager().get(key)
    if value is None:
        typer.echo(f"{key} is not set.", err=True)
        raise typer.Exit(1)
    typer.echo(value)


@env_app.command("list")
def env_list() -> None:
    """List all configured environment variable keys (no values)."""
    keys = _env_manager().list_keys()
    if not keys:
        typer.echo("No environment variables configured.")
        return
    for key in keys:
        typer.echo(key)


@env_app.command("delete")
def env_delete(
    key: str = typer.Argument(..., help="Environment variable name to delete."),
) -> None:
    """Delete an environment variable from the .env file."""
    _env_manager().delete(key)
    typer.echo(f"Deleted {key}.")


if __name__ == "__main__":
    app()
