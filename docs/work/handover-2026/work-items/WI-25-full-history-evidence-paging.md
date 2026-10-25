---
id: WI-25
status: in-progress
owner: ITO
---

# Page complete evidence history

Authority: [APPROVAL-06 H12](../approval-06.md). Fred defers full-history paging to keep the same-day release bounded. Branch: not started.

Current Twin responses expose up to 20 recent events; learner-record responses expose 25 despite the internal 200-event statistics read. Current ledger pagination navigates only the returned array. Copy must disclose those windows and describe bounded statistics as recent activity.

Future work defines authorized cursor pagination, deterministic ordering, scope boundaries and honest total/count semantics before implementation. Cover concurrent arrivals, empty pages, learner switching and tenant isolation. Do not enlarge or relabel today's window as a lifetime history.

## APPROVAL-07 implementation round

The earlier same-day deferral is superseded by APPROVAL-07 and Amendment 1. Lane H works on `codex/wi25-evidence-history` under coordinator-owned TWIN-REQ-010 / INSTR-REQ-010; keyset is `(created_at DESC, id DESC)`, preserving createdAt. Query/frontend/index work may follow the committed spec; new router additions wait for SEC merge. An optional index-only 0039 goes to Fred FG-6. Owner stays ITO; this item is not complete until local integration and FG-9 live acceptance. No hosted operation is authorized to agents.
