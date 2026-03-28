"""AgentFactory: builds crewAI Agent instances for each dev team role."""

from __future__ import annotations

from typing import Any

from crewai import Agent

from core.models import AgentConfig

ROLES = [
    "dev_manager",
    "developer",
    "product_manager",
    "architect",
    "security_engineer",
    "devops",
]

_DEFAULT_MODEL = "gpt-4o"

_DEFAULTS: dict[str, dict[str, Any]] = {
    "dev_manager": {
        "goal": "Orchestrate the team to deliver software on time and to spec",
        "backstory": (
            "You are an experienced engineering manager who excels at coordinating "
            "cross-functional teams, removing blockers, and ensuring timely delivery."
        ),
        "allow_delegation": True,
    },
    "developer": {
        "goal": "Write clean, tested, production-ready code",
        "backstory": (
            "You are a senior software engineer with deep expertise in multiple "
            "languages and frameworks, committed to code quality and test coverage."
        ),
        "allow_delegation": False,
    },
    "product_manager": {
        "goal": "Define requirements and prioritize the backlog",
        "backstory": (
            "You are a seasoned product manager who translates business needs into "
            "clear, actionable requirements and keeps the team focused on value."
        ),
        "allow_delegation": False,
    },
    "architect": {
        "goal": "Design scalable, maintainable system architecture",
        "backstory": (
            "You are a principal architect with broad experience designing distributed "
            "systems, selecting appropriate technologies, and enforcing best practices."
        ),
        "allow_delegation": False,
    },
    "security_engineer": {
        "goal": "Identify and remediate security vulnerabilities",
        "backstory": (
            "You are a security engineer specializing in threat modeling, secure "
            "coding practices, and vulnerability assessment across the full stack."
        ),
        "allow_delegation": False,
    },
    "devops": {
        "goal": "Provision infrastructure and maintain deployment pipelines",
        "backstory": (
            "You are a DevOps engineer skilled in cloud infrastructure, CI/CD "
            "pipelines, and site reliability engineering."
        ),
        "allow_delegation": False,
    },
}


class AgentFactory:
    """Builds crewAI Agent instances for all six dev team roles."""

    def default_config(self, role: str) -> AgentConfig:
        """Return an AgentConfig populated with defaults for the given role."""
        if role not in _DEFAULTS:
            raise ValueError(f"Unknown role: {role!r}. Must be one of {ROLES}")
        d = _DEFAULTS[role]
        return AgentConfig(
            role=role,
            goal=d["goal"],
            backstory=d["backstory"],
            model=_DEFAULT_MODEL,
            allow_delegation=d["allow_delegation"],
        )

    def build_agents(self, overrides: dict[str, Any] | None = None) -> list[Agent]:
        """Return a list of six crewAI Agent instances, applying any overrides.

        Args:
            overrides: Optional dict mapping role name to a dict of field overrides.
                       E.g. {"developer": {"model": "gpt-4-turbo"}}

        Returns:
            List of six crewAI Agent instances, one per role.
        """
        if overrides is None:
            overrides = {}

        agents: list[Agent] = []
        for role in ROLES:
            config = self.default_config(role)
            role_overrides = overrides.get(role, {})
            for key, value in role_overrides.items():
                if hasattr(config, key):
                    setattr(config, key, value)
            agents.append(
                Agent(
                    role=config.role,
                    goal=config.goal,
                    backstory=config.backstory,
                    llm=config.model,
                    allow_delegation=config.allow_delegation,
                )
            )
        return agents
