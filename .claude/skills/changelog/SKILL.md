---
name: changelog
description: Record a finished change as a tracked changelog entry (ID, UTC timestamp, type, summary, reason) using changelog.py, so IDs and times are never invented. Use before committing a finished slice.
---
# Changelog entry

Never write entry files by hand and never invent IDs or timestamps. The script does both.

1. Look at the staged/unstaged diff and the conversation. Draft:
   - `type`: one of feat, fix, refactor, test, docs, chore, perf, security
   - `summary`: one line, what changed, user-facing where possible
   - `reason`: why it changed (the issue, bug or decision behind it)
   - `issue`: the GitHub issue number if there is one
2. Show the user the draft and ask them to confirm or correct the reason. Wait.
3. Write it:
   ```bash
   python3 .claude/skills/changelog/changelog.py add --type feat \
     --summary "..." --reason "..." [--issue 4]
   ```
4. Run `python3 .claude/skills/changelog/changelog.py validate` and include the new
   file in the same commit as the change.

Other commands: `list` (newest first), `render` (prints a Markdown CHANGELOG to stdout).
