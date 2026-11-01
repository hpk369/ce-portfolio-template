# How this repo is set up (template guide)

This repo started from `ce-portfolio-template`, the starting point for each of the six
Customer Engineer portfolio projects. Rules, Claude Code settings, subagents, skills, CI and
secret scanning are written once in the template and inherited by every project. The
project's own story lives in the top-level `README.md`.

## What's inside

```text
README.md                  project README skeleton: problem, demo, architecture, run, decisions
LICENSE                    MIT; change the copyright line to your name if you like
CLAUDE.md                  rules Claude reads every session
SPEC.md                    fill in per project from the portfolio doc
LEARNING.md                your daily five-line log
.claude/settings.json      project permissions + format-on-edit hook (committed)
.claude/hooks/             format-edited-file.sh: formats only the file Claude just edited
.claude/agents/            scope-reviewer, security-reviewer, test-writer subagents
.claude/skills/            /adr, /ship-check, /interview-me (manual) and changelog skills
changelog/entries/         one JSON file per changelog entry (CL-YYYYMMDD-HHMM-xxxx.json)
tests/test_changelog*.py   tests for the changelog and diagrams tool (stdlib unittest)
.env.example               variable names only, no values
.pre-commit-config.yaml    gitleaks secret scan before every commit
.github/workflows/ci.yml   secret scan, changelog check, Python and/or Node lint, types, tests
docs/adr/0000-template.md  decision record template
docs/diagrams/             generated code diagrams (components, UML classes, call graph)
docs/integration-guide.md  deliverable 4: for the customer's engineers
docs/runbook.md            deliverable 5: for whoever is on call
docs/template-guide.md     this guide
setup/user-settings.json   security baseline for ~/.claude/settings.json (one-time, per machine)
scripts/                   fetch-customer-data.sh, plus live-API scripts you run yourself
```

CI detects the stack: the Python job runs when `pyproject.toml` exists, the Node job when
`package.json` exists. The secret-scan, changelog and code-diagrams jobs always run, and every
pull request must add at least one changelog entry.

## Code diagrams

`python3 .claude/skills/changelog/changelog.py diagrams` reads the Python and
TypeScript/JavaScript source (standard library only, no Graphviz or Java) and writes
`docs/diagrams/architecture.md` with three Mermaid diagrams that GitHub renders inline:

| Diagram | Like | Shows |
| --- | --- | --- |
| Components | Structurizr (C4 component view) | modules grouped by package or folder; arrows are imports |
| Classes | Umbrello (UML class diagram) | attributes, methods, visibility, `<<interface>>`/`<<abstract>>`, inheritance and implements |
| Call graph | Doxygen call graph | which project function calls which (Python) |

Tests, `.venv`, `node_modules`, dot-folders and untracked files are left out, so the
diagrams show exactly what is committed.

- **On every commit**, the `code-diagrams` pre-commit hook regenerates the file. If it changed,
  the commit stops once: review the diff, `git add docs/diagrams`, and commit again.
- **On every push and PR**, the `Code diagrams` CI job regenerates them from scratch, shows them
  in the run summary, uploads them as the `code-diagrams` artifact, and fails if the committed
  copy is stale (for example, a commit made with `--no-verify`).

Add `Code diagrams` to the required checks in your `main` ruleset to enforce this. Link the file
from each project's README for the "README with architecture diagram" deliverable; draw the
hand-made context diagram (customer systems, external APIs) yourself, since no tool can infer it.

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
   **Updating:** when `setup/user-settings.json` changes, re-run the merge above; it replaces the
   `deny` list and `sandbox` block with the new baseline. The baseline lists real secret files
   by name (`.env`, `.env.local`, `.env.production`, ...) rather than `.env.*`, because the
   sandbox turns read denies into file blocks and would hide `.env.example` from git, failing
   every commit. It also lets sandboxed commands write to three tool caches
   (`~/.cache/pre-commit`, `~/.cache/uv`, `~/.npm`) so pre-commit, `uv sync` and `npm ci` work.
   If you sign commits with an SSH key in `~/.ssh`, Claude's commits fail inside the sandbox
   (it hides `~/.ssh`); sign only your own merges, or turn signing off per repo with
   `git config commit.gpgsign false`.
4. Verify: start `claude`, run `/permissions` and `/status` to confirm the rules loaded, then
   ask Claude to run `touch ~/sandbox-probe`. It must fail with "Operation not permitted" or
   "Read-only file system". If Claude offers to retry outside the sandbox, decline.
5. In `/config`, set the output style to **Explanatory** or **Learning**.

## One-time setup: plugins (per machine, user scope)

Install exactly two plugins, both language servers from the official marketplace.

1. Install the server binaries and check they're on your PATH. Pin `typescript@6`:
   TypeScript 7 (now `latest` on npm) no longer ships `tsserver`, so
   `typescript-language-server` fails with "Could not find a valid TypeScript installation".
   ```bash
   npm install -g typescript-language-server typescript@6 pyright
   which typescript-language-server pyright-langserver
   tsc --version    # must print 6.x
   ```
2. In a Claude Code session, install each plugin and choose **Install for you (user scope)**
   so nothing is written into the repo's committed settings:
   ```text
   /plugin install typescript-lsp@claude-plugins-official
   /plugin install pyright-lsp@claude-plugins-official
   ```
   If either says the marketplace `claude-plugins-official` isn't found, add it and retry:
   `/plugin marketplace add anthropics/claude-plugins-official`.
3. Confirm only what you intended is loaded: `claude plugin list` in a terminal, `/skills`
   inside a session. Each plugin should show 0 skills, hooks and MCP servers and ~0 tokens
   (`claude plugin details pyright-lsp`).
4. Confirm the servers start (they launch on the first edit, and only in local terminal
   sessions, not cloud sessions). Ask Claude: *"In a scratch .py file, add a call that passes
   a string where an int is expected, then fix it."* A line like
   `Found 1 new diagnostic issue in 1 file` must appear under the edit; repeat with a `.ts`
   file. If not, `/plugin` → **Errors** tab names the missing binary.

Skip `/autofix-pr`, the `commit-commands` and `github` plugins, `/batch`, and any community
marketplace: they push for you, duplicate `gh`, or add third-party code you don't need.

## Built-in commands by stage

| Stage | Commands |
| --- | --- |
| First session in a new repo | `/init` (edit the result down), `/run-skill-generator` once the app runs |
| Start of every slice | `/plan` |
| During a task | `/claude-api` (`build-eval` for P5, `cost-optimize` for P6), `/context`, `/usage` |
| After implementing | `/verify` |
| Before you push, in this order | `/code-review` → `/security-review` → `/simplify`, plus the `scope-reviewer` subagent |
| Weekly | `/doctor`; `/fewer-permission-prompts` once a project is underway (read what it adds) |

## One-time setup (GitHub, this template repo)

- Settings → General → tick **Template repository**.
- Settings → Branches → protect `main`: require a pull request and the CI checks to pass.
- Settings → Code security → enable **Secret scanning** with **Push protection**, and
  **Dependabot alerts**.

## Starting a new project

```bash
cd ~/code/portfolio
# Public: reviewers need to see it, and on a free plan rulesets and secret scanning
# are only enforced on public repos.
gh repo create <project-name> --template hpk369/ce-portfolio-template --public --clone
cd <project-name>
pre-commit install --install-hooks   # outside Claude, so hook environments are ready
cp .env.example .env                 # this project's own Console key, with a spend limit
scripts/fetch-customer-data.sh       # synthetic customer profiles into data/
```

Then:

1. Apply the same ruleset and secret scanning settings to the new repo, and add
   `Code diagrams` to its required checks.
2. Fill in `SPEC.md`, and replace the `<Project name>` placeholders in `README.md`,
   `docs/integration-guide.md` and `docs/runbook.md` (fill them in as the project grows;
   `/ship-check` reports what's still missing).
3. Run the kickoff in plan mode (`claude --permission-mode plan`):

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
6. **Review** — read `git diff` yourself; run `/code-review`, `/security-review`, `/simplify`,
   and ask the `scope-reviewer` subagent (plus `security-reviewer` for P3, P4, P6).
7. **Commit and ship** — changelog entry (you confirm the reason), conventional commit; *you*
   push, `gh pr create`, merge on green. After merging, render `CHANGELOG.md` on `main`:
   `python3 .claude/skills/changelog/changelog.py render`.
8. **Capture** — `/adr` draft, rewrite it yourself; *"Update CLAUDE.md so this doesn't happen again."*

## Daily and weekly

- End of day: five lines in `LEARNING.md`, rewrite ADR drafts, tear down anything in AWS.
- Weekly: `claude doctor`; prune "don't ask again" approvals in `.claude/settings.local.json`;
  break-fix drill without AI.
