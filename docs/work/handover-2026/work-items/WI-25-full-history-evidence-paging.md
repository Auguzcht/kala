---
id: WI-25
status: deferred
owner: ITO
---

# Page complete evidence history

Authority: [APPROVAL-06 H12](../approval-06.md). Fred defers full-history paging to keep the same-day release bounded. Branch: not started.

Current Twin responses expose up to 20 recent events; learner-record responses expose 25 despite the internal 200-event statistics read. Current ledger pagination navigates only the returned array. Copy must disclose those windows and describe bounded statistics as recent activity.

Future work defines authorized cursor pagination, deterministic ordering, scope boundaries and honest total/count semantics before implementation. Cover concurrent arrivals, empty pages, learner switching and tenant isolation. Do not enlarge or relabel today's window as a lifetime history.
