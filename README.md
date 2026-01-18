# CoDA Code
CoDA Code is a terminal-based AI coding assistant.

## Key Features
- **Terminal-based AI Assistant**: Interactive coding agent that lives in your terminal with conversation memory and persistent threads
- **Sandbox Execution**: Run code safely in isolated environments (Modal, Runloop, Daytona, or local)

## Model Configuration
- **Environment Setup**: Configure API keys (OpenAI, Tavily, **DeepSeek**) and dependencies via `.env` file
- **Model Support**: Compatible with OpenAI models (GPT-4, GPT-3.5) and **DeepSeek** models via LangChain integration

## Built-in Tools

| Tool | Description | Middleware Integration |
|------|-------------|------------------------|
| **Shell Execution** | Run bash commands in isolated environments | ShellMiddleware for safe command execution |
| **Filesystem Operations** | Read, write, edit, and search files | FilesystemBackend for file management |
| **Web Search** | Search the web using Tavily API | Tavily client integration via HTTP middleware |
| **HTTP Requests** | Make API calls (GET, POST, PUT, DELETE) | Requests library with timeout/error handling |
| **URL Fetching** | Fetch web pages and convert to markdown | Markdownify integration for HTML processing |
| **Subagent Delegation** | Spawn parallel agents for complex tasks | Task tool with isolated context windows |
| **Clipboard Integration** | Copy/paste between terminal and system | System clipboard access via platform APIs |
| **Image Utilities** | Process and analyze images | Pillow integration for image manipulation |

## Customization
- **Agent Configuration**: Create custom agents with specific prompts and tool sets in `~/.coda/agent/` directory. Each agent has its own `AGENTS.md` file defining behavior, tools, and memory settings
- **Skill System**: Add custom skills in `.coda/skills/` directory with SKILL.md instructions and supporting scripts. Skills follow progressive disclosure pattern and can be executed via skill-specific workflows

## Development
- **Local Setup**: Install with `uv sync`, development mode with `uv run coda` in project directory
- **Testing**: Run tests with `pytest`, lint with `ruff`, type check with `mypy`
- **Python Version**: This project requires Python 3.11+. Always use `python3` and `pip3` commands to ensure the correct Python version is used.

