"""Unit tests for AgentFactory."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from core.agent_factory import ROLES, AgentFactory
from core.models import AgentConfig


class TestROLES:
    def test_all_six_roles_present(self):
        expected = {
            "dev_manager",
            "developer",
            "product_manager",
            "architect",
            "security_engineer",
            "devops",
        }
        assert set(ROLES) == expected

    def test_roles_has_exactly_six_entries(self):
        assert len(ROLES) == 6

    def test_roles_are_unique(self):
        assert len(ROLES) == len(set(ROLES))


class TestDefaultConfig:
    def setup_method(self):
        self.factory = AgentFactory()

    def test_returns_agent_config_instance(self):
        config = self.factory.default_config("developer")
        assert isinstance(config, AgentConfig)

    def test_default_model_is_gpt4o(self):
        for role in ROLES:
            assert self.factory.default_config(role).model == "gpt-4o"

    def test_dev_manager_goal(self):
        config = self.factory.default_config("dev_manager")
        assert config.goal == "Orchestrate the team to deliver software on time and to spec"

    def test_dev_manager_allow_delegation_true(self):
        config = self.factory.default_config("dev_manager")
        assert config.allow_delegation is True

    def test_developer_goal(self):
        config = self.factory.default_config("developer")
        assert config.goal == "Write clean, tested, production-ready code"

    def test_developer_allow_delegation_false(self):
        config = self.factory.default_config("developer")
        assert config.allow_delegation is False

    def test_product_manager_goal(self):
        config = self.factory.default_config("product_manager")
        assert config.goal == "Define requirements and prioritize the backlog"

    def test_product_manager_allow_delegation_false(self):
        config = self.factory.default_config("product_manager")
        assert config.allow_delegation is False

    def test_architect_goal(self):
        config = self.factory.default_config("architect")
        assert config.goal == "Design scalable, maintainable system architecture"

    def test_architect_allow_delegation_false(self):
        config = self.factory.default_config("architect")
        assert config.allow_delegation is False

    def test_security_engineer_goal(self):
        config = self.factory.default_config("security_engineer")
        assert config.goal == "Identify and remediate security vulnerabilities"

    def test_security_engineer_allow_delegation_false(self):
        config = self.factory.default_config("security_engineer")
        assert config.allow_delegation is False

    def test_devops_goal(self):
        config = self.factory.default_config("devops")
        assert config.goal == "Provision infrastructure and maintain deployment pipelines"

    def test_devops_allow_delegation_false(self):
        config = self.factory.default_config("devops")
        assert config.allow_delegation is False

    def test_all_roles_have_non_empty_backstory(self):
        for role in ROLES:
            config = self.factory.default_config(role)
            assert config.backstory, f"Backstory for {role!r} should not be empty"

    def test_role_field_matches_requested_role(self):
        for role in ROLES:
            config = self.factory.default_config(role)
            assert config.role == role

    def test_unknown_role_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown role"):
            self.factory.default_config("unknown_role")


class TestBuildAgents:
    def setup_method(self):
        self.factory = AgentFactory()

    def test_returns_exactly_six_agents(self):
        mock_agent = MagicMock()
        with patch("core.agent_factory.Agent", return_value=mock_agent) as MockAgent:
            agents = self.factory.build_agents()
            assert len(agents) == 6
            assert MockAgent.call_count == 6

    def test_returns_six_agents_with_no_overrides(self):
        mock_agent = MagicMock()
        with patch("core.agent_factory.Agent", return_value=mock_agent):
            agents = self.factory.build_agents(None)
            assert len(agents) == 6

    def test_agents_created_with_correct_roles(self):
        created_roles = []

        def capture_agent(**kwargs):
            created_roles.append(kwargs["role"])
            return MagicMock()

        with patch("core.agent_factory.Agent", side_effect=capture_agent):
            self.factory.build_agents()

        assert created_roles == ROLES

    def test_override_goal_is_applied(self):
        captured_kwargs = []

        def capture_agent(**kwargs):
            captured_kwargs.append(kwargs)
            return MagicMock()

        overrides = {"developer": {"goal": "Write blazing fast Rust code"}}
        with patch("core.agent_factory.Agent", side_effect=capture_agent):
            self.factory.build_agents(overrides)

        dev_kwargs = next(k for k in captured_kwargs if k["role"] == "developer")
        assert dev_kwargs["goal"] == "Write blazing fast Rust code"

    def test_override_model_is_applied(self):
        captured_kwargs = []

        def capture_agent(**kwargs):
            captured_kwargs.append(kwargs)
            return MagicMock()

        overrides = {"architect": {"model": "gpt-4-turbo"}}
        with patch("core.agent_factory.Agent", side_effect=capture_agent):
            self.factory.build_agents(overrides)

        arch_kwargs = next(k for k in captured_kwargs if k["role"] == "architect")
        assert arch_kwargs["llm"] == "gpt-4-turbo"

    def test_non_overridden_roles_use_defaults(self):
        captured_kwargs = []

        def capture_agent(**kwargs):
            captured_kwargs.append(kwargs)
            return MagicMock()

        overrides = {"developer": {"goal": "Custom goal"}}
        with patch("core.agent_factory.Agent", side_effect=capture_agent):
            self.factory.build_agents(overrides)

        devops_kwargs = next(k for k in captured_kwargs if k["role"] == "devops")
        assert devops_kwargs["goal"] == "Provision infrastructure and maintain deployment pipelines"

    def test_empty_overrides_dict_uses_defaults(self):
        captured_kwargs = []

        def capture_agent(**kwargs):
            captured_kwargs.append(kwargs)
            return MagicMock()

        with patch("core.agent_factory.Agent", side_effect=capture_agent):
            self.factory.build_agents({})

        mgr_kwargs = next(k for k in captured_kwargs if k["role"] == "dev_manager")
        assert mgr_kwargs["allow_delegation"] is True
