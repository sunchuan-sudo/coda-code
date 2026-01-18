"""Status bar widget for CoDA Code."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Any

from textual.containers import Horizontal
from textual.css.query import NoMatches
from textual.reactive import reactive
from textual.widgets import Static

if TYPE_CHECKING:
    from textual.app import ComposeResult


class StatusBar(Horizontal):
    """Status bar showing mode, auto-approve status, and working directory."""

    DEFAULT_CSS = """
    StatusBar {
        height: 1;
        dock: bottom;
        background: $surface;
        padding: 0 1;
    }

    StatusBar .status-mode {
        width: auto;
        padding: 0 1;
    }

    StatusBar .status-mode.normal {
        display: none;
    }

    StatusBar .status-mode.bash {
        background: #ff1493;
        color: white;
        text-style: bold;
    }

    StatusBar .status-mode.command {
        background: #8b5cf6;
        color: white;
    }

    StatusBar .status-auto-approve {
        width: auto;
        padding: 0 1;
    }

    StatusBar .status-auto-approve.on {
        background: #10b981;
        color: black;
    }

    StatusBar .status-auto-approve.off {
        background: #f59e0b;
        color: black;
    }

    StatusBar .status-message {
        width: auto;
        padding: 0 1;
        color: $text-muted;
    }

    StatusBar .status-message.thinking {
        color: $warning;
    }

    StatusBar .status-cwd {
        width: 1fr;
        text-align: right;
        color: $text-muted;
    }

    # StatusBar .status-tokens {
    #     width: auto;
    #     padding: 0 1;
    #     color: $text-muted;
    # }
    StatusBar .status-tokens {
        width: auto;
        background: yellow;
        color: black;
    }
    
    StatusBar .status-git {
        width: auto;
        padding: 0 1;
        color: $text-muted;
    }

    StatusBar .status-git.main {
        background: #10b981;
        color: black;
    }
    
    StatusBar .status-git.master {
        background: #10b981;
        color: black;
    }

    StatusBar .status-git.feature {
        background: #8b5cf6;
        color: white;
    }

    StatusBar .status-git.develop {
        background: #3b82f6;
        color: white;
    }

    StatusBar .status-git.other {
        background: #6b7280;
        color: white;
    }
    """

    mode: reactive[str] = reactive("normal", init=False)
    status_message: reactive[str] = reactive("", init=False)
    auto_approve: reactive[bool] = reactive(default=False, init=False)
    cwd: reactive[str] = reactive("", init=False)
    tokens: reactive[int] = reactive(0, init=False)
    git_branch: reactive[str] = reactive("", init=False)

    def __init__(self, cwd: str | Path | None = None, **kwargs: Any) -> None:
        """Initialize the status bar.

        Args:
            cwd: Current working directory to display
            **kwargs: Additional arguments passed to parent
        """
        super().__init__(**kwargs)
        # Store initial cwd - will be used in compose()
        self._initial_cwd = str(cwd) if cwd else str(Path.cwd())

    def compose(self) -> ComposeResult:
        """Compose the status bar layout."""
        yield Static("", classes="status-mode normal", id="mode-indicator")
        yield Static(
            "manual | shift+tab to cycle",
            classes="status-auto-approve off",
            id="auto-approve-indicator",
        )
        yield Static("", classes="status-git", id="git-branch")
        yield Static("", classes="status-tokens", id="tokens-display")
        yield Static("", classes="status-message", id="status-message")
        # CWD shown in welcome banner, not pinned in status bar

    def on_mount(self) -> None:
        """Set reactive values after mount to trigger watchers safely."""
        self.cwd = self._initial_cwd
        # Initialize git branch
        self.git_branch = self._get_git_branch(self._initial_cwd)

    def watch_mode(self, mode: str) -> None:
        """Update mode indicator when mode changes."""
        try:
            indicator = self.query_one("#mode-indicator", Static)
        except NoMatches:
            return
        indicator.remove_class("normal", "bash", "command")

        if mode == "bash":
            indicator.update("BASH")
            indicator.add_class("bash")
        elif mode == "command":
            indicator.update("CMD")
            indicator.add_class("command")
        else:
            indicator.update("")
            indicator.add_class("normal")

    def watch_auto_approve(self, new_value: bool) -> None:  # noqa: FBT001
        """Update auto-approve indicator when state changes."""
        try:
            indicator = self.query_one("#auto-approve-indicator", Static)
        except NoMatches:
            return
        indicator.remove_class("on", "off")

        if new_value:
            indicator.update("auto | shift+tab to cycle")
            indicator.add_class("on")
        else:
            indicator.update("manual | shift+tab to cycle")
            indicator.add_class("off")

    def watch_cwd(self, new_value: str) -> None:
        """Update cwd display when it changes and refresh git branch."""
        try:
            display = self.query_one("#cwd-display", Static)
        except NoMatches:
            return
        display.update(self._format_cwd(new_value))
        
        # Update git branch when CWD changes
        # Use call_later to prevent blocking UI thread
        from textual import work
        self.call_later(self._update_git_branch, new_value)
    
    def _update_git_branch(self, cwd: str) -> None:
        """Update git branch in a non-blocking way."""
        self.git_branch = self._get_git_branch(cwd)

    def watch_status_message(self, new_value: str) -> None:
        """Update status message display."""
        try:
            msg_widget = self.query_one("#status-message", Static)
        except NoMatches:
            return

        msg_widget.remove_class("thinking")
        if new_value:
            msg_widget.update(new_value)
            if "thinking" in new_value.lower() or "executing" in new_value.lower():
                msg_widget.add_class("thinking")
        else:
            msg_widget.update("")

    def watch_git_branch(self, new_value: str) -> None:
        """Update git branch display when branch changes."""
        try:
            git_widget = self.query_one("#git-branch", Static)
        except NoMatches:
            return

        # Remove all branch-specific classes
        git_widget.remove_class("main", "master", "feature", "develop", "other")
        
        if new_value:
            # Get branch class for styling
            branch_class = self._get_branch_class(new_value)
            
            # Check if repository has uncommitted changes
            is_dirty = self._get_git_status(self.cwd or self._initial_cwd)
            
            # Update display - add "*" if repository is dirty
            display_text = f"git:{new_value}"
            if is_dirty:
                display_text += "*"
            git_widget.update(display_text)
            git_widget.add_class(branch_class)
        else:
            git_widget.update("")

    def _format_cwd(self, cwd_path: str = "") -> str:
        """Format the current working directory for display."""
        path = Path(cwd_path or self.cwd or self._initial_cwd)
        try:
            # Try to use ~ for home directory
            home = Path.home()
            if path.is_relative_to(home):
                return "~/" + str(path.relative_to(home))
        except (ValueError, RuntimeError):
            pass
        return str(path)

    def _get_git_branch(self, cwd: str) -> str:
        """Get current git branch for directory.
        
        Args:
            cwd: Directory to check for git repository
            
        Returns:
            Git branch name or empty string if not in git repo
        """
        # Skip if cwd is empty
        if not cwd:
            return ""
            
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=0.5  # Reduced timeout to prevent UI blocking
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except (subprocess.SubprocessError, FileNotFoundError, TimeoutError):
            # Silently fail - not a git repo or git not available
            pass
        except Exception:
            # Catch any other exceptions to prevent UI issues
            pass
        return ""

    def _get_git_status(self, cwd: str) -> bool:
        """Check if git repository has uncommitted changes.
        
        Args:
            cwd: Directory to check for git status
            
        Returns:
            True if repository has uncommitted changes
        """
        # Skip if cwd is empty
        if not cwd:
            return False
            
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=0.5  # Reduced timeout to prevent UI blocking
            )
            if result.returncode == 0:
                return bool(result.stdout.strip())
        except (subprocess.SubprocessError, FileNotFoundError, TimeoutError):
            # Silently fail - not a git repo or git not available
            pass
        except Exception:
            # Catch any other exceptions to prevent UI issues
            pass
        return False

    def _get_branch_class(self, branch_name: str) -> str:
        """Get CSS class for git branch based on its name.
        
        Args:
            branch_name: Git branch name
            
        Returns:
            CSS class for styling
        """
        if not branch_name:
            return "other"
        
        branch_lower = branch_name.lower()
        if branch_lower in ["main", "master"]:
            return "main"
        elif branch_lower.startswith("feature/") or branch_lower.startswith("feat/"):
            return "feature"
        elif branch_lower == "develop" or branch_lower.startswith("dev/"):
            return "develop"
        else:
            return "other"

    def set_mode(self, mode: str) -> None:
        """Set the current input mode.

        Args:
            mode: One of "normal", "bash", or "command"
        """
        self.mode = mode

    def set_auto_approve(self, *, enabled: bool) -> None:
        """Set the auto-approve state.

        Args:
            enabled: Whether auto-approve is enabled
        """
        self.auto_approve = enabled

    def set_status_message(self, message: str) -> None:
        """Set the status message.

        Args:
            message: Status message to display (empty string to clear)
        """
        self.status_message = message

    def watch_tokens(self, new_value: int) -> None:
        """Update token display when count changes."""
        try:
            display = self.query_one("#tokens-display", Static)
        except NoMatches:
            return

        if new_value > 0:
            # Format with K suffix for thousands
            if new_value >= 1000:
                display.update(f"{new_value / 1000:.1f}K tokens")
            else:
                display.update(f"{new_value} tokens")
        else:
            display.update("")

    def set_tokens(self, count: int) -> None:
        """Set the token count.

        Args:
            count: Current context token count
        """
        self.tokens = count

    def refresh_git_branch(self) -> None:
        """Refresh git branch information from current directory."""
        self.git_branch = self._get_git_branch(self.cwd or self._initial_cwd)
