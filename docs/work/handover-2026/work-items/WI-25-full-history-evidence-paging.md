---
id: WI-25
status: in-progress
owner: ITO
---

# Page complete evidence history

Requirements: [TWIN-REQ-010](../../../features/twin/README.md#twin-req-010-browse-complete-own-evidence-history) and [INSTR-REQ-010/011](../../../features/instructor-insights/README.md#instr-req-010-browse-authorized-learner-evidence-history). APPROVAL-07 supersedes the earlier deferral. Branch `codex/wi25-evidence-history` is locally merged; human migration/deployment/acceptance gates remain pending.

## Original bounded-history finding

Current Twin responses expose up to 20 recent events; learner-record responses expose 25 despite the internal 200-event statistics read. Current ledger pagination navigates only the returned array. Copy must disclose those windows and describe bounded statistics as recent activity.

Future work defines authorized cursor pagination, deterministic ordering, scope boundaries and honest total/count semantics before implementation. Cover concurrent arrivals, empty pages, learner switching and tenant isolation. Do not enlarge or relabel today's window as a lifetime history.

## APPROVAL-07 implementation round

The earlier same-day deferral is superseded by APPROVAL-07 and Amendment 1. Lane H works on `codex/wi25-evidence-history` under coordinator-owned TWIN-REQ-010 / INSTR-REQ-010; keyset is `(created_at DESC, id DESC)`, preserving createdAt. Query/frontend/index work may follow the committed spec; new router additions wait for SEC merge. An optional index-only 0039 goes to Fred FG-6. Owner stays ITO; this item is not complete until local integration and FG-9 live acceptance. No hosted operation is authorized to agents.


## Reviewed local delivery

H revision `cf169ec587a639feaeae86cdc429f9ca1ae9550a` merged at `bc8a2f5`. API history, 0039 index, shared ledger and instructor denial states are implemented locally. H reports 898 API tests (69 history cases), 1,474 browser assertions, 33 frontend/tour unit tests with zero skips, four Study component tests and web/docs checks passing. Existing handler ASTs and historical SQL bytes are preserved. The original comparator failure is retained in evidence with its reviewed correction; it is not silently omitted.

Port5173 was restored to Kala U after H testing and independently verified HTTP200. Generated contracts, final full integrated checks, Fred FG-6/FG-8 and FG-9 remain required. Owner stays ITO and status stays in-progress; no hosted migration or live full-history acceptance is claimed.

## Verified by

- [H full inventory and verification](../evidence/wi25-evidence-history.md)
- [0039 procedure](../../../runbooks/0039-apply.md)
