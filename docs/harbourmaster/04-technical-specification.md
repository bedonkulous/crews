# 4. Technical Specification

This document specifies how the requirements in [03](03-requirements.md) are
met by **LibreChat + LiteLLM Proxy + Harbourmaster Services** on one Linux
server. Requirement IDs in brackets show traceability.

---

## 4.1 Architecture overview

```
                    Club LAN (192.168.x.0/24)          Tailnet (100.64.0.0/10)
                              │                                  │
                              ▼                                  ▼
 ┌──────────────────────────────────────────────────────────────────────────────┐
 │ Linux host (Ubuntu 24.04, LUKS, nftables default-deny)                        │
 │                                                                               │
 │  :443 on LAN IP ─┐                       ┌─ :443 on tailscale0 IP             │
 │                  ▼                       ▼                                    │
 │            ┌───────────────────────────────────┐   tailscaled (host)          │
 │            │ Caddy (reverse proxy, TLS, IP ACL)│                              │
 │            └──────┬──────────────┬─────────────┘                              │
 │      /            │              │ /hm/*                                      │
 │                   ▼              ▼                                            │
 │   ┌──────────────────┐   ┌──────────────────────────────┐   ┌──────────────┐  │
 │   │ LibreChat (UI+API)│   │ Harbourmaster Services (HM)  │   │ IdP (OIDC):  │  │
 │   │ chats, projects,  │   │  hm-web  : Feed, Archive,    │   │ Entra ID or  │  │
 │   │ agents, memory,   │   │            Admin extras      │   │ Pocket ID    │  │
 │   │ file search, MCP  │   │  hm-worker: ingestion, tasks,│   └──────────────┘  │
 │   │ client            │   │            archive, checks   │                     │
 │   └─┬───┬───┬───┬────┘   │  hm-mcp-proxy: MCP gateway   │                     │
 │     │   │   │   │        │  litellm hooks: ZDR, auto,   │                     │
 │     │   │   │   │        │            budgets, metadata │                     │
 │     │   │   │   │        └──┬──────────┬───────┬────────┘                     │
 │     │   │   │   └─ MCP ────────────────▶│ hm-mcp-proxy │──▶ MCP servers       │
 │     │   │   │               │          │ (role/tool    │    (containers or    │
 │     │   │   │               │          │  enforcement) │     remote HTTPS)    │
 │     │   │   ▼               ▼          └───────────────┘                      │
 │     │   │  ┌─────────────────────────┐                                        │
 │     │   │  │ LiteLLM Proxy (gateway) │──▶ OpenRouter (ZDR only) ── internet   │
 │     │   │  │ aliases: auto/flash/    │──▶ Ollama / local OpenAI-compatible   │
 │     │   │  │ standard/frontier       │                                        │
 │     │   │  └─────────────────────────┘                                        │
 │     │   ▼                                                                     │
 │     │  rag_api ──▶ Postgres+pgvector ◀── HM (collections index, HM tables,    │
 │     ▼                                         LiteLLM spend DB)               │
 │   MongoDB, Meilisearch, Redis                                                 │
 │                                                                               │
 │  /srv/harbourmaster/ingest/* (ro mounts, SMB)   /srv/harbourmaster/archive/*  │
 └──────────────────────────────────────────────────────────────────────────────┘
          │ outbound only: OpenRouter, Microsoft Graph, MCP endpoints, Tailscale, backups
```

### Responsibilities

| Component | Responsibility | Key requirements |
|---|---|---|
| **Caddy** | TLS termination, binding to LAN + tailnet IPs only, IP allow-list, security headers, routing `/` → LibreChat, `/hm` → HM | NET-001…006, SEC-004 |
| **LibreChat** | Chat UI, personal chats, projects, agents, memory, uploads/file search, streaming + reasoning display, MCP client | CHAT, UX, PROJ, MEM |
| **LiteLLM Proxy** | Single gateway for all LLM calls; tier aliases; fallbacks; spend tracking; budgets; custom hooks from HM | MODEL, COST, PRIV |
| **HM `litellm_hooks`** (Python module loaded by LiteLLM) | ZDR enforcement and request rewriting, `auto` routing, local-only enforcement, attribution metadata | PRIV-001…007, MODEL-020…023, PRIV-020 |
| **HM `hm-mcp-proxy`** | Aggregates admin-configured MCP servers; filters `tools/list` per role/project; rejects disallowed `tools/call`; audits; limits; exposes the **Club Library** search tool | MCP-010…024, ROLE-003, ING-021 |
| **HM `hm-worker`** | SharePoint/local ingestion, scheduler + task runner, feed writer, archiver, compliance/exposure checks, price refresh, notifications | ING, SCHED, FEED, ARCH, NET-007, PRIV-007, COST-007 |
| **HM `hm-web`** | Feed, Archive browser, admin pages not covered by LibreChat (MCP governance, tiers, budgets, sources, health) | FEED, ARCH-005, ADM |
| **IdP** | OIDC for LibreChat and HM (Entra ID if M365 tenant; otherwise self-hosted Pocket ID/Authelia with passkeys/TOTP) | AUTH |
| **Ollama** (optional, GPU) | Local Flash model, embeddings, OCR-assist | MODEL-001, ING-013 |
| **Postgres 16 + pgvector** | HM schema, collection vectors, LibreChat rag_api vectors, LiteLLM DB | — |
| **MongoDB, Meilisearch, Redis** | LibreChat persistence, search, cache/streams | — |

### Design principles
1. **Never fork LibreChat or LiteLLM.** Integrate through configuration, documented APIs, plugin hooks and MCP.
2. **Everything model-bound goes through LiteLLM; everything tool-bound goes through hm-mcp-proxy.** These two choke points enforce privacy, cost and read-only rules regardless of which UI feature issued the call.
3. **Files are the durable truth for archives.** Archives never depend on a database.

---

## 4.2 Integration assumptions to verify in Phase 0

LibreChat moves quickly. The spec depends on these behaviours; each has a
fallback so the pilot is not blocked.

| # | Assumption about the pinned LibreChat release | Verification | Fallback |
|---|---|---|---|
| A1 | Custom OpenAI-compatible endpoint can point at LiteLLM with a fixed model list (`auto`, `flash`, `standard`, `frontier`) and displays streamed `reasoning_content` as a thinking block | Spike: stream from LiteLLM → OpenRouter reasoning model | Normalise reasoning into the field LibreChat renders, inside the LiteLLM hook |
| A2 | Custom endpoint and MCP server configs support per-request header placeholders for user identity (e.g. `{{LIBRECHAT_USER_ID}}`, `{{LIBRECHAT_USER_EMAIL}}`) | Inspect headers received by LiteLLM and hm-mcp-proxy | Resolve user from LiteLLM virtual key per user (HM issues one key per user and writes it via LibreChat user-provided-key mechanism) |
| A3 | Projects (v0.8.8) hold chats + files; project instructions/memory either native or via a project **agent** (instructions, file_search, tools, isolated memory) | Create a project + agent, confirm isolation | Model each project as "project + dedicated agent"; HM provisions/updates the agent via the Agents API |
| A4 | MCP servers declared in `librechat.yaml` are admin-only; users can only toggle them | Log in as user, attempt to add MCP | Disable user MCP UI via `interface` config/permissions |
| A5 | Role permissions can disable agent creation/marketplace sharing for Executives where needed | Role config test | Accept; enforcement remains in hm-mcp-proxy |
| A6 | Conversations can be exported/imported as JSON (for archive/restore) | Export/import test | HM reads MongoDB via read-only user for archive; restore via import API |
| A7 | Interface allows custom navigation links (Feed, Archive) | Config test | Small, documented branding overlay adding two links |
| A8 | Scheduled Chats (beta) are not required | n/a | HM scheduler is primary (§4.7) |

Phase 0 deliverable: an **integration contract test suite** (pytest + Playwright) that runs on every LibreChat upgrade and verifies A1–A7.

---

## 4.3 Deployment

### 4.3.1 Host
- Ubuntu Server 24.04 LTS, LUKS2 full-disk encryption with TPM2 auto-unlock + recovery passphrase in the club safe [SEC-002].
- Packages: Docker Engine + Compose v2, tailscale, nftables, unattended-upgrades (security only), restic, smartmontools, ClamAV (container).
- Optional NVIDIA driver + NVIDIA Container Toolkit when a GPU is present.

### 4.3.2 Filesystem layout
```
/srv/harbourmaster/
├── compose.yaml
├── .env                         # non-secret settings (club name, TZ, hostnames, CIDRs)
├── secrets/                     # SOPS/age-encrypted; decrypted to tmpfs at start
├── config/
│   ├── librechat.yaml
│   ├── litellm.yaml
│   ├── Caddyfile
│   ├── hm.yaml                  # HM config (exportable, ADM-002)
│   └── branding/                # logo, favicon, colours
├── data/                        # container volumes
│   ├── mongo/  meili/  redis/  postgres/  librechat-uploads/  ollama/  hm-files/
├── ingest/                      # local folder sources (mounted read-only into hm-worker)
│   └── <source-name>/
├── archive/                     # ARCH root (plain files)
│   ├── projects/<yyyy>/...
│   └── chats/<user>/...
├── logs/
└── backups/                     # local restic repo (or mounted NAS/USB)
```

### 4.3.3 Containers (Compose)

| Service | Image (pin by digest) | Network | Exposes |
|---|---|---|---|
| caddy | caddy:2.x | `edge` + host binds on LAN IP and tailscale IP :443/:80 | 443 |
| librechat | ghcr.io/danny-avila/librechat:v0.8.x | `app` | 3080 (internal) |
| rag_api | ghcr.io/danny-avila/librechat-rag-api-dev-lite:<tag> | `app` | 8000 (internal) |
| mongodb | mongo:7 | `data` | — |
| meilisearch | getmeili/meilisearch:v1.x | `data` | — |
| redis | redis:7 | `data` | — |
| postgres | pgvector/pgvector:pg16 | `data` | — |
| litellm | ghcr.io/berriai/litellm:<stable tag> + mounted `hm/litellm_hooks` | `app`, `egress` | 4000 (internal) |
| hm-web | ghcr.io/<club>/harbourmaster:<ver> (`web`) | `app` | 8080 (internal) |
| hm-worker | same image (`worker`) | `app`, `egress`, `data` | — |
| hm-mcp-proxy | same image (`mcp-proxy`) | `app`, `mcp` | 8100 (internal) |
| mcp-* | per integration | `mcp` (+ `egress` only if it needs a remote API) | internal |
| ollama | ollama/ollama:<tag> (optional, GPU) | `app` | 11434 (internal) |
| clamav | clamav/clamav:stable | `app` | 3310 (internal) |
| pocket-id (if no Entra) | ghcr.io/pocket-id/pocket-id:<tag> | `app` | internal |

Rules: no service except Caddy publishes host ports [NET-002]; containers run as non-root with `read_only: true` where supported, `no-new-privileges`, dropped capabilities [SEC-003]; the `egress` network is the only one with outbound internet.

### 4.3.4 Install flow (`install.sh`) [HOST-004]
1. Preflight: OS version, LUKS active, disk/RAM, time sync, GPU detection.
2. Prompt/config: club name, time zone, LAN CIDR(s), LAN IP, hostname, IdP choice, OpenRouter key (stored via SOPS), Tailscale auth key (optional).
3. Install packages; configure nftables (§4.10); `tailscale up --ssh=false --advertise-tags=tag:harbourmaster`.
4. Render config templates; generate secrets (DB passwords, LiteLLM master key, HM signing keys).
5. `docker compose up -d`; run migrations; create Administrator; run self-tests (exposure check, ZDR check, model test prompt per tier, backup dry run).
6. Print onboarding summary (URLs for LAN and tailnet, CA certificate download link for LAN devices).

---

## 4.4 Identity and access

- **IdP:** OIDC provider shared by LibreChat and HM [AUTH-002/003]. Entra ID (if M365) with app assignment restricted to a security group `EHYC-Harbourmaster`; otherwise Pocket ID (passkeys) or Authelia (password + TOTP).
- **Role source of truth:** HM `users` table (synced on login from IdP group claims if available: `hm-admin`, `hm-gm`, `hm-exec`). HM pushes role to LibreChat (`ADMIN` for Administrator, `USER` + custom role for others) via LibreChat's admin/role API or config.
- **Request identity:**
  - LibreChat → LiteLLM: per-request headers `X-HM-User`, `X-HM-Conversation` (A2) + per-user LiteLLM virtual key fallback.
  - LibreChat → hm-mcp-proxy: header `X-HM-User` (A2) + shared secret `X-HM-Proxy-Key` so only LibreChat/HM can call the proxy.
  - HM task runner → LiteLLM/hm-mcp-proxy: service key + `X-HM-User: <task owner>` + `X-HM-Task-Run`.
- **Break-glass** [SEC-010]: HM endpoint `POST /hm/api/admin/break-glass` requiring two distinct approvals (Admin + GM) within 24 h; produces a time-limited read-only export of the specified user's chats; audited and user-notified.

---

## 4.5 Model gateway (LiteLLM) and tiers

### 4.5.1 LiteLLM configuration (excerpt)

```yaml
# config/litellm.yaml  — tier models are managed by HM through the LiteLLM admin API
# (store_model_in_db) so changes apply without restart [MODEL-012]
model_list:
  - model_name: flash
    litellm_params:
      model: openrouter/<vendor>/<flash-model>
      api_key: os.environ/OPENROUTER_API_KEY
      extra_body:
        provider: { zdr: true, data_collection: deny }     # PRIV-002(b)
        reasoning: { effort: minimal }                     # MODEL-013
    model_info: { hm_tier: flash, hm_zdr: openrouter }
  - model_name: flash
    litellm_params:                                        # same alias = load-balanced/fallback
      model: ollama_chat/<local-flash-model>
      api_base: http://ollama:11434
    model_info: { hm_tier: flash, hm_zdr: local, hm_local: true }
  - model_name: standard
    litellm_params:
      model: openrouter/<vendor>/<standard-model>
      api_key: os.environ/OPENROUTER_API_KEY
      extra_body:
        provider: { zdr: true, data_collection: deny }
        reasoning: { effort: medium }
    model_info: { hm_tier: standard, hm_zdr: openrouter }
  - model_name: frontier
    litellm_params:
      model: openrouter/<vendor>/<frontier-model>
      api_key: os.environ/OPENROUTER_API_KEY
      extra_body:
        provider: { zdr: true, data_collection: deny }
        reasoning: { effort: high }
    model_info: { hm_tier: frontier, hm_zdr: openrouter }
  - model_name: embed
    litellm_params: { model: ollama/<embedding-model>, api_base: http://ollama:11434 }

router_settings:
  fallbacks: [{ "frontier": ["standard"] }, { "standard": ["flash"] }]   # each target also ZDR
  timeout: 600
  num_retries: 1

litellm_settings:
  turn_off_message_logging: true        # PRIV-006: no prompt/completion content in logs
  callbacks: ["hm.litellm_hooks.HarbourmasterHook"]

general_settings:
  master_key: os.environ/LITELLM_MASTER_KEY
  database_url: os.environ/LITELLM_DATABASE_URL
  store_model_in_db: true
  store_prompts_in_spend_logs: false    # PRIV-006
```

Concrete model IDs are chosen at deployment from the live ZDR-eligible list (03 §12.4).

### 4.5.2 `HarbourmasterHook` (pre-call / post-call)

Pre-call, for every request:
1. **Identify** user, role, project, conversation/task (headers, virtual key metadata).
2. **Resolve `auto`** [MODEL-020]: call `flash` with a compact classifier prompt (request text truncated to 2k tokens, presence of attachments/tools, project default tier) returning `{tier, reason, confidence}`; apply admin rules (role tier restrictions, Frontier confidence threshold, cost estimate cap); rewrite `model`; add `x-hm-tier-reason` to response headers/metadata for the UI footer [MODEL-021].
3. **Local-only** [PRIV-020]: if project is "Local models only", restrict deployment selection to `hm_local: true`; if none healthy → raise `403 local_model_unavailable`.
4. **ZDR enforcement** [PRIV-001/002]: reject if the resolved deployment's `hm_zdr` ∉ {`local`, `openrouter`, `agreement:<ref>`}; for OpenRouter deployments force-merge `provider.zdr=true`, `provider.data_collection="deny"`, remove `plugins`/`web_search` options [PRIV-004]; verify the model is on the HM ZDR allow-list (refreshed by PRIV-007 job).
5. **Budget** [COST-002/003]: check org hard cap, user hard limit, task run cap (from `X-HM-Task-Run`); on user hard limit downgrade to `flash`/local or reject per policy; return a user-readable error.
6. **Context hygiene** [COST-006]: no-op by default (LibreChat summarises); for task runs HM pre-builds the context.

Post-call: write `usage_events` row (tokens incl. reasoning and cached, provider-reported cost, deployment actually used, latency, fallback flag) to HM DB [COST-001]; emit budget alerts [COST-004].

### 4.5.3 Tier management UI (hm-web, Admin) [MODEL-011…014]
- Table of tiers → primary model, thinking level, max output, temperature, context limit, fallbacks; per-role availability; Auto rules (default tier, escalation threshold, max auto cost).
- Model picker lists only ZDR-eligible models (OpenRouter `GET /api/v1/models` + endpoint ZDR data; local models from Ollama `/api/tags`), showing price per 1M input/output tokens, context length and reasoning support [COST-007, MODEL-013].
- "Test" runs a fixed prompt on the mapping and shows TTFT, total time, tokens, cost and whether reasoning was returned.
- Saving writes to LiteLLM via `/model/new|update|delete`, stores a versioned copy in `tier_config_versions` [MODEL-012].

### 4.5.4 Thinking-level translation [MODEL-013]

| HM level | OpenRouter (`reasoning`) | Ollama | Models without reasoning |
|---|---|---|---|
| off | omit / `{ exclude: true }` | `think: false` | — |
| minimal | `{ effort: "minimal" }` (if supported, else `low`) | `think: true` | ignored |
| low / medium / high | `{ effort: "<level>" }` | `think: true` (or model-specific level) | ignored |
| budget N | `{ max_tokens: N }` | n/a | ignored |

Reasoning returned by providers is passed through as `reasoning_content` in the stream so LibreChat renders the Thinking block [UX-010]; HM never synthesises reasoning text [UX-012].

---

## 4.6 MCP gateway (`hm-mcp-proxy`)

### 4.6.1 Topology
- LibreChat's `librechat.yaml` declares **one MCP server per integration**, each pointing at the proxy:
  `http://hm-mcp-proxy:8100/mcp/<integration-slug>` (Streamable HTTP). This keeps LibreChat's per-server UI (icons, toggles) while all traffic passes the proxy.
- The proxy connects upstream to the real MCP server over stdio (spawned container), Streamable HTTP or SSE [MCP-002].
- Adding an integration in hm-web writes the upstream config to HM DB and regenerates the `mcpServers` block in `librechat.yaml`; LibreChat is reloaded in a maintenance window or via its config-reload mechanism if available. (Tool enable/disable changes do **not** require reload — they are enforced live in the proxy.)

```yaml
# generated block in config/librechat.yaml
mcpServers:
  membership:
    type: streamable-http
    url: http://hm-mcp-proxy:8100/mcp/membership
    headers:
      X-HM-User: "{{LIBRECHAT_USER_ID}}"
      X-HM-Proxy-Key: "${HM_PROXY_KEY}"
    timeout: 30000
  club-library:
    type: streamable-http
    url: http://hm-mcp-proxy:8100/mcp/club-library
    headers:
      X-HM-User: "{{LIBRECHAT_USER_ID}}"
      X-HM-Proxy-Key: "${HM_PROXY_KEY}"
```

### 4.6.2 Enforcement logic
- `tools/list`: return only tools where `tool.enabled ∧ tool.classification ∈ allowed(role) ∧ integration.roles ∋ role` (and, when the request carries a project context, `project.integration_enabled`) [MCP-010…012, PROJ-030]. Executive allowed set = `{read}`.
- `tools/call`: re-check the same predicate (never trust the client's list) [ROLE-003]; validate arguments against the tool's JSON schema; apply rate limit, timeout and result-size cap (truncate with `…[truncated by Harbourmaster: 50 kB limit]`) [MCP-006]; for `requires_approval` tools, require the LibreChat approval flow (or deny if unavailable) [MCP-015].
- Results are wrapped with provenance metadata and returned as tool output (never merged into system instructions) [MCP-022, SEC-020].
- Audit row per call [MCP-021]; argument fields marked sensitive are hashed.
- Health: periodic `initialize`/`ping` per upstream; status exposed to hm-web and as a degraded notice through a synthetic tool description suffix ("currently unavailable") [MCP-020].
- Tool-list drift: on upstream `tools/list` change, new tools are inserted as `enabled=false, classification=unknown` and the Administrator is notified [MCP-011].

### 4.6.3 Built-in HM MCP servers
| Server | Tools (all `read`) | Notes |
|---|---|---|
| `club-library` | `search(query, collections?, filters?, top_k≤10)`, `get_document(doc_id, section?)`, `list_collections()` | Hybrid search over HM collection index; returns chunks with citation metadata (title, URL/path, page) [ING-014, ING-016, ING-021] |
| `datasets` | `list_tables()`, `describe(table)`, `query(sql)` | DuckDB over admin-registered CSV/XLSX snapshots; `SELECT`-only parser, 10 s timeout, 1,000-row cap [ING-017, MCP-013] |

### 4.6.4 SQL integrations guidance [MCP-013]
Create a dedicated DB role, e.g. `hm_readonly`, with `SELECT` on curated views only (`v_members_public`, `v_moorage_assignments`, `v_events`), `statement_timeout=10s`, `default_transaction_read_only=on`; never expose base tables containing payment data.

---

## 4.7 Scheduler and feed

### 4.7.1 Approach
HM runs its own scheduler (in `hm-worker`) because tasks need owner-scoped
permissions, per-run cost caps, feed output, retries and missed-run policy
[SCHED-004…010]. LibreChat Scheduled Chats (beta) is not used for the pilot (A8).

### 4.7.2 Execution pipeline
```
APScheduler (Postgres job store, club TZ)
   └─▶ enqueue run (task_runs: queued) ── concurrency gate (global=3, per-task=1) [SCHED-009]
         └─▶ Runner
              1. Load task, project instructions (current version), project memory (≤2k tokens),
                 previous run summary (for "only if changed") [SCHED-011]
              2. Build tool set = task.tools ∩ project.integrations ∩ allowed(owner.role)
              3. Retrieval: if enabled, call club-library + project files search with the task prompt
              4. Agent loop via LiteLLM (model = task.tier), tools via hm-mcp-proxy,
                 headers X-HM-User=<owner>, X-HM-Task-Run=<run_id>; max 12 tool steps
              5. Enforce cost cap & timeout each step [SCHED-006]
              6. Ask the model (same run, final step) to return structured output:
                 { post: bool, status: info|attention, title, summary, body_md, sources[],
                   memory_updates[] }
              7. Write feed item (if post), memory updates (if allowed) [MEM-012c],
                 optional project file [FEED-007]; store transcript [SCHED-005]
              8. Notifications [FEED-006]
         └─▶ on failure: retry with backoff (2 retries); then failure feed item [SCHED-007]
```

### 4.7.3 Task definition (YAML / API payload)
```yaml
name: Weekly financial snapshot
project_id: prj_01J...
owner: user_treasurer
schedule: { kind: weekly, days: [MON], time: "07:15", tz: America/Vancouver }  # or cron: "15 7 * * 1"
tier: standard
thinking: low
tools: [accounting.get_profit_and_loss, accounting.get_bank_balances, club-library.search]
use_project_files: true
collections: [finance-reports]
may_update_memory: false
post_policy: only_if_noteworthy      # always | only_if_noteworthy
outputs: [feed, file:reports/finance/{{date}}.md]
max_cost_usd: 0.50
timeout_s: 600
missed_run_policy: run_once_if_missed_within: 6h
prompt: |
  Summarise last week's financial position versus budget. Flag any expense line
  more than 10% over budget and any bank balance change over $5,000.
```

### 4.7.4 Feed UI (hm-web `/hm/feed`) [FEED-001…006]
- Card list: status colour, project chip, title, summary, relative time, unread dot; expand to body with citations; actions: mark read, pin, "Continue in chat" (calls LibreChat to create a conversation in the project seeded with the item body as context — A3/A6), "View run" (transcript, tools, cost).
- Unread count exposed at `GET /hm/api/feed/unread-count` and shown on the sidebar link (A7).
- Live updates via SSE `GET /hm/api/feed/stream`.

---

## 4.8 Archive format

Path: `${ARCHIVE_ROOT}/projects/<yyyy>/<project-slug>--<project-id>--<yyyymmdd-hhmm>/` [ARCH-002]

```
regatta-2027--prj_01J9X…--20261111-1530/
├── manifest.json            # schema version, app versions, archived_by, archived_at,
│                            # counts, sha256 of every file [ARCH-003]
├── README.md                # human summary: what the project was, members, dates, contents
├── project.json             # metadata: name, description, owner, members/roles, settings,
│                            # enabled integrations, tier defaults, sensitivity
├── instructions/
│   ├── current.md
│   └── history/2026-10-02T18-04-11Z--jdoe.md …
├── memory/
│   ├── memory.md            # human-readable list with source + timestamp
│   └── memory.json
├── files/                   # original uploaded binaries (original names, de-duplicated)
│   ├── Sailing Instructions v3.pdf
│   └── _index.json          # file id → name, uploader, uploaded_at, sha256, mime
├── chats/
│   ├── 2026-10-03--race-committee-roster--conv_…/
│   │   ├── chat.md          # rendered transcript incl. thinking (collapsed as <details>),
│   │   │                    # tool calls (name, args, truncated result), citations, footers
│   │   └── chat.json        # full-fidelity export incl. branches
│   └── …
├── feed/
│   ├── feed.md              # chronological digest
│   └── items/2026-11-04--weekly-entries-update--fi_….md
├── tasks/
│   ├── tasks.yaml           # definitions (disabled)
│   └── runs/2026-11-04T15-15--run_….json
└── audit.json               # audit events scoped to the project
```

Procedure [ARCH-004, ARCH-008]: lock project (read-only flag in HM; disable tasks) → export LibreChat data (API export, else read-only Mongo user — A6) and HM data → write to `.<name>.tmp/` → compute checksums → verify by re-reading → `rename()` to final name → mark project archived in HM, remove from LibreChat active views (delete LibreChat project/conversations only after verification and only if `ARCHIVE_PURGE_SOURCE=true`; default keeps them hidden/read-only) → feed system item "Archive completed" → audit.

Restore [ARCH-006]: validate manifest checksums → recreate project + agent → import chats (A6) → re-upload files (re-index) → restore instructions/memory → import tasks as disabled.

Personal chat archive [ARCH-010]: `${ARCHIVE_ROOT}/chats/<user-slug>/<yyyy>/<date>--<title-slug>--<conv-id>/{chat.md,chat.json,attachments/}`.

---

## 4.9 Ingestion pipeline

```
Source (SharePoint delta | local fs events + nightly rescan)
   └─▶ change list ─▶ fetch (Graph /drives/{id}/items/{id}/content | read-only mount)
        └─▶ ClamAV scan ─▶ parse (Docling; OCR via Tesseract/RapidOCR for scans)
             └─▶ normalise to Markdown with page/heading anchors
                  └─▶ chunk (heading-aware, ~800 tok, 100 overlap)
                       └─▶ embed (local `embed` via LiteLLM→Ollama) ─▶ pgvector + tsvector (BM25)
                            └─▶ documents/chunks tables (collection, source, URL, checksum, mtime)
Deletes/moves ─▶ tombstone + remove chunks.  Unchanged checksum ─▶ skip.
```

- **SharePoint auth** [ING-001]: Entra app registration `Harbourmaster-Ingest`, application permission `Sites.Selected`; the M365 admin grants `read` on specific sites via Graph `POST /sites/{site-id}/permissions`; certificate credential (private key in HM secrets). Delta tokens stored per drive [ING-003].
- **Local folders** [ING-004/005]: bind-mount `/srv/harbourmaster/ingest/<name>:/ingest/<name>:ro`; for SMB shares, mount on host via `cifs` with a read-only service account then bind-mount; watcher uses inotify (watchdog) with debounce 30 s.
- **Collections** map to sources with include/exclude globs [ING-020]; ACL per collection (roles, projects) enforced in `club-library` [ING-021].
- **Project uploads** stay in LibreChat's native file search (rag_api) [PROJ-010…013].
- Sync report rows in `ingestion_runs` [ING-015].

---

## 4.10 Network configuration

### 4.10.1 Caddy
```caddyfile
{
    admin off
    # no trusted_proxies: nothing sits in front of Caddy, so remote_ip is the TCP peer [NET-004]
}

# LAN listener
https://harbourmaster.ehyc.lan {
    bind {$LAN_IP}
    tls internal                       # Caddy local CA; root cert distributed to club devices
    @blocked not remote_ip {$LAN_CIDRS}
    respond @blocked 403
    import common
}

# Tailnet listener (cert obtained automatically from local tailscaled for *.ts.net)
https://harbourmaster.{$TAILNET}.ts.net {
    bind {$TAILSCALE_IP}
    @blocked not remote_ip 100.64.0.0/10 fd7a:115c:a1e0::/48
    respond @blocked 403
    import common
}

(common) {
    header {
        Strict-Transport-Security "max-age=31536000"
        X-Frame-Options DENY
        Referrer-Policy strict-origin-when-cross-origin
        X-Content-Type-Options nosniff
    }
    handle_path /hm/* { reverse_proxy hm-web:8080 }
    handle            { reverse_proxy librechat:3080 { flush_interval -1 } }   # SSE streaming
}
```
Caddy runs with `network_mode` that can bind host IPs (host network for the edge container, or explicit `ports: ["${LAN_IP}:443:443", "${TAILSCALE_IP}:443:443"]`).

### 4.10.2 nftables (excerpt) [NET-003]
```nft
table inet filter {
  chain input {
    type filter hook input priority 0; policy drop;
    ct state established,related accept
    iif lo accept
    ip saddr $LAN_CIDRS tcp dport { 80, 443 } accept
    iifname "tailscale0" ip saddr 100.64.0.0/10 tcp dport { 80, 443 } accept
    iifname "tailscale0" tcp dport 22 ip saddr $ADMIN_TAILNET_IPS accept
    udp dport 41641 accept            # Tailscale direct connections (outbound-initiated)
    icmp type echo-request limit rate 5/second accept
  }
}
```
Docker publishes ports by inserting its own rules; therefore ports are published **only** on specific IPs (never `0.0.0.0`) and the `DOCKER-USER` chain repeats the source CIDR restriction.

### 4.10.3 Tailscale [NET-005]
- Server tagged `tag:harbourmaster`; ACL: `{"action":"accept","src":["group:ehyc-exec","group:ehyc-admin"],"dst":["tag:harbourmaster:443"]}`; SSH only `group:ehyc-admin`.
- `tailscale serve`/`funnel` not used (Caddy terminates TLS); Funnel disabled in tailnet policy (`nodeAttrs` without `funnel`).
- MagicDNS + HTTPS certificates enabled in the tailnet.

### 4.10.4 Exposure self-check (hm-worker, hourly + at start) [NET-007]
1. Enumerate listening sockets (`/proc/net/tcp*` via host-mounted read-only `/proc` of PID 1 namespace, or a tiny host systemd timer that writes JSON to a shared file).
2. Fail if any listener on a non-loopback, non-LAN, non-tailscale address, or if any listener on `0.0.0.0`/`::` other than Tailscale's UDP.
3. Verify nftables ruleset hash matches the expected template.
4. Optional external probe: a monthly scheduled check from an outside host is **not** used (no public exposure to probe); instead verify the router has no port forwards (manual checklist item).
5. On failure: alert Administrator; if `EXPOSURE_FAILSAFE=stop`, stop Caddy.

---

## 4.11 Data model (HM Postgres schema, principal tables)

| Table | Key columns |
|---|---|
| `users` | id, idp_subject, email, display_name, role (`admin`/`gm`/`exec`), status, librechat_user_id, monthly_soft_usd, monthly_hard_usd, created_at |
| `projects` | id, librechat_project_id, librechat_agent_id, name, slug, owner_id, visibility (`private`/`shared`/`club`), sensitivity (`standard`/`local_only`), default_tier, default_thinking, state (`active`/`archived`/`deleted`), archive_path |
| `project_members` | project_id, user_id, role (`owner`/`editor`/`viewer`) |
| `project_instruction_versions` | id, project_id, body_md, author_id, created_at |
| `project_memory` | id, project_id, text, source_type (`chat`/`task`/`manual`), source_id, author_id/`auto`, status (`active`/`suggested`/`deleted`), created_at |
| `integrations` | id, slug, name, description, transport, upstream_url/command, secret_ref, roles[], timeout_ms, max_result_bytes, rate_limit, status, last_health_at |
| `integration_tools` | id, integration_id, name, schema_json, classification (`read`/`write`/`unknown`), enabled, requires_approval, granted_roles[], grant_expires_at |
| `project_integrations` | project_id, integration_id, enabled |
| `tool_calls` | id, ts, user_id, project_id, conversation_id, task_run_id, integration_id, tool, args_redacted_json, status, duration_ms, result_bytes |
| `tier_config_versions` | id, version, config_json, author_id, created_at, active |
| `zdr_allowlist` | model_id, provider_source (`openrouter`/`local`/`agreement`), endpoint_info, verified_at, agreement_ref |
| `usage_events` | id, ts, user_id, project_id, conversation_id, task_run_id, tier, requested_model, used_model, provider, input_tokens, output_tokens, reasoning_tokens, cached_tokens, cost_usd, latency_ms, fallback, auto_reason |
| `budgets` | scope (`org`/`user`/`project`), scope_id, period, soft_usd, hard_usd, action_on_hard |
| `sources` | id, type (`sharepoint`/`local`), name, config_json (site/drive/paths/globs or mount path), schedule, secret_ref, status |
| `collections` | id, name, slug, description, roles[], club_library (bool) |
| `collection_sources` | collection_id, source_id, include_globs, exclude_globs |
| `documents` | id, collection_id, source_id, external_id, path, url, title, mime, author, modified_at, sha256, status, error |
| `chunks` | id, document_id, ordinal, text, heading_path, page, tsv (tsvector), embedding (vector) |
| `ingestion_runs` | id, source_id, started_at, finished_at, seen, added, updated, deleted, failed, report_json |
| `scheduled_tasks` | id, project_id, owner_id, name, definition_json, schedule_json, enabled, next_run_at |
| `task_runs` | id, task_id, scheduled_for, started_at, finished_at, status, tier, used_model, cost_usd, tokens_json, transcript_json, error |
| `feed_items` | id, project_id, task_run_id, kind (`task`/`system`), status, title, summary, body_md, sources_json, cost_usd, created_at, supersedes_id |
| `feed_reads` | feed_item_id, user_id, read_at, pinned |
| `archives` | id, project_id/conversation_id, path, manifest_sha256, created_by, created_at, restored_at |
| `audit_events` | id, ts, actor_id, action, target_type, target_id, details_json, ip — append-only (no UPDATE/DELETE grants; daily JSONL export) [SEC-030] |
| `settings` | key, value_json (branding, timeouts, thresholds, currency) |

---

## 4.12 HM API (internal, JSON over HTTPS, OIDC session or service key)

| Method & path | Purpose | Role |
|---|---|---|
| `GET /hm/api/me` | Current user, role, budget status | any |
| `GET/POST/PATCH /hm/api/projects[/{id}]` | Project metadata, members, sensitivity, integrations | per membership |
| `GET/PUT /hm/api/projects/{id}/instructions` (+ `/versions`) | Instructions & history | editor |
| `GET/POST/PATCH/DELETE /hm/api/projects/{id}/memory` | Project memory | viewer(read)/editor |
| `GET/POST/PATCH/DELETE /hm/api/projects/{id}/tasks[/{tid}]` | Scheduled tasks | editor |
| `POST /hm/api/tasks/{tid}/run` · `/pause` · `/resume` | Task control | editor |
| `GET /hm/api/tasks/{tid}/runs[/{rid}]` | Run history/transcript | viewer |
| `GET /hm/api/feed` · `/unread-count` · `/stream` (SSE) | Feed | any |
| `POST /hm/api/feed/{id}/read` · `/pin` · `/continue` | Feed actions | any |
| `POST /hm/api/projects/{id}/archive` · `/restore` | Archive/restore | owner/admin |
| `GET /hm/api/archive` · `/archive/{id}/…` | Browse archives | per original membership/admin |
| `GET /hm/api/usage` | Usage/cost (own; org for GM/Admin) | any/gm/admin |
| `…/admin/users` `…/admin/integrations` `…/admin/integrations/{id}/test` `…/admin/tools/{id}` | Administration | admin |
| `…/admin/tiers` `…/admin/tiers/test` `…/admin/zdr` `…/admin/budgets` | Models, ZDR, budgets | admin |
| `…/admin/sources` `…/admin/sources/{id}/sync` `…/admin/collections` | Ingestion | admin |
| `…/admin/health` `…/admin/audit` `…/admin/config/export|import` `…/admin/break-glass` | Operations | admin (+gm for break-glass) |

OpenAPI spec generated by FastAPI; all endpoints audited for mutations.

---

## 4.13 HM implementation stack
- Python 3.12, FastAPI, SQLAlchemy 2 + Alembic, Pydantic v2, APScheduler 3 (Postgres job store), `mcp` Python SDK (client + server), `httpx`, `msgraph-sdk`/raw Graph, `docling`, `watchdog`, `duckdb`, `pgvector`.
- hm-web UI: server-rendered pages with HTMX + Alpine, styled to match LibreChat (Tailwind) — small, no SPA build chain; or React if the team prefers.
- Tests: pytest (unit, ≥ 80 % coverage), contract tests vs. pinned LibreChat/LiteLLM (A1–A7), Playwright E2E for UX timing rules (UX-002/004/006), security tests (role bypass attempts, prompt-injection fixtures for MCP-022).
- Packaging: one container image with entrypoints `web`, `worker`, `mcp-proxy`; LiteLLM hook as a Python package mounted into the LiteLLM container.

---

## 4.14 Key flows

### 4.14.1 Chat with tools in a project
1. User sends message in project chat (tier Auto) → LibreChat agent (project instructions, memory, file_search) → LiteLLM `auto`.
2. Hook: classify via `flash` → `standard` ("analysis across 2 documents"); ZDR params injected; budget OK.
3. Model streams reasoning → LibreChat Thinking block; requests tool `moorage.list_waitlist` → LibreChat calls hm-mcp-proxy → role check (Exec, `read`) ✔ → upstream → result (truncated to 50 kB) → tool card.
4. Model writes answer with citations; post-call usage recorded; footer shows "Standard · model · 3.4k tok · $0.006 · 9.1 s".

### 4.14.2 Executive attempts a write
Model requests `accounting.create_invoice` (classification `write`) → not in `tools/list` for Exec; if called anyway, proxy returns `403 tool_not_permitted` → tool card shows "Denied: read-only access" → audit row [ROLE-003, MCP-012].

### 4.14.3 Non-compliant model
Admin attempts to map a model with no ZDR endpoint → model not shown in picker; API-level save rejected. Weekly job finds a mapped model lost ZDR → mapping disabled, fallback activated, Admin alerted [PRIV-007].

---

## 4.15 Configuration reference (`hm.yaml`, exportable) [ADM-002]
```yaml
club: { name: "Eagle Harbour Yacht Club", short: "EHYC", timezone: "America/Vancouver", currency: USD }
branding: { logo: branding/logo.svg, accent: "#0B4F8A" }
network:
  lan_cidrs: ["192.168.10.0/24"]
  lan_hostname: harbourmaster.ehyc.lan
  tailnet_hostname: harbourmaster.<tailnet>.ts.net
  exposure_failsafe: alert            # alert | stop
models:
  auto: { default_tier: standard, frontier_min_confidence: 0.8, max_auto_cost_usd: 0.20 }
  role_tiers: { exec: [flash, standard, frontier], gm: [flash, standard, frontier] }
  frontier_confirm_exec: true
budgets:
  org_monthly_hard_usd: 75
  user_monthly_soft_usd: 5
  user_monthly_hard_usd: 10
  on_user_hard: downgrade_to_flash     # downgrade_to_flash | block
  confirm_request_over_usd: 0.25
  task_run_default_cap_usd: 0.50
memory: { personal_auto: true, project_auto: true, private_chat_entries: suggest }
limits: { upload_mb: 50, project_files: 500, project_gb: 2, ingest_file_mb: 100 }
retention: { deleted_chat_days: 30, logs_days: 30, audit_years: 2, archive_purge_db_after_days: null }
archive: { root: /srv/harbourmaster/archive, purge_source: false }
notifications: { smtp_relay: "smtp.office365.com:587", from: "harbourmaster@<club-domain>" }
```
