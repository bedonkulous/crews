"""Slack integration using Slack Bolt SDK with retry logic."""

import logging
import os
import re
import time
from typing import Callable, Optional

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from core.exceptions import SlackUnavailableError

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3

# Matches @role mentions like @developer, @architect, @dev_manager, etc.
_ROLE_MENTION_RE = re.compile(r"@([a-zA-Z_][a-zA-Z0-9_]*)")


class SlackIntegration:
    """Wraps Slack Bolt SDK for channel creation, messaging, and event listening."""

    def __init__(
        self,
        bot_token: Optional[str] = None,
        app_token: Optional[str] = None,
    ) -> None:
        self.bot_token = bot_token or os.environ.get("SLACK_BOT_TOKEN", "")
        self.app_token = app_token or os.environ.get("SLACK_APP_TOKEN", "")
        self.client = WebClient(token=self.bot_token)
        self._app: Optional[App] = None  # lazy — created only when start_listener() is called
        # Per-channel handlers registered via register_crew_handler()
        self._channel_handlers: dict[str, Callable] = {}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _with_retry(self, fn, *args, **kwargs):
        """Call *fn* with up to _MAX_RETRIES attempts, exponential backoff."""
        last_exc: Optional[Exception] = None
        for attempt in range(_MAX_RETRIES):
            try:
                return fn(*args, **kwargs)
            except SlackApiError as exc:
                last_exc = exc
                logger.warning(
                    "Slack API error on attempt %d/%d: %s",
                    attempt + 1,
                    _MAX_RETRIES,
                    exc,
                )
                if attempt < _MAX_RETRIES - 1:
                    sleep_secs = 2 ** attempt  # 0s, 2s, 4s  (attempt 0→0, 1→2, 2→4)
                    # attempt 0: 2^0 = 1 — but spec says 0, 2, 4
                    # Use: attempt * 2 to get 0, 2, 4
                    sleep_secs = attempt * 2
                    time.sleep(sleep_secs)
        raise SlackUnavailableError(
            f"Slack API unavailable after {_MAX_RETRIES} attempts"
        ) from last_exc

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_channel(self, name: str) -> str:
        """Create a Slack channel and return its channel ID.

        Args:
            name: The channel name (lowercase, no spaces).

        Returns:
            The Slack channel ID string.

        Raises:
            SlackUnavailableError: After 3 failed attempts.
        """
        response = self._with_retry(
            self.client.conversations_create, name=name
        )
        return response["channel"]["id"]

    def post_message(self, channel_id: str, text: str) -> None:
        """Post a text message to a Slack channel.

        Args:
            channel_id: The Slack channel ID.
            text: The message text.

        Raises:
            SlackUnavailableError: After 3 failed attempts.
        """
        self._with_retry(
            self.client.chat_postMessage, channel=channel_id, text=text
        )

    def register_crew_handler(self, channel_id: str, handler: Callable) -> None:
        """Register a per-channel handler for a specific crew.

        When a message arrives in *channel_id*, *handler* will be called instead
        of (or in addition to) the global crew_handler passed to start_listener().

        Args:
            channel_id: The Slack channel ID to bind this handler to.
            handler: Callable invoked as handler(channel_id, text) or
                     handler(channel_id, text, role=role_name) when a @role mention
                     is detected.
        """
        self._channel_handlers[channel_id] = handler

    def start_listener(
        self,
        crew_handler: Optional[Callable] = None,
        crew_configs: Optional[list] = None,
    ) -> None:
        """Start the Slack Bolt Socket Mode event loop.

        Routes incoming messages to the appropriate handler:
        1. If a per-channel handler is registered via register_crew_handler(), use it.
        2. Otherwise fall back to the global *crew_handler* if provided.

        If the message text contains a @role mention (e.g. @developer), the role
        name is extracted and passed as a keyword argument: handler(channel_id, text,
        role=role_name).

        The return value of the handler (if a non-None string) is posted back to the
        originating channel via post_message().

        Args:
            crew_handler: Optional global callable invoked with (channel_id, text)
                          or (channel_id, text, role=role_name) for each message
                          that has no per-channel handler registered.
            crew_configs: Optional list of CrewConfig objects used to look up crews
                          by channel_id. Currently used for logging/future routing.
        """

        if self._app is None:
            self._app = App(token=self.bot_token)

        # Capture references for use inside the closure
        _crew_handler = crew_handler
        _integration = self

        @self._app.message("")
        def handle_message(message, say):  # noqa: ANN001
            channel_id = message.get("channel", "")
            text = message.get("text", "")
            _integration.dispatch_message(channel_id, text, _crew_handler)

        handler = SocketModeHandler(self._app, self.app_token)
        handler.start()

    def dispatch_message(
        self,
        channel_id: str,
        text: str,
        crew_handler: Optional[Callable] = None,
    ) -> None:
        """Dispatch an incoming message to the appropriate handler.

        This method contains the core routing logic and is separated from the
        Bolt event loop so it can be tested independently.

        Args:
            channel_id: The Slack channel the message arrived in.
            text: The message text.
            crew_handler: Optional global fallback handler.
        """
        logger.info("Received message in channel %s: %s", channel_id, text)

        # Determine which handler to use (per-channel takes priority)
        handler = self._channel_handlers.get(channel_id) or crew_handler
        if handler is None:
            logger.debug("No handler registered for channel %s — ignoring", channel_id)
            return

        # Extract optional @role mention from the message text
        role_match = _ROLE_MENTION_RE.search(text)
        role_name = role_match.group(1) if role_match else None

        # Dispatch to handler
        if role_name is not None:
            result = handler(channel_id, text, role=role_name)
        else:
            result = handler(channel_id, text)

        # Post response back if the handler returned a non-None string
        if isinstance(result, str):
            self.post_message(channel_id, result)
