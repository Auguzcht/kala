# Historical duplicate-submit decision

Recorded: 2026-10-24 under APPROVAL-01 / WI-03. Source: [MEMORY, original lines 265–267](../../../archive/session-recaps/MEMORY.md).

The 2026-10-11 read-only audit found **11** user/item/set groups with multiple graded rows before commit `9cb4774`. The decision was to leave those historical rows unchanged. This extraction omits identities. No backfill, deletion, re-scoring or hosted cleanup is authorized. Current attempt-aware retry semantics belong in the future practice-tests spec; this historical count is not a current duplicate count.

Evidence environment: historical dev-hosted record, not re-run. Current lane performed document extraction only.
