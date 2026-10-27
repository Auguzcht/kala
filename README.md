<div align="center">
  <img src="apps/web/public/Kala-Logo.png" alt="Kala hornbill logo" width="160" />
  <h1>Kala</h1>
  <p><strong>An AI learning companion and digital learning twin for Blackboard Learn.</strong></p>
</div>

## About Kala

Kala is an AI learning companion and digital learning twin. It runs as an intelligence layer on top of Blackboard Learn. Students and instructors enter through an LTI 1.3 link. Blackboard owns course content and grades. Supabase owns learning evidence.

**Handed over to ITO. Frozen October 28, 2026.** For the handover, known limits and open items, [read this first](docs/work/handover-2026/closeout.md).

[Open Kala](https://kala-web-lovat.vercel.app)

## Where to start

- [Repository guide](AGENTS.md) — project rules and the spec-first process.
- [Documentation guide](docs/README.md) — find the right feature spec or operating procedure.
- [Local development](docs/engineering/local-development.md) — setup, commands and verification.

## Stack

- **Web:** React, TypeScript and Vite on Vercel.
- **API:** FastAPI on AWS Lambda behind HTTP API Gateway.
- **Worker:** AWS Lambda scheduled by EventBridge.
- **Database:** Supabase Postgres with pgvector.
- **Models:** application provider routing for language models and embeddings; see the [AI platform spec](docs/features/ai-platform/README.md).

## Repository layout

| Area | What lives here |
| --- | --- |
| [apps/web/src/features/](apps/web/src/features/) | Feature screens, clients, hooks and schemas |
| [apps/web/src/components/](apps/web/src/components/) | Shared UI, shell and tours |
| [apps/web/src/app/](apps/web/src/app/) | Router and application providers |
| [services/api/app/routers/](services/api/app/routers/) | Authenticated HTTP endpoints |
| [services/api/app/ai/](services/api/app/ai/) | Provider routing and retrieval |
| [services/api/app/learn/](services/api/app/learn/) | Learning and review logic |
| [services/api/app/twin/](services/api/app/twin/) | Evidence and twin calculations |
| [services/worker/app/jobs/](services/worker/app/jobs/) | Scheduled, resumable jobs |
| [packages/db/migrations/](packages/db/migrations/) | Immutable migration history |
| [scripts/](scripts/) | Maintenance and verification tools |
| [infra/](infra/) | Infrastructure source |
| [docs/](docs/) | Feature specs, runbooks and handover records |

## Attribution

Developed by **Alfred Nodado (Auguzcht)** for **Mapúa Malayan Colleges of Mindanao’s Office for Artificial Intelligence Curriculum Integration (OAICI)**.

## Copyright and license

To be determined by Mapúa Malayan Colleges of Mindanao (OAICI).

---

<div align="center">
  <p><strong>Built with ❤️ for Mapúa Malayan Colleges of Mindanao’s OAICI.</strong></p>
</div>
