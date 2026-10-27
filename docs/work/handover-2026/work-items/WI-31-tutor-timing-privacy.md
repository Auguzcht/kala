---
id: WI-31
status: planned
owner: ITO; separate diagnostics scope required
---

# Remove identifying timing field before another delegated log analysis

FG-L under APPROVAL-08 Amendment2 stopped on actual returned field user_id_prefix. No raw values are retained; raw data is local only, not retained. Stage/model/status aggregate results were not produced and no latency attribution is established.

A future named diagnostics lane must review/remove that field without changing provider routing, persistence or response semantics, prove logging allowlist/privacy with synthetic tests, and obtain a new explicit read delegation before rerunning hosted analysis. T2's E1 scope does not authorize a logging change. Do not paste/query/share raw records to reproduce the finding.
