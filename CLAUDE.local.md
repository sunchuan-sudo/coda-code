# CLAUDE.local.md - Local Configuration & Notes

> Template for local project configuration, notes, and development instructions. Edit as needed.

## Project Overview
- **Name**: CoDA Code
- **Description**: Coding agent that lives in your terminal
- **Version**: 0.1.0 (from pyproject.toml)
- **Language**: Python 3.11+

## Local Development Setup
### Python Environment
- Python version: >=3.11,<4.0
- **Important**: Always use `python3` command to ensure Python 3.x is used (not Python 2.7)
- Package manager: uv (from tool.uv.sources in pyproject.toml)
- Dependencies: See `pyproject.toml`

### Installation
```bash
# Install all dependencies including development dependencies
uv sync --group dev
```

### Development Dependencies
- Test dependencies: `pytest`, `pytest-cov`, `pytest-asyncio`, etc.
- Linting: `ruff`, `mypy`
- Build: `build`, `twine`

## Environment Variables
Create a `.env` file in project root with necessary variables:
```
# Example - adjust based on actual requirements
OPENAI_API_KEY=your_key_here
TAVILY_API_KEY=your_key_here
```

## Development Commands
### Running Tests
```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov=coda_cli tests/

# Run specific test file
pytest tests/unit_tests/test_config.py
```

**Note**: Test dependencies are installed with `uv sync --group dev`

### Linting & Formatting
```bash
# Run ruff linter
ruff check .

# Run ruff formatter
ruff format .

# Type checking with mypy
mypy .
```

### Building & Distribution
```bash
# Build package
python3 -m build

# Check distribution
twine check dist/*
```

## Project Structure
- `coda_cli/` - Main package
- `tests/` - Test files
- `pyproject.toml` - Project configuration
- `README.md` - Project documentation

## Agent Configuration
- LangChain integration
- SQLite checkpointing via `langgraph-checkpoint-sqlite`

## Development Notes
- Add any local setup quirks, workarounds, or custom configurations here
- Document any local paths, network configurations, or proxy settings
- Note any platform-specific issues (macOS/Linux/Windows)

## How to Test

### Setup
```bash
# Install dependencies (includes test dependencies)
uv sync --group dev

# Install local deepagents (required)
cd ../deepagents && uv pip install -e . && cd -
```

### Run Tests
```bash
pytest
```

### Test Info
- Uses Python 3.11+
- 10 second timeout default
- Some tests skipped if external services not available

## Deployment
- Modal deployment support (`modal>=0.65.0`)
- Daytona integration (`daytona>=0.113.0`)

## Troubleshooting
- Common issues and their solutions
- Dependency conflicts resolution
- Environment setup problems

### Python Version Issues
**IMPORTANT**: This project requires Python 3.11+.
- Use `uv` for package management (preferred)
- If using pip, use `pip3` or `python3 -m pip` to ensure Python 3 is used
- Check Python version with: `python3 --version`
- Check uv version with: `uv --version`

---

*This file is auto-generated template. Edit with your local configuration details.*