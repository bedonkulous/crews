"""Root conftest.py — ensures the project root is on sys.path for all tests.

Heavy optional dependencies (crewai, slack-bolt, typer) are stubbed out here
so the test suite can run in environments that only have the lightweight
dependencies installed (flask, python-dotenv, pyyaml, pytest).
"""

from __future__ import annotations

import sys
import types
import unittest.mock as _mock


def _stub_module(name: str, **attrs) -> types.ModuleType:
    """Register stub module (and all parent packages) in sys.modules."""
    parts = name.split(".")
    for i in range(1, len(parts) + 1):
        pkg = ".".join(parts[:i])
        if pkg not in sys.modules:
            sys.modules[pkg] = types.ModuleType(pkg)
    mod = sys.modules[name]
    for k, v in attrs.items():
        setattr(mod, k, v)
    return mod


# ---------------------------------------------------------------------------
# crewai stub — only Agent is used by core/agent_factory.py
# ---------------------------------------------------------------------------
class _FakeAgent:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


_stub_module("crewai", Agent=_FakeAgent)

# ---------------------------------------------------------------------------
# slack_bolt / slack_sdk stubs — used by integrations/slack.py
# ---------------------------------------------------------------------------
_stub_module("slack_bolt", App=_mock.MagicMock)
_stub_module("slack_bolt.adapter", SocketModeHandler=_mock.MagicMock)
_stub_module("slack_bolt.adapter.socket_mode", SocketModeHandler=_mock.MagicMock)
_stub_module("slack_sdk", WebClient=_mock.MagicMock)
_slack_sdk_errors = _stub_module("slack_sdk.errors")
_slack_sdk_errors.SlackApiError = Exception

# ---------------------------------------------------------------------------
# typer stub — used by cli/main.py and core/env_manager.py
# ---------------------------------------------------------------------------
_typer_mod = _stub_module("typer")
_typer_mod.prompt = _mock.MagicMock(return_value="")
_typer_mod.echo = _mock.MagicMock()
_typer_mod.Typer = _mock.MagicMock
_typer_mod.Argument = _mock.MagicMock
_typer_mod.Option = _mock.MagicMock
_typer_mod.Exit = SystemExit
