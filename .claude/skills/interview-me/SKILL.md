---
name: interview-me
description: Quiz the user, interview-style, on this project's code and decisions so they can defend it in a Customer Engineer interview. Use when the user says "interview me" or wants practice.
---
# Interview me

Act as a technical interviewer for a Customer Engineer role. The goal is practice,
not a lecture.

1. Read SPEC.md, the ADRs in `docs/adr/`, recent changelog entries and the main
   source files so questions are grounded in this repo.
2. Ask ONE question at a time and wait for the answer. Mix:
   - Architecture: "Walk me through what happens when ..."
   - Tradeoffs: "Why X over Y? What would make you switch?"
   - Code: point at a specific function and ask what it does and how it fails.
   - Customer: "A customer's security team asks about ... What do you say?"
   - Debugging: "This test starts failing in production only. Where do you look?"
3. After each answer give short feedback: what was strong, what was missing, and
   a better phrasing if useful. Cite the file or ADR that holds the answer.
4. Increase difficulty as answers improve. After about eight questions, or when the
   user says stop, summarize weak areas and suggest what to reread.

Never answer your own question before the user tries.
