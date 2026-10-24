# Recap-only knowledge preserved before archive

Date: 2026-10-24. Source of extraction approval: [APPROVAL-01](../approval-01.md), WI-02/WI-03. These are historical facts and rationale, not new production observations.

| Inventory section 2 item | Durable treatment | Evidence / limits |
| --- | --- | --- |
| Legacy flashcard XP grandfathering | [ADR-016](../../../decisions/ADR-016-legacy-flashcard-xp.md) | [MEMORY original lines 228–230](../../../archive/session-recaps/MEMORY.md). Decide before real learner history is affected; no backfill authorized. |
| Historical duplicate submit cohort | [Practice evidence](../../practice/evidence/historical-duplicate-submits.md) | MEMORY original lines 265–267 records 11 user/item/set groups with multiple graded rows before `9cb4774`. Intentionally left unchanged; identities omitted from extraction. |
| Provisioned concurrency unresolved | [Infrastructure notes](../../../engineering/infrastructure-requirements.md#verification-gap-provisioned-concurrency) | MEMORY original lines 268–274 records account cap 10, PC=1 unable to leave 10 unreserved, a rejected request for 11 and pending quota request for 1,001. No current quota/support state established. No support identifier is reproduced here. |
| Feedback should match persona | [ADR-017](../../../decisions/ADR-017-persona-feedback.md) | [Local closeout original lines 386–409](../../../archive/session-recaps/DEEPSEEK_SEPT1_CLOSEOUT.md). Rationale retained; new dashboard work still requires a spec. |
| Image/secret bootstrap sequence | [Deploy runbook extraction](../../../engineering/runbooks/deploy-backend.md) | Closeout original lines 28–35. ECR must exist before image-dependent Lambdas; an empty secret can make cold initialization fail. Not executed or currently verified. |
| Motion registry provenance and React 19 changes | [Local development](../../../engineering/local-development.md#component-provenance) and [design notes](../../../design/handover-findings.md) | Main-only motion guide original lines 3–14, 30–34. Registry rate limits prompted manual source copies; reduced motion remains consumer-owned. |

Historical provider configurations and successful deploy hashes are evidence at their recorded dates. They do not certify current hosted state. The exact raw main-only guides are retained in the main checkout; their useful rationale is versioned in [guide knowledge](local-guide-knowledge.md).
