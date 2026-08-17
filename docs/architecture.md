# Architecture (summary)

Full detail and diagram are in `masterplan.md` section 4. In short:

Users enter through the LMS. An LTI 1.3 link opens Kala as a first-party page (React + Vite on a static host). The frontend calls API Gateway + Lambda (FastAPI). The API fans out to an LMS connector (REST reads and grade passback), a tiered model router (Bedrock: Claude + Titan embeddings), and Supabase (Postgres + pgvector, the digital twin and RAG index). An EventBridge schedule drives an async worker that recomputes mastery and re-embeds content. CloudWatch handles observability.

Request path is synchronous (frontend -> API -> services). The twin recompute and content re-embedding run asynchronously off EventBridge. Everything is tenant-scoped by `institution_id` with RLS.
