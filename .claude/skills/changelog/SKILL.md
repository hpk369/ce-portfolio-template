---
name: changelog
description: Record a changelog entry (ID, UTC timestamp, type, summary, reason) for a finished change, or list, show or render the changelog. Use before committing a completed slice.
---
Record changes only with the script in this folder. Never write entry files, IDs or
timestamps by hand. Run commands from the repo root.

To add an entry:
1. Run `git status` and `git diff` to see what changed.
2. Draft the entry: type (added, changed, fixed, removed, security or docs), a one-line
   summary of what changed, and the reason: the problem it solves or the decision behind
   it. Add the issue number and ADR path if there are any.
3. Show me the draft in the same three lines the changelog uses, and wait for my OK or edits:
   ```
   <ID assigned on write> · <UTC timestamp assigned on write>
   Change: (<type>) <summary>
   Reason: <reason>
   ```
   Never record a reason I haven't confirmed.
4. Run:
   python3 .claude/skills/changelog/changelog.py add --type <type> --summary "<summary>" --reason "<reason>" [--issue <n>] [--adr <path>]
5. Report the ID and timestamp it prints, and stage the new file in changelog/entries/
   with the rest of the change.

Other commands:
- Recent entries: python3 .claude/skills/changelog/changelog.py list --last 10
- One entry: python3 .claude/skills/changelog/changelog.py show <ID>
- Check every entry is well formed (CI runs this): python3 .claude/skills/changelog/changelog.py validate
- Rebuild CHANGELOG.md: python3 .claude/skills/changelog/changelog.py render
  Only on main after merging, never on a feature branch.
