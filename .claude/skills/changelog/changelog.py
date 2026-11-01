#!/usr/bin/env python3
"""Changelog tool for the changelog skill.

Each entry is its own JSON file in changelog/entries/, so parallel branches
and worktrees never conflict. CHANGELOG.md is rendered from those files.

  changelog.py add --type fixed --summary "..." --reason "..." [--issue 12] [--adr docs/adr/0003-x.md]
  changelog.py list [--last 10]
  changelog.py show CL-20261029-1405-a3f2
  changelog.py validate
  changelog.py render
  changelog.py diagrams [--check | --fail-on-change]

The diagrams command reads the project's Python and TypeScript/JavaScript source
and writes docs/diagrams/architecture.md with three Mermaid diagrams, which GitHub
renders inline: a component view of module imports (like Structurizr), a UML class
diagram (like Umbrello) and a call graph (like Doxygen). Output is deterministic, so
--check can fail CI when the committed diagrams are stale.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
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


# --- Code diagrams ----------------------------------------------------------

DIAGRAMS = ROOT / "docs" / "diagrams" / "architecture.md"
PY_EXT = (".py",)
JS_EXT = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs")
# Tests, tooling and generated folders would drown out the application's structure.
SKIP_DIRS = {
    "node_modules",
    "venv",
    "tests",
    "test",
    "__tests__",
    "dist",
    "build",
    "coverage",
    "docs",
    "changelog",
    "__pycache__",
}


def is_source(rel: str) -> bool:
    parts = rel.split("/")
    if any(d.startswith(".") or d in SKIP_DIRS for d in parts[:-1]):
        return False
    name = parts[-1]
    if name.endswith((".d.ts", "_test.py")) or name.startswith("test_"):
        return False
    if re.search(r"\.(test|spec)\.[cm]?[jt]sx?$", name):
        return False
    return name.endswith(PY_EXT + JS_EXT)


def source_files() -> list[str]:
    # In a git repo use the index, so the diagrams match what is committed (and what
    # CI sees); untracked scratch files stay out. Otherwise walk the folder.
    listed = git("ls-files", "-z", strip=False)
    if listed:
        rels = [f for f in listed.split("\0") if f]
    else:
        rels = [
            str(p.relative_to(ROOT)).replace(os.sep, "/")
            for p in ROOT.rglob("*")
            if p.is_file()
        ]
    return sorted(f for f in rels if is_source(f) and (ROOT / f).is_file())


def node_id(name: str) -> str:
    return "n_" + re.sub(r"\W", "_", name)


class Model:
    """What the diagrams draw, collected from every source file."""

    def __init__(self) -> None:
        self.modules: dict[str, str] = {}  # module name -> language
        self.imports: set[tuple[str, str]] = set()
        self.classes: dict[str, dict] = {}  # "module.Class" -> details
        self.functions: set[str] = set()  # "module.func" and "module.Class.method"
        self.calls: set[tuple[str, str]] = set()


def py_module_name(rel: str) -> str:
    parts = rel[: -len(".py")].split("/")
    if parts[0] == "src" and len(parts) > 1:
        parts = parts[1:]
    if parts[-1] == "__init__" and len(parts) > 1:
        parts = parts[:-1]
    return ".".join(parts)


def py_resolve(name: str, known: dict[str, str]) -> str | None:
    """Longest project module that name refers to, or None for third-party code."""
    parts = name.split(".")
    for i in range(len(parts), 0, -1):
        candidate = ".".join(parts[:i])
        if known.get(candidate) == "python":
            return candidate
    return None


def py_args(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    names = [a.arg for a in fn.args.posonlyargs + fn.args.args + fn.args.kwonlyargs]
    return ", ".join(n for n in names if n not in ("self", "cls"))


def py_callee(
    model: Model, call: ast.Call, mod: str, cls: str | None, aliases: dict[str, str]
) -> str | None:
    """The project function a call refers to: local, imported, module.attr or self.method."""
    f = call.func
    if isinstance(f, ast.Name):
        for cand in (f"{mod}.{f.id}", aliases.get(f.id, "")):
            if cand in model.functions:
                return cand
    elif isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name):
        own = f"{mod}.{cls}.{f.attr}"
        if f.value.id in ("self", "cls") and cls and own in model.functions:
            return own
        cand = f"{aliases.get(f.value.id, f.value.id)}.{f.attr}"
        if cand in model.functions:
            return cand
    return None


def py_scan_calls(
    model: Model,
    fn: ast.AST,
    caller: str,
    mod: str,
    cls: str | None,
    aliases: dict[str, str],
) -> None:
    for sub in ast.walk(fn):
        if isinstance(sub, ast.Call):
            target = py_callee(model, sub, mod, cls, aliases)
            if target and target != caller:
                model.calls.add((caller, target))


def collect_python(model: Model, files: dict[str, str]) -> None:
    trees = {}
    for rel, mod in files.items():
        try:
            trees[mod] = (rel, ast.parse((ROOT / rel).read_text(encoding="utf-8"), rel))
        except (SyntaxError, UnicodeDecodeError) as exc:
            print(f"warning: skipped {rel}: {exc}", file=sys.stderr)
    for mod in trees:
        model.modules[mod] = "python"
    # First pass: what each module defines.
    for mod, (_, tree) in trees.items():
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                model.functions.add(f"{mod}.{node.name}")
            elif isinstance(node, ast.ClassDef):
                attrs, methods = set(), []
                for item in node.body:
                    if isinstance(item, ast.AnnAssign) and isinstance(
                        item.target, ast.Name
                    ):
                        attrs.add(item.target.id)
                    elif isinstance(item, ast.Assign):
                        attrs.update(
                            t.id for t in item.targets if isinstance(t, ast.Name)
                        )
                    elif isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        model.functions.add(f"{mod}.{node.name}.{item.name}")
                        for sub in ast.walk(item):
                            if isinstance(sub, (ast.Assign, ast.AnnAssign)):
                                targets = (
                                    sub.targets
                                    if isinstance(sub, ast.Assign)
                                    else [sub.target]
                                )
                                for t in targets:
                                    if (
                                        isinstance(t, ast.Attribute)
                                        and isinstance(t.value, ast.Name)
                                        and t.value.id == "self"
                                    ):
                                        attrs.add(t.attr)
                        if not (
                            item.name.startswith("__") and item.name.endswith("__")
                        ):
                            ret = (
                                item.returns.id
                                if isinstance(item.returns, ast.Name)
                                else ""
                            )
                            methods.append((item.name, py_args(item), ret))
                model.classes[f"{mod}.{node.name}"] = {
                    "name": node.name,
                    "module": mod,
                    "attrs": sorted(attrs),
                    "methods": methods,
                    "bases": [ast.unparse(b) for b in node.bases],
                    "implements": [],
                    "stereotype": "abstract"
                    if any(
                        ast.unparse(b) in ("ABC", "abc.ABC", "Protocol")
                        for b in node.bases
                    )
                    else "",
                }
    # Second pass: imports and calls, resolved against what the project defines.
    for mod, (rel, tree) in trees.items():
        is_pkg = rel.endswith("__init__.py")
        aliases: dict[str, str] = {}  # local name -> "module" or "module.name"
        for imp in ast.walk(tree):
            if isinstance(imp, ast.Import):
                for a in imp.names:
                    target = py_resolve(a.name, model.modules)
                    if target:
                        model.imports.add((mod, target))
                        aliases[a.asname or a.name.split(".")[0]] = (
                            target if a.asname else a.name.split(".")[0]
                        )
            elif isinstance(imp, ast.ImportFrom):
                base = imp.module or ""
                if imp.level:
                    pkg = mod.split(".") if is_pkg else mod.split(".")[:-1]
                    pkg = pkg[: len(pkg) - (imp.level - 1)] if imp.level > 1 else pkg
                    base = ".".join(pkg + ([imp.module] if imp.module else []))
                for a in imp.names:
                    target = py_resolve(
                        f"{base}.{a.name}", model.modules
                    ) or py_resolve(base, model.modules)
                    if target:
                        model.imports.add((mod, target))
                        aliases[a.asname or a.name] = f"{base}.{a.name}"
        model.imports.discard((mod, mod))

        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                py_scan_calls(model, node, f"{mod}.{node.name}", mod, None, aliases)
            elif isinstance(node, ast.ClassDef):
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        caller = f"{mod}.{node.name}.{item.name}"
                        py_scan_calls(model, item, caller, mod, node.name, aliases)


JS_IMPORT = re.compile(
    r"""(?:\bfrom\s*|\bimport\s*\(?\s*|\brequire\(\s*)['"](\.{1,2}/[^'"]+)['"]"""
)
JS_CLASS = re.compile(
    r"\b(abstract\s+)?(class|interface)\s+(\w+)(?:<[^>{]*>)?"
    r"(?:\s+extends\s+([\w.,\s]+?))?(?:\s+implements\s+([\w.,\s]+?))?\s*\{"
)
JS_METHOD = re.compile(
    r"^\s*(?:(?:public|private|protected|static|async|readonly|override|get|set)\s+)*(#?\w+)\s*\(([^)]*)\)"
)
JS_FIELD = re.compile(
    r"^\s*(?:(?:public|private|protected|static|readonly)\s+)*(#?\w+)\s*[?!]?\s*[:=]"
)
JS_KEYWORDS = {
    "if",
    "for",
    "while",
    "switch",
    "catch",
    "return",
    "function",
    "constructor",
    "super",
}


def js_resolve(rel: str, spec: str, known: set[str]) -> str | None:
    base = os.path.normpath(os.path.join(os.path.dirname(rel), spec)).replace(
        os.sep, "/"
    )
    base = re.sub(r"\.[cm]?[jt]sx?$", "", base)
    for cand in (base, f"{base}/index"):
        if cand in known:
            return cand
    return None


def collect_js(model: Model, files: list[str]) -> None:
    mods = {re.sub(r"\.[cm]?[jt]sx?$", "", f): f for f in files}
    for js_mod in mods:
        model.modules[js_mod] = "typescript"
    for mod, rel in mods.items():
        text = (ROOT / rel).read_text(encoding="utf-8", errors="replace")
        for spec in JS_IMPORT.findall(text):
            target = js_resolve(rel, spec, set(mods))
            if target and target != mod:
                model.imports.add((mod, target))
        for match in JS_CLASS.finditer(text):
            # Members are lines at brace depth 1 inside the class body.
            depth, i, body = 1, match.end(), []
            line, line_depth = "", 1
            while i < len(text) and depth:
                ch = text[i]
                if ch == "\n":
                    if line_depth == 1:
                        body.append(line)
                    line, line_depth = "", depth
                elif depth == 1:
                    line += ch
                depth += {"{": 1, "}": -1}.get(ch, 0)
                i += 1
            if line_depth == 1:
                body.append(line)
            attrs, methods = set(), []
            for ln in body:
                m = JS_METHOD.match(ln)
                if m and m.group(1) not in JS_KEYWORDS:
                    private = m.group(1).startswith("#") or re.search(
                        r"\bprivate\b", ln
                    )
                    args = ", ".join(
                        a.split(":")[0].split("=")[0].strip(" ?.")
                        for a in m.group(2).split(",")
                        if a.strip()
                    )
                    methods.append(
                        (
                            "_" + m.group(1).lstrip("#") if private else m.group(1),
                            args,
                            "",
                        )
                    )
                elif (f := JS_FIELD.match(ln)) and f.group(1) not in JS_KEYWORDS:
                    private = f.group(1).startswith("#") or re.search(
                        r"\bprivate\b", ln
                    )
                    attrs.add("_" + f.group(1).lstrip("#") if private else f.group(1))
            abstract, kind, name = match.group(1), match.group(2), match.group(3)
            bases = [b.strip() for b in (match.group(4) or "").split(",") if b.strip()]
            impls = [b.strip() for b in (match.group(5) or "").split(",") if b.strip()]
            model.classes[f"{mod}.{name}"] = {
                "name": name,
                "module": mod,
                "attrs": sorted(attrs),
                "methods": methods,
                "bases": bases,
                "implements": impls,
                "stereotype": "interface"
                if kind == "interface"
                else "abstract"
                if abstract
                else "",
            }


def build_model() -> Model:
    model = Model()
    files = source_files()
    collect_python(model, {f: py_module_name(f) for f in files if f.endswith(PY_EXT)})
    collect_js(model, [f for f in files if f.endswith(JS_EXT)])
    return model


def parent(name: str, siblings: list[str]) -> str:
    sep = "/" if "/" in name else "."
    if any(o.startswith(name + sep) for o in siblings):
        return name  # a package (its __init__) belongs inside its own group
    return name.rsplit(sep, 1)[0] if sep in name else "(root)"


def grouped_nodes(names: list[str], label) -> list[str]:
    """Mermaid subgraphs: one per package or folder (or module, for functions)."""
    groups: dict[str, list[str]] = {}
    for n in names:
        groups.setdefault(parent(n, names), []).append(n)
    out = []
    for g in sorted(groups):
        out.append(f'  subgraph {node_id("g_" + g)}["{g}"]')
        out += [f'    {node_id(n)}["{label(n)}"]' for n in sorted(groups[g])]
        out.append("  end")
    return out


def diagrams_markdown(model: Model) -> str:
    py = sum(1 for v in model.modules.values() if v == "python")
    js = len(model.modules) - py
    out = [
        "# Code diagrams",
        "",
        "<!-- Generated by `python3 .claude/skills/changelog/changelog.py diagrams`. Do not edit:",
        "     the pre-commit hook regenerates this file and CI fails if it is stale. -->",
        "",
        (
            f"Python modules: {py}. TypeScript/JavaScript modules: {js}. "
            f"Classes: {len(model.classes)}. Functions and methods: {len(model.functions)}."
        ),
        "Tests, tooling and dot-folders are left out.",
        "",
    ]
    if not model.modules:
        out += [
            "_No source code yet. Diagrams appear here after the first module is committed._",
            "",
        ]
        return "\n".join(out)

    out += [
        "## Components",
        "",
        (
            'Each box is a module, grouped by package; an arrow means "imports" '
            "(a component view, like Structurizr)."
        ),
        "",
        "```mermaid",
        "flowchart LR",
    ]
    out += grouped_nodes(
        list(model.modules), lambda n: n.rsplit(".", 1)[-1].rsplit("/", 1)[-1]
    )
    out += [f"  {node_id(a)} --> {node_id(b)}" for a, b in sorted(model.imports)]
    out += ["```", ""]

    out += [
        "## Classes",
        "",
        (
            "Attributes and methods per class; `+` public, `-` private (underscore or `#`); "
            "`<|--` inherits, `<|..` implements (a UML class diagram, like Umbrello)."
        ),
        "",
    ]
    if model.classes:
        short = {}
        for key, c in model.classes.items():
            dupes = [k for k, d in model.classes.items() if d["name"] == c["name"]]
            short[key] = c["name"] if len(dupes) == 1 else re.sub(r"\W", "_", key)
        by_name = {c["name"]: k for k, c in model.classes.items()}
        out += ["```mermaid", "classDiagram"]
        for key in sorted(model.classes):
            c = model.classes[key]
            out.append(f"  class {short[key]}")
            if c["stereotype"]:
                out.append(f"  <<{c['stereotype']}>> {short[key]}")
            for a in c["attrs"]:
                out.append(
                    f"  {short[key]} : {'-' if a.startswith('_') else '+'}{a.lstrip('_')}"
                )
            for name, args, ret in c["methods"]:
                vis = "-" if name.startswith("_") else "+"
                out.append(
                    f"  {short[key]} : {vis}{name.lstrip('_')}({args}){' ' + ret if ret else ''}"
                )
        for key in sorted(model.classes):
            for base in model.classes[key]["bases"]:
                target = by_name.get(base.rsplit(".", 1)[-1])
                if target:
                    out.append(f"  {short[target]} <|-- {short[key]}")
            for iface in model.classes[key]["implements"]:
                target = by_name.get(iface.rsplit(".", 1)[-1])
                if target:
                    out.append(f"  {short[target]} <|.. {short[key]}")
        out += ["```", ""]
    else:
        out += ["_No classes found._", ""]

    out += [
        "## Call graph",
        "",
        (
            "Which project function calls which, grouped by module "
            "(a call graph, like Doxygen). Python only; calls into libraries are left out."
        ),
        "",
    ]
    if model.calls:
        used = sorted({n for edge in model.calls for n in edge})
        out += ["```mermaid", "flowchart LR"]
        out += grouped_nodes([n for n in used], lambda n: n.rsplit(".", 1)[-1] + "()")
        out += [f"  {node_id(a)} --> {node_id(b)}" for a, b in sorted(model.calls)]
        out += ["```", ""]
    else:
        out += ["_No calls between project functions found._", ""]
    return "\n".join(out)


def cmd_diagrams(a):
    text = diagrams_markdown(build_model())
    current = DIAGRAMS.read_text() if DIAGRAMS.exists() else None
    rel = DIAGRAMS.relative_to(ROOT)
    if a.check:
        if current != text:
            sys.exit(
                f"error: {rel} is out of date; run: python3 .claude/skills/changelog/changelog.py diagrams"
            )
        print(f"{rel} is up to date")
        return
    if current == text:
        print(f"{rel} unchanged")
        return
    DIAGRAMS.parent.mkdir(parents=True, exist_ok=True)
    DIAGRAMS.write_text(text)
    print(f"wrote {rel}")
    if a.fail_on_change:
        # pre-commit only notices edits to tracked files, so a first-time file would
        # slip through; failing here stops the commit either way.
        sys.exit(
            f"{rel} was updated; review it, git add {rel.parent}, and commit again"
        )


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
    dg = sub.add_parser("diagrams", help="write docs/diagrams/architecture.md")
    dg.add_argument("--check", action="store_true", help="fail if the file is stale")
    dg.add_argument(
        "--fail-on-change",
        action="store_true",
        help="write, then fail if it changed (pre-commit)",
    )
    dg.set_defaults(fn=cmd_diagrams)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
