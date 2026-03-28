"""Data models for crewai-dev-teams."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentConfig:
    """Configuration for a single crewAI agent."""

    role: str               # one of ROLES
    goal: str
    backstory: str
    model: str              # e.g. "gpt-4o"
    allow_delegation: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "goal": self.goal,
            "backstory": self.backstory,
            "model": self.model,
            "allow_delegation": self.allow_delegation,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AgentConfig:
        return cls(
            role=data["role"],
            goal=data["goal"],
            backstory=data["backstory"],
            model=data["model"],
            allow_delegation=bool(data["allow_delegation"]),
        )


@dataclass
class CrewConfig:
    """Configuration for a crewAI development team."""

    name: str
    slack_channel_id: str
    slack_channel_name: str
    project_path: str           # relative to crew/ root
    agents: list[AgentConfig]
    created_at: str             # ISO 8601

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "slack_channel_id": self.slack_channel_id,
            "slack_channel_name": self.slack_channel_name,
            "project_path": self.project_path,
            "agents": [a.to_dict() for a in self.agents],
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CrewConfig:
        return cls(
            name=data["name"],
            slack_channel_id=data["slack_channel_id"],
            slack_channel_name=data["slack_channel_name"],
            project_path=data["project_path"],
            agents=[AgentConfig.from_dict(a) for a in data["agents"]],
            created_at=data["created_at"],
        )
