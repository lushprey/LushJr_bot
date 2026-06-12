"""
readme_agent.py
───────────────
Automatic README generator that watches for project file changes.
Updates README.md automatically with current project structure and documentation.

Usage:
    python -m agents.readme_agent          # Run once
    python -m agents.readme_agent --watch  # Watch for changes (Ctrl+C to stop)
    
    Or directly:
    python agents/readme_agent.py          # Run once
    python agents/readme_agent.py --watch  # Watch for changes (Ctrl+C to stop)
"""

import os
import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict

# Optional: watchdog for file monitoring
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False


class ProjectAnalyzer:
    """Analyzes project structure and generates README content."""
    
    def __init__(self, root_path: str = "."):
        self.root_path = Path(root_path).resolve()
        self.project_name = self.root_path.name
    
    def get_structure_tree(self) -> str:
        """Generate directory tree structure."""
        ignore_dirs = {'.git', '__pycache__', '.venv', 'venv', 'node_modules', '.vscode', '.idea'}
        ignore_files = {'.gitignore', '.env', '.DS_Store', '*.pyc'}
        
        lines = [f"{self.project_name}/"]
        
        def add_tree(path: Path, prefix: str = "", is_last: bool = True):
            try:
                items = sorted([p for p in path.iterdir() 
                               if p.name not in ignore_dirs and 
                               not any(p.name.endswith(ext) for ext in ignore_files)])
            except PermissionError:
                return
            
            for i, item in enumerate(items):
                is_last_item = i == len(items) - 1
                current_prefix = "└── " if is_last_item else "├── "
                next_prefix = "    " if is_last_item else "│   "
                
                lines.append(f"{prefix}{current_prefix}{item.name}{'/' if item.is_dir() else ''}")
                
                if item.is_dir() and item.name not in ignore_dirs:
                    add_tree(item, prefix + next_prefix, is_last_item)
        
        add_tree(self.root_path)
        return "\n".join(lines)
    
    def get_dependencies(self) -> List[str]:
        """Extract dependencies from requirements.txt."""
        req_file = self.root_path / "requirements.txt"
        if req_file.exists():
            return [line.strip() for line in req_file.read_text().split('\n') 
                    if line.strip() and not line.startswith('#')]
        return []
    
    def get_python_files(self) -> Dict[str, List[str]]:
        """Get all Python files organized by directory."""
        files_by_dir = {}
        for py_file in self.root_path.rglob("*.py"):
            if '__pycache__' in py_file.parts:
                continue
            rel_path = py_file.relative_to(self.root_path)
            dir_name = str(rel_path.parent) if rel_path.parent != Path(".") else "root"
            if dir_name not in files_by_dir:
                files_by_dir[dir_name] = []
            files_by_dir[dir_name].append(rel_path.name)
        return files_by_dir
    
    def extract_docstrings(self) -> Dict[str, str]:
        """Extract module docstrings from Python files."""
        docstrings = {}
        for py_file in self.root_path.rglob("*.py"):
            if '__pycache__' in py_file.parts:
                continue
            try:
                content = py_file.read_text(encoding='utf-8')
                # Simple extraction of first docstring
                if '"""' in content:
                    start = content.find('"""') + 3
                    end = content.find('"""', start)
                    if end > start:
                        rel_path = py_file.relative_to(self.root_path)
                        docstrings[str(rel_path)] = content[start:end].strip().split('\n')[0]
            except Exception:
                pass
        return docstrings


class ReadmeGenerator:
    """Generates README.md content from project analysis."""
    
    def __init__(self, analyzer: ProjectAnalyzer):
        self.analyzer = analyzer
    
    def generate(self) -> str:
        """Generate complete README content."""
        dependencies = self.analyzer.get_dependencies()
        structure = self.analyzer.get_structure_tree()
        python_files = self.analyzer.get_python_files()
        docstrings = self.analyzer.extract_docstrings()
        
        content = []
        
        # Header
        content.append(f"# {self.analyzer.project_name}\n")
        content.append("_Auto-generated README - Last updated: {}_\n".format(
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        
        # Project Description (try to preserve from existing README)
        content.append("## Overview\n")
        content.append("Telegram bot with AI integration and calendar management.\n")
        
        # Directory Structure
        content.append("## Project Structure\n")
        content.append("```")
        content.append(structure)
        content.append("```\n")
        
        # Python Files & Documentation
        if python_files:
            content.append("## Components\n")
            for dir_name in sorted(python_files.keys()):
                content.append(f"### {dir_name.replace('/', ' / ').title()}\n")
                for file_name in sorted(python_files[dir_name]):
                    file_path = f"{dir_name}/{file_name}" if dir_name != "root" else file_name
                    content.append(f"- **{file_name}**")
                    if file_path in docstrings:
                        content.append(f" — {docstrings[file_path]}")
                    content.append("")
                content.append("")
        
        # Dependencies
        if dependencies:
            content.append("## Dependencies\n")
            content.append("```")
            for dep in dependencies:
                content.append(dep)
            content.append("```\n")
        
        # Quick Start
        content.append("## Quick Start\n")
        content.append("```bash")
        content.append("pip install -r requirements.txt")
        content.append("python main.py")
        content.append("```\n")
        
        # Environment Variables (if mentioned in main.py)
        content.append("## Configuration\n")
        content.append("Set up the following environment variables in a `.env` file:\n")
        content.append("- `TELEGRAM_TOKEN`")
        content.append("- `NVIDIA_API_KEY`")
        content.append("- `NOTION_TOKEN`")
        content.append("- `DATABASE_ID`\n")
        
        return "\n".join(content)


class FileWatcher(FileSystemEventHandler):
    """Watches for file changes and triggers README updates."""
    
    def __init__(self, callback):
        self.callback = callback
        self.last_update = 0
    
    def on_modified(self, event):
        if event.is_directory:
            return
        if self._should_trigger(event.src_path):
            self.callback()
    
    def on_created(self, event):
        if not event.is_directory and self._should_trigger(event.src_path):
            self.callback()
    
    def on_deleted(self, event):
        if not event.is_directory and self._should_trigger(event.src_path):
            self.callback()
    
    @staticmethod
    def _should_trigger(file_path: str) -> bool:
        """Check if file change should trigger README update."""
        ignore = {'.env', '.git', '__pycache__', '.vscode', 'agents'}
        path = Path(file_path)
        if any(part in ignore for part in path.parts):
            return False
        if path.suffix in {'.py', '.txt', '.md'}:
            return True
        return False


class ReadmeAgent:
    """Main agent coordinating README updates."""
    
    def __init__(self, root_path: str = "."):
        self.root_path = root_path
        self.analyzer = ProjectAnalyzer(root_path)
        self.generator = ReadmeGenerator(self.analyzer)
        self.readme_path = Path(root_path) / "README.md"
    
    def update_readme(self) -> bool:
        """Generate and write README.md."""
        try:
            content = self.generator.generate()
            self.readme_path.write_text(content, encoding='utf-8')
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[{timestamp}] ✓ README.md updated successfully")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to update README.md: {e}")
            return False
    
    def watch(self):
        """Watch for file changes and update README automatically."""
        if not WATCHDOG_AVAILABLE:
            print("ERROR: watchdog not installed. Run: pip install watchdog")
            sys.exit(1)
        
        observer = Observer()
        event_handler = FileWatcher(self.update_readme)
        
        observer.schedule(event_handler, self.root_path, recursive=True)
        observer.start()
        
        print(f"👀 Watching {self.root_path} for changes...")
        print("Press Ctrl+C to stop\n")
        
        try:
            while True:
                observer.join(timeout=1)
        except KeyboardInterrupt:
            print("\n✓ Watcher stopped")
            observer.stop()
            observer.join()


def main():
    parser = argparse.ArgumentParser(
        description="Automatic README generator for your project"
    )
    parser.add_argument(
        '--watch', '-w',
        action='store_true',
        help='Watch for file changes and update README automatically'
    )
    parser.add_argument(
        '--path', '-p',
        default='.',
        help='Root path of project (default: current directory)'
    )
    
    args = parser.parse_args()
    
    agent = ReadmeAgent(args.path)
    
    if args.watch:
        agent.watch()
    else:
        agent.update_readme()


if __name__ == "__main__":
    main()
