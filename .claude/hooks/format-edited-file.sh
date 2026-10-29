#!/bin/bash
# PostToolUse hook: format only the file Claude just wrote or edited.
# Never fails the tool call; a missing formatter is simply skipped.
file=$(python3 -c 'import json,sys; print(json.load(sys.stdin).get("tool_input", {}).get("file_path", ""))' 2>/dev/null)
[ -f "$file" ] || exit 0
cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0
case "$file" in
  *.py)
    [ -f pyproject.toml ] && uv run --quiet ruff format --quiet "$file" ;;
  *.ts|*.tsx|*.js|*.jsx|*.mjs|*.cjs|*.json|*.css|*.md|*.yml|*.yaml)
    # --no-install: use the project's own prettier, never download one.
    [ -f package.json ] && npx --no-install prettier --write --log-level silent "$file" ;;
esac >/dev/null 2>&1
exit 0
