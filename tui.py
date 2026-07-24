"""
Resumind Terminal UI — Textual-based interactive dashboard.
"""
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Header, Footer, Static, DataTable, Button
from textual.containers import Horizontal, Vertical
import httpx
import asyncio


class DashboardScreen(Screen):
    BINDINGS = [
        Binding("d", "show_dashboard", "Dashboard"),
        Binding("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield Static(" Resumind Dashboard", classes="title")
            with Horizontal():
                yield Static("API: Checking...", id="api-status")
                yield Static("Queue: -", id="queue-status")
                yield Static("Evals: -", id="eval-count")
            yield DataTable(id="recent-evals")
            yield Button("Evaluate Resume", id="evaluate-btn", variant="primary")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#recent-evals", DataTable)
        table.add_columns("Candidate", "Score", "Status", "Date")
        self.set_interval(30, self.refresh_status)
        asyncio.create_task(self.refresh_status())

    async def refresh_status(self) -> None:
        api_url = self.app.api_url
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(f"{api_url}/health", timeout=5)
                if r.status_code == 200:
                    self.query_one("#api-status", Static).update(" Connected")
                else:
                    self.query_one("#api-status", Static).update(" Error")
        except Exception as e:
            self.query_one("#api-status", Static).update(f" {str(e)}")


class ResumindTUI(App):
    TITLE = "Resumind"
    SUB_TITLE = "Hiring Evaluation Platform"

    def __init__(self, api_url: str = "http://localhost:8000", api_key: str = None):
        super().__init__()
        self.api_url = api_url
        self.api_key = api_key

    def on_ready(self) -> None:
        self.push_screen(DashboardScreen())


def run_tui(api_url: str = "http://localhost:8000", api_key: str = None):
    """Launch the Resumind TUI."""
    app = ResumindTUI(api_url=api_url, api_key=api_key)
    app.run()


if __name__ == "__main__":
    run_tui()