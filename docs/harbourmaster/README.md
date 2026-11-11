# Harbourmaster — AI Assistant for Non-Profit Clubs

**Working name:** Harbourmaster
**Pilot customer:** Eagle Harbour Yacht Club (EHYC)
**Document status:** Draft v0.1 for review — 2026-11-11
**Audience:** EHYC executive, General Manager, Administrator, implementer

Harbourmaster is a self-hosted AI assistant that runs on a single Linux server
at the club. It gives the executive team, the General Manager and the
Administrator a modern chat interface with personal chats, projects (with their
own files, instructions and memory), read-only access to club data through MCP
integrations, document ingestion from SharePoint and local folders, and
scheduled agent tasks that post to a feed. It routes requests to local
(Ollama) or OpenRouter models through three cost tiers — **Flash**, **Standard**
and **Frontier** — and only uses providers that do not retain or train on
prompts.

## Document set

| # | Document | What it contains |
|---|---|---|
| 1 | [Platform evaluation](01-platform-evaluation.md) | Open-source agent/chat platforms assessed against the brief; build-vs-reuse decision |
| 2 | [Chat UI benchmark](02-chat-ui-benchmark.md) | Assessment of modern chat interfaces and the UX requirements derived from it |
| 3 | [Requirements](03-requirements.md) | Numbered functional and non-functional requirements (MUST/SHOULD/MAY) |
| 4 | [Technical specification](04-technical-specification.md) | Architecture, components, data model, configuration, APIs, network, deployment |
| 5 | [Pilot plan](05-pilot-plan.md) | Phases, acceptance tests, cost model, risks, open questions |

## Decision summary

1. **Reuse, don't rebuild.** Base the chat application on **LibreChat** (MIT
   licence): it already ships projects, agents, MCP clients, memory, file
   search (RAG), reasoning display, multi-provider support and (beta)
   scheduled chats. See [01](01-platform-evaluation.md).
2. **Put a model gateway in front of every LLM call.** **LiteLLM Proxy** (MIT)
   exposes the `flash` / `standard` / `frontier` aliases, enforces the
   zero-data-retention policy, tracks spend and applies budgets.
3. **Add one small companion service** ("Harbourmaster Services") for what
   neither product does well: SharePoint/local-folder ingestion, project
   archiving to plain files, the activity feed, the tier/ZDR admin screen and
   the network-exposure guard.
4. **Private by network design.** The web UI binds only to the LAN interface
   and the `tailscale0` interface. There is no public listener, no port
   forwarding and no public DNS record.
5. **Single Linux box.** Ubuntu Server 24.04 LTS (or Debian 13), Docker Compose,
   nightly encrypted backups. An optional GPU enables local models; without one
   the system runs entirely on OpenRouter ZDR endpoints.

## Conventions

- **MUST / SHOULD / MAY** follow RFC 2119.
- Requirement IDs are stable (`CHAT-012`, `MCP-004`, …). Do not renumber; retire
  instead.
- "Pilot" = EHYC deployment, 12 named users. "GA" = reusable for other clubs.
