"""Welcome banner widget for CoDA Code."""

from __future__ import annotations

from typing import Any

from textual.widgets import Static

from coda_cli._version import __version__
from coda_cli.config import CODA_CODE_ASCII, settings


class WelcomeBanner(Static):
    """Welcome banner displayed at startup."""

    DEFAULT_CSS = """
    WelcomeBanner {
        height: auto;
        padding: 1;
        margin-bottom: 1;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the welcome banner."""
        # Use the same green color as the original UI (#10b981)
        # banner_text = f"[bold #10b981]{CODA_CODE_ASCII}[/bold #10b981]"
        banner_text = f"[bold #f7f7f7]{CODA_CODE_ASCII}[/bold #f7f7f7]"
        banner_text += "\n"
        banner_text += f"[dim]󰪩 {settings.model_provider}:{settings.model_name} •  {settings.project_root}[/dim]\n"
        banner_text += "[dim]Enter send • Ctrl+J newline • @ files • / commands[/dim]"
        super().__init__(banner_text, **kwargs)
