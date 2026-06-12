# Agents

Automated agents for project management and maintenance tasks in the LushJr Bot.

## Overview

All agents are centralized in this folder to keep the project organized. Each agent handles a specific automation task.

## Available Agents

### 🗑️ Cache Agent (`cache_agent.py`)

Automatically cleans Python cache files during VS Code development.

**Features:**
- ✅ Removes `__pycache__`, `.pyc`, `.pyo`, `.pytest_cache`, `.mypy_cache`
- ✅ Only runs in VS Code (production-safe)
- ✅ Optional watch mode for auto-cleanup on file changes

**Usage:**
```bash
# One-time cleanup
python agents/cache_agent.py

# Watch mode (auto-cleanup)
python agents/cache_agent.py --watch

# Show environment info
python agents/cache_agent.py --info

# Force cleanup (not recommended)
python agents/cache_agent.py --force
```

**From root with module syntax:**
```bash
python -m agents.cache_agent
python -m agents.cache_agent --watch
python -m agents.cache_agent --info
```

---

### 📖 README Agent (`readme_agent.py`)

Automatically generates and updates `README.md` from project structure.

**Features:**
- ✅ Auto-generates project structure tree
- ✅ Extracts dependencies from `requirements.txt`
- ✅ Collects Python file docstrings
- ✅ Optional watch mode for continuous updates

**Usage:**
```bash
# One-time README update
python agents/readme_agent.py

# Watch mode (auto-update on changes)
python agents/readme_agent.py --watch

# Custom project path
python agents/readme_agent.py --path /path/to/project
```

**From root with module syntax:**
```bash
python -m agents.readme_agent
python -m agents.readme_agent --watch
```

---

## Quick Start

### Run All Agents Once
```bash
python agents/cache_agent.py
python agents/readme_agent.py
```

### Run All Agents in Watch Mode
Start multiple terminals:

**Terminal 1:**
```bash
python agents/cache_agent.py --watch
```

**Terminal 2:**
```bash
python agents/readme_agent.py --watch
```

---

## Installation

All agents use only standard Python libraries. Optional dependencies:

### Optional: File Watching (watchdog)

For `--watch` mode on both agents:
```bash
pip install watchdog
```

Add to `requirements.txt`:
```
watchdog>=3.0.0
```

---

## Environment Detection

The Cache Agent detects VS Code by checking:
- `TERM_PROGRAM` environment variable
- `VSCODE_IPC_HOOK` environment variable
- `VSCODE_CWD` environment variable
- `.vscode/` folder presence

**Production Safety:** Cleanup is disabled outside VS Code to prevent accidental cache removal in production.

---

## Directory Structure

```
agents/
├── __init__.py           # Package initialization
├── cache_agent.py        # Cache cleaning agent
├── readme_agent.py       # README generation agent
└── README.md            # This file
```

---

## Running from VS Code Terminal

Add these to your VS Code tasks (`.vscode/tasks.json`) for quick access:

```json
{
    "label": "Cache Agent: Clean",
    "type": "shell",
    "command": "python",
    "args": ["agents/cache_agent.py"],
    "problemMatcher": []
},
{
    "label": "Cache Agent: Watch",
    "type": "shell",
    "command": "python",
    "args": ["agents/cache_agent.py", "--watch"],
    "isBackground": true,
    "problemMatcher": []
},
{
    "label": "README Agent: Update",
    "type": "shell",
    "command": "python",
    "args": ["agents/readme_agent.py"],
    "problemMatcher": []
},
{
    "label": "README Agent: Watch",
    "type": "shell",
    "command": "python",
    "args": ["agents/readme_agent.py", "--watch"],
    "isBackground": true,
    "problemMatcher": []
}
```

Then run with `Ctrl+Shift+B` (Run Task) in VS Code.

---

## Troubleshooting

### Module not found
Ensure you're running from the project root directory:
```bash
cd /path/to/LushJr_bot
python -m agents.cache_agent
```

### Watchdog not available
Install watchdog for watch mode:
```bash
pip install watchdog
```

### Permission denied errors
The agents skip files they can't access but continue cleaning others. Run with appropriate permissions if needed.

---

## Future Agents

Potential agents to add:
- 🧪 Test Runner Agent - Run tests automatically
- 🔍 Linter Agent - Auto-format and lint code
- 📊 Metrics Agent - Generate project metrics
- 🚀 Deployment Agent - Pre-deployment checks

---

**Last Updated:** 2026-06-12
