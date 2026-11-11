# 2. Chat Interface Benchmark and UX Requirements

## 2.1 Interfaces assessed

| Product | Notable patterns worth adopting |
|---|---|
| **ChatGPT** (web) | Projects with files + instructions + project memory; "Thinking…" header with elapsed time and expandable reasoning summary; tool-use status lines ("Searching…", "Reading 3 files"); stop button replaces send; message edit creates a branch; Tasks (scheduled prompts) with notifications; Canvas side panel |
| **Claude.ai** | Projects with knowledge + custom instructions; collapsible extended-thinking block that streams live then collapses to "Thought for 12s"; tool-call cards showing inputs/results; Artifacts side panel; citations to project files; memory; connectors (MCP) per user, admin-managed in Team/Enterprise |
| **Gemini** | "Show thinking" toggle; Gems (reusable instructions); scheduled actions; strong document upload previews |
| **Perplexity** | Live step list (searching → reading N sources → writing); numbered inline citations with hover previews; Spaces (≈ projects) |
| **Microsoft Copilot (M365)** | Grounding on SharePoint/OneDrive with permission trimming; file-chip citations; "Pages" for persistent outputs |
| **LibreChat** | Multi-provider model picker; agents; MCP tool approval prompts; conversation branching/forking; projects; scheduled chats (beta) |
| **Open WebUI** | Inline reasoning blocks, knowledge "#" attach, admin-managed MCP, model presets, arena mode |

## 2.2 Common patterns of a "modern" chat UI (2026)

1. **Token streaming** with first token typically < 1 s for fast models.
2. **Visible reasoning**: a dedicated, collapsible block above the answer,
   streamed live, auto-collapsed when the answer starts, with duration.
3. **Activity narration**: every non-token phase is announced — queued,
   connecting to model, thinking, calling tool *X*, reading file *Y*,
   searching knowledge, writing.
4. **Tool transparency**: tool cards with name, arguments, status, duration,
   and an expandable result preview.
5. **Interruptibility**: Stop at any time; partial output is kept.
6. **Branching**: edit a prior message or regenerate → sibling versions with
   `< 2/3 >` navigation.
7. **Citations**: inline numbered markers linked to source documents/chunks.
8. **Projects/spaces**: sidebar grouping with shared files, instructions,
   memory.
9. **Rich rendering**: Markdown, tables, code with copy, Mermaid diagrams,
   LaTeX, file previews, downloadable outputs.
10. **Responsive layout**: collapsible sidebar, mobile-first composer, PWA.
11. **Resumability**: closing the tab does not kill a running response; it can
    be reopened and continues streaming.
12. **Cost/model awareness** (pro tools): model/tier chip on each message.

## 2.3 Derived UX requirements

These are the source of the `UX-*` requirements in
[03-requirements.md](03-requirements.md#4-chat-user-experience-ux). The
guiding rule: **the user is never left wondering whether the system is
working.**

### Activity state machine (shown in the message area)

```
 queued ─▶ routing ─▶ connecting ─▶ thinking ─▶ (tool_call ⇄ tool_result)* ─▶ writing ─▶ done
   │          │           │             │                   │                    │
   └──────────┴───────────┴─────────────┴───────────────────┴────────────────────┴─▶ error / stopped
```

| State | Visual | Text example |
|---|---|---|
| queued | pulsing dot | "Queued (1 ahead)" |
| routing | pulsing dot + tier chip | "Choosing model… Standard" |
| connecting | shimmer on placeholder line | "Contacting model…" |
| thinking | animated "Thinking" header, elapsed seconds, live reasoning text in collapsible block | "Thinking · 7s" |
| tool_call | tool card with spinner | "Querying Membership DB (read-only)…" |
| tool_result | tool card ticks, collapsible result | "Got 42 rows · 0.8s" |
| retrieval | file chips appear | "Reading 3 project files" |
| writing | streaming tokens + caret | — |
| done | footer: tier, model, tokens, cost, time | "Standard · 2.1k tokens · $0.004 · 6.2s" |
| error | red inline banner + Retry | "Model timed out — Retry with Flash?" |
| stopped | grey footer | "Stopped by you" |

### Latency budget and heartbeat rules
- Visual acknowledgement of Send: **≤ 100 ms** (optimistic user bubble +
  queued state).
- Status update at least every **2 s** during any non-streaming phase; if no
  backend event arrives, the client shows elapsed time ticking so the screen is
  never static.
- After **20 s** of no tokens, show "Still working — the model is thinking
  deeply" with a Stop option; after the configured timeout show an error with
  Retry options.
- Server-Sent Events (or WebSocket) keep-alive every **15 s**; client
  auto-reconnects and resumes from the last event id.

### Layout
- **Desktop:** left sidebar (New chat, Search, Projects, Chats, Feed, Archive);
  centre conversation; optional right panel (project files, sources, artifact
  preview).
- **Tablet/phone:** sidebar as drawer; sticky composer; tool/thinking blocks
  collapsed by default; tap targets ≥ 44 px.
- **Theme:** light/dark/system; club branding (logo, accent colour) applied via
  configuration, not code changes.
- **Accessibility:** WCAG 2.2 AA; status changes announced via ARIA live
  region (polite); full keyboard operation; reduced-motion honoured.
