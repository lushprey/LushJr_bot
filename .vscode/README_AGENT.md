# README Agent Instructions

This agent automatically generates and updates the README.md file whenever project files change.

## Quick Start

### Option 1: Update README Now
```
Terminal → Run Task → "README Agent: Update Now"
```
Or press `Ctrl+Shift+P` → `Tasks: Run Task` → select "README Agent: Update Now"

### Option 2: Watch Mode (Automatic Updates)
```
Terminal → Run Task → "README Agent: Watch Files"
```
The agent will monitor all `.py`, `.txt`, and `.md` files and regenerate README automatically when changes are detected. Press `Ctrl+C` to stop watching.

### Option 3: Command Line
```bash
# Update README once
python readme_agent.py

# Watch for changes and update automatically
python readme_agent.py --watch

# Watch a specific folder
python readme_agent.py --watch --path ./core
```

## First-Time Setup

1. Install file watcher dependency:
   ```
   Terminal → Run Task → "README Agent: Install Dependencies"
   ```
   Or manually: `pip install watchdog`

2. Run the agent at least once to generate initial README

## What Gets Updated

- ✅ Project directory structure (file tree)
- ✅ Component listing with descriptions from docstrings
- ✅ Dependencies from `requirements.txt`
- ✅ Installation instructions
- ✅ Environment variables reference
- ✅ Last update timestamp

## Customization

### To Preserve Custom Sections
Edit `readme_agent.py` and modify the `generate()` method to preserve your custom sections. The current version focuses on auto-generated content.

### To Add Custom Content
Create a `README.template.md` and the agent will merge auto-generated content with your template:
```python
# In readme_agent.py
# Load template if it exists
template_path = self.root_path / "README.template.md"
if template_path.exists():
    custom = template_path.read_text()
    # Merge with generated content
```

## When to Use

- **After adding new Python files** → Auto-updates structure
- **After updating dependencies** → Auto-updates dependency list
- **After changing module docstrings** → Auto-updates component descriptions
- **When project structure changes** → Auto-detects and reflects changes

## Tips

- Use clear docstrings in your Python modules - the agent extracts the first line as description
- Keep `requirements.txt` updated - changes are automatically reflected
- The `.env` file and `.git/` are ignored by the agent
- If README.md has unsaved changes, the agent will overwrite them

## Keyboard Shortcuts

Add to `.vscode/keybindings.json` for quick access:

```json
{
  "key": "ctrl+shift+r",
  "command": "workbench.action.tasks.runTask",
  "args": "README Agent: Update Now"
},
{
  "key": "ctrl+shift+w",
  "command": "workbench.action.tasks.runTask",
  "args": "README Agent: Watch Files"
}
```

Then:
- `Ctrl+Shift+R` → Update README immediately
- `Ctrl+Shift+W` → Start watching for changes
