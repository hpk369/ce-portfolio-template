---
name: ship-check
description: Check the project against SPEC.md's "Done when" list and Deliverables list and report what is missing. Use before calling a project finished or before a demo.
---
# Ship check

Read-only. Don't fix anything; report.

1. Read SPEC.md. Extract every "Done when" item and every Deliverable.
2. For each item, look for evidence in the repo: code, tests that exercise it, docs,
   ADRs, scripts, README sections, CI config. Run the test suite, linter and type checker
   (see CLAUDE.md "Commands") and note the result.
3. Also check the basics:
   - README explains what it is, how to run it and how to demo it
   - `.env.example` lists every variable the code reads
   - at least one ADR besides the template, and none still marked DRAFT
   - changelog entries exist and `changelog.py validate` passes
   - no TODO/FIXME left in shipped code paths
4. Output a table: item | status (done / partial / missing) | evidence (file paths) | what's left.
5. End with the three most important gaps, in order.
