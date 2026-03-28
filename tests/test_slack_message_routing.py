"""Unit tests for Slack message routing in SlackIntegration.

Tests use dispatch_message() directly to avoid instantiating a real Slack Bolt App
(which would make a live auth.test API call). This tests the routing logic in isolation.

Covers:
- Message routed to correct handler by channel_id
- @role mention extracted and passed to handler
- Response posted back to channel
- Unknown channel_id is ignored (no error)
"""

from unittest.mock import MagicMock, patch

import pytest

from integrations.slack import SlackIntegration


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_integration() -> SlackIntegration:
    """Return a SlackIntegration with dummy tokens (no real API calls)."""
    return SlackIntegration(bot_token="xoxb-test", app_token="xapp-test")


# ---------------------------------------------------------------------------
# register_crew_handler
# ---------------------------------------------------------------------------

class TestRegisterCrewHandler:
    def test_registers_handler_for_channel(self):
        """register_crew_handler should store the handler keyed by channel_id."""
        integration = _make_integration()
        handler = MagicMock()

        integration.register_crew_handler("C123", handler)

        assert integration._channel_handlers["C123"] is handler

    def test_multiple_channels_registered_independently(self):
        """Each channel_id should map to its own handler."""
        integration = _make_integration()
        h1, h2 = MagicMock(), MagicMock()

        integration.register_crew_handler("C001", h1)
        integration.register_crew_handler("C002", h2)

        assert integration._channel_handlers["C001"] is h1
        assert integration._channel_handlers["C002"] is h2


# ---------------------------------------------------------------------------
# Message routing by channel_id
# ---------------------------------------------------------------------------

class TestMessageRoutingByChannel:
    def test_message_routed_to_registered_handler(self):
        """A message in a registered channel should call that channel's handler."""
        integration = _make_integration()
        handler = MagicMock(return_value=None)
        integration.register_crew_handler("C_CREW1", handler)

        integration.dispatch_message("C_CREW1", "hello world")

        handler.assert_called_once_with("C_CREW1", "hello world")

    def test_message_not_routed_to_wrong_channel_handler(self):
        """A message in channel A should not trigger channel B's handler."""
        integration = _make_integration()
        handler_a = MagicMock(return_value=None)
        handler_b = MagicMock(return_value=None)
        integration.register_crew_handler("C_A", handler_a)
        integration.register_crew_handler("C_B", handler_b)

        integration.dispatch_message("C_A", "ping")

        handler_a.assert_called_once()
        handler_b.assert_not_called()

    def test_unknown_channel_id_is_ignored(self):
        """A message in an unregistered channel with no global handler should not error."""
        integration = _make_integration()

        # No handlers registered, no global crew_handler — should silently do nothing
        integration.dispatch_message("C_UNKNOWN", "hello")  # must not raise

    def test_global_crew_handler_used_when_no_per_channel_handler(self):
        """Global crew_handler should be called for channels without a specific handler."""
        integration = _make_integration()
        global_handler = MagicMock(return_value=None)

        integration.dispatch_message("C_ANY", "task request", crew_handler=global_handler)

        global_handler.assert_called_once_with("C_ANY", "task request")

    def test_per_channel_handler_takes_priority_over_global(self):
        """Per-channel handler should be preferred over the global crew_handler."""
        integration = _make_integration()
        global_handler = MagicMock(return_value=None)
        specific_handler = MagicMock(return_value=None)
        integration.register_crew_handler("C_SPECIFIC", specific_handler)

        integration.dispatch_message("C_SPECIFIC", "hello", crew_handler=global_handler)

        specific_handler.assert_called_once()
        global_handler.assert_not_called()

    def test_no_handler_for_channel_does_not_call_global_for_other_channel(self):
        """Global handler should still be called for unregistered channels."""
        integration = _make_integration()
        global_handler = MagicMock(return_value=None)
        specific_handler = MagicMock(return_value=None)
        integration.register_crew_handler("C_SPECIFIC", specific_handler)

        # Message to a different channel — global handler should fire
        integration.dispatch_message("C_OTHER", "hello", crew_handler=global_handler)

        global_handler.assert_called_once_with("C_OTHER", "hello")
        specific_handler.assert_not_called()


# ---------------------------------------------------------------------------
# @role mention extraction
# ---------------------------------------------------------------------------

class TestRoleMentionExtraction:
    def test_role_mention_passed_as_keyword_arg(self):
        """@role mention in message text should be extracted and passed as role= kwarg."""
        integration = _make_integration()
        handler = MagicMock(return_value=None)
        integration.register_crew_handler("C1", handler)

        integration.dispatch_message("C1", "hey @developer please fix this bug")

        handler.assert_called_once_with("C1", "hey @developer please fix this bug", role="developer")

    def test_architect_role_mention(self):
        """@architect mention should be extracted correctly."""
        integration = _make_integration()
        handler = MagicMock(return_value=None)
        integration.register_crew_handler("C2", handler)

        integration.dispatch_message("C2", "@architect design the new service")

        handler.assert_called_once_with("C2", "@architect design the new service", role="architect")

    def test_no_role_mention_calls_handler_without_role(self):
        """Messages without @role should call handler with just (channel_id, text)."""
        integration = _make_integration()
        handler = MagicMock(return_value=None)
        integration.register_crew_handler("C3", handler)

        integration.dispatch_message("C3", "please deploy the app")

        handler.assert_called_once_with("C3", "please deploy the app")

    def test_first_role_mention_used_when_multiple_present(self):
        """When multiple @role mentions exist, the first one should be used."""
        integration = _make_integration()
        handler = MagicMock(return_value=None)
        integration.register_crew_handler("C4", handler)

        integration.dispatch_message("C4", "@developer and @architect should collaborate")

        # First match wins
        handler.assert_called_once_with(
            "C4", "@developer and @architect should collaborate", role="developer"
        )

    def test_dev_manager_role_mention(self):
        """@dev_manager (with underscore) should be extracted correctly."""
        integration = _make_integration()
        handler = MagicMock(return_value=None)
        integration.register_crew_handler("C5", handler)

        integration.dispatch_message("C5", "@dev_manager please review")

        handler.assert_called_once_with("C5", "@dev_manager please review", role="dev_manager")

    def test_security_engineer_role_mention(self):
        """@security_engineer mention should be extracted correctly."""
        integration = _make_integration()
        handler = MagicMock(return_value=None)
        integration.register_crew_handler("C6", handler)

        integration.dispatch_message("C6", "@security_engineer audit this code")

        handler.assert_called_once_with("C6", "@security_engineer audit this code", role="security_engineer")


# ---------------------------------------------------------------------------
# Response posted back to channel
# ---------------------------------------------------------------------------

class TestResponsePostedBack:
    def test_string_response_posted_back(self):
        """When handler returns a string, it should be posted back to the channel."""
        integration = _make_integration()
        integration.client.chat_postMessage = MagicMock(return_value={"ok": True})

        handler = MagicMock(return_value="Task complete!")
        integration.register_crew_handler("C_RESP", handler)

        integration.dispatch_message("C_RESP", "do something")

        integration.client.chat_postMessage.assert_called_once_with(
            channel="C_RESP", text="Task complete!"
        )

    def test_none_response_not_posted(self):
        """When handler returns None, post_message should NOT be called."""
        integration = _make_integration()
        integration.client.chat_postMessage = MagicMock(return_value={"ok": True})

        handler = MagicMock(return_value=None)
        integration.register_crew_handler("C_NONE", handler)

        integration.dispatch_message("C_NONE", "do something")

        integration.client.chat_postMessage.assert_not_called()

    def test_non_string_response_not_posted(self):
        """When handler returns a non-string (e.g. int), post_message should NOT be called."""
        integration = _make_integration()
        integration.client.chat_postMessage = MagicMock(return_value={"ok": True})

        handler = MagicMock(return_value=42)
        integration.register_crew_handler("C_INT", handler)

        integration.dispatch_message("C_INT", "do something")

        integration.client.chat_postMessage.assert_not_called()

    def test_global_handler_response_posted_back(self):
        """Global crew_handler string response should also be posted back."""
        integration = _make_integration()
        integration.client.chat_postMessage = MagicMock(return_value={"ok": True})

        global_handler = MagicMock(return_value="Global response")

        integration.dispatch_message("C_GLOBAL", "hello", crew_handler=global_handler)

        integration.client.chat_postMessage.assert_called_once_with(
            channel="C_GLOBAL", text="Global response"
        )

    def test_response_posted_to_correct_channel(self):
        """Response should be posted to the same channel the message came from."""
        integration = _make_integration()
        integration.client.chat_postMessage = MagicMock(return_value={"ok": True})

        handler = MagicMock(return_value="done")
        integration.register_crew_handler("C_TARGET", handler)

        integration.dispatch_message("C_TARGET", "run task")

        call_kwargs = integration.client.chat_postMessage.call_args
        assert call_kwargs.kwargs["channel"] == "C_TARGET"


# ---------------------------------------------------------------------------
# crew_configs parameter in start_listener
# ---------------------------------------------------------------------------

class TestCrewConfigsParameter:
    def test_start_listener_accepts_crew_configs(self):
        """start_listener should accept crew_configs without error (Bolt App mocked)."""
        from core.models import CrewConfig

        integration = _make_integration()

        cfg = CrewConfig(
            name="alpha",
            slack_channel_id="C_ALPHA",
            slack_channel_name="alpha",
            project_path="crew/alpha",
            agents=[],
            created_at="2024-01-01T00:00:00",
        )

        with patch("integrations.slack.App") as mock_app_cls, \
             patch("integrations.slack.SocketModeHandler") as mock_handler_cls:
            mock_app_instance = MagicMock()
            mock_app_cls.return_value = mock_app_instance
            mock_handler_cls.return_value.start = MagicMock()

            # Should not raise
            integration.start_listener(crew_configs=[cfg])

        mock_app_cls.assert_called_once_with(token="xoxb-test")
