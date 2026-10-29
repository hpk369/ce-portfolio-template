"""Tests for .claude/skills/changelog/changelog.py (standard library only).

Run: python3 -m unittest discover -s tests
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parents[1]
    / ".claude"
    / "skills"
    / "changelog"
    / "changelog.py"
)
REASON = "Signatures failed because the JSON was re-serialized before the HMAC check"


class ChangelogTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.entries = self.root / "changelog" / "entries"

    def tearDown(self):
        self._tmp.cleanup()

    def run_cl(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=self.root,
            capture_output=True,
            text=True,
            check=False,
        )

    def add(
        self, summary="Verify webhook signatures on the raw body", reason=REASON, *extra
    ):
        return self.run_cl(
            "add", "--type", "fixed", "--summary", summary, "--reason", reason, *extra
        )

    def only_entry(self):
        files = list(self.entries.glob("CL-*.json"))
        self.assertEqual(len(files), 1)
        return files[0], json.loads(files[0].read_text())

    def test_add_writes_entry_with_generated_id_and_utc_timestamp(self):
        result = self.add(
            "Verify webhook signatures on the raw body", REASON, "--issue", "12"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        path, entry = self.only_entry()
        self.assertRegex(entry["id"], r"^CL-\d{8}-\d{4}-[0-9a-f]{4}$")
        self.assertEqual(path.stem, entry["id"])
        self.assertRegex(entry["timestamp"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
        self.assertEqual(entry["issue"], 12)
        self.assertEqual(entry["reason"], REASON)
        self.assertIn(entry["id"], result.stdout)

    def test_add_rejects_short_reason(self):
        result = self.add("Something changed", "because")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("at least 15", result.stderr)
        self.assertFalse(self.entries.exists())

    def test_add_rejects_reason_that_repeats_summary(self):
        result = self.add("Verify webhook signatures", "verify webhook signatures")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not repeat the summary", result.stderr)

    def test_add_rejects_unknown_type(self):
        result = self.run_cl(
            "add", "--type", "chore", "--summary", "x", "--reason", REASON
        )
        self.assertNotEqual(result.returncode, 0)

    def test_validate_accepts_entries_written_by_add(self):
        self.add()
        result = self.run_cl("validate")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("checked 1 entries, 0 errors", result.stdout)

    def test_validate_rejects_hand_written_entry(self):
        self.entries.mkdir(parents=True)
        (self.entries / "CL-20261029-1405-zzzz.json").write_text(
            json.dumps(
                {
                    "id": "CL-20261029-1405-zzzz",
                    "timestamp": "yesterday",
                    "type": "chore",
                    "summary": "Same text in both fields",
                    "reason": "same text in both fields",
                }
            )
        )
        result = self.run_cl("validate")
        self.assertEqual(result.returncode, 1)
        for expected in (
            "id must look like",
            "type must be one of",
            "timestamp must be UTC",
            "must say why",
        ):
            self.assertIn(expected, result.stderr)

    def test_validate_rejects_filename_id_mismatch(self):
        self.add()
        path, _ = self.only_entry()
        path.rename(self.entries / "CL-20200101-0000-abcd.json")
        result = self.run_cl("validate")
        self.assertEqual(result.returncode, 1)
        self.assertIn("filename does not match id", result.stderr)

    def test_list_show_and_render(self):
        self.add()
        _, entry = self.only_entry()
        listed = self.run_cl("list", "--last", "5").stdout.splitlines()
        self.assertEqual(
            listed,
            [
                f"{entry['id']} · {entry['timestamp']}",
                "Change: (fixed) Verify webhook signatures on the raw body",
                f"Reason: {REASON}",
            ],
        )
        self.assertIn(REASON, self.run_cl("show", entry["id"]).stdout)
        self.assertNotEqual(self.run_cl("show", "CL-20000101-0000-0000").returncode, 0)
        self.assertEqual(self.run_cl("render").returncode, 0)
        rendered = (self.root / "CHANGELOG.md").read_text()
        self.assertIn(
            f"### {entry['id']} · {entry['timestamp']}\n"
            "- **Change:** (fixed) Verify webhook signatures on the raw body\n"
            f"- **Reason:** {REASON}\n",
            rendered,
        )

    def test_list_separates_entries_with_a_blank_line(self):
        self.add()
        self.add("Second change to the same feature", REASON)
        blocks = self.run_cl("list").stdout.strip().split("\n\n")
        self.assertEqual(len(blocks), 2)
        self.assertTrue(all(len(b.splitlines()) == 3 for b in blocks))

    def git(self, *args):
        subprocess.run(["git", *args], cwd=self.root, check=True, capture_output=True)

    def init_repo(self):
        self.git("init", "-q")
        self.git("config", "user.name", "Tester")
        self.git("config", "user.email", "tester@example.com")

    def test_add_from_subfolder_writes_at_repo_root(self):
        self.init_repo()
        sub = self.root / "src" / "deep"
        sub.mkdir(parents=True)
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "add",
                "--type",
                "added",
                "--summary",
                "x",
                "--reason",
                REASON,
            ],
            cwd=sub,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(list(self.entries.glob("CL-*.json"))), 1)
        self.assertFalse((sub / "changelog").exists())

    def test_add_records_branch_author_and_raw_changed_paths(self):
        self.init_repo()
        (self.root / "old.py").write_text("a")
        (self.root / "my file.py").write_text("b")
        self.git("add", "-A")
        self.git("commit", "-qm", "init")
        self.git("mv", "old.py", "new.py")
        (self.root / "my file.py").write_text("changed")
        (self.root / "untracked dir").mkdir()
        (self.root / "untracked dir" / "n.ts").write_text("c")
        self.add()
        _, entry = self.only_entry()
        self.assertEqual(entry["files"], ["my file.py", "new.py", "untracked dir/n.ts"])
        self.assertEqual(entry["author"], "Tester")
        self.assertIsNotNone(entry["branch"])
        self.assertRegex(entry["base_commit"], r"^[0-9a-f]{7,}$")

    def test_validate_reports_non_object_and_bad_json_without_crashing(self):
        self.entries.mkdir(parents=True)
        (self.entries / "CL-20261029-0000-aaaa.json").write_text("[]")
        (self.entries / "CL-20261029-0000-bbbb.json").write_text("{not json")
        result = self.run_cl("validate")
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("Traceback", result.stderr)
        self.assertIn("must be a JSON object", result.stderr)
        self.assertIn("invalid JSON", result.stderr)

    def test_list_and_render_refuse_malformed_entries_cleanly(self):
        self.entries.mkdir(parents=True)
        (self.entries / "CL-20261029-0000-cccc.json").write_text(
            '{"id": "CL-20261029-0000-cccc"}'
        )
        for cmd in ("list", "render"):
            result = self.run_cl(cmd)
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn("Traceback", result.stderr)
            self.assertIn("run the validate command", result.stderr)

    def test_ids_stay_unique_across_many_adds_in_one_minute(self):
        for i in range(30):
            self.assertEqual(self.add(f"Change number {i}", REASON).returncode, 0)
        ids = [p.stem for p in self.entries.glob("CL-*.json")]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(self.run_cl("validate").returncode, 0)


if __name__ == "__main__":
    unittest.main()
