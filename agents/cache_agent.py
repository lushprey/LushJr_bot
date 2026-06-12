"""
cache_agent.py
──────────────
Automatic cache cleaner that only runs in VS Code development environment.
Safely removes Python cache files (__pycache__, *.pyc, *.pyo) to maintain clean state.

Detects VS Code environment and skips cleanup in production deployments.

Usage:
    python -m agents.cache_agent          # Clean cache once
    python -m agents.cache_agent --watch  # Watch for changes and auto-clean (Ctrl+C to stop)
    python -m agents.cache_agent --info   # Show environment info without cleaning
    
    Or directly:
    python agents/cache_agent.py          # Clean cache once
    python agents/cache_agent.py --watch  # Watch for changes and auto-clean
    python agents/cache_agent.py --info   # Show environment info without cleaning
"""

import os
import sys
import shutil
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Tuple

# Optional: watchdog for file monitoring
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False


class EnvironmentDetector:
    """Detects if running in VS Code or production environment."""
    
    @staticmethod
    def is_vscode() -> bool:
        """
        Check if running in VS Code development environment.
        Returns True only if in VS Code, False for production/other environments.
        """
        indicators = [
            os.getenv("TERM_PROGRAM") == "vscode",  # Terminal.app integration
            os.getenv("VSCODE_IPC_HOOK") is not None,  # VS Code IPC hook
            os.getenv("VSCODE_CWD") is not None,  # VS Code working directory
            Path(".vscode").exists(),  # Local .vscode folder
        ]
        return any(indicators)
    
    @staticmethod
    def get_environment_info() -> dict:
        """Get detailed environment information."""
        return {
            "is_vscode": EnvironmentDetector.is_vscode(),
            "term_program": os.getenv("TERM_PROGRAM"),
            "vscode_ipc_hook": bool(os.getenv("VSCODE_IPC_HOOK")),
            "vscode_cwd": bool(os.getenv("VSCODE_CWD")),
            "has_vscode_folder": Path(".vscode").exists(),
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        }


class CacheManager:
    """Manages Python cache files and directories."""
    
    # Cache patterns to remove
    CACHE_PATTERNS = ["__pycache__", "*.pyc", "*.pyo", "*.pyd", ".pytest_cache", ".mypy_cache"]
    IGNORE_DIRS = {".git", ".venv", "venv", "env", "node_modules", ".idea", ".vscode", "agents"}
    
    def __init__(self, root_path: str = "."):
        self.root_path = Path(root_path).resolve()
        self.cleaned_items: List[Path] = []
        self.stats = {"dirs": 0, "files": 0, "skipped": 0}
    
    def clean_cache(self) -> Tuple[int, int]:
        """
        Recursively clean cache files from project root.
        Returns: (directories_removed, files_removed)
        """
        self._scan_and_clean(self.root_path)
        return self.stats["dirs"], self.stats["files"]
    
    def _scan_and_clean(self, path: Path) -> None:
        """Recursively scan and clean cache from path."""
        try:
            for item in path.iterdir():
                # Skip ignored directories
                if item.is_dir() and item.name in self.IGNORE_DIRS:
                    continue
                
                # Remove __pycache__ directories
                if item.is_dir() and item.name == "__pycache__":
                    try:
                        shutil.rmtree(item)
                        self.cleaned_items.append(item)
                        self.stats["dirs"] += 1
                    except Exception as e:
                        print(f"  ⚠ Failed to remove {item}: {e}")
                        self.stats["skipped"] += 1
                
                # Remove cache files
                elif item.is_file() and item.suffix in {".pyc", ".pyo", ".pyd"}:
                    try:
                        item.unlink()
                        self.cleaned_items.append(item)
                        self.stats["files"] += 1
                    except Exception as e:
                        print(f"  ⚠ Failed to remove {item}: {e}")
                        self.stats["skipped"] += 1
                
                # Remove pytest cache
                elif item.is_dir() and item.name == ".pytest_cache":
                    try:
                        shutil.rmtree(item)
                        self.cleaned_items.append(item)
                        self.stats["dirs"] += 1
                    except Exception as e:
                        print(f"  ⚠ Failed to remove {item}: {e}")
                        self.stats["skipped"] += 1
                
                # Remove mypy cache
                elif item.is_dir() and item.name == ".mypy_cache":
                    try:
                        shutil.rmtree(item)
                        self.cleaned_items.append(item)
                        self.stats["dirs"] += 1
                    except Exception as e:
                        print(f"  ⚠ Failed to remove {item}: {e}")
                        self.stats["skipped"] += 1
                
                # Recurse into subdirectories
                elif item.is_dir():
                    self._scan_and_clean(item)
        
        except PermissionError as e:
            print(f"  ⚠ Permission denied: {path}")
        except Exception as e:
            print(f"  ⚠ Error scanning {path}: {e}")
    
    def get_report(self) -> str:
        """Generate a human-readable cleanup report."""
        report = [
            f"📊 Cache Cleanup Report",
            f"├─ Directories removed: {self.stats['dirs']}",
            f"├─ Files removed: {self.stats['files']}",
            f"├─ Items skipped: {self.stats['skipped']}",
            f"└─ Total cleaned: {len(self.cleaned_items)} items",
        ]
        
        if self.cleaned_items:
            report.append(f"\n📝 Cleaned items:")
            for item in self.cleaned_items[:10]:  # Show first 10
                rel_path = item.relative_to(self.root_path)
                report.append(f"   ✓ {rel_path}")
            
            if len(self.cleaned_items) > 10:
                report.append(f"   ... and {len(self.cleaned_items) - 10} more")
        
        return "\n".join(report)


class CacheWatcher(FileSystemEventHandler):
    """Watches for Python file changes and triggers cache cleanup."""
    
    def __init__(self, cache_manager: CacheManager, debounce_seconds: float = 2.0):
        self.cache_manager = cache_manager
        self.debounce_seconds = debounce_seconds
        self.last_cleanup = datetime.now()
        self.pending_extensions = {".py", ".pyc", ".pyo"}
    
    def on_modified(self, event):
        """React to file modifications."""
        if not event.is_directory:
            path = Path(event.src_path)
            if path.suffix in self.pending_extensions:
                self._maybe_clean()
    
    def on_created(self, event):
        """React to file creation."""
        if not event.is_directory:
            path = Path(event.src_path)
            if path.suffix in self.pending_extensions:
                self._maybe_clean()
    
    def _maybe_clean(self):
        """Clean cache if enough time has passed since last cleanup."""
        now = datetime.now()
        elapsed = (now - self.last_cleanup).total_seconds()
        
        if elapsed >= self.debounce_seconds:
            self.last_cleanup = now
            print(f"\n⏱ [{now.strftime('%H:%M:%S')}] Change detected, cleaning cache...")
            dirs_removed, files_removed = self.cache_manager.clean_cache()
            if dirs_removed or files_removed:
                print(f"✅ Cleaned: {dirs_removed} directories, {files_removed} files")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Automatic cache cleaner for VS Code development"
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Watch for changes and auto-clean cache (Ctrl+C to stop)"
    )
    parser.add_argument(
        "--info",
        action="store_true",
        help="Show environment information without cleaning"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force cleanup even if not in VS Code (use with caution)"
    )
    
    args = parser.parse_args()
    
    # Show environment info
    env_detector = EnvironmentDetector()
    is_vscode = env_detector.is_vscode()
    
    print("🔍 Cache Agent - Environment Detection")
    print("─" * 50)
    
    env_info = env_detector.get_environment_info()
    print(f"Running in VS Code: {'✅ Yes' if is_vscode else '❌ No'}")
    print(f"Python version: {env_info['python_version']}")
    
    if args.info:
        print("\n📋 Detailed Environment Info:")
        for key, value in env_info.items():
            print(f"  {key}: {value}")
        return 0
    
    # Check if we should proceed
    if not is_vscode and not args.force:
        print("\n⚠️  Cache cleanup is disabled in production.")
        print("💡 Tip: Run with --force to override (not recommended)")
        return 1
    
    if args.force and not is_vscode:
        print("\n⚠️  Warning: Forcing cleanup outside VS Code environment!")
    
    # Initialize cache manager
    cache_manager = CacheManager()
    
    if args.watch:
        if not WATCHDOG_AVAILABLE:
            print("\n❌ Watchdog not installed. Install with: pip install watchdog")
            return 1
        
        print("\n👀 Watching for changes (Press Ctrl+C to stop)...")
        print("─" * 50)
        
        watcher = CacheWatcher(cache_manager)
        observer = Observer()
        observer.schedule(watcher, str(cache_manager.root_path), recursive=True)
        observer.start()
        
        try:
            observer.join()
        except KeyboardInterrupt:
            print("\n\n✋ Stopped watching")
            observer.stop()
            observer.join()
    
    else:
        print("\n🧹 Cleaning cache...")
        print("─" * 50)
        dirs_removed, files_removed = cache_manager.clean_cache()
        print(cache_manager.get_report())
        
        if dirs_removed or files_removed:
            print(f"\n✅ Cleanup complete!")
        else:
            print(f"\n✨ Cache already clean!")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
