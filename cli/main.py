"""CLI entry point for crewai-dev-teams using Typer."""

from __future__ import annotations

from typing import Optional

import typer
import yaml
from dotenv import load_dotenv

# Load .env into os.environ early so all components can read tokens
load_dotenv()

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
    typer.echo(f"  Channel ID: {config.slack_channel_id}")
    typer.echo(f"  Project dir: {config.project_path}")

    # Build file tools scoped to this crew's project directory
    from pathlib import Path
    from crewai import Agent as CrewAgent, Crew, Task as CrewTask, Process
    from core.tools import (
        FileWriterTool, FileReaderTool,
        SlackUpdateTool, StatusReportTool, ActivityLog,
        GitCommitTool, GitDiffTool, GitPushTool,
    )

    project_dir = Path(config.project_path)
    project_dir.mkdir(parents=True, exist_ok=True)

    file_writer = FileWriterTool(project_dir=project_dir)
    file_reader = FileReaderTool(project_dir=project_dir)
    file_tools = [file_writer, file_reader]

    # Git tools scoped to project directory
    git_commit = GitCommitTool(project_dir=project_dir)
    git_diff = GitDiffTool(project_dir=project_dir)
    git_push = GitPushTool(project_dir=project_dir)

    # Slack client for posting progress updates mid-run
    slack = SlackIntegration()
    channel_id = config.slack_channel_id

    # Shared activity log — all agents write to it, product_manager reads it
    activity_log = ActivityLog()

    agents_by_role: dict[str, CrewAgent] = {}
    for agent_cfg in config.agents:
        # Every agent gets a SlackUpdateTool to post progress
        update_tool = SlackUpdateTool(
            slack_integration=slack,
            channel_id=channel_id,
            agent_role=agent_cfg.role,
            activity_log=activity_log,
        )

        # Base tools: everyone can post updates
        tools = [update_tool]

        # developer, devops, architect also get file tools
        if agent_cfg.role in ("developer", "devops", "architect"):
            tools.extend(file_tools)

        # developer gets git commit tool
        if agent_cfg.role == "developer":
            tools.append(git_commit)

        # architect and security_engineer get git diff tool
        if agent_cfg.role in ("architect", "security_engineer"):
            tools.append(git_diff)

        # product_manager gets the status report tool
        if agent_cfg.role == "product_manager":
            tools.append(StatusReportTool(activity_log=activity_log))

        # Enhance backstories for better coordination
        backstory = agent_cfg.backstory
        if agent_cfg.role == "dev_manager":
            backstory = (
                f"{agent_cfg.backstory} "
                "You break requests into clear phases: planning, implementation, review. "
                "Delegate each phase to the right team member. "
                "After implementation, ALWAYS delegate a code review to the architect "
                "and/or security_engineer before pushing. Use git_diff to inspect changes "
                "yourself. Only use git_push after reviewers approve. "
                "After all work is done, produce a concise final summary listing "
                "what was accomplished and which files were created. "
                "Do NOT continue delegating once the request is fully addressed."
            )
            tools = [update_tool, git_push, git_diff]  # manager delegates + can push/review
        elif agent_cfg.role == "architect":
            backstory = (
                f"{agent_cfg.backstory} "
                "When asked to review code, use the git_diff tool to see what changed. "
                "Provide structured feedback: approve or request changes with specifics."
            )
        elif agent_cfg.role == "security_engineer":
            backstory = (
                f"{agent_cfg.backstory} "
                "When asked to review code, use the git_diff tool to inspect changes "
                "for security issues. Provide structured feedback: approve or flag concerns."
            )
        elif agent_cfg.role == "product_manager":
            backstory = (
                f"{agent_cfg.backstory} "
                "You track project progress and can provide status updates at any time. "
                "Use the status_report tool to see what all agents have done. "
                "Use the slack_update tool to post summaries to the channel."
            )

        # Tell all agents to post updates
        agent_instructions = (
            f"{backstory} "
            "IMPORTANT: Use the slack_update tool to post brief progress updates "
            "as you work — what you're starting, what you've completed, any issues."
        )

        crew_agent = CrewAgent(
            role=agent_cfg.role,
            goal=agent_cfg.goal,
            backstory=agent_instructions,
            llm=agent_cfg.model,
            allow_delegation=agent_cfg.allow_delegation,
            tools=tools,
        )
        agents_by_role[agent_cfg.role] = crew_agent

    all_agents = list(agents_by_role.values())
    manager = agents_by_role.get("dev_manager")
    # crewAI requires manager_agent NOT be in the agents list for hierarchical process
    worker_agents = [a for a in all_agents if a is not manager]

    def _post_update(msg: str) -> None:
        """Post a progress update to the crew's Slack channel."""
        try:
            slack.post_message(channel_id, msg)
        except Exception:
            print(f"[crew] Failed to post update: {msg}", flush=True)

    def _step_callback(step_output) -> None:
        """Called after each agent step — posts progress to Slack."""
        try:
            agent_role = getattr(step_output, "agent", "unknown")
            # step_output.output can be the raw text or a structured object
            raw = getattr(step_output, "output", None) or str(step_output)
            # Truncate long outputs for Slack
            preview = str(raw)[:300]
            _post_update(f"📋 *{agent_role}* completed a step:\n```{preview}```")
        except Exception as exc:
            print(f"[crew] step_callback error: {exc}", flush=True)

    def _task_callback(task_output) -> None:
        """Called when a task finishes — posts summary to Slack."""
        try:
            raw = getattr(task_output, "raw", None) or str(task_output)
            preview = str(raw)[:500]
            _post_update(f"✅ Task completed:\n```{preview}```")
        except Exception as exc:
            print(f"[crew] task_callback error: {exc}", flush=True)

    def crew_handler(channel_id: str, text: str, role: str | None = None) -> str | None:
        """Handle a Slack message by kicking off the crewAI crew."""
        print(f"[crew] Processing: {text[:80]}...", flush=True)
        _post_update(f"🚀 Starting work on: _{text[:200]}_")

        if role and role != "dev_manager":
            # Direct message to a specific agent — single task, sequential
            agent = agents_by_role.get(role, manager)
            _post_update(f"🎯 Routing to *{role}*...")
            task = CrewTask(
                description=text,
                expected_output="A helpful response. Write any code to files using the file_writer tool.",
                agent=agent,
            )
            crew = Crew(
                agents=[agent],
                tasks=[task],
                verbose=True,
                step_callback=_step_callback,
                task_callback=_task_callback,
            )
        else:
            # No specific role or dev_manager — use hierarchical process
            _post_update("👔 *dev_manager* is coordinating the team...")
            task = CrewTask(
                description=text,
                expected_output=(
                    "Coordinate the team to complete this request. "
                    "Write all code and config files using the file_writer tool. "
                    "When finished, produce a final summary listing: "
                    "1) What was accomplished, 2) Which files were created, "
                    "3) How to run/use the result. Then stop."
                ),
            )
            crew = Crew(
                agents=worker_agents,
                tasks=[task],
                process=Process.hierarchical,
                manager_agent=manager,
                verbose=True,
                step_callback=_step_callback,
                task_callback=_task_callback,
            )

        try:
            result = crew.kickoff()
            final = str(result)
            _post_update(f"🏁 *Done!* Final summary:\n{final[:1500]}")
            return None  # Already posted to Slack via callback
        except Exception as exc:
            print(f"[crew] Error: {exc}", flush=True)
            return f"Error processing request: {exc}"

    slack.register_crew_handler(config.slack_channel_id, crew_handler)
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
