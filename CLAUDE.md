# Project instructions

This project is specified in SPEC.md. Read it before doing anything.

## Rules
- Follow SPEC.md Section 0 ("Instructions to the coding agent") at all times.
- Work one milestone at a time (SPEC.md Section 16). Plan first and wait
  for my approval before writing code.
- Never start the next milestone until I confirm the current one's
  acceptance criteria pass.
- Record every non-obvious design choice in docs/DECISIONS.md.
- Never commit .env or API keys. ANTHROPIC_API_KEY is not set yet;
  don't block on it before Milestone 4.
- Ask before adding dependencies not listed in SPEC.md Section 3.

## Progress
- [ ] M1 Foundation + data
- [ ] M2 Parsing, chunking, embeddings, retrieval
- [ ] M3 MCP servers
- [ ] M4 Agent runtime
- [ ] M5 Eval harness + baselines
- [ ] M6 Experiments + CI
- [ ] M7 API, frontend, docs
- [ ] M8 Deploy + publish (optional)

## Notes for the next session
(Updated at the end of each milestone: what was built, known issues,
anything the next milestone needs to know.)

M1 implementation is built and locally verified: 37 tests pass, Ruff checks pass,
and the database contains 20 companies, 275 filings, and 2,715 facts (563 derived).
The network-blocked full cache replay preserves fact values, provenance, and IDs.
See docs/M1_STATUS.md and docs/DECISIONS.md (D001–D016).

M1 is intentionally still unchecked: the student must review the 12 revenue
values in docs/M1_REVENUE_REVIEW.md and explicitly confirm acceptance. The fixture
is marked pending_user_verification. Do not start M2 until that confirmation.
System Python was not changed; use the project-local Python 3.12.15 environment.
