"""Tests for the diagrams command in .claude/skills/changelog/changelog.py.

Run: python3 -m unittest discover -s tests -p "test_changelog*.py"
"""

import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parents[1]
    / ".claude"
    / "skills"
    / "changelog"
    / "changelog.py"
)
OUT = Path("docs") / "diagrams" / "architecture.md"

PY_FILES = {
    "src/triage/__init__.py": "from .score import score_ticket\n",
    "src/triage/models.py": """
        from dataclasses import dataclass


        @dataclass
        class Ticket:
            id: str
            tenant: str

            def is_urgent(self) -> bool:
                return True


        class EnterpriseTicket(Ticket):
            def _escalate(self, reason):
                self.escalated = True
                return self.is_urgent()
        """,
    "src/triage/score.py": """
        import json
        from triage.models import Ticket
        from . import rules


        def score_ticket(t: Ticket) -> int:
            return rules.weight(t) + bonus(t)


        def bonus(t):
            return 1
        """,
    "src/triage/rules.py": "def weight(t):\n    return 1\n",
    "src/triage/adapters/store.py": """
        from ..models import Ticket


        class TicketStore:
            def __init__(self, rows):
                self._rows = rows

            def list_tickets(self, tenant):
                return self._rows

            def ranked(self, tenant):
                return self.list_tickets(tenant)
        """,
    "src/triage/broken.py": "def oops(:\n",
    "tests/test_score.py": "class ShouldNotAppear: pass\n",
    ".venv/lib/vendor.py": "class Vendored: pass\n",
}

TS_FILES = {
    "web/src/lib/http.ts": """
        export interface Transport { send(body: string): Promise<void> }
        export abstract class BaseClient {
          protected readonly baseUrl: string;
          #retries = 3;
          constructor(baseUrl: string) { this.baseUrl = baseUrl; }
          async post(path: string, body?: unknown): Promise<Response> {
            if (path) { return fetch(this.baseUrl + path); }
            return fetch(this.baseUrl);
          }
          private backoff(attempt: number) { return attempt * 2; }
        }
        """,
    "web/src/webhook.ts": """
        import { BaseClient, Transport } from "./lib/http";
        import type { Foo } from "external-lib";
        export class WebhookClient extends BaseClient implements Transport {
          secret?: string;
          async send(body: string): Promise<void> { await this.post("/hook", body); }
        }
        """,
    "web/src/index.ts": 'export * from "./webhook";\nconst lazy = () => import("./lib/http");\n',
    "web/src/webhook.test.ts": "export class ShouldNotAppearEither {}\n",
}


class DiagramsTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.git("init", "-q")
        self.git("config", "user.name", "Tester")
        self.git("config", "user.email", "tester@example.com")

    def tearDown(self):
        self._tmp.cleanup()

    def git(self, *args):
        subprocess.run(["git", *args], cwd=self.root, check=True, capture_output=True)

    def write(self, files):
        for rel, text in files.items():
            path = self.root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(textwrap.dedent(text).lstrip("\n"))
        self.git("add", "-A")

    def run_cl(self, *args, cwd=None):
        return subprocess.run(
            [sys.executable, str(SCRIPT), "diagrams", *args],
            cwd=cwd or self.root,
            capture_output=True,
            text=True,
            check=False,
        )

    def diagrams(self):
        result = self.run_cl()
        self.assertEqual(result.returncode, 0, result.stderr)
        return (self.root / OUT).read_text()

    def test_empty_project_gets_placeholder(self):
        text = self.diagrams()
        self.assertIn("No source code yet", text)
        self.assertNotIn("```mermaid", text)

    def test_check_fails_when_missing_or_stale_and_passes_when_current(self):
        self.write({"app.py": "def main():\n    pass\n"})
        missing = self.run_cl("--check")
        self.assertEqual(missing.returncode, 1)
        self.assertIn("out of date", missing.stderr)
        self.diagrams()
        self.assertEqual(self.run_cl("--check").returncode, 0)
        self.write({"other.py": "import app\n"})
        self.assertEqual(self.run_cl("--check").returncode, 1)

    def test_fail_on_change_writes_then_fails_only_when_the_file_changed(self):
        self.write({"app.py": "def main():\n    pass\n"})
        first = self.run_cl("--fail-on-change")
        self.assertEqual(first.returncode, 1)
        self.assertIn("git add docs/diagrams", first.stderr)
        self.assertTrue((self.root / OUT).exists())
        self.assertEqual(self.run_cl("--fail-on-change").returncode, 0)

    def test_output_is_deterministic(self):
        self.write({**PY_FILES, **TS_FILES})
        first = self.diagrams()
        self.assertIn("unchanged", self.run_cl().stdout)
        self.assertEqual(first, (self.root / OUT).read_text())

    def test_python_components_resolve_absolute_relative_and_package_imports(self):
        self.write(PY_FILES)
        text = self.diagrams()
        for edge in (
            "n_triage --> n_triage_score",  # package __init__, relative
            "n_triage_score --> n_triage_models",  # absolute, src/ layout
            "n_triage_score --> n_triage_rules",  # from . import module
            "n_triage_adapters_store --> n_triage_models",  # from ..models
        ):
            self.assertIn(edge, text)
        self.assertNotIn("json", text.split("## Classes")[0])  # stdlib import left out
        self.assertIn('subgraph n_g_triage_adapters["triage.adapters"]', text)

    def test_python_classes_members_visibility_and_inheritance(self):
        self.write(PY_FILES)
        text = self.diagrams()
        for line in (
            "Ticket : +id",
            "Ticket : +is_urgent() bool",
            "EnterpriseTicket : +escalated",
            "EnterpriseTicket : -escalate(reason)",
            "TicketStore : -rows",
            "TicketStore : +list_tickets(tenant)",
            "Ticket <|-- EnterpriseTicket",
        ):
            self.assertIn(line, text)
        self.assertNotIn("__init__", text)

    def test_python_call_graph(self):
        self.write(PY_FILES)
        graph = self.diagrams().split("## Call graph")[1]
        for edge in (
            "n_triage_score_score_ticket --> n_triage_rules_weight",  # module.attr
            "n_triage_score_score_ticket --> n_triage_score_bonus",  # same module
            # self.method()
            (
                "n_triage_adapters_store_TicketStore_ranked --> "
                "n_triage_adapters_store_TicketStore_list_tickets"
            ),
        ):
            self.assertIn(edge, graph)

    def test_typescript_imports_classes_interfaces_and_multiline_methods(self):
        self.write(TS_FILES)
        text = self.diagrams()
        for line in (
            "n_web_src_webhook --> n_web_src_lib_http",
            "n_web_src_index --> n_web_src_webhook",  # export * from
            "n_web_src_index --> n_web_src_lib_http",  # dynamic import()
            "<<interface>> Transport",
            "<<abstract>> BaseClient",
            "BaseClient : +post(path, body)",  # body spans several lines
            "BaseClient : -backoff(attempt)",
            "BaseClient : -retries",  # #private field
            "BaseClient <|-- WebhookClient",
            "Transport <|.. WebhookClient",
        ):
            self.assertIn(line, text)
        self.assertNotIn("constructor", text)
        self.assertNotIn("external", text)

    def test_tests_vendored_untracked_and_broken_files_are_left_out(self):
        self.write({**PY_FILES, **TS_FILES})
        (self.root / "src" / "triage" / "scratch.py").write_text(
            "class Untracked: pass\n"
        )
        result = self.run_cl()
        self.assertEqual(result.returncode, 0)
        self.assertIn("skipped src/triage/broken.py", result.stderr)
        text = (self.root / OUT).read_text()
        for absent in ("ShouldNotAppear", "Vendored", "Untracked", "broken"):
            self.assertNotIn(absent, text)

    def test_runs_from_a_subfolder(self):
        self.write(PY_FILES)
        result = self.run_cl(cwd=self.root / "src" / "triage")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.root / OUT).exists())


if __name__ == "__main__":
    unittest.main()
