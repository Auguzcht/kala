"""FastAPI application. Runs under uvicorn locally and under Lambda via Mangum.
Wires the LTI auth spine and the feature routers together."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

from app.config import get_settings
from app.lti.routes import router as lti_router
from app.routers.courses import router as courses_router
from app.routers.dashboard import router as dashboard_router
from app.routers.diagnostic import router as diagnostic_router
from app.routers.flashcards import router as flashcards_router
from app.routers.health import router as health_router
from app.routers.practice import router as practice_router
from app.routers.tutor import router as tutor_router
from app.routers.twin import router as twin_router

app = FastAPI(title="Kala API", version="0.1.0")

_settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[_settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(lti_router)
app.include_router(courses_router)
app.include_router(diagnostic_router)
app.include_router(practice_router)
app.include_router(flashcards_router)
app.include_router(tutor_router)
app.include_router(twin_router)
app.include_router(dashboard_router)

# Lambda entrypoint (referenced by the Dockerfile CMD: app.main.handler)
handler = Mangum(app)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
