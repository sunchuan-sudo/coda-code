# CoDA Code — Cooperative Development Agent

A terminal-based AI coding assistant with multi-LLM support, a rich Textual TUI,
human-in-the-loop approvals, remote sandbox execution, and extensible agent skills.

---

## Features

- **Multi-LLM** — OpenAI, Anthropic, Google, DeepSeek. Auto-detects provider from model name or API key.
- **Rich TUI** — Textual-based interface with markdown streaming, collapsible tool calls, diff highlighting, status bar (mode, git branch, tokens, CWD).
- **File Ops** — read/write/edit files with diff previews; `ls`, `glob`, `grep`.
- **Shell** — Agent shell with timeout; user bash via `!` prefix.
- **Web** — Search (Tavily), URL fetch, HTTP requests.
- **Remote Sandboxes** — Execute code in isolated environments via [Modal](https://modal.com), [Daytona](https://daytona.io), or [Runloop](https://runloop.dev).
- **Conversations** — Thread persistence via SQLite. Resume with `--resume`.
- **HITL** — Review/approve/reject tool calls before execution.
- **Sub-Agents** — Delegate tasks to parallel sub-agents.
- **Skills** — Custom skills in `~/.coda/<agent>/skills/`. Follows [Agent Skills spec](https://agentskills.io/specification).
- **Image** (macOS) — Paste clipboard images for vision models.
- **Clipboard** — Copy via OSC 52 (SSH/tmux) or pyperclip.

## Quick Start

```bash
# Install
uv tool install coda-code

# Create .env with at least one API key
echo "DEEPSEEK_API_KEY=sk-..." > .env

# Run
coda
```

## CLI Usage

| Command | Description |
|---|---|
| `coda` | Start interactive TUI session |
| `coda --model <MODEL>` | Use specific model (auto-detects provider) |
| `coda -r [THREAD_ID]` | Resume most recent or specific thread |
| `coda --auto-approve` | Disable HITL, auto-approve all tools |
| `coda --sandbox <modal\|daytona\|runloop>` | Execute in remote sandbox |
| `coda threads list` | List conversation threads |
| `coda threads delete <ID>` | Delete a thread |
| `coda skills list [--project]` | List agent skills |

In-chat: `!command` for bash, `/command` for slash commands, `@file` to inject file content.

## Requirements

- Python 3.11+
- At least one API key: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`, or `DEEPSEEK_API_KEY`
- Optional: `TAVILY_API_KEY` (web search), sandbox keys for remote execution

## Architecture

1. **deepagents** — Agent execution, middleware stack, backend protocols
2. **Textual TUI** — `CoDACodeApp` chat interface, approval dialogs, diff viewer, autocomplete
3. **Tools & Integrations** — File ops, shell, web tools, sandbox backends, skills

## License

[Apache License 2.0](LICENSE)

