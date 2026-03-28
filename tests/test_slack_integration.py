"""Unit tests for SlackIntegration — all Slack API calls are mocked."""

from unittest.mock import MagicMock, call, patch

import pytest
from slack_sdk.errors import SlackApiError

from core.exceptions import SlackUnavailableError
from integrations.slack import SlackIntegration


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_slack_api_error(message: str = "channel_not_found") -> SlackApiError:
    """Build a minimal SlackApiError for testing."""
    response = {"error": message, "headers": {}}
    return SlackApiError(message=message, response=response)


def _make_integration() -> SlackIntegration:
    """Return a SlackIntegration with dummy tokens (no real API calls)."""
    return SlackIntegration(bot_token="xoxb-test", app_token="xapp-test")


# ---------------------------------------------------------------------------
# create_channel
# ---------------------------------------------------------------------------

class TestCreateChannel:
    def test_returns_channel_id_on_success(self):
        """create_channel should return the channel ID from the API response."""
        integration = _make_integration()
        mock_response = {"channel": {"id": "C12345678"}}
        integration.client.conversations_create = MagicMock(return_value=mock_response)

        channel_id = integration.create_channel("my-crew")

        assert channel_id == "C12345678"
        integration.client.conversations_create.assert_called_once_with(name="my-crew")

    def test_passes_name_to_api(self):
        """create_channel should forward the channel name to conversations.create."""
        integration = _make_integration()
        integration.client.conversations_create = MagicMock(
            return_value={"channel": {"id": "CABC"}}
        )

        integration.create_channel("team-alpha")

        integration.client.conversations_create.assert_called_once_with(name="team-alpha")


# ---------------------------------------------------------------------------
# post_message
# ---------------------------------------------------------------------------

class TestPostMessage:
    def test_calls_chat_post_message(self):
        """post_message should call chat.postMessage with channel and text."""
        integration = _make_integration()
        integration.client.chat_postMessage = MagicMock(return_value={"ok": True})

        integration.post_message("C12345678", "Hello, crew!")

        integration.client.chat_postMessage.assert_called_once_with(
            channel="C12345678", text="Hello, crew!"
        )

    def test_post_message_no_return_value(self):
        """post_message should return None on success."""
        integration = _make_integration()
        integration.client.chat_postMessage = MagicMock(return_value={"ok": True})

        result = integration.post_message("C99", "hi")

        assert result is None


# ---------------------------------------------------------------------------
# Retry logic
# ---------------------------------------------------------------------------

class TestRetryLogic:
    def test_retries_on_slack_api_error_then_succeeds(self):
        """Should retry and succeed when API fails once then succeeds."""
        integration = _make_integration()
        error = _make_slack_api_error()
        success_response = {"channel": {"id": "C_RETRY"}}

        integration.client.conversations_create = MagicMock(
            side_effect=[error, success_response]
        )

        with patch("integrations.slack.time.sleep") as mock_sleep:
            channel_id = integration.create_channel("retry-crew")

        assert channel_id == "C_RETRY"
        assert integration.client.conversations_create.call_count == 2
        mock_sleep.assert_called_once_with(0)  # attempt 0 → sleep 0s

    def test_retries_twice_then_succeeds(self):
        """Should retry twice and succeed on the third attempt."""
        integration = _make_integration()
        error = _make_slack_api_error()
        success_response = {"channel": {"id": "C_THIRD"}}

        integration.client.conversations_create = MagicMock(
            side_effect=[error, error, success_response]
        )

        with patch("integrations.slack.time.sleep") as mock_sleep:
            channel_id = integration.create_channel("third-time")

        assert channel_id == "C_THIRD"
        assert integration.client.conversations_create.call_count == 3
        # Slept after attempt 0 (0s) and attempt 1 (2s)
        assert mock_sleep.call_args_list == [call(0), call(2)]

    def test_post_message_retries_on_failure_then_succeeds(self):
        """post_message should also retry on SlackApiError."""
        integration = _make_integration()
        error = _make_slack_api_error()

        integration.client.chat_postMessage = MagicMock(
            side_effect=[error, {"ok": True}]
        )

        with patch("integrations.slack.time.sleep"):
            integration.post_message("C1", "hello")

        assert integration.client.chat_postMessage.call_count == 2


# ---------------------------------------------------------------------------
# SlackUnavailableError after 3 failures
# ---------------------------------------------------------------------------

class TestSlackUnavailableError:
    def test_raises_after_three_failures_create_channel(self):
        """create_channel should raise SlackUnavailableError after 3 API failures."""
        integration = _make_integration()
        error = _make_slack_api_error()

        integration.client.conversations_create = MagicMock(
            side_effect=[error, error, error]
        )

        with patch("integrations.slack.time.sleep"):
            with pytest.raises(SlackUnavailableError):
                integration.create_channel("doomed-channel")

        assert integration.client.conversations_create.call_count == 3

    def test_raises_after_three_failures_post_message(self):
        """post_message should raise SlackUnavailableError after 3 API failures."""
        integration = _make_integration()
        error = _make_slack_api_error()

        integration.client.chat_postMessage = MagicMock(
            side_effect=[error, error, error]
        )

        with patch("integrations.slack.time.sleep"):
            with pytest.raises(SlackUnavailableError):
                integration.post_message("C1", "text")

        assert integration.client.chat_postMessage.call_count == 3

    def test_slack_unavailable_error_is_raised_not_slack_api_error(self):
        """The raised exception should be SlackUnavailableError, not SlackApiError."""
        integration = _make_integration()
        error = _make_slack_api_error("fatal_error")

        integration.client.conversations_create = MagicMock(
            side_effect=[error, error, error]
        )

        with patch("integrations.slack.time.sleep"):
            with pytest.raises(SlackUnavailableError) as exc_info:
                integration.create_channel("bad-channel")

        # Should NOT be a raw SlackApiError
        assert not isinstance(exc_info.value, SlackApiError)

    def test_exactly_three_attempts_made(self):
        """Exactly 3 attempts should be made before giving up."""
        integration = _make_integration()
        error = _make_slack_api_error()

        integration.client.conversations_create = MagicMock(side_effect=error)

        with patch("integrations.slack.time.sleep"):
            with pytest.raises(SlackUnavailableError):
                integration.create_channel("any")

        assert integration.client.conversations_create.call_count == 3
