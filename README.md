# ce-portfolio-template

Starting point for each of the six Customer Engineer portfolio projects. Rules, Claude Code
settings, subagents, skills, CI and secret scanning are written once here and inherited by
every project created from this template.

## What's inside

```text
CLAUDE.md                  rules Claude reads every session
SPEC.md                    fill in per project from the portfolio doc
LEARNING.md                your daily five-line log
.claude/settings.json      project permissions + format-on-edit hook (committed)
.claude/agents/            reviewer, security-reviewer, test-writer subagents
.claude/skills/            adr, ship-check, interview-me, changelog skills
changelog/entries/         one JSON file per changelog entry
.env.example               variable names only, no values
.pre-commit-config.yaml    gitleaks secret scan before every commit
.github/workflows/ci.yml   secret scan, changelog check, Python and/or Node lint, types, tests
docs/adr/0000-template.md  decision record template
setup/user-settings.json   security baseline for ~/.claude/settings.json (one-time, per machine)
scripts/                   live-API scripts you run yourself
```

CI detects the stack: the Python job runs when `pyproject.toml` exists, the Node job when
`package.json` exists. The secret-scan and changelog jobs always run.

## One-time setup (per machine)

These run on your machine, not in a Claude session. On Windows, do all of it inside WSL 2.

1. Install Claude Code and sign in with your personal account:
   ```bash
   curl -fsSL https://claude.ai/install.sh | bash
   claude --version && claude doctor
   ```
   Don't export `ANTHROPIC_API_KEY` in your shell profile.
2. Install tools yourself (not through Claude): git, `gh`, Docker Desktop, Node 22 LTS,
   Python 3.12 + `uv`, `pre-commit`, and on Linux/WSL the sandbox deps:
   `sudo apt-get install bubblewrap socat`.
3. Install the security baseline into your user settings. If `~/.claude/settings.json`
   doesn't exist yet:
   ```bash
   mkdir -p ~/.claude && cp setup/user-settings.json ~/.claude/settings.json
   ```
   If it exists, merge instead (values from the baseline win on conflicts; arrays are replaced, so re-add any of your own deny rules and review the result):
   ```bash
   jq -s '.[0] * .[1]' ~/.claude/settings.json setup/user-settings.json > /tmp/s.json \
     && mv /tmp/s.json ~/.claude/settings.json
   ```
4. Verify: start `claude`, run `/permissions` and `/status` to confirm the rules loaded, then
   ask Claude to run `touch ~/sandbox-probe`. It must fail with "Operation not permitted" or
   "Read-only file system". If Claude offers to retry outside the sandbox, decline.
5. In `/config`, set the output style to **Explanatory** or **Learning**.

## One-time setup (GitHub, this template repo)

- Settings → General → tick **Template repository**.
- Settings → Branches → protect `main`: require a pull request and the CI checks to pass.
- Settings → Code security → enable **Secret scanning** with **Push protection**, and
  **Dependabot alerts**.

## Starting a new project

```bash
cd ~/code/portfolio
gh repo create <project-name> --template <you>/ce-portfolio-template --private --clone
cd <project-name>
pre-commit install
cp .env.example .env        # fill in this project's own Console key, with a spend limit
```

Then apply the same branch protection / secret scanning settings to the new repo, fill in
`SPEC.md`, and run the kickoff in plan mode (`claude --permission-mode plan`):

```text
Read CLAUDE.md and SPEC.md. Don't write code yet.
Propose: the architecture and folder structure, the first five vertical
slices as GitHub issues with acceptance tests, and every decision I need
to make, each as an ADR candidate with two or three options and tradeoffs.
Flag anything in SPEC.md that is ambiguous or too big for the MVP.
```

For Docker projects (2 and 6), `docker compose` is excluded from the sandbox and runs with
your full access: read the compose file before approving each run. For Project 4, add the
`tfsec` or `checkov` step to CI and keep every `terraform plan/apply/destroy` for yourself.

## The loop for every slice

1. **Issue** — one "Done when" item → one GitHub issue with acceptance criteria.
2. **Branch** — `claude --worktree p1-<slice>`.
3. **Plan** — plan mode; *"Read CLAUDE.md, SPEC.md and issue #N. Propose a plan, the tests
   that prove it, and any decision I need to make. Don't write code."*
4. **Test first** — accept-edits mode; use the `test-writer` subagent, then implement.
5. **Verify** — Claude runs tests, lint, types; then *"prove this works"* end to end.
6. **Review** — read `git diff` yourself; ask the `reviewer` (and `security-reviewer`) subagent.
7. **Commit and ship** — `/changelog`, conventional commit; *you* push, `gh pr create`, merge on green.
8. **Capture** — `/adr` draft, rewrite it yourself; *"Update CLAUDE.md so this doesn't happen again."*

## Daily and weekly

- End of day: five lines in `LEARNING.md`, rewrite ADR drafts, tear down anything in AWS.
- Weekly: `claude doctor`; prune "don't ask again" approvals in `.claude/settings.local.json`;
  break-fix drill without AI.
