# 3. Requirements

Requirement keywords: **MUST**, **SHOULD**, **MAY** (RFC 2119).
Priority: **P1** = pilot launch blocker, **P2** = during pilot, **P3** = post-pilot/GA.

---

## 1. Scope, users and roles

### 1.1 In scope (pilot)
A self-hosted AI assistant for Eagle Harbour Yacht Club used by 12 named
people: 10 executive members, the General Manager (GM) and the Administrator.

### 1.2 Out of scope (pilot)
- Members-at-large, the public, or any internet-facing access.
- Write-back to club systems by Executives (read-only by design).
- Voice calls, image generation, autonomous email sending.
- Per-document SharePoint permission trimming (see ING-012).
- Native mobile apps (the web app is a responsive PWA).

### 1.3 Roles

| Role | Count | Summary |
|---|---|---|
| **Administrator** | 1 (+1 named backup recommended) | Configures the system: users, MCP integrations, models and tiers, budgets, ingestion sources, network, backups. Also a chat user. |
| **General Manager** | 1 | Executive capabilities plus: create club-wide shared projects, view usage and cost reports, manage the club feed, request MCP integrations. Write-capable MCP tools only if the Administrator explicitly grants them (ROLE-007). |
| **Executive** | 10 | Personal chats and projects; **read-only** access to all data sets (MCP sources and shared document collections); can upload their own files into their own projects. |

### 1.4 Permission matrix (P1)

| Capability | Admin | GM | Exec |
|---|:-:|:-:|:-:|
| Personal chats | ✔ | ✔ | ✔ |
| Create/own projects | ✔ | ✔ | ✔ |
| Upload files to own project | ✔ | ✔ | ✔ |
| Share own project with named users | ✔ | ✔ | ✔ |
| Create club-wide project (visible to all) | ✔ | ✔ | ✖ |
| Use admin-approved MCP tools (read) | ✔ | ✔ | ✔ |
| Use write-capable MCP tools | grant | grant | ✖ |
| Add/edit/remove MCP servers & credentials | ✔ | ✖ | ✖ |
| Add/edit ingestion sources & collections | ✔ | ✖ | ✖ |
| Create scheduled tasks in own/shared project | ✔ | ✔ | ✔ |
| Map tiers to models; set thinking levels | ✔ | ✖ | ✖ |
| Set budgets | ✔ | view | ✖ |
| View org usage/cost dashboard | ✔ | ✔ | own only |
| Manage users and roles | ✔ | ✖ | ✖ |
| Archive/restore own project | ✔ | ✔ | ✔ |
| Archive/restore any project | ✔ | ✖ | ✖ |
| Read other users' private chats | break-glass only (SEC-010) | ✖ | ✖ |
| View audit log | ✔ | ✖ | ✖ |

### Role requirements
- **ROLE-001 (P1)** The system MUST implement exactly the three roles above for the pilot, with permissions enforced server-side, not only hidden in the UI.
- **ROLE-002 (P1)** A user MUST have exactly one role. Role changes MUST take effect on the next request without requiring re-login and MUST be audited.
- **ROLE-003 (P1)** Executives MUST NOT be able to invoke any MCP tool classified as `write` or `unknown` (MCP-010), regardless of prompt content.
- **ROLE-004 (P1)** Executives MUST have read-only access to shared document collections: they can search/cite but cannot add, modify or delete collection documents.
- **ROLE-005 (P1)** Files an Executive uploads to their own project are project files, not shared data sets, and MAY be added/removed by project editors.
- **ROLE-006 (P2)** The Administrator SHOULD be able to define role *templates* for GA (e.g. Treasurer, Commodore) without code changes.
- **ROLE-007 (P2)** The Administrator MAY grant individual write-capable tools to the GM or Administrator role, per tool, with an expiry date; each invocation MUST require explicit in-chat user confirmation.

---

## 2. Authentication and accounts (AUTH)

- **AUTH-001 (P1)** Self-registration MUST be disabled. Accounts are created by the Administrator (invite link or SSO pre-provisioning).
- **AUTH-002 (P1)** The system MUST support Microsoft Entra ID (Azure AD) OpenID Connect sign-in if the club has a Microsoft 365 tenant, restricted to an allow-list of 12 accounts or an Entra security group.
- **AUTH-003 (P1)** If SSO is not used, local accounts MUST require passwords of ≥ 14 characters checked against a breached-password list, and TOTP two-factor authentication MUST be mandatory.
- **AUTH-004 (P1)** Sessions MUST expire after 12 h of inactivity (configurable) and absolute 30 days; cookies `Secure`, `HttpOnly`, `SameSite=Lax`.
- **AUTH-005 (P1)** Login attempts MUST be rate-limited (e.g. 5 failures / 15 min per account and per IP) and audited.
- **AUTH-006 (P1)** The Administrator MUST be able to disable a user immediately, terminating active sessions and pausing that user's scheduled tasks.
- **AUTH-007 (P2)** A break-glass local Administrator account MUST exist for SSO outages, with credentials stored offline (sealed envelope / password manager) and every use audited and alerted.
- **AUTH-008 (P2)** When a user leaves the executive, the Administrator MUST be able to transfer ownership of their projects and scheduled tasks to another user before disabling them.

---

## 3. Personal chats (CHAT)

- **CHAT-001 (P1)** Any user MUST be able to start a new personal chat from the sidebar or with keyboard shortcut (Ctrl/Cmd+Shift+O).
- **CHAT-002 (P1)** Personal chats MUST be private to their owner (see SEC-010 for the break-glass exception).
- **CHAT-003 (P1)** Chats MUST be auto-titled by the Flash tier after the first exchange; the user MUST be able to rename.
- **CHAT-004 (P1)** Users MUST be able to search their chats by title and content (full-text) from the sidebar.
- **CHAT-005 (P1)** Users MUST be able to attach files (PDF, DOCX, XLSX, PPTX, CSV, TXT, MD, images) to a message, max 50 MB per file (configurable).
- **CHAT-006 (P1)** Users MUST be able to choose tier per message: **Auto** (default), **Flash**, **Standard**, **Frontier** (MODEL-010).
- **CHAT-007 (P1)** Users MUST be able to enable/disable admin-approved MCP tools for a personal chat from a tools menu; defaults are set by the Administrator.
- **CHAT-008 (P1)** Users MUST be able to edit a previous message or regenerate a response, creating a branch, and navigate between branches.
- **CHAT-009 (P1)** Users MUST be able to stop generation at any time; partial output is retained and marked "Stopped".
- **CHAT-010 (P1)** Users MUST be able to move a personal chat into one of their projects.
- **CHAT-011 (P2)** Users MUST be able to pin, archive (ARCH-010) and delete chats. Deletion MUST be soft for 30 days, then purged.
- **CHAT-012 (P2)** Users SHOULD be able to export a chat to Markdown, PDF and JSON.
- **CHAT-013 (P2)** Users SHOULD be able to share a read-only snapshot of a chat with other named users of the system (never public links).
- **CHAT-014 (P1)** Personal chats MUST use the user's personal memory (MEM-001) when memory is enabled.
- **CHAT-015 (P2)** Users SHOULD be able to save reusable prompts ("snippets") and insert them with `/`.

---

## 4. Chat User Experience (UX)

Derived from [02-chat-ui-benchmark.md](02-chat-ui-benchmark.md).

### 4.1 Streaming and activity
- **UX-001 (P1)** Responses MUST stream token-by-token.
- **UX-002 (P1)** On Send, the user's message MUST appear within 100 ms with a visible "queued" indicator (optimistic UI).
- **UX-003 (P1)** The UI MUST display the current activity state for every request: queued → routing → connecting → thinking → tool call/result → retrieval → writing → done/error/stopped (state table in 02 §2.3).
- **UX-004 (P1)** During any phase without streamed tokens, the UI MUST update visibly at least every 2 s (elapsed-time counter, state text, or animation). A static screen for > 2 s while work is in progress is a defect.
- **UX-005 (P1)** After 20 s without new tokens, the UI MUST show a "still working" message with elapsed time and a Stop button; at the configured timeout (default 180 s Standard, 600 s Frontier) it MUST show an error with Retry and "Retry on a different tier".
- **UX-006 (P1)** A running response MUST survive page reload, tab close or network drop: on return the client MUST reattach to the in-flight stream (or show the completed result) using event IDs.
- **UX-007 (P1)** Streams MUST send keep-alive events at least every 15 s.

### 4.2 Thinking / reasoning display
- **UX-010 (P1)** When the model returns reasoning content (full or summarised), the UI MUST show it live in a collapsible "Thinking" block above the answer, with an elapsed timer.
- **UX-011 (P1)** The thinking block MUST auto-collapse when answer tokens begin and show "Thought for N s"; the user can expand it at any time, including in history.
- **UX-012 (P1)** If the model does not expose reasoning, the UI MUST still show the "Thinking · N s" state (no fabricated reasoning text).
- **UX-013 (P2)** Users SHOULD be able to set a personal preference: thinking blocks expanded / collapsed / hidden by default.

### 4.3 Tool and source transparency
- **UX-020 (P1)** Every MCP tool invocation MUST render as a tool card showing: integration name, tool name, read/write badge, status (running/succeeded/failed/denied), duration, and an expandable view of arguments and a truncated result.
- **UX-021 (P1)** Retrieval from project files or collections MUST show the files being read and render answers with numbered inline citations linking to source document, page/section and the matched excerpt.
- **UX-022 (P1)** For write-capable tools (ROLE-007), the UI MUST show a confirmation dialog containing the exact action and arguments before execution.
- **UX-023 (P2)** Multi-step agent runs SHOULD show a compact step list ("Step 3 of ~5: querying Moorage DB").

### 4.4 Message footer and cost awareness
- **UX-030 (P1)** Each assistant message MUST show a footer: tier, model display name, thinking level, input/output tokens, cost (to $0.001), and total time. Executives MAY have cost hidden by Administrator setting.
- **UX-031 (P1)** If the estimated cost of a request exceeds a configurable threshold (default $0.25), the UI MUST ask for confirmation before sending.
- **UX-032 (P2)** The composer SHOULD show remaining personal monthly budget when below 25 %.

### 4.5 Rendering
- **UX-040 (P1)** Render GitHub-flavoured Markdown, tables, syntax-highlighted code with copy button, LaTeX math and Mermaid diagrams.
- **UX-041 (P1)** Tables in answers MUST be exportable to CSV/XLSX with one click.
- **UX-042 (P2)** Generated documents (e.g. a board report draft) SHOULD open in a side panel with copy and download (DOCX/MD/PDF).
- **UX-043 (P1)** Copy-message, copy-code, and thumbs up/down feedback (with optional comment) on every assistant message.

### 4.6 Layout, responsiveness and accessibility
- **UX-050 (P1)** Layout MUST be responsive from 360 px phone width to 4K; sidebar collapses to a drawer below 900 px.
- **UX-051 (P1)** The app MUST be installable as a PWA on iOS, Android, macOS and Windows.
- **UX-052 (P1)** Light, dark and system themes; club logo, name and accent colour configurable by the Administrator.
- **UX-053 (P1)** WCAG 2.2 AA: contrast, focus visibility, full keyboard operation, screen-reader labels; activity state changes announced through an ARIA polite live region.
- **UX-054 (P1)** Honour `prefers-reduced-motion` (replace animations with text/elapsed timers).
- **UX-055 (P1)** UI interactions (open chat, switch project, open sidebar) MUST complete within 200 ms p95 on the LAN.
- **UX-056 (P2)** Sidebar sections: New chat · Search · Feed (with unread badge) · Projects · Chats (Today / Last 7 days / Older) · Archive.
- **UX-057 (P2)** Keyboard shortcuts with a `?` cheat-sheet.
- **UX-058 (P1)** The UI language is English (Canadian spelling); dates/times in the club time zone (default `America/Vancouver`).

---

## 5. Projects (PROJ)

A **project** is a workspace that bundles chats, files, instructions, memory,
enabled integrations, scheduled tasks and a feed.

### 5.1 Lifecycle
- **PROJ-001 (P1)** Any user MUST be able to create a project with: name (required), description, icon/colour (optional).
- **PROJ-002 (P1)** Project states: **Active** → **Archived** (→ **Restored** = Active) → **Deleted** (Admin, after archive only).
- **PROJ-003 (P1)** Each project MUST have one owner. The owner MAY share it with named users as **Editor** (chat, upload files, edit instructions, manage tasks) or **Viewer** (read chats, files, feed; may start their own chats in the project).
- **PROJ-004 (P1)** GM and Administrator MUST be able to create **club-wide** projects visible to all users (default member role Viewer, configurable).
- **PROJ-005 (P1)** Chats inside a project MUST be private to the chat's author by default, with a per-chat option "Share with project members". Club-wide and shared-project feeds are visible to all members.
- **PROJ-006 (P2)** Project templates (e.g. "Board meeting prep", "Regatta planning", "Budget review") SHOULD be available, pre-filling instructions and suggested tasks.

### 5.2 Project files (context)
- **PROJ-010 (P1)** Project editors MUST be able to upload files (same types as CHAT-005; up to 500 files and 2 GB per project, configurable).
- **PROJ-011 (P1)** Uploaded files MUST be parsed, chunked and embedded automatically; processing status per file (queued / processing / ready / failed with reason) MUST be shown.
- **PROJ-012 (P1)** Editors MUST be able to attach admin-managed shared **collections** (ING-020) to the project (read-only).
- **PROJ-013 (P1)** All chats in the project MUST be able to retrieve from project files and attached collections, with citations (UX-021).
- **PROJ-014 (P2)** Small projects (total extracted text below a threshold, e.g. 60k tokens) SHOULD support "always include in context" mode instead of retrieval, using prompt caching where the provider supports it.
- **PROJ-015 (P2)** Files SHOULD support versioning: re-uploading a file with the same name replaces it and keeps the previous version for 30 days.

### 5.3 Project instructions
- **PROJ-020 (P1)** Each project MUST have editable instructions (Markdown, up to 8,000 characters) prepended to every chat and scheduled task in that project.
- **PROJ-021 (P1)** Instruction edits MUST be versioned with author and timestamp, with the ability to view and revert previous versions.
- **PROJ-022 (P2)** The project MAY set a default tier and default thinking level overriding the user default.

### 5.4 Project integrations
- **PROJ-030 (P1)** Project editors MUST be able to enable/disable, per project, any MCP integration the Administrator has made available to their role. They MUST NOT be able to add new integrations or change credentials.
- **PROJ-031 (P1)** The project's sensitivity setting MUST support **"Local models only"**, which forces all chats and tasks in the project to local models (PRIV-020).

### 5.5 Project memory — see MEM-010…MEM-016.
### 5.6 Project tasks and feed — see SCHED and FEED.
### 5.7 Project archive — see ARCH.

---

## 6. Memory (MEM)

### 6.1 Personal memory
- **MEM-001 (P1)** Each user MUST have a personal memory used only in their personal chats (never in project chats unless the user opts in per project, and never visible to others).
- **MEM-002 (P1)** Memory MUST be viewable, editable and deletable by the user as a list of plain-language statements.
- **MEM-003 (P1)** Users MUST be able to add memory explicitly ("Remember that…") and turn automatic memory extraction on/off (default **on**, extraction by the Flash tier).
- **MEM-004 (P1)** The UI MUST indicate when a memory was created or used in a response ("Memory updated" / "Used 2 memories").

### 6.2 Project memory
- **MEM-010 (P1)** Each project MUST have its own memory, isolated from personal memory and from other projects.
- **MEM-011 (P1)** Project memory MUST be readable by all project members and editable by owner/editors.
- **MEM-012 (P1)** Project memory MUST be updated (a) explicitly by users, (b) automatically by Flash-tier extraction from project chats when enabled, and (c) by scheduled tasks when their configuration allows "update project memory".
- **MEM-013 (P1)** Every memory entry MUST record source (chat/task id), author or "auto", and timestamp.
- **MEM-014 (P1)** Project memory MUST be included in context for all project chats and tasks (summarised if over budget, default 2,000 tokens).
- **MEM-015 (P2)** A "Compact memory" action SHOULD consolidate duplicates using the Flash tier, showing a diff for approval.
- **MEM-016 (P1)** Memory content from private chats MUST NOT leak into shared project memory without being visible to the author (auto-extracted entries from a private chat are shown to the author as "suggested" until accepted, configurable).

---

## 7. Archive (ARCH)

- **ARCH-001 (P1)** Owners (and the Administrator for any project) MUST be able to archive a project. Archiving requires confirmation and shows what will happen.
- **ARCH-002 (P1)** Archiving MUST write the complete project to a directory of plain files on the server's filesystem at `${ARCHIVE_ROOT}/projects/<yyyy>/<project-slug>--<project-id>--<yyyymmdd-hhmm>/` (layout in [04 §4.8](04-technical-specification.md#48-archive-format)), including: manifest, project metadata, instructions (+history), memory, all chats (Markdown and JSON), all uploaded files (original binaries), feed items, scheduled task definitions and run history.
- **ARCH-003 (P1)** The archive MUST be human-readable without the application (Markdown + JSON + original files) and MUST include a `manifest.json` with SHA-256 checksums of every file.
- **ARCH-004 (P1)** After a successful archive write and checksum verification, the project MUST become read-only, disappear from the active project list, appear under **Archive**, and all its scheduled tasks MUST be disabled.
- **ARCH-005 (P1)** Archived projects MUST remain browsable read-only in the UI (rendered from the archive directory or retained database records).
- **ARCH-006 (P2)** The owner or Administrator MUST be able to restore an archived project to Active from its archive directory; restored projects re-index files and keep tasks disabled until re-enabled.
- **ARCH-007 (P2)** After a configurable retention period (default: never), the Administrator MAY purge database records of archived projects, leaving only the archive directory.
- **ARCH-008 (P1)** Archive operations MUST be atomic (write to a temporary directory, verify, then rename) and audited.
- **ARCH-009 (P1)** The archive root MUST be included in backups (OPS-001) and SHOULD be exposable as a read-only SMB share to the Administrator/GM.
- **ARCH-010 (P2)** Individual personal chats MUST be archivable using the same format under `${ARCHIVE_ROOT}/chats/<user>/...`.

---

## 8. MCP integrations (MCP)

### 8.1 Administration
- **MCP-001 (P1)** Only the Administrator MUST be able to add, edit, test, enable, disable or remove MCP servers and their credentials.
- **MCP-002 (P1)** Supported transports: **Streamable HTTP** (remote), **stdio** (server run as a managed container/process on the host), and legacy **SSE** (for older servers).
- **MCP-003 (P1)** Credentials (API keys, OAuth client secrets, database passwords) MUST be stored encrypted at rest, never displayed after entry, and never sent to the LLM.
- **MCP-004 (P1)** The Administrator MUST be able to "Test connection", which performs MCP `initialize` and `tools/list` and displays server info, protocol version, tools, resources and prompts.
- **MCP-005 (P2)** OAuth 2.1-based MCP servers MUST be supported with a **service-account** authorisation performed once by the Administrator (shared, read-only identity), not per-user OAuth, for the pilot.
- **MCP-006 (P1)** The Administrator MUST be able to set per-server: display name, description (shown to users and the model), icon, timeout (default 30 s), max result size (default 50 kB, truncated with notice), rate limit, and which roles may use it.

### 8.2 Tool governance and read-only enforcement
- **MCP-010 (P1)** Every discovered tool MUST be classified as `read`, `write` or `unknown`. Default classification uses the MCP `readOnlyHint`/`destructiveHint` annotations; tools without annotations default to `unknown`. The Administrator confirms or overrides.
- **MCP-011 (P1)** Only tools explicitly **enabled** by the Administrator are exposed; newly discovered tools after a server update are disabled until reviewed, and the Administrator is notified.
- **MCP-012 (P1)** Read-only access for Executives MUST be enforced in three layers: (1) the integration's credential is read-only at the source system where possible; (2) only `read` tools are exposed to the Executive role; (3) the gateway rejects any `write`/`unknown` tool call from an Executive context even if the model requests it.
- **MCP-013 (P1)** For SQL-style data sources, the MCP server MUST connect with a database role that has `SELECT`-only privileges on approved views/tables, plus a statement timeout and row limit.
- **MCP-014 (P1)** Tool calls from scheduled tasks MUST run with the permissions of the task owner.
- **MCP-015 (P2)** Per-tool "require user approval" flag; when set, each call pauses for confirmation (UX-022).

### 8.3 Runtime
- **MCP-020 (P1)** MCP server health MUST be checked every 5 min; failures show a status badge in admin and a degraded notice to users when a tool is unavailable.
- **MCP-021 (P1)** Each tool call MUST be audited: timestamp, user, project/chat/task id, server, tool, arguments (redacted fields configurable), result size, duration, status.
- **MCP-022 (P1)** Tool results MUST be treated as untrusted content: they are passed to the model as data, and tool-originated text MUST NOT be able to enable other tools, change permissions or alter system instructions (prompt-injection defence, SEC-020).
- **MCP-023 (P2)** MCP **resources** and **prompts** exposed by servers SHOULD be browsable and attachable in the composer.
- **MCP-024 (P2)** To control context cost, when more than 20 tools are enabled the system SHOULD use deferred/lazy tool discovery (tool search) rather than sending all schemas each turn.

### 8.4 Expected EHYC integrations (to be confirmed — see 05 §5.6)
| Integration | Likely mechanism | Access |
|---|---|---|
| Membership/registry system | Vendor API → custom MCP, or read-only DB view → SQL MCP | read |
| Moorage / slip management | Vendor API or DB → MCP | read |
| Accounting (e.g. QuickBooks Online / Xero / Sage) | Vendor/community MCP or API → MCP | read |
| Club calendar / events | Microsoft 365 / Google Calendar MCP | read |
| Microsoft 365 (SharePoint, OneDrive, Outlook) | Microsoft Graph MCP (service account) | read |
| Board minutes & policies | Ingested collection (ING) — not MCP | read |
| Spreadsheets/CSV data sets | Harbourmaster "Datasets" SQL MCP over DuckDB/Postgres | read |

---

## 9. Document ingestion (ING)

### 9.1 Sources
- **ING-001 (P1)** The Administrator MUST be able to configure **SharePoint Online** sources via a Microsoft Entra app registration using **`Sites.Selected`** application permission (read) scoped to specific sites, with certificate credentials.
- **ING-002 (P1)** A SharePoint source MUST allow selection of site → document library → optional folder paths, with include/exclude glob patterns and file-type filters.
- **ING-003 (P1)** SharePoint sync MUST be incremental using Microsoft Graph **delta** queries; new, modified, moved and deleted files MUST be reflected in the index.
- **ING-004 (P1)** The Administrator MUST be able to configure **local folder** sources: directories on the server (or mounted SMB/NFS shares) mounted **read-only** into the ingestion service.
- **ING-005 (P1)** Local folders MUST be watched for changes (filesystem events) with a full reconciliation rescan on schedule (default nightly).
- **ING-006 (P1)** Each source MUST have a sync schedule (manual, hourly, daily at time, cron) and a "Sync now" action.
- **ING-007 (P2)** The system SHOULD support OneDrive folders and Teams-channel files (same Graph mechanism).
- **ING-008 (P3)** Google Drive, Dropbox and email (IMAP/Graph mailbox) sources MAY be added post-pilot.

### 9.2 Processing
- **ING-010 (P1)** Supported formats: PDF (text and scanned via OCR), DOCX, DOC, XLSX, XLS, CSV, PPTX, TXT, MD, HTML, RTF, EML/MSG; images (PNG/JPG) via OCR optional.
- **ING-011 (P1)** Documents MUST be parsed with layout awareness (headings, tables, page numbers), chunked (default ~800 tokens, 100 overlap, heading-aware), and embedded.
- **ING-012 (P1)** Pilot permission model: access control is at **collection** level (which roles/projects may use it). The system MUST NOT claim per-document permission trimming. The Administrator MUST only connect libraries suitable for all permitted roles; this limitation MUST be displayed on the source configuration screen.
- **ING-013 (P1)** Embeddings SHOULD be computed **locally** (e.g. via Ollama embedding model) so document content is not sent to external services for indexing; if an external embedding endpoint is configured it MUST meet PRIV-001.
- **ING-014 (P1)** Each document MUST retain metadata: source, path, URL (SharePoint web link), author, modified date, checksum, collection; citations MUST link back to the original (SharePoint URL or local path).
- **ING-015 (P1)** Sync runs MUST report: files seen/added/updated/deleted/failed, duration, and per-file errors; failures notify the Administrator.
- **ING-016 (P2)** Retrieval MUST be hybrid (vector + keyword/BM25) with re-ranking (local or Flash tier) and metadata filters (date ranges, folder, file type).
- **ING-017 (P2)** Spreadsheets/CSVs SHOULD additionally be loadable as queryable tables via the Datasets MCP (MCP §8.4) so numeric questions are answered by query, not by text retrieval.
- **ING-018 (P1)** Maximum file size default 100 MB; files over the limit are skipped and reported.

### 9.3 Collections
- **ING-020 (P1)** Ingested content MUST be organised into named **collections** (e.g. "Board Minutes", "Bylaws & Policies", "Finance Reports"), each mapped from one or more sources.
- **ING-021 (P1)** Collections MUST have access settings: available to roles (Admin/GM/Exec) and attachable to projects; a "Club Library" collection MAY be made available in all personal chats.
- **ING-022 (P2)** Users SHOULD be able to browse a collection's document list and open originals.

---

## 10. Scheduled agent tasks (SCHED)

- **SCHED-001 (P1)** Project owners/editors MUST be able to create scheduled tasks within a project.
- **SCHED-002 (P1)** A task definition MUST include: name; prompt (Markdown); schedule; tier and thinking level; enabled MCP tools (subset of the project's); whether to use project files/collections; whether it may update project memory; output target(s); max cost per run; owner.
- **SCHED-003 (P1)** Schedules MUST support: once at date/time; every N hours; daily at time; weekly on days at time; monthly on day N or "first Monday"; and advanced 5-field cron. All in the club time zone, DST-correct.
- **SCHED-004 (P1)** A task MUST run with the owner's role and permissions (MCP-014); if the owner is disabled, the task pauses and the project owner/Administrator is notified.
- **SCHED-005 (P1)** Each run MUST record: start/end time, status (succeeded / failed / skipped / cost-capped / timed-out), tier/model, tokens, cost, tool calls, and the full transcript (viewable as a chat).
- **SCHED-006 (P1)** Runs MUST be abortable at the per-run cost cap (default $0.50) and timeout (default 10 min).
- **SCHED-007 (P1)** Failed runs MUST retry with exponential backoff (default 2 retries); persistent failure posts a failure item to the feed and notifies the owner.
- **SCHED-008 (P1)** Users MUST be able to "Run now" (test) a task, pause/resume, edit, duplicate and delete it.
- **SCHED-009 (P1)** Concurrency: at most one run of the same task at a time; global concurrency limit (default 3) to protect cost and local GPU.
- **SCHED-010 (P2)** Missed runs (server down) MUST be handled per task policy: skip or run once on recovery (default run once if missed by < 6 h).
- **SCHED-011 (P2)** Tasks SHOULD support "only post if something changed / noteworthy": the run compares with the previous result and posts only if the model flags a material change.
- **SCHED-012 (P2)** Tasks SHOULD support simple templates: "Weekly financial snapshot", "Upcoming events digest", "New documents in Board Minutes summary", "Moorage waitlist changes".
- **SCHED-013 (P1)** Total scheduled-task spend MUST count toward the owner's and the organisation's budgets (COST).

## 11. Feed (FEED)

- **FEED-001 (P1)** Every project MUST have a **feed**: a reverse-chronological stream of items produced by its scheduled tasks (and system events such as "Archive completed", "Sync failed").
- **FEED-002 (P1)** A feed item MUST contain: title, summary (≤ 3 lines), body (Markdown), source task + run link, timestamp, status badge (info / attention / failure), citations/sources, tier/cost.
- **FEED-003 (P1)** A global **My Feed** MUST aggregate items from all projects the user can access, with filters (project, status, unread) and an unread count badge in the sidebar.
- **FEED-004 (P1)** Users MUST be able to mark read/unread, pin, and "Continue in chat" (opens a new project chat seeded with the item).
- **FEED-005 (P1)** Feed items MUST be immutable after posting (corrections post a new item that references the old).
- **FEED-006 (P2)** Notifications: users SHOULD be able to opt in per project to email digest (daily/weekly) and browser/PWA push for "attention" items. Email delivery uses the club's SMTP/M365 relay, contains only title + link by default (no confidential body).
- **FEED-007 (P2)** Task output MAY additionally be written as a file into the project (e.g. `reports/2026-11-weekly-finance.md`).
- **FEED-008 (P3)** Feed items MAY be published to a Microsoft Teams channel via webhook.

---

## 12. Models, tiers and routing (MODEL)

### 12.1 Providers
- **MODEL-001 (P1)** The system MUST support model sources: **Ollama** (local), **local OpenAI-compatible servers** (vLLM, llama.cpp server, LM Studio), and **OpenRouter**.
- **MODEL-002 (P2)** Direct provider APIs (e.g. Anthropic, OpenAI, Google, Mistral) MAY be added only when the Administrator records a zero-data-retention agreement for that key (PRIV-003).
- **MODEL-003 (P1)** All LLM traffic from every component (chat, tasks, memory extraction, titles, ingestion, routing) MUST pass through the single model gateway. No component may call a provider directly.

### 12.2 Tiers
- **MODEL-010 (P1)** The system MUST define three tiers with defaults:

| Tier (UI label) | Admin label | Purpose | Default thinking | Typical use |
|---|---|---|---|---|
| **Flash** | low | Fast evaluation and synthesis | off / minimal | routing, titles, memory extraction, summaries, feed synthesis, re-ranking, simple Q&A |
| **Standard** | medium | Common tasks | low–medium | drafting, analysis of a few documents, most tool use |
| **Frontier** | high | Complex tasks | high | multi-document reasoning, strategy, complex multi-tool agent runs |

- **MODEL-011 (P1)** The Administrator MUST be able to map each tier to: primary model (provider + model id), thinking/reasoning level (`off`, `minimal`, `low`, `medium`, `high`, or token budget), max output tokens, temperature, context limit, and an ordered **fallback list** (each fallback must also be ZDR-compliant).
- **MODEL-012 (P1)** Changing a tier mapping MUST take effect for new requests without restart and MUST be audited, with one-click revert to previous mapping.
- **MODEL-013 (P1)** Thinking levels MUST be translated per provider (e.g. OpenRouter unified `reasoning.effort` / `reasoning.max_tokens`; Ollama `think`; providers without reasoning ignore the setting) and the admin UI MUST show whether the chosen model supports reasoning.
- **MODEL-014 (P1)** The Administrator MUST be able to restrict tiers per role (e.g. Frontier available to Executives but requires confirmation, or disabled).
- **MODEL-015 (P2)** The Administrator SHOULD be able to define additional named presets (e.g. "Local-private", "Long-document") beyond the three tiers for GA.
- **MODEL-016 (P1)** A separate **embedding** model setting (default local) and optional **re-rank** model setting MUST exist.

### 12.3 Routing ("Auto")
- **MODEL-020 (P1)** In **Auto** mode, the Flash tier MUST classify each request (complexity, need for tools/documents, length) and select a tier, using rules the Administrator can tune (e.g. default Standard; escalate to Frontier only if classifier confidence ≥ threshold and estimated cost ≤ cap).
- **MODEL-021 (P1)** The chosen tier and a short reason ("Standard: drafting task with 2 documents") MUST be shown in the message footer; the user can re-run on a different tier with one click.
- **MODEL-022 (P2)** Auto routing SHOULD prefer the cheapest tier that historically satisfied similar requests (thumbs-up feedback) — post-pilot learning loop.
- **MODEL-023 (P1)** If the primary model fails (timeout, 5xx, rate limit), the gateway MUST fall back along the tier's fallback list and the footer MUST show the model actually used.

### 12.4 Default model candidates
Model availability and pricing change monthly; the Administrator selects
models at deployment from the gateway's live **ZDR-eligible** list (PRIV-002).
Illustrative defaults to evaluate during Phase 1 (05 §5.2):

| Tier | Cloud candidate (OpenRouter, ZDR endpoint) | Local candidate (Ollama, if GPU) |
|---|---|---|
| Flash | A current "flash/mini/haiku-class" model priced ≲ $0.50 / M input tokens | 7–14B instruct model (e.g. Qwen/Gemma/Llama family) |
| Standard | A current mid-tier model priced ≲ $3 / M input tokens | 27–32B model (needs ≥ 24 GB VRAM) |
| Frontier | A current frontier model with high reasoning | none (cloud only) |

---

## 13. Cost management (COST)

- **COST-001 (P1)** The gateway MUST record per request: user, project, chat/task, tier, model, provider, input/output/reasoning/cached tokens, cost (from provider-reported usage where available, otherwise price table), latency.
- **COST-002 (P1)** Budgets: an **organisation monthly hard cap** (default CAD/USD $75, configurable); **per-user monthly** soft and hard limits (default soft $5, hard $10); **per-task per-run** cap (SCHED-006); **per-request** confirmation threshold (UX-031).
- **COST-003 (P1)** On soft limit, users see a warning; on hard limit, requests are restricted to Flash and local models (configurable: block entirely) until reset or Administrator override.
- **COST-004 (P1)** Alerts to the Administrator and GM at 50 %, 80 % and 100 % of the organisation budget.
- **COST-005 (P1)** Usage dashboard: spend by day, user, project, tier, model, task; top expensive requests; projected month-end spend.
- **COST-006 (P1)** Cost-saving defaults MUST be on: Flash for all background work; prompt caching where supported (stable system/instruction prefix ordering); conversation history summarisation beyond a token threshold (default 24k); retrieval top-k limits; tool-schema minimisation (MCP-024).
- **COST-007 (P1)** Model prices MUST be refreshed daily from OpenRouter's models API; the Administrator sees cost per 1M tokens next to each model in the tier mapping UI.
- **COST-008 (P2)** Monthly cost report (CSV/PDF) for the treasurer.
- **COST-009 (P1)** Display currency configurable (USD native; optional CAD conversion at an admin-set rate).

---

## 14. Data privacy and zero data retention (PRIV)

- **PRIV-001 (P1)** **Only models whose provider does not retain prompts/completions and does not train on them may be used.** This is a hard system rule, not a guideline.
- **PRIV-002 (P1)** For OpenRouter, the system MUST: (a) require the account-level **Zero Data Retention** setting and disabled prompt logging (verified by the Administrator at setup, recorded with date); (b) send `provider: { "zdr": true, "data_collection": "deny" }` on **every** request; (c) only list models with at least one ZDR endpoint in the tier mapping UI; (d) refuse requests to any model not on the ZDR allow-list.
- **PRIV-003 (P1)** Direct provider keys (MODEL-002) MUST be marked ZDR only when the Administrator uploads/records the provider agreement reference; otherwise they cannot be selected.
- **PRIV-004 (P1)** OpenRouter plugins (web search, etc.) and any provider-side features outside ZDR scope MUST be disabled unless the Administrator explicitly enables them with a displayed warning.
- **PRIV-005 (P1)** Local models (Ollama/local) are inherently compliant; their servers MUST bind only to the internal Docker network/localhost.
- **PRIV-006 (P1)** The gateway MUST NOT persist prompt or completion content in its own logs by default (metadata only). Chat content is stored only in the chat application's database and archives.
- **PRIV-007 (P1)** A weekly automated **compliance check** MUST re-verify that every mapped model still has a ZDR endpoint; non-compliant mappings are disabled, fallbacks used, and the Administrator alerted.
- **PRIV-010 (P1)** The deployment MUST support the club's obligations under BC's *Personal Information Protection Act* (PIPA): purpose notice on login, access/deletion of a user's data on request, documented retention schedule (05 §5.7), and breach-response contact.
- **PRIV-011 (P2)** Optional PII redaction (names, phone numbers, emails, member numbers) before sending to cloud models, with re-insertion in the answer, configurable per collection/integration.
- **PRIV-020 (P1)** Projects flagged **Local models only** (PROJ-031) MUST never send content to a cloud provider; if no local model is available, requests fail with a clear message rather than falling back to cloud.
- **PRIV-021 (P2)** The Administrator SHOULD be able to restrict OpenRouter providers by region/jurisdiction (e.g. prefer Canadian/US providers) using provider allow/deny lists.

---

## 15. Network access (NET)

- **NET-001 (P1)** The web interface MUST be reachable only from (a) the club's local network(s) and (b) the club's **Tailscale** tailnet when Tailscale is configured. It MUST NOT be reachable from the public internet.
- **NET-002 (P1)** The reverse proxy MUST bind only to the LAN interface address and the `tailscale0` interface address — never `0.0.0.0` on a host with a public address. All application containers MUST bind to the internal Docker network only.
- **NET-003 (P1)** A host firewall (nftables/ufw) MUST default-deny inbound, allowing TCP 443 (and 80 → redirect) only from configured LAN CIDRs and the Tailscale CGNAT range `100.64.0.0/10` on `tailscale0`; SSH only from the Administrator's devices/tailnet.
- **NET-004 (P1)** The application MUST additionally enforce an IP allow-list middleware (defence in depth) using the real peer address, not client-supplied `X-Forwarded-For`.
- **NET-005 (P1)** Tailscale **Funnel** MUST NOT be used. Tailscale ACLs SHOULD restrict access to the server to a `tag:harbourmaster-users` group.
- **NET-006 (P1)** HTTPS MUST be used on both paths: on the tailnet via Tailscale HTTPS certificates (MagicDNS name); on the LAN via a certificate from an internal CA (Caddy local CA, installed on club devices) or a DNS-01-issued certificate for a private hostname.
- **NET-007 (P1)** A startup and hourly **exposure self-check** MUST verify listening sockets and firewall rules and alert (and optionally stop the proxy) if any app port is listening on a public interface.
- **NET-008 (P1)** No inbound port forwarding on the club router is required or permitted; the system works with outbound connections only.
- **NET-009 (P1)** Outbound egress SHOULD be restricted to required destinations: OpenRouter, Microsoft Graph/login endpoints, configured remote MCP servers, Tailscale coordination/DERP, OS/container registries, SMTP relay.
- **NET-010 (P2)** If the club LAN has guest Wi-Fi, the guest VLAN/CIDR MUST be excluded from the allow-list.

---

## 16. Security (SEC)

- **SEC-001 (P1)** All secrets (API keys, certificates, DB passwords) MUST be stored in an encrypted secrets file or store (e.g. SOPS/age or Docker secrets), readable only by root and the service; never in Git.
- **SEC-002 (P1)** Data at rest MUST be encrypted (LUKS full-disk encryption on the server; backup encryption OPS-002).
- **SEC-003 (P1)** Containers run as non-root, read-only root filesystems where supported, no Docker socket mounted into app containers.
- **SEC-004 (P1)** Security headers: HSTS, CSP, X-Frame-Options DENY, Referrer-Policy; CSRF protection on state-changing requests.
- **SEC-005 (P1)** Uploaded files MUST be scanned (ClamAV) and processed in an isolated worker; active content (macros, scripts) is never executed.
- **SEC-006 (P1)** Dependencies and images MUST be pinned by version/digest; monthly patch window; critical CVEs within 7 days.
- **SEC-010 (P1)** No user, including the Administrator, can read another user's private chats through the UI. A **break-glass** procedure (e.g. legal request, departed user handover) MUST require GM + Administrator dual approval recorded in the audit log, and the affected user is notified unless legally prohibited.
- **SEC-020 (P1)** Prompt-injection defences: system/project instructions are separated from retrieved content and tool results; retrieved/tool content is delimited and labelled as untrusted; write tools require confirmation; tool permissions are enforced by the gateway, not the model.
- **SEC-021 (P1)** stdio MCP servers MUST run in separate containers with no host filesystem access except explicitly mounted read-only paths, and egress limited to their target system.
- **SEC-030 (P1)** Audit log (immutable append-only table + daily export file) MUST record: logins/logouts/failures, role/user changes, admin configuration changes (MCP, models, budgets, sources, network), tool calls (MCP-021), archive/restore/delete, exports, break-glass events. Retained 2 years.

---

## 17. Administration console (ADM)

- **ADM-001 (P1)** A single admin console MUST provide: Users & roles · MCP integrations · Models & tiers · Budgets & usage · Ingestion sources & collections · Scheduled tasks (all) · Archive · Network & exposure status · Backups · Audit log · Branding · System health.
- **ADM-002 (P1)** All configuration MUST also be exportable/importable as versioned YAML (configuration-as-code) for disaster recovery and replication to other clubs.
- **ADM-003 (P1)** Every configuration form MUST validate inputs and offer "Test" actions where applicable (MCP test, model test prompt with latency/cost, SharePoint connection test, SMTP test).
- **ADM-004 (P1)** System health page: service status, CPU/RAM/disk/GPU usage, queue depths, last backup result, last sync per source, MCP health, gateway error rate, ZDR compliance status.
- **ADM-005 (P2)** Admin notifications (email/push) for: budget thresholds, sync failures, MCP down, backup failure, exposure-check failure, ZDR non-compliance, disk > 80 %, new MCP tools pending review.

---

## 18. Operations (OPS)

- **OPS-001 (P1)** Nightly automated backup of databases (consistent dumps), uploaded files, vector index, configuration, secrets (encrypted) and the archive root.
- **OPS-002 (P1)** Backups MUST be encrypted (restic/borg) and stored on (a) a local USB/NAS target and (b) an off-site target (e.g. S3-compatible bucket in Canada), retention 7 daily / 4 weekly / 12 monthly.
- **OPS-003 (P1)** Restore MUST be tested at pilot go-live and quarterly; documented runbook.
- **OPS-004 (P1)** RPO ≤ 24 h; RTO ≤ 4 h (same hardware) / ≤ 1 business day (replacement hardware).
- **OPS-005 (P1)** Upgrades via pinned image versions and a documented upgrade script with pre-upgrade backup and rollback.
- **OPS-006 (P1)** Logs: structured JSON, rotated, 30-day retention (metadata only; no prompt content — PRIV-006).
- **OPS-007 (P2)** Monitoring with Uptime Kuma or Prometheus/Grafana, alerting to the Administrator.
- **OPS-008 (P1)** Runbooks: install, add user, add MCP integration, change tier mapping, rotate keys, restore from backup, archive/restore project, Tailscale onboarding of a device, incident response.

---

## 19. Host platform (HOST)

- **HOST-001 (P1)** Runs on a single Linux server: Ubuntu Server 24.04 LTS (primary) or Debian 13; x86_64.
- **HOST-002 (P1)** Minimum (cloud models only): 8 CPU cores, 32 GB RAM, 1 TB NVMe SSD, gigabit Ethernet, UPS.
- **HOST-003 (P2)** Recommended (local Flash/embeddings/OCR): above plus NVIDIA GPU with ≥ 16 GB VRAM (24 GB for a local Standard-class model), 64 GB RAM.
- **HOST-004 (P1)** Deployment via Docker Engine + Docker Compose v2; a single `install.sh` bootstraps the host (packages, firewall, Tailscale, LUKS check, Compose stack).
- **HOST-005 (P1)** The server MUST be physically secured (locked office/cabinet) and on the club's wired LAN.

---

## 20. Non-functional requirements (NFR)

| ID | Requirement | Target |
|---|---|---|
| NFR-001 (P1) | Concurrent active users | 12 named, 6 concurrent streaming without degradation |
| NFR-002 (P1) | Time to first visible activity after Send | ≤ 100 ms |
| NFR-003 (P1) | Time to first token, Flash (cloud) | p95 ≤ 2 s |
| NFR-004 (P1) | Time to first token or thinking event, Standard | p95 ≤ 4 s |
| NFR-005 (P1) | Retrieval latency (project files/collections) | p95 ≤ 1.5 s |
| NFR-006 (P1) | Page load (cold, LAN) | ≤ 2 s; PWA warm ≤ 1 s |
| NFR-007 (P1) | Availability | 99 % during 07:00–22:00 local; planned maintenance announced 48 h ahead |
| NFR-008 (P1) | Capacity | 50k ingested documents, 200 GB files, 5 years of chats |
| NFR-009 (P1) | Ingestion throughput | ≥ 500 pages/min (CPU) for text PDFs |
| NFR-010 (P1) | Browser support | Latest two versions of Chrome, Edge, Safari (macOS/iOS), Firefox |
| NFR-011 (P1) | Maintainability | No fork of upstream products; custom code ≤ ~5k LOC with ≥ 80 % unit-test coverage |
| NFR-012 (P1) | Portability | Club-specific settings in configuration only, so a second club can be deployed from the same release |
| NFR-013 (P1) | Documentation | Administrator guide, user quick-start (2 pages), runbooks (OPS-008) |
