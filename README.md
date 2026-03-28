# crewai-dev-teams

AI-powered software development teams you manage through Slack. Each "crew" is a team of six AI agents — dev manager, developer, product manager, architect, security engineer, and devops — built on [crewAI](https://github.com/joaomdmoura/crewAI) and connected to a dedicated Slack channel.

Send a message in Slack, and the dev manager coordinates the team to design, build, review, and deploy code. Output goes to the file system, not walls of code in chat.

## What You Get

- A CLI (`crew`) to create and manage AI dev teams
- Each crew gets its own Slack channel, git repo, and project directory
- Six specialized AI agents that collaborate via crewAI's hierarchical process
- Code and config files written to disk automatically
- AWS deployment scaffolding (CloudFormation + GitHub Actions) out of the box
- Environment variable management for secrets

## Quick Start

```bash
git clone <your-repo-url>
cd crew
bash setup.sh
source venv/bin/activate
crew env setup        # prompts for all required tokens
crew create my-team   # creates crew, Slack channel, git repo
crew start my-team    # starts listening for Slack messages
```

## Prerequisites

- Python 3.10+
- git
- A Slack workspace where you can install apps
- An OpenAI API key

## Slack App Setup

Go to [api.slack.com/apps](https://api.slack.com/apps) and create a new app (from scratch).

### 1. Enable Socket Mode

Settings → Socket Mode → toggle ON.

### 2. Create an App-Level Token

Basic Information → App-Level Tokens → Generate Token.

- Name it anything (e.g. `socket-token`)
- Add the scope: `connections:write`
- Copy the token — it starts with `xapp-`

This is your `SLACK_APP_TOKEN`.

### 3. Bot Token Scopes

OAuth & Permissions → Scopes → Bot Token Scopes. Add all of these:

| Scope | Purpose |
|---|---|
| `channels:manage` | Create Slack channels for new crews |
| `channels:read` | Read channel info |
| `channels:history` | Receive messages in public channels via Socket Mode |
| `chat:write` | Post messages and responses to channels |
| `app_mentions:read` | Receive @bot mention events |
| `groups:history` | Receive messages in private channels (optional) |

### 4. Event Subscriptions

Event Subscriptions → toggle ON → Subscribe to bot events. Add:

| Event | Purpose |
|---|---|
| `message.channels` | Receive messages in public channels |
| `message.groups` | Receive messages in private channels (optional) |
| `app_mention` | Receive @bot mentions |

### 5. Install the App

OAuth & Permissions → Install to Workspace. Authorize the requested permissions.

Copy the **Bot User OAuth Token** — it starts with `xoxb-`. This is your `SLACK_BOT_TOKEN`.

> Every time you change scopes or event subscriptions, Slack will ask you to reinstall. The bot token changes on reinstall — update it with `crew env set SLACK_BOT_TOKEN xoxb-new-token`.

## Environment Variables

Run `crew env setup` for an interactive prompt, or set them individually:

```bash
crew env set SLACK_BOT_TOKEN xoxb-your-bot-token
crew env set SLACK_APP_TOKEN xapp-your-app-token
crew env set OPENAI_API_KEY sk-your-openai-key
crew env set AWS_ACCESS_KEY_ID AKIA...
crew env set AWS_SECRET_ACCESS_KEY your-secret-key
crew env set AWS_DEFAULT_REGION us-east-1
```

These are stored in `.env` (gitignored). View keys with `crew env list` (values are never shown).

## CLI Reference

```
crew create <name>          Create a new crew with all six agents
  --model <model>           Override the LLM model for all agents (default: gpt-4o)
crew list                   List all crews
crew show <name>            Show a crew's full config (YAML)
crew start <name>           Start the Slack listener (blocks)
crew project init <name>    Re-scaffold git repo and deployment files

crew env setup              Interactive setup for all required env vars
crew env set <key> <value>  Set an env var
crew env get <key>          Get an env var value
crew env list               List all env var keys (no values)
crew env delete <key>       Delete an env var
```

## Talking to Your Crew

Once `crew start <name>` is running, go to the crew's Slack channel and send messages.

**Team coordination** (dev_manager orchestrates):
```
Build a Python Flask API for user authentication with JWT tokens
```

**Target a specific agent:**
```
@developer Write a function that validates email addresses
@architect Design a microservices architecture for an e-commerce platform
@product_manager Write user stories for a notification system
@security_engineer Review this auth flow for vulnerabilities
@devops Write a Dockerfile and docker-compose.yml for this project
@dev_manager Break this down into tasks: build a real-time chat app
```

The dev_manager posts progress updates as work happens. Code is written to `crew/<name>/` on disk — Slack gets summaries, not code dumps.

## Project Structure

```
crew/
├── cli/main.py                  # Typer CLI entry point
├── core/
│   ├── agent_factory.py         # Builds crewAI agents with defaults
│   ├── config_store.py          # YAML config persistence
│   ├── crew_factory.py          # Orchestrates crew creation
│   ├── deployment_scaffold.py   # GitHub Actions + CloudFormation stubs
│   ├── env_manager.py           # .env file management
│   ├── git_manager.py           # Git repo init and scaffolding
│   ├── models.py                # CrewConfig / AgentConfig dataclasses
│   ├── tools.py                 # FileWriterTool / FileReaderTool
│   └── exceptions.py            # Custom exceptions
├── integrations/slack.py        # Slack Bolt integration
├── tests/                       # pytest + hypothesis tests
├── crew/<name>/                 # Per-crew project directories
│   ├── crew.yaml                # Crew config
│   ├── .github/workflows/       # GitHub Actions deploy workflow
│   └── infra/cloudformation/    # CloudFormation stubs
├── setup.sh                     # Venv + dependency setup
├── requirements.txt
└── pyproject.toml
```

## Running Tests

```bash
source venv/bin/activate
pytest tests/ -v
```

## License

MIT
