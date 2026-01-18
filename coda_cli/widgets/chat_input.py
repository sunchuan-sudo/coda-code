"""Chat input widget for CoDA Code with autocomplete and history support."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

from rich.text import Text
from textual import events  # noqa: TC002 - used at runtime in _on_key
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Static, TextArea

from coda_cli.widgets.autocomplete import (
    SLASH_COMMANDS,
    CompletionResult,
    FuzzyFileController,
    MultiCompletionManager,
    SlashCommandController,
)
from coda_cli.widgets.history import HistoryManager

if TYPE_CHECKING:
    from textual.app import ComposeResult


class CompletionPopup(Static):
    """Popup widget that displays completion suggestions."""

    DEFAULT_CSS = """
    CompletionPopup {
        display: none;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the completion popup."""
        super().__init__("", **kwargs)
        self.can_focus = False

    def update_suggestions(self, suggestions: list[tuple[str, str]], selected_index: int) -> None:
        """Update the popup with new suggestions."""
        if not suggestions:
            self.hide()
            return

        text = Text()
        for idx, (label, description) in enumerate(suggestions):
            if idx:
                text.append("\n")

            if idx == selected_index:
                label_style = "bold reverse"
                desc_style = "italic"
            else:
                label_style = "bold"
                desc_style = "dim"

            text.append(label, style=label_style)
            if description:
                text.append("  ")
                text.append(description, style=desc_style)

        self.update(text)
        self.show()

    def hide(self) -> None:
        """Hide the popup."""
        self.update("")
        self.styles.display = "none"

    def show(self) -> None:
        """Show the popup."""
        self.styles.display = "block"


class ChatTextArea(TextArea):
    """TextArea subclass with custom key handling for chat input."""

    BINDINGS: ClassVar[list[Binding]] = [
        Binding(
            "shift+enter,ctrl+j,alt+enter,ctrl+enter",
            "insert_newline",
            "New Line",
            show=False,
            priority=True,
        ),
        # Emacs-style navigation bindings
        Binding("ctrl+a", "move_to_line_start", "Start of Line", show=False, priority=True),
        Binding("ctrl+e", "move_to_line_end", "End of Line", show=False, priority=True),
        Binding("ctrl+f", "move_forward", "Forward Char", show=False, priority=True),
        Binding("ctrl+b", "move_backward", "Backward Char", show=False, priority=True),
        # Emacs-style editing bindings
        Binding("ctrl+d", "delete_forward", "Delete Forward", show=False, priority=True),
        Binding("ctrl+h", "delete_backward", "Delete Backward", show=False, priority=True),
        Binding("ctrl+k", "kill_to_line_end", "Kill to Line End", show=False, priority=True),
        Binding("ctrl+w", "kill_previous_word", "Kill Previous Word", show=False, priority=True),
        Binding("ctrl+y", "yank", "Yank", show=False, priority=True),
        Binding("ctrl+_,ctrl+/", "undo", "Undo", show=False, priority=True),
        Binding("ctrl+shift+_,ctrl+shift+/", "redo", "Redo", show=False, priority=True),
        # Mac Cmd+Z/Cmd+Shift+Z for undo/redo (in addition to Ctrl+Z/Y)
        Binding("cmd+z,super+z", "undo", "Undo", show=False, priority=True),
        Binding("cmd+shift+z,super+shift+z", "redo", "Redo", show=False, priority=True),
    ]

    class Submitted(Message):
        """Message sent when text is submitted."""

        def __init__(self, value: str) -> None:
            """Initialize with submitted value."""
            self.value = value
            super().__init__()

    class HistoryPrevious(Message):
        """Request previous history entry."""

        def __init__(self, current_text: str) -> None:
            """Initialize with current text for saving."""
            self.current_text = current_text
            super().__init__()

    class HistoryNext(Message):
        """Request next history entry."""

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the chat text area."""
        # Remove placeholder if passed, TextArea doesn't support it the same way
        kwargs.pop("placeholder", None)
        super().__init__(**kwargs)
        self._navigating_history = False
        self._completion_active = False
        self._app_has_focus = True
        self._killed_text = ""  # For Emacs kill/yank operations

    def set_app_focus(self, *, has_focus: bool) -> None:
        """Set whether the app should show the cursor as active.

        When has_focus=False (e.g., agent is running), disables cursor blink
        so the cursor doesn't flash while waiting for a response.
        """
        self._app_has_focus = has_focus
        self.cursor_blink = has_focus
        if has_focus and not self.has_focus:
            self.call_after_refresh(self.focus)

    def set_completion_active(self, *, active: bool) -> None:
        """Set whether completion suggestions are visible."""
        self._completion_active = active

    def action_insert_newline(self) -> None:
        """Insert a newline character."""
        self.insert("\n")

    def action_select_all_text(self) -> None:
        """Select all text in the text area."""
        if not self.text:
            return
        # Select from start to end
        lines = self.text.split("\n")
        end_row = len(lines) - 1
        end_col = len(lines[end_row])
        self.selection = ((0, 0), (end_row, end_col))

    def action_move_to_line_start(self) -> None:
        """Move cursor to start of current line (Emacs Ctrl+A)."""
        row, col = self.cursor_location
        self.move_cursor((row, 0))

    def action_move_to_line_end(self) -> None:
        """Move cursor to end of current line (Emacs Ctrl+E)."""
        row, col = self.cursor_location
        lines = self.text.split("\n")
        if row < len(lines):
            self.move_cursor((row, len(lines[row])))

    def action_move_forward(self) -> None:
        """Move cursor forward one character (Emacs Ctrl+F)."""
        row, col = self.cursor_location
        lines = self.text.split("\n")
        if row < len(lines):
            if col < len(lines[row]):
                self.move_cursor((row, col + 1))
            elif row < len(lines) - 1:
                # Move to next line
                self.move_cursor((row + 1, 0))

    def action_move_backward(self) -> None:
        """Move cursor backward one character (Emacs Ctrl+B)."""
        row, col = self.cursor_location
        if col > 0:
            self.move_cursor((row, col - 1))
        elif row > 0:
            # Move to end of previous line
            lines = self.text.split("\n")
            self.move_cursor((row - 1, len(lines[row - 1])))

    def action_delete_forward(self) -> None:
        """Delete character under cursor (Emacs Ctrl+D)."""
        row, col = self.cursor_location
        lines = self.text.split("\n")
        if row < len(lines) and col < len(lines[row]):
            # Delete character at cursor
            current_line = lines[row]
            new_line = current_line[:col] + current_line[col + 1:]
            lines[row] = new_line
            self.text = "\n".join(lines)
            # Cursor stays at same position
            self.move_cursor((row, col))

    def action_delete_backward(self) -> None:
        """Delete character before cursor (Emacs Ctrl+H)."""
        row, col = self.cursor_location
        if col > 0:
            lines = self.text.split("\n")
            if row < len(lines):
                current_line = lines[row]
                new_line = current_line[:col - 1] + current_line[col:]
                lines[row] = new_line
                self.text = "\n".join(lines)
                # Move cursor back one position
                self.move_cursor((row, col - 1))
        elif row > 0:
            # At beginning of line, merge with previous line
            lines = self.text.split("\n")
            if row < len(lines):
                prev_line = lines[row - 1]
                current_line = lines[row]
                # Merge previous line with current line
                lines[row - 1] = prev_line + current_line
                # Remove current line
                del lines[row]
                self.text = "\n".join(lines)
                # Move cursor to end of previous line
                self.move_cursor((row - 1, len(prev_line)))

    def action_kill_to_line_end(self) -> None:
        """Delete from cursor to end of line (Emacs Ctrl+K)."""
        row, col = self.cursor_location
        lines = self.text.split("\n")
        if row < len(lines):
            current_line = lines[row]
            if col < len(current_line):
                # Store killed text for yank
                self._killed_text = current_line[col:]
                # Truncate line at cursor
                lines[row] = current_line[:col]
                self.text = "\n".join(lines)
                # Cursor stays at same position
                self.move_cursor((row, col))

    def action_kill_previous_word(self) -> None:
        """Delete previous word (Emacs Ctrl+W)."""
        row, col = self.cursor_location
        lines = self.text.split("\n")
        if row < len(lines):
            current_line = lines[row]
            if col > 0:
                # Find start of previous word
                text_before = current_line[:col]
                # Find last word boundary
                import re
                # Match word characters or whitespace
                matches = list(re.finditer(r'\w+|\s+', text_before))
                if matches:
                    last_match = matches[-1]
                    if last_match.group().isspace():
                        # If last match is whitespace, check if there's a word before it
                        if len(matches) > 1:
                            last_match = matches[-2]
                            start_pos = last_match.start()
                        else:
                            # Only whitespace before cursor
                            start_pos = 0
                    else:
                        start_pos = last_match.start()
                else:
                    start_pos = 0
                
                # Store killed text for yank
                self._killed_text = current_line[start_pos:col]
                # Delete from start_pos to col
                new_line = current_line[:start_pos] + current_line[col:]
                lines[row] = new_line
                self.text = "\n".join(lines)
                # Move cursor to start_pos
                self.move_cursor((row, start_pos))

    def action_yank(self) -> None:
        """Paste killed text (Emacs Ctrl+Y)."""
        if hasattr(self, '_killed_text') and self._killed_text:
            row, col = self.cursor_location
            lines = self.text.split("\n")
            if row < len(lines):
                current_line = lines[row]
                # Insert killed text at cursor
                new_line = current_line[:col] + self._killed_text + current_line[col:]
                lines[row] = new_line
                self.text = "\n".join(lines)
                # Move cursor past inserted text
                self.move_cursor((row, col + len(self._killed_text)))

    async def _on_key(self, event: events.Key) -> None:
        """Handle key events."""
        # Modifier+Enter inserts newline (Ctrl+J is most reliable across terminals)
        if event.key in ("shift+enter", "ctrl+j", "alt+enter", "ctrl+enter"):
            event.prevent_default()
            event.stop()
            self.insert("\n")
            return

        # If completion is active, let parent handle navigation keys
        if self._completion_active and event.key in ("up", "down", "tab", "enter"):
            # Prevent TextArea's default behavior (e.g., Enter inserting newline)
            # but let event bubble to ChatInput for completion handling
            event.prevent_default()
            return

        # Plain Enter submits
        if event.key == "enter":
            event.prevent_default()
            event.stop()
            value = self.text.strip()
            if value:
                self.post_message(self.Submitted(value))
            return

        # Up arrow on first line = history previous
        if event.key == "up":
            row, _ = self.cursor_location
            if row == 0:
                event.prevent_default()
                event.stop()
                self._navigating_history = True
                self.post_message(self.HistoryPrevious(self.text))
                return

        # Down arrow on last line = history next
        if event.key == "down":
            row, _ = self.cursor_location
            total_lines = self.text.count("\n") + 1
            if row == total_lines - 1:
                event.prevent_default()
                event.stop()
                self._navigating_history = True
                self.post_message(self.HistoryNext())
                return

        await super()._on_key(event)

    def set_text_from_history(self, text: str) -> None:
        """Set text from history navigation."""
        self._navigating_history = True
        self.text = text
        # Move cursor to end
        lines = text.split("\n")
        last_row = len(lines) - 1
        last_col = len(lines[last_row])
        self.move_cursor((last_row, last_col))
        self._navigating_history = False

    def clear_text(self) -> None:
        """Clear the text area."""
        self.text = ""
        self.move_cursor((0, 0))


class ChatInput(Vertical):
    """Chat input widget with prompt indicator, multi-line text, autocomplete, and history.

    Features:
    - Multi-line input with TextArea
    - Enter to submit, Ctrl+J for newlines (most reliable across terminals)
    - Up/Down arrows for command history on first/last line
    - Autocomplete for @ (files) and / (commands)
    """

    DEFAULT_CSS = """
    ChatInput {
        height: auto;
        min-height: 3;
        max-height: 12;
        padding: 0;
        background: $surface;
        border: solid $primary;
    }

    ChatInput .input-row {
        height: auto;
        width: 100%;
    }

    ChatInput .input-prompt {
        width: 3;
        height: 1;
        padding: 0 1;
        color: $primary;
        text-style: bold;
    }

    ChatInput ChatTextArea {
        width: 1fr;
        height: auto;
        min-height: 1;
        max-height: 8;
        border: none;
        background: transparent;
        padding: 0;
    }

    ChatInput ChatTextArea:focus {
        border: none;
    }
    """

    class Submitted(Message):
        """Message sent when input is submitted."""

        def __init__(self, value: str, mode: str = "normal") -> None:
            """Initialize with value and mode."""
            super().__init__()
            self.value = value
            self.mode = mode

    class ModeChanged(Message):
        """Message sent when input mode changes."""

        def __init__(self, mode: str) -> None:
            """Initialize with new mode."""
            super().__init__()
            self.mode = mode

    mode: reactive[str] = reactive("normal")

    def __init__(
        self,
        cwd: str | Path | None = None,
        history_file: Path | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the chat input widget.

        Args:
            cwd: Current working directory for file completion
            history_file: Path to history file (default: ~/.coda/history.jsonl)
            **kwargs: Additional arguments for parent
        """
        super().__init__(**kwargs)
        self._cwd = Path(cwd) if cwd else Path.cwd()
        self._text_area: ChatTextArea | None = None
        self._popup: CompletionPopup | None = None
        self._completion_manager: MultiCompletionManager | None = None

        # Set up history manager
        if history_file is None:
            history_file = Path.home() / ".coda" / "history.jsonl"
        self._history = HistoryManager(history_file)

    def compose(self) -> ComposeResult:
        """Compose the chat input layout."""
        with Horizontal(classes="input-row"):
            yield Static(">", classes="input-prompt", id="prompt")
            yield ChatTextArea(id="chat-input")

        yield CompletionPopup(id="completion-popup")

    def on_mount(self) -> None:
        """Initialize components after mount."""
        self._text_area = self.query_one("#chat-input", ChatTextArea)
        self._popup = self.query_one("#completion-popup", CompletionPopup)

        self._completion_manager = MultiCompletionManager(
            [
                SlashCommandController(SLASH_COMMANDS, self),
                FuzzyFileController(self, cwd=self._cwd),
            ]
        )

        self._text_area.focus()

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        """Detect input mode and update completions."""
        text = event.text_area.text

        # Update mode based on first character
        if text.startswith("!"):
            self.mode = "bash"
        elif text.startswith("/"):
            self.mode = "command"
        else:
            self.mode = "normal"

        # Skip completion during history navigation to avoid popup flashing
        if self._text_area and self._text_area._navigating_history:
            if self._completion_manager:
                self._completion_manager.reset()
            return

        # Update completion suggestions
        if self._completion_manager and self._text_area:
            cursor_offset = self._get_cursor_offset()
            self._completion_manager.on_text_changed(text, cursor_offset)

    def on_chat_text_area_submitted(self, event: ChatTextArea.Submitted) -> None:
        """Handle text submission."""
        value = event.value
        if value:
            if self._completion_manager:
                self._completion_manager.reset()

            self._history.add(value)
            self.post_message(self.Submitted(value, self.mode))
            if self._text_area:
                self._text_area.clear_text()
            self.mode = "normal"

    def on_chat_text_area_history_previous(self, event: ChatTextArea.HistoryPrevious) -> None:
        """Handle history previous request."""
        entry = self._history.get_previous(event.current_text)
        if entry is not None and self._text_area:
            self._text_area.set_text_from_history(entry)

    def on_chat_text_area_history_next(
        self,
        event: ChatTextArea.HistoryNext,  # noqa: ARG002
    ) -> None:
        """Handle history next request."""
        entry = self._history.get_next()
        if entry is not None and self._text_area:
            self._text_area.set_text_from_history(entry)

    async def on_key(self, event: events.Key) -> None:
        """Handle key events for completion navigation."""
        if not self._completion_manager or not self._text_area:
            return

        text = self._text_area.text
        cursor = self._get_cursor_offset()

        result = self._completion_manager.on_key(event, text, cursor)

        match result:
            case CompletionResult.HANDLED:
                event.prevent_default()
                event.stop()
            case CompletionResult.SUBMIT:
                event.prevent_default()
                event.stop()
                value = self._text_area.text.strip()
                if value:
                    self._completion_manager.reset()
                    self._history.add(value)
                    self.post_message(self.Submitted(value, self.mode))
                    self._text_area.clear_text()
                    self.mode = "normal"
            case CompletionResult.IGNORED if event.key == "enter":
                # Handle Enter when completion is not active (bash/normal modes)
                value = self._text_area.text.strip()
                if value:
                    event.prevent_default()
                    event.stop()
                    self._history.add(value)
                    self.post_message(self.Submitted(value, self.mode))
                    self._text_area.clear_text()
                    self.mode = "normal"

    def _get_cursor_offset(self) -> int:
        """Get the cursor offset as a single integer."""
        if not self._text_area:
            return 0

        text = self._text_area.text
        row, col = self._text_area.cursor_location

        if not text:
            return 0

        lines = text.split("\n")
        row = max(0, min(row, len(lines) - 1))
        col = max(0, col)

        offset = sum(len(lines[i]) + 1 for i in range(row))
        return offset + min(col, len(lines[row]))

    def watch_mode(self, mode: str) -> None:
        """Post mode changed message when mode changes."""
        self.post_message(self.ModeChanged(mode))

    def focus_input(self) -> None:
        """Focus the input field."""
        if self._text_area:
            self._text_area.focus()

    @property
    def value(self) -> str:
        """Get the current input value."""
        if self._text_area:
            return self._text_area.text
        return ""

    @value.setter
    def value(self, val: str) -> None:
        """Set the input value."""
        if self._text_area:
            self._text_area.text = val

    @property
    def input_widget(self) -> ChatTextArea | None:
        """Get the underlying TextArea widget."""
        return self._text_area

    def set_disabled(self, *, disabled: bool) -> None:
        """Enable or disable the input widget."""
        if self._text_area:
            self._text_area.disabled = disabled
            if disabled:
                self._text_area.blur()
                if self._completion_manager:
                    self._completion_manager.reset()

    def set_cursor_active(self, *, active: bool) -> None:
        """Set whether the cursor should be actively blinking.

        When active=False (e.g., agent is working), disables cursor blink
        so the cursor doesn't flash while waiting for a response.
        """
        if self._text_area:
            self._text_area.set_app_focus(has_focus=active)

    # =========================================================================
    # CompletionView protocol implementation
    # =========================================================================

    def render_completion_suggestions(
        self, suggestions: list[tuple[str, str]], selected_index: int
    ) -> None:
        """Render completion suggestions in the popup."""
        if self._popup:
            self._popup.update_suggestions(suggestions, selected_index)
        # Tell TextArea that completion is active so it yields navigation keys
        if self._text_area:
            self._text_area.set_completion_active(active=bool(suggestions))

    def clear_completion_suggestions(self) -> None:
        """Clear/hide the completion popup."""
        if self._popup:
            self._popup.hide()
        # Tell TextArea that completion is no longer active
        if self._text_area:
            self._text_area.set_completion_active(active=False)

    def replace_completion_range(self, start: int, end: int, replacement: str) -> None:
        """Replace text in the input field."""
        if not self._text_area:
            return

        text = self._text_area.text
        start = max(0, min(start, len(text)))
        end = max(start, min(end, len(text)))

        prefix = text[:start]
        suffix = text[end:]

        # Add space after completion unless it's a directory path
        if replacement.endswith("/"):
            insertion = replacement
        else:
            insertion = replacement + " " if not suffix.startswith(" ") else replacement

        new_text = f"{prefix}{insertion}{suffix}"
        self._text_area.text = new_text

        # Calculate new cursor position and move cursor
        new_offset = start + len(insertion)
        lines = new_text.split("\n")
        remaining = new_offset
        for row, line in enumerate(lines):
            if remaining <= len(line):
                self._text_area.move_cursor((row, remaining))
                break
            remaining -= len(line) + 1
