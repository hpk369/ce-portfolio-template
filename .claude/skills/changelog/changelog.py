#!/usr/bin/env python3
"""Tracked changelog entries: one JSON file per entry in changelog/entries/.

The script assigns IDs and UTC timestamps so they are never invented by hand.
Standard library only, so it runs in any project and in CI without installs.
"""

from __future__ import annotations

import argparse
import json
import re
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path

ENTRIES_DIR = Path(__file__).resolve().parents[3] / "changelog" / "entries"
TYPES = ("feat", "fix", "refactor", "test", "docs", "chore", "perf", "security")
REQUIRED = ("id", "timestamp", "type", "summary", "reason")
ID_RE = re.compile(r"^\d{8}T\d{6}Z-[0-9a-f]{4}$")


def _load_all() -> list[tuple[Path, dict]]:
    out = []
    for path in sorted(ENTRIES_DIR.glob("*.json")):
        out.append((path, json.loads(path.read_text(encoding="utf-8"))))
    return out


def cmd_add(args: argparse.Namespace) -> int:
    summary, reason = args.summary.strip(), args.reason.strip()
    if not summary or not reason:
        print("summary and reason must be non-empty", file=sys.stderr)
        return 1
    now = datetime.now(timezone.utc).replace(microsecond=0)
    # Timestamp prefix keeps files sorted; random suffix avoids clashes across worktrees.
    entry_id = f"{now:%Y%m%dT%H%M%SZ}-{secrets.token_hex(2)}"
    entry = {
        "id": entry_id,
        "timestamp": now.isoformat().replace("+00:00", "Z"),
        "type": args.type,
        "summary": summary,
        "reason": reason,
    }
    if args.issue is not None:
        entry["issue"] = args.issue
    ENTRIES_DIR.mkdir(parents=True, exist_ok=True)
    path = ENTRIES_DIR / f"{entry_id}.json"
    path.write_text(json.dumps(entry, indent=2) + "\n", encoding="utf-8")
    print(path.relative_to(ENTRIES_DIR.parents[1]))
    return 0


def cmd_validate(_: argparse.Namespace) -> int:
    errors = []
    seen = set()
    for path, entry in _load_all():
        for key in REQUIRED:
            if not str(entry.get(key, "")).strip():
                errors.append(f"{path.name}: missing {key}")
        if entry.get("type") not in TYPES:
            errors.append(f"{path.name}: type must be one of {', '.join(TYPES)}")
        entry_id = entry.get("id", "")
        if not ID_RE.match(entry_id):
            errors.append(f"{path.name}: malformed id {entry_id!r}")
        if path.stem != entry_id:
            errors.append(f"{path.name}: filename does not match id")
        if entry_id in seen:
            errors.append(f"{path.name}: duplicate id")
        seen.add(entry_id)
        try:
            datetime.fromisoformat(str(entry.get("timestamp", "")).replace("Z", "+00:00"))
        except ValueError:
            errors.append(f"{path.name}: timestamp is not ISO 8601")
    for err in errors:
        print(err, file=sys.stderr)
    print(f"{len(seen)} entries, {len(errors)} errors")
    return 1 if errors else 0


def cmd_list(_: argparse.Namespace) -> int:
    for _, e in reversed(_load_all()):
        issue = f" (#{e['issue']})" if "issue" in e else ""
        print(f"{e['timestamp']}  {e['type']:<8} {e['summary']}{issue}")
    return 0


def cmd_render(_: argparse.Namespace) -> int:
    print("# Changelog\n")
    current_day = None
    for _, e in reversed(_load_all()):
        day = e["timestamp"][:10]
        if day != current_day:
            print(f"\n## {day}\n")
            current_day = day
        issue = f" (#{e['issue']})" if "issue" in e else ""
        print(f"- **{e['type']}**: {e['summary']}{issue}  \n  _Why:_ {e['reason']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    add = sub.add_parser("add", help="record a new entry")
    add.add_argument("--type", required=True, choices=TYPES)
    add.add_argument("--summary", required=True)
    add.add_argument("--reason", required=True)
    add.add_argument("--issue", type=int)
    add.set_defaults(func=cmd_add)
    for name, func in (("validate", cmd_validate), ("list", cmd_list), ("render", cmd_render)):
        sub.add_parser(name).set_defaults(func=func)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
