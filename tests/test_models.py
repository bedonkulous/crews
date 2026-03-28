"""Unit tests for AgentConfig and CrewConfig data models."""

import pytest
from core.models import AgentConfig, CrewConfig


# ---------------------------------------------------------------------------
# AgentConfig tests
# ---------------------------------------------------------------------------

def make_agent(**kwargs) -> AgentConfig:
    defaults = dict(
        role="developer",
        goal="Write clean code",
        backstory="Experienced software engineer",
        model="gpt-4o",
        allow_delegation=False,
    )
    defaults.update(kwargs)
    return AgentConfig(**defaults)


def test_agent_config_instantiation():
    agent = make_agent()
    assert agent.role == "developer"
    assert agent.goal == "Write clean code"
    assert agent.backstory == "Experienced software engineer"
    assert agent.model == "gpt-4o"
    assert agent.allow_delegation is False


def test_agent_config_to_dict():
    agent = make_agent(allow_delegation=True)
    d = agent.to_dict()
    assert d == {
        "role": "developer",
        "goal": "Write clean code",
        "backstory": "Experienced software engineer",
        "model": "gpt-4o",
        "allow_delegation": True,
    }


def test_agent_config_from_dict():
    data = {
        "role": "architect",
        "goal": "Design systems",
        "backstory": "Senior architect",
        "model": "gpt-4o-mini",
        "allow_delegation": False,
    }
    agent = AgentConfig.from_dict(data)
    assert agent.role == "architect"
    assert agent.goal == "Design systems"
    assert agent.model == "gpt-4o-mini"
    assert agent.allow_delegation is False


def test_agent_config_round_trip():
    original = make_agent(role="devops", allow_delegation=True)
    restored = AgentConfig.from_dict(original.to_dict())
    assert restored == original


def test_agent_config_from_dict_coerces_allow_delegation():
    # YAML may deserialize booleans as 0/1 integers
    data = {
        "role": "developer",
        "goal": "g",
        "backstory": "b",
        "model": "gpt-4o",
        "allow_delegation": 0,
    }
    agent = AgentConfig.from_dict(data)
    assert agent.allow_delegation is False


# ---------------------------------------------------------------------------
# CrewConfig tests
# ---------------------------------------------------------------------------

def make_crew(**kwargs) -> CrewConfig:
    agents = [
        make_agent(role="dev_manager", allow_delegation=True),
        make_agent(role="developer"),
        make_agent(role="product_manager"),
        make_agent(role="architect"),
        make_agent(role="security_engineer"),
        make_agent(role="devops"),
    ]
    defaults = dict(
        name="alpha",
        slack_channel_id="C12345",
        slack_channel_name="alpha",
        project_path="alpha",
        agents=agents,
        created_at="2024-01-01T00:00:00Z",
    )
    defaults.update(kwargs)
    return CrewConfig(**defaults)


def test_crew_config_instantiation():
    crew = make_crew()
    assert crew.name == "alpha"
    assert crew.slack_channel_id == "C12345"
    assert crew.slack_channel_name == "alpha"
    assert crew.project_path == "alpha"
    assert len(crew.agents) == 6
    assert crew.created_at == "2024-01-01T00:00:00Z"


def test_crew_config_to_dict_structure():
    crew = make_crew()
    d = crew.to_dict()
    assert d["name"] == "alpha"
    assert d["slack_channel_id"] == "C12345"
    assert d["slack_channel_name"] == "alpha"
    assert d["project_path"] == "alpha"
    assert d["created_at"] == "2024-01-01T00:00:00Z"
    assert isinstance(d["agents"], list)
    assert len(d["agents"]) == 6
    # Each agent entry should be a plain dict
    for agent_dict in d["agents"]:
        assert isinstance(agent_dict, dict)
        assert "role" in agent_dict


def test_crew_config_round_trip():
    original = make_crew()
    restored = CrewConfig.from_dict(original.to_dict())
    assert restored == original


def test_crew_config_round_trip_preserves_agents():
    original = make_crew()
    restored = CrewConfig.from_dict(original.to_dict())
    assert len(restored.agents) == len(original.agents)
    for orig_agent, rest_agent in zip(original.agents, restored.agents):
        assert orig_agent == rest_agent


def test_crew_config_from_dict_missing_key_raises():
    data = {
        "name": "beta",
        # slack_channel_id intentionally omitted
        "slack_channel_name": "beta",
        "project_path": "beta",
        "agents": [],
        "created_at": "2024-01-01T00:00:00Z",
    }
    with pytest.raises(KeyError):
        CrewConfig.from_dict(data)


def test_crew_config_empty_agents_round_trip():
    crew = make_crew(agents=[])
    restored = CrewConfig.from_dict(crew.to_dict())
    assert restored.agents == []
