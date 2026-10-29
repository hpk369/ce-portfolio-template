---
name: adr
description: Draft an Architecture Decision Record from the current conversation into docs/adr/, for the user to rewrite in their own words. Use when a design choice has been made or the user says "ADR".
---
# Draft an ADR

1. Identify the single decision to record. If there are several, ask which one.
2. Find the next number: list `docs/adr/`, take the highest `NNNN-` prefix and add one.
3. Copy the structure of `docs/adr/0000-template.md` into `docs/adr/NNNN-<kebab-title>.md`.
4. Fill it from the conversation: context, the two or three options actually considered
   with honest tradeoffs, the decision, and its consequences. Set status to `proposed`
   and the date to today.
5. Leave "How I'd explain this to a customer" as a prompt for the user. Don't write it.
6. Mark the file clearly as a draft at the top: `> DRAFT by Claude. Rewrite in your own words.`
7. Tell the user the path and the parts most worth rewriting. Don't commit it.
