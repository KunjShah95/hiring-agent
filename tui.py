"""
Resumind Terminal UI — Textual-based interactive dashboard.
Screens: Dashboard, Candidates, Evaluations, Jobs, Integrations, Settings
"""
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Header, Footer, Static, DataTable, Button, Input, Label, ListView, ListItem, TextArea
from textual.containers import Horizontal, Vertical, ScrollableContainer
from textual import events
import httpx
import asyncio
import logging

logger = logging.getLogger(__name__)


# ─── Shared helpers ──────────────────────────────────────────────────────

async def api_get(url: str, path: str, timeout: int = 10) -> dict:
    """Make a GET request to the API."""
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{url}{path}", timeout=timeout)
            if r.status_code == 200:
                return {"ok": True, "data": r.json()}
            return {"ok": False, "error": f"HTTP {r.status_code}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


async def api_post(url: str, path: str, data: dict = None, timeout: int = 30) -> dict:
    """Make a POST request to the API."""
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(f"{url}{path}", json=data, timeout=timeout)
            if r.status_code in (200, 201):
                return {"ok": True, "data": r.json()}
            return {"ok": False, "error": f"HTTP {r.status_code}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ─── Dashboard Screen ────────────────────────────────────────────────────

class DashboardScreen(Screen):
    BINDINGS = [
        Binding("1", "show_dashboard", "Dashboard", show=True),
        Binding("2", "show_candidates", "Candidates", show=True),
        Binding("3", "show_evaluations", "Evaluations", show=True),
        Binding("4", "show_jobs", "Jobs", show=True),
        Binding("5", "show_integrations", "Integrations", show=True),
        Binding("6", "show_settings", "Settings", show=True),
        Binding("q", "quit", "Quit", show=True),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield Static("Resumind Dashboard", classes="title")
            with Horizontal(classes="status-bar"):
                yield Static("🔌 API: Checking...", id="api-status", classes="status-item")
                yield Static("📨 Queue: -", id="queue-status", classes="status-item")
                yield Static("📋 Evals: -", id="eval-count", classes="status-item")
                yield Static("👥 Candidates: -", id="candidate-count", classes="status-item")
            yield Static("Recent Evaluations", classes="section-title")
            yield DataTable(id="recent-evals")
            yield Static("\n[prompt]Press 1-6 to navigate screens | q to quit[/prompt]")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#recent-evals", DataTable)
        table.add_columns("Candidate", "Score", "Status", "Date")
        self.set_interval(30, self.refresh_status)
        asyncio.create_task(self.refresh_status())
        asyncio.create_task(self.refresh_evaluations())

    async def refresh_status(self) -> None:
        api_url = self.app.api_url
        result = await api_get(api_url, "/health", timeout=5)
        if result["ok"]:
            data = result["data"]
            db_status = data.get("database", "unknown")
            self.query_one("#api-status", Static).update(f"🔌 API: ✅ Connected | DB: {db_status}")
        else:
            self.query_one("#api-status", Static).update(f"🔌 API: ❌ {result['error']}")

    async def refresh_evaluations(self) -> None:
        """Fetch and display recent evaluations."""
        from db import get_engine, Evaluation, Candidate
        from sqlalchemy import select
        from sqlalchemy.orm import Session

        engine = get_engine()
        if not engine:
            self.query_one("#eval-count", Static).update("📋 Evals: DB not configured")
            return

        try:
            with Session(engine) as session:
                # Count evaluations
                count = session.query(Evaluation).count()
                self.query_one("#eval-count", Static).update(f"📋 Evals: {count}")

                # Count candidates
                cand_count = session.query(Candidate).count()
                self.query_one("#candidate-count", Static).update(f"👥 Candidates: {cand_count}")

                # Recent 10 evaluations
                recent = (
                    session.query(Evaluation)
                    .order_by(Evaluation.created_at.desc())
                    .limit(10)
                    .all()
                )

                table = self.query_one("#recent-evals", DataTable)
                table.clear()
                for ev in recent:
                    name = "Unknown"
                    if ev.candidate:
                        name = ev.candidate.name or f"Candidate #{ev.candidate_id}"
                    score = f"{ev.overall_score}/{ev.max_score}" if ev.overall_score else "-"
                    status = ev.status or "pending"
                    date = ev.created_at.strftime("%Y-%m-%d %H:%M") if ev.created_at else "-"
                    table.add_row(name, score, status, date)

        except Exception as e:
            self.query_one("#eval-count", Static).update(f"📋 Evals: Error ({str(e)[:30]})")

    def action_show_dashboard(self) -> None:
        self.app.push_screen(DashboardScreen())

    def action_show_candidates(self) -> None:
        self.app.push_screen(CandidatesScreen())

    def action_show_evaluations(self) -> None:
        self.app.push_screen(EvaluationsScreen())

    def action_show_jobs(self) -> None:
        self.app.push_screen(JobsScreen())

    def action_show_integrations(self) -> None:
        self.app.push_screen(IntegrationsScreen())

    def action_show_settings(self) -> None:
        self.app.push_screen(SettingsScreen())


# ─── Candidates Screen ───────────────────────────────────────────────────

class CandidatesScreen(Screen):
    BINDINGS = [
        Binding("r", "refresh", "Refresh", show=True),
        Binding("escape", "back", "Back", show=True),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield Static("👥 Candidates", classes="title")
            with Horizontal(classes="toolbar"):
                yield Button("🔄 Refresh", id="refresh-btn", variant="default")
                yield Button("➕ Add Candidate", id="add-btn", variant="primary")
            yield DataTable(id="candidates-table")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#candidates-table", DataTable)
        table.add_columns("ID", "Name", "Email", "Source", "CTC Current", "Location", "Created")
        asyncio.create_task(self.load_candidates())

    async def load_candidates(self) -> None:
        api_url = self.app.api_url
        result = await api_get(api_url, "/candidates?limit=50")
        if result["ok"]:
            table = self.query_one("#candidates-table", DataTable)
            table.clear()
            for c in result["data"]:
                table.add_row(
                    str(c["id"]),
                    c.get("name", "-"),
                    c.get("email", "-"),
                    c.get("source", "-"),
                    c.get("ctc_current", "-"),
                    c.get("location", "-"),
                    c.get("created_at", "-")[:10] if c.get("created_at") else "-",
                )
        else:
            self.query_one("#candidates-table", Static).update(f"Error: {result['error']}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "refresh-btn":
            asyncio.create_task(self.load_candidates())
        elif event.button.id == "add-btn":
            self.app.push_screen(CandidateFormScreen())

    def action_refresh(self) -> None:
        asyncio.create_task(self.load_candidates())

    def action_back(self) -> None:
        self.app.pop_screen()


class CandidateFormScreen(Screen):
    BINDINGS = [
        Binding("escape", "back", "Cancel", show=True),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield Static("➕ Add New Candidate", classes="title")
            with ScrollableContainer():
                yield Input(placeholder="Full Name *", id="input-name")
                yield Input(placeholder="Email", id="input-email")
                yield Input(placeholder="Phone", id="input-phone")
                yield Input(placeholder="Location", id="input-location")
                yield Input(placeholder="Current CTC (e.g. 25 LPA)", id="input-ctc")
                yield Input(placeholder="Expected CTC", id="input-ctc-expected")
                yield Input(placeholder="Notice Period (days)", id="input-notice")
                yield Input(placeholder="Visa Status", id="input-visa")
            with Horizontal():
                yield Button("✅ Save", id="save-btn", variant="primary")
                yield Button("❌ Cancel", id="cancel-btn", variant="default")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save-btn":
            asyncio.create_task(self.save_candidate())
        elif event.button.id == "cancel-btn":
            self.app.pop_screen()

    async def save_candidate(self) -> None:
        data = {
            "name": self.query_one("#input-name", Input).value,
            "email": self.query_one("#input-email", Input).value,
            "phone": self.query_one("#input-phone", Input).value,
            "location": self.query_one("#input-location", Input).value,
            "ctc_current": self.query_one("#input-ctc", Input).value or None,
            "ctc_expected": self.query_one("#input-ctc-expected", Input).value or None,
            "visa_status": self.query_one("#input-visa", Input).value or None,
        }

        notice = self.query_one("#input-notice", Input).value
        if notice:
            try:
                data["notice_period_days"] = int(notice)
            except ValueError:
                pass

        api_url = self.app.api_url
        result = await api_post(api_url, "/candidates", data=data)
        if result["ok"]:
            self.app.pop_screen()
            # Refresh candidates list
            if self.app.screen_stack:
                prev = self.app.screen_stack[-1]
                if hasattr(prev, "load_candidates"):
                    asyncio.create_task(prev.load_candidates())
        else:
            self.query_one("#save-btn", Button).label = f"❌ Error: {result['error'][:20]}"

    def action_back(self) -> None:
        self.app.pop_screen()


# ─── Evaluations Screen ──────────────────────────────────────────────────

class EvaluationsScreen(Screen):
    BINDINGS = [
        Binding("r", "refresh", "Refresh", show=True),
        Binding("escape", "back", "Back", show=True),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield Static("📋 Evaluation History", classes="title")
            with Horizontal(classes="toolbar"):
                yield Button("🔄 Refresh", id="refresh-btn", variant="default")
            yield DataTable(id="evaluations-table")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#evaluations-table", DataTable)
        table.add_columns("ID", "Candidate", "Score", "Status", "LLM Trace", "Date")
        asyncio.create_task(self.load_evaluations())

    async def load_evaluations(self) -> None:
        from db import get_engine, Evaluation
        from sqlalchemy.orm import Session

        engine = get_engine()
        if not engine:
            # Fallback: show API-based data
            self.query_one("#evaluations-table", DataTable).add_row(
                "DB not configured", "", "", "", "", ""
            )
            return

        try:
            with Session(engine) as session:
                evals = (
                    session.query(Evaluation)
                    .order_by(Evaluation.created_at.desc())
                    .limit(100)
                    .all()
                )

                table = self.query_one("#evaluations-table", DataTable)
                table.clear()
                for ev in evals:
                    name = "Unknown"
                    if ev.candidate:
                        name = ev.candidate.name or f"Candidate #{ev.candidate_id}"
                    score = f"{ev.overall_score}/{ev.max_score}" if ev.overall_score else "-"
                    trace = ev.llm_trace_id or "-"
                    date = ev.created_at.strftime("%Y-%m-%d %H:%M") if ev.created_at else "-"
                    table.add_row(str(ev.id), name, score, ev.status, trace, date)

        except Exception as e:
            self.query_one("#evaluations-table", DataTable).add_row(
                f"Error: {str(e)[:30]}", "", "", "", "", ""
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "refresh-btn":
            asyncio.create_task(self.load_evaluations())

    def action_refresh(self) -> None:
        asyncio.create_task(self.load_evaluations())

    def action_back(self) -> None:
        self.app.pop_screen()


# ─── Jobs Screen ─────────────────────────────────────────────────────────

class JobsScreen(Screen):
    BINDINGS = [
        Binding("r", "refresh", "Refresh", show=True),
        Binding("n", "new_job", "New Job", show=True),
        Binding("escape", "back", "Back", show=True),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield Static("💼 Jobs", classes="title")
            with Horizontal(classes="toolbar"):
                yield Button("🔄 Refresh", id="refresh-btn", variant="default")
                yield Button("➕ New Job", id="new-btn", variant="primary")
            yield DataTable(id="jobs-table")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#jobs-table", DataTable)
        table.add_columns("ID", "Title", "Location", "CTC Range", "Status", "Created")
        asyncio.create_task(self.load_jobs())

    async def load_jobs(self) -> None:
        api_url = self.app.api_url
        result = await api_get(api_url, "/jobs?limit=50")
        if result["ok"]:
            table = self.query_one("#jobs-table", DataTable)
            table.clear()
            for j in result["data"]:
                table.add_row(
                    str(j["id"]),
                    j.get("title", "-"),
                    j.get("location", "-"),
                    j.get("ctc_range", "-"),
                    j.get("status", "-"),
                    j.get("created_at", "-")[:10] if j.get("created_at") else "-",
                )
        else:
            self.query_one("#jobs-table", DataTable).add_row(
                f"Error: {result['error'][:30]}", "", "", "", "", ""
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "refresh-btn":
            asyncio.create_task(self.load_jobs())
        elif event.button.id == "new-btn":
            self.app.push_screen(JobFormScreen())

    def action_refresh(self) -> None:
        asyncio.create_task(self.load_jobs())

    def action_new_job(self) -> None:
        self.app.push_screen(JobFormScreen())

    def action_back(self) -> None:
        self.app.pop_screen()


class JobFormScreen(Screen):
    BINDINGS = [
        Binding("escape", "back", "Cancel", show=True),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield Static("💼 Create New Job", classes="title")
            with ScrollableContainer():
                yield Input(placeholder="Job Title *", id="input-title")
                yield Input(placeholder="Location", id="input-location")
                yield Input(placeholder="CTC Range (e.g. 20-30 LPA)", id="input-ctc")
                yield Input(placeholder="Skills (comma separated)", id="input-skills")
                yield TextArea(id="input-description", text="Job description...")
            with Horizontal():
                yield Button("✅ Save & Post", id="save-btn", variant="primary")
                yield Button("❌ Cancel", id="cancel-btn", variant="default")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save-btn":
            asyncio.create_task(self.save_job())
        elif event.button.id == "cancel-btn":
            self.app.pop_screen()

    async def save_job(self) -> None:
        skills_text = self.query_one("#input-skills", Input).value
        skills = [s.strip() for s in skills_text.split(",") if s.strip()] if skills_text else []

        data = {
            "title": self.query_one("#input-title", Input).value,
            "location": self.query_one("#input-location", Input).value,
            "ctc_range": self.query_one("#input-ctc", Input).value,
            "skills": skills,
            "description": self.query_one("#input-description", TextArea).text,
        }

        api_url = self.app.api_url
        result = await api_post(api_url, "/jobs", data=data)
        if result["ok"]:
            self.app.pop_screen()
        else:
            self.query_one("#save-btn", Button).label = f"❌ Error: {result['error'][:20]}"

    def action_back(self) -> None:
        self.app.pop_screen()


# ─── Integrations Screen ─────────────────────────────────────────────────

class IntegrationsScreen(Screen):
    BINDINGS = [
        Binding("r", "refresh", "Refresh", show=True),
        Binding("escape", "back", "Back", show=True),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield Static("🔌 Integrations", classes="title")

            yield Static("Naukri.com", classes="section-title")
            with Horizontal(classes="integration-card"):
                yield Static("Status: Checking...", id="naukri-status", classes="status-item")
                yield Button("🔄 Sync Now", id="sync-naukri", variant="primary")
                yield Button("Test Connection", id="test-naukri", variant="default")

            yield Static("Indeed", classes="section-title")
            with Horizontal(classes="integration-card"):
                yield Static("Status: Checking...", id="indeed-status", classes="status-item")
                yield Button("🔄 Sync Now", id="sync-indeed", variant="primary")
                yield Button("Test Connection", id="test-indeed", variant="default")

            yield Static("Glassdoor", classes="section-title")
            with Horizontal(classes="integration-card"):
                yield Static("Status: Checking...", id="glassdoor-status", classes="status-item")
                yield Button("🔄 Sync Now", id="sync-glassdoor", variant="primary")
                yield Button("Test Connection", id="test-glassdoor", variant="default")

            yield Static("\nSync History", classes="section-title")
            yield DataTable(id="sync-history-table")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#sync-history-table", DataTable)
        table.add_columns("Platform", "Type", "Status", "Processed", "Failed", "Date")
        asyncio.create_task(self.refresh_all())
        self.set_interval(30, self.refresh_all)

    async def refresh_all(self) -> None:
        await self.refresh_integration_status()
        await self.refresh_sync_history()

    async def refresh_integration_status(self) -> None:
        from config import settings

        platforms = {
            "naukri": ("NAUKRI_API_KEY", "#naukri-status"),
            "indeed": ("INDEED_API_KEY", "#indeed-status"),
            "glassdoor": ("GLASSDOOR_API_KEY", "#glassdoor-status"),
        }

        for platform, (config_key, widget_id) in platforms.items():
            if settings.get(config_key):
                self.query_one(widget_id, Static).update(f"Status: ✅ Configured (key set)")
            else:
                self.query_one(widget_id, Static).update(f"Status: ⚠️ Not configured")

    async def refresh_sync_history(self) -> None:
        api_url = self.app.api_url
        result = await api_get(api_url, "/integrations/syncs?limit=20")
        if result["ok"]:
            table = self.query_one("#sync-history-table", DataTable)
            table.clear()
            for s in result["data"]:
                table.add_row(
                    s.get("platform", "-"),
                    s.get("sync_type", "-"),
                    s.get("status", "-"),
                    str(s.get("items_processed", 0)),
                    str(s.get("items_failed", 0)),
                    s.get("created_at", "-")[:16] if s.get("created_at") else "-",
                )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id

        if btn_id == "sync-naukri":
            asyncio.create_task(self.trigger_sync("naukri"))
        elif btn_id == "sync-indeed":
            asyncio.create_task(self.trigger_sync("indeed"))
        elif btn_id == "sync-glassdoor":
            asyncio.create_task(self.trigger_sync("glassdoor"))
        elif btn_id == "test-naukri":
            asyncio.create_task(self.test_connection("naukri"))
        elif btn_id == "test-indeed":
            asyncio.create_task(self.test_connection("indeed"))
        elif btn_id == "test-glassdoor":
            asyncio.create_task(self.test_connection("glassdoor"))

    async def trigger_sync(self, platform: str) -> None:
        api_url = self.app.api_url
        result = await api_post(api_url, f"/integrations/{platform}/sync")
        if result["ok"]:
            self.query_one(f"#sync-{platform}", Button).label = "✅ Triggered!"
        else:
            self.query_one(f"#sync-{platform}", Button).label = f"❌ {result['error'][:15]}"

    async def test_connection(self, platform: str) -> None:
        api_url = self.app.api_url
        result = await api_get(api_url, "/health")
        if result["ok"]:
            self.query_one(f"#test-{platform}", Button).label = "✅ API OK"
        else:
            self.query_one(f"#test-{platform}", Button).label = f"❌ {result['error'][:15]}"

    def action_refresh(self) -> None:
        asyncio.create_task(self.refresh_all())

    def action_back(self) -> None:
        self.app.pop_screen()


# ─── Settings Screen ─────────────────────────────────────────────────────

class SettingsScreen(Screen):
    BINDINGS = [
        Binding("escape", "back", "Back", show=True),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield Static("⚙️ Settings", classes="title")
            with ScrollableContainer():
                yield Static("[bold]Application[/bold]", classes="section-title")
                yield Static("Loading settings...", id="settings-content")
                yield Static("\n[bold]API Configuration[/bold]", classes="section-title")
                yield Input(placeholder="API URL", id="api-url-input")
                yield Button("💾 Save Settings", id="save-settings-btn", variant="primary")
        yield Footer()

    def on_mount(self) -> None:
        from config import settings
        self.app_settings = settings
        self._render_settings()

    def _render_settings(self) -> None:
        s = self.app_settings
        env = s.get("ENV", "development")
        provider = s.get("LLM_PROVIDER", "ollama")
        model = s.get("DEFAULT_MODEL", "deepseek-v4-flash")
        langfuse = "✅ Configured" if s.get("LANGFUSE_HOST") else "❌ Not configured"
        otel = "✅ Configured" if s.get("OTEL_EXPORTER_OTLP_ENDPOINT") else "❌ Not configured"
        naukri = "✅ Configured" if s.get("NAUKRI_API_KEY") else "❌ Not configured"
        indeed = "✅ Configured" if s.get("INDEED_API_KEY") else "❌ Not configured"
        glassdoor = "✅ Configured" if s.get("GLASSDOOR_API_KEY") else "❌ Not configured"

        content = (
            f"[bold]Application[/bold]\n"
            f"App Name: Resumind\n"
            f"Version: 0.1.0\n"
            f"Environment: {env}\n\n"
            f"[bold]LLM Provider[/bold]\n"
            f"Provider: {provider}\n"
            f"Model: {model}\n"
            f"Ollama Host: {s.get('OLLAMA_HOST', 'local') or 'local'}\n\n"
            f"[bold]Observability[/bold]\n"
            f"LangFuse: {langfuse}\n"
            f"OpenTelemetry: {otel}\n\n"
            f"[bold]Integrations[/bold]\n"
            f"Naukri: {naukri}\n"
            f"Indeed: {indeed}\n"
            f"Glassdoor: {glassdoor}"
        )
        self.query_one("#settings-content", Static).update(content)
        self.query_one("#api-url-input", Input).value = self.app.api_url

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save-settings-btn":
            new_url = self.query_one("#api-url-input", Input).value
            if new_url:
                self.app.api_url = new_url
                self.query_one("#save-settings-btn", Button).label = "✅ Saved!"
            else:
                self.query_one("#save-settings-btn", Button).label = "❌ Invalid URL"

    def action_back(self) -> None:
        self.app.pop_screen()


# ─── Main App ────────────────────────────────────────────────────────────

class ResumindTUI(App):
    TITLE = "Resumind"
    SUB_TITLE = "Hiring Evaluation Platform"
    CSS = """
    .title {
        text-style: bold;
        padding: 1;
        content-align: center middle;
        background: $primary-background;
    }
    .section-title {
        text-style: bold;
        padding: 0 1;
        margin-top: 1;
    }
    .status-bar {
        height: 3;
        padding: 1;
        background: $surface;
    }
    .status-item {
        padding: 0 1;
    }
    .toolbar {
        height: 3;
        padding: 0 1;
    }
    .integration-card {
        height: 3;
        padding: 1;
        background: $surface;
        margin: 0 1;
    }
    DataTable {
        height: 1fr;
    }
    Button {
        margin: 0 1;
    }
    Input {
        margin: 0 1;
    }
    TextArea {
        margin: 0 1;
        height: 8;
    }
    """

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
