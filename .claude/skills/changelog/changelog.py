#!/usr/bin/env python3
"""Changelog tool for the changelog skill.

Each entry is its own JSON file in changelog/entries/, so parallel branches
and worktrees never conflict. CHANGELOG.md is rendered from those files.

  changelog.py add --type fixed --summary "..." --reason "..." [--issue 12] [--adr docs/adr/0003-x.md]
  changelog.py list [--last 10]
  changelog.py show CL-20261029-1405-a3f2
  changelog.py validate
  changelog.py render
"""

import argparse
import json
import re
import secrets
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

TYPES = ["added", "changed", "fixed", "removed", "security", "docs"]
ID_RE = re.compile(r"^CL-\d{8}-\d{4}-[0-9a-f]{4}$")
MIN_REASON = 15


def git(*args, strip=True):
    try:
        out = subprocess.run(["git", *args], capture_output=True, text=True, check=True)
        return out.stdout.strip() if strip else out.stdout.rstrip("\n")
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


# Paths are anchored at the repo root, so running from a subfolder still writes
# entries where CI looks for them. Outside a git repo, the current folder is the root.
ROOT = Path(git("rev-parse", "--show-toplevel") or ".")
ENTRIES = ROOT / "changelog" / "entries"
OUTPUT = ROOT / "CHANGELOG.md"


def changed_files():
    # -z gives raw paths (no quoting of spaces) separated by NUL. Each record is a
    # two-character status, a space and the path; a rename or copy is followed by an
    # extra record holding the old path, which we skip.
    records = git(
        "status", "--porcelain", "-z", "--untracked-files=all", strip=False
    ).split("\0")
    files, i = set(), 0
    while i < len(records):
        rec = records[i]
        if len(rec) > 3:
            files.add(rec[3:])
            if rec[0] in "RC":
                i += 1
        i += 1
    return sorted(
        f for f in files if not f.startswith("changelog/") and f != "CHANGELOG.md"
    )


def new_id(now):
    while True:
        cid = f"CL-{now:%Y%m%d-%H%M}-{secrets.token_hex(2)}"
        if not (ENTRIES / f"{cid}.json").exists():
            return cid


def reason_error(summary, reason):
    if len(reason) < MIN_REASON:
        return f"--reason must explain why (at least {MIN_REASON} characters)"
    if reason.lower() == summary.lower():
        return "--reason must say why, not repeat the summary"
    return None


def load_entries():
    entries = []
    for p in ENTRIES.glob("CL-*.json"):
        try:
            e = json.loads(p.read_text())
        except json.JSONDecodeError:
            e = None
        if not isinstance(e, dict) or not all(
            k in e for k in ("id", "timestamp", "type", "summary", "reason")
        ):
            sys.exit(
                f"error: {p.name} is malformed; run the validate command for details"
            )
        entries.append(e)
    return sorted(entries, key=lambda e: e["timestamp"], reverse=True)


def cmd_add(a):
    summary, reason = a.summary.strip(), a.reason.strip()
    err = reason_error(summary, reason)
    if err:
        sys.exit(f"error: {err}")
    now = datetime.now(timezone.utc)  # noqa: UP017 (datetime.UTC needs Python 3.11; macOS python3 is 3.9)
    entry = {
        "id": new_id(now),
        "timestamp": now.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "type": a.type,
        "summary": summary,
        "reason": reason,
        "issue": a.issue,
        "adr": a.adr,
        "branch": git("rev-parse", "--abbrev-ref", "HEAD") or None,
        "base_commit": git("rev-parse", "--short", "HEAD") or None,
        "author": git("config", "user.name") or None,
        "files": changed_files(),
    }
    ENTRIES.mkdir(parents=True, exist_ok=True)
    path = ENTRIES / f"{entry['id']}.json"
    path.write_text(json.dumps(entry, indent=2) + "\n")
    print(f"{entry['id']}  {entry['timestamp']}  {path.relative_to(ROOT)}")


def three_lines(e):
    """Every entry reads the same way: ID and timestamp, the change, the reason."""
    return [
        f"{e['id']} · {e['timestamp']}",
        f"Change: ({e['type']}) {e['summary']}",
        f"Reason: {e['reason']}",
    ]


def cmd_list(a):
    print("\n\n".join("\n".join(three_lines(e)) for e in load_entries()[: a.last]))


def cmd_show(a):
    path = ENTRIES / f"{a.id}.json"
    if not path.exists():
        sys.exit(f"error: no entry {a.id}")
    print(path.read_text(), end="")


def cmd_validate(_):
    errors = []
    count = 0
    for path in sorted(ENTRIES.glob("*.json")):
        count += 1
        name = path.name
        try:
            e = json.loads(path.read_text())
        except json.JSONDecodeError as exc:
            errors.append(f"{name}: invalid JSON ({exc})")
            continue
        if not isinstance(e, dict):
            errors.append(f"{name}: must be a JSON object")
            continue
        if not ID_RE.match(str(e.get("id", ""))):
            errors.append(f"{name}: id must look like CL-YYYYMMDD-HHMM-xxxx")
        elif path.stem != e["id"]:
            errors.append(f"{name}: filename does not match id {e['id']}")
        if e.get("type") not in TYPES:
            errors.append(f"{name}: type must be one of {', '.join(TYPES)}")
        try:
            datetime.strptime(str(e.get("timestamp", "")), "%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            errors.append(f"{name}: timestamp must be UTC like 2026-10-29T14:05:32Z")
        summary, reason = (
            str(e.get("summary", "")).strip(),
            str(e.get("reason", "")).strip(),
        )
        if not summary:
            errors.append(f"{name}: summary is empty")
        err = reason_error(summary, reason)
        if err:
            errors.append(f"{name}: {err.removeprefix('--')}")
    for err in errors:
        print(err, file=sys.stderr)
    print(f"checked {count} entries, {len(errors)} errors")
    if errors:
        sys.exit(1)


def cmd_render(_):
    lines = [
        "# Changelog",
        "",
        "Generated from changelog/entries/ by the changelog skill. Newest first; times in UTC.",
        "",
    ]
    for e in load_entries():
        head, change, reason = three_lines(e)
        lines += [
            f"### {head}",
            f"- **{change.replace(':', ':**', 1)}",
            f"- **{reason.replace(':', ':**', 1)}",
            "",
        ]
    OUTPUT.write_text("\n".join(lines))
    print(f"rendered {len(load_entries())} entries to {OUTPUT.name}")


def main():
    p = argparse.ArgumentParser(description="Record and render changelog entries")
    sub = p.add_subparsers(dest="cmd", required=True)
    add = sub.add_parser("add")
    add.add_argument("--type", required=True, choices=TYPES)
    add.add_argument("--summary", required=True)
    add.add_argument("--reason", required=True)
    add.add_argument("--issue", type=int)
    add.add_argument("--adr")
    add.set_defaults(fn=cmd_add)
    ls = sub.add_parser("list")
    ls.add_argument("--last", type=int, default=10)
    ls.set_defaults(fn=cmd_list)
    show = sub.add_parser("show")
    show.add_argument("id")
    show.set_defaults(fn=cmd_show)
    sub.add_parser("validate").set_defaults(fn=cmd_validate)
    sub.add_parser("render").set_defaults(fn=cmd_render)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
