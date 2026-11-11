# 1. Platform Evaluation

## 1.1 Purpose

The brief asks to "reuse existing systems where appropriate". This document
scores the credible open-source options against the EHYC requirements and
records the build-vs-reuse decision. Facts were checked against vendor
documentation and changelogs in November 2026; re-verify versions and licences
at implementation time.

## 1.2 Must-have criteria (from the brief)

| Ref | Criterion |
|---|---|
| C1 | Runs self-hosted on one Linux server |
| C2 | Role-based access: Admin, General Manager, Executive (read-only to data) |
| C3 | MCP client; MCP servers configured **only** by the Administrator |
| C4 | Personal chats **and** projects with own files, instructions and memory |
| C5 | Project archive to a plain directory of files |
| C6 | Modern streaming UI with visible reasoning and live activity status |
| C7 | Ingestion from SharePoint and local folders |
| C8 | Scheduled agent tasks inside a project, posting to a feed |
| C9 | Ollama, local OpenAI-compatible and OpenRouter models |
| C10 | Admin maps low/medium/high tiers to models and thinking levels |
| C11 | Cost control and zero-data-retention (ZDR) enforcement |
| C12 | Licence permits a non-profit to deploy and rebrand modestly |

## 1.3 Candidates

### LibreChat (MIT)
- **Strengths:** Projects (since v0.8.7, redesigned in v0.8.8); agents with
  tools, sub-agents and human-in-the-loop approvals; MCP client with servers
  declared centrally in `librechat.yaml` (admin-controlled) plus OAuth for MCP;
  user memory with per-agent isolation; file search/RAG via its `rag_api`
  (pgvector); reasoning/"thinking" display; custom OpenAI-compatible endpoints
  (OpenRouter, Ollama, LiteLLM); LDAP/OIDC/local auth; role permissions;
  **Scheduled Chats** (v0.8.8, beta, off by default) with cron, time zones and
  project destinations. Active project with frequent releases.
- **Gaps for EHYC:** no SharePoint connector; no archive-to-files; no activity
  feed; scheduled chats are beta; no per-tier ZDR enforcement (solved by the
  gateway); MongoDB + Meilisearch footprint.
- **Fit:** 9/12 criteria natively, 3 via companion service.

### Open WebUI (BSD-3 + branding clause)
- **Strengths:** polished UI; first-class Ollama integration; native MCP
  (Streamable HTTP) reserved to admins; knowledge bases; folders; groups and
  permissions; pipelines/functions for extension.
- **Gaps:** projects are folders + knowledge, not a first-class object with its
  own memory and instructions; no official scheduled-task feature; licence
  forbids removing "Open WebUI" branding above 50 users/30 days without an
  enterprise licence (fine for 12 users, but a constraint for GA across clubs).
- **Fit:** strong runner-up; weaker on C4, C8, C12.

### AnythingLLM (MIT)
- **Strengths:** "Workspaces" map well to projects (own documents and system
  prompt); simple Docker deploy; built-in document collectors; MCP support;
  agent flows.
- **Gaps:** thinner multi-user role model; less polished streaming/reasoning
  UX; scheduling limited; smaller ecosystem for enterprise auth.
- **Fit:** good for a single-user desktop; weaker for a 12-user governed pilot.

### Onyx Community Edition (MIT core; Enterprise features separately licensed)
- **Strengths:** best-in-class connectors including **SharePoint** (certificate
  auth), indexing pipeline, hybrid search, agents.
- **Gaps:** permission sync is Enterprise-only; heavier stack (Vespa, multiple
  workers); chat/project UX is secondary to search; would be a second app.
- **Fit:** considered as the ingestion engine; rejected for the pilot because
  its footprint exceeds the value for one SharePoint site. Revisit if EHYC
  adds many sources (Google Drive, Confluence, email).

### LobeHub / LobeChat (Apache-2.0 based, with commercial terms)
- Attractive UI, MCP marketplace, knowledge base. Multi-user server mode and
  admin governance are less mature; licence has commercial conditions. Not
  selected.

### Dify (modified Apache-2.0)
- Strong workflow builder and scheduling, but it is an app-builder, not a
  members' chat client; licence restricts multi-tenant use and rebranding.
  Not selected.

### Build from scratch
- Full control, but re-implements thousands of hours of chat UX, auth, file
  handling and MCP plumbing. Not justified for 12 users.

## 1.4 Scoring

Scores 0–3 (3 = native and mature). Weighted total out of 100.

| Criterion (weight) | LibreChat | Open WebUI | AnythingLLM | Onyx CE | Build |
|---|---|---|---|---|---|
| C1 self-host (5) | 3 | 3 | 3 | 2 | 3 |
| C2 roles (8) | 2 | 3 | 1 | 2 | 3 |
| C3 admin MCP (10) | 3 | 3 | 2 | 2 | 2 |
| C4 projects (12) | 3 | 1 | 2 | 1 | 3 |
| C5 archive (4) | 0 | 0 | 0 | 0 | 3 |
| C6 UI/thinking (12) | 3 | 3 | 2 | 2 | 1 |
| C7 ingestion (8) | 1 | 1 | 2 | 3 | 1 |
| C8 scheduling/feed (10) | 2 | 0 | 1 | 1 | 2 |
| C9 model sources (8) | 3 | 3 | 3 | 2 | 2 |
| C10 tier mapping (6) | 2 | 1 | 1 | 1 | 3 |
| C11 cost/ZDR (10) | 1 | 1 | 1 | 1 | 2 |
| C12 licence (7) | 3 | 2 | 3 | 2 | 3 |
| **Weighted /100** | **76** | 60 | 59 | 54 | 74* |

\* "Build" scores high on paper but carries the highest delivery risk and cost.

Gaps that every option shares (C5, C7, C10, C11) are closed by two reusable
components that sit beside the chat app:

| Component | Licence | Closes |
|---|---|---|
| **LiteLLM Proxy** | MIT (core) | C10 tier aliases, C11 spend tracking, budgets, ZDR request parameters, fallbacks |
| **Harbourmaster Services** (new, small) | MIT (club-owned) | C5 archive, C7 SharePoint/local ingestion, C8 feed, C11 ZDR allow-list admin, network guard |

## 1.5 Decision

**Adopt LibreChat + LiteLLM Proxy + Harbourmaster Services.**

Rationale:
1. Highest native coverage of the hardest-to-build parts (chat UX, projects,
   agents, MCP, memory).
2. MIT licence allows the club, and later other clubs, to rebrand freely.
3. Each gap is an *additive* service talking to documented APIs, so LibreChat
   upgrades are not blocked by forks.

**Upgrade policy:** pin LibreChat to a tagged release; do not fork. Customise
only via `librechat.yaml`, environment variables, branding assets and the
public/agents APIs. Any unavoidable patch is maintained as a small, documented
overlay with an upstream issue reference.

**Fallback:** if LibreChat Scheduled Chats remains unsuitable (beta, missing
feed output), Harbourmaster Services runs the scheduler itself and invokes the
LibreChat Agents API (or LiteLLM directly with the project context). This is
specified in [04 §4.7](04-technical-specification.md#47-scheduler-and-feed).

**Exit strategy:** all durable data (chats, projects, memory, files, feed,
archives) is exportable to Markdown/JSON files; the gateway and MCP servers
are reusable with Open WebUI if the chat front end is ever replaced.
