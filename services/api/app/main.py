"""FastAPI application. Runs under uvicorn locally and under Lambda via Mangum.
Wires the LTI auth spine and the feature routers together."""
from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from mangum import Mangum

from app.ai.errors import ModelUnavailableError
from app.config import get_settings
from app.lti.routes import router as lti_router
from app.routers.courses import router as courses_router
from app.routers.dashboard import router as dashboard_router
from app.routers.diagnostic import router as diagnostic_router
from app.routers.flashcards import router as flashcards_router
from app.routers.gamification import router as gamification_router
from app.routers.health import router as health_router
from app.routers.lessons import router as lessons_router
from app.routers.practice import router as practice_router
from app.routers.tutor import router as tutor_router
from app.routers.twin import router as twin_router

app = FastAPI(title="Kala API", version="0.1.0")


@app.exception_handler(ModelUnavailableError)
def _model_unavailable(_request: Request, exc: ModelUnavailableError) -> JSONResponse:
    """A retired model id, provider outage, or timeout in the model layer is
    a dependency being unavailable, not a bug in the request — so it must not
    surface as a bare 500. 502 (Bad Gateway) is the honest status: an
    upstream we depend on failed. The message is intentionally generic
    (never leaks the provider, model id, or upstream body to the client) and
    always safe to show the user directly; the specifics are in the Lambda
    logs from bedrock.py's own error lines."""
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content={"detail": str(exc)},
    )

_settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[_settings.frontend_url, "http://localhost:5173"],
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
app.include_router(lessons_router)
app.include_router(tutor_router)
app.include_router(twin_router)
app.include_router(dashboard_router)
app.include_router(gamification_router)

# Lambda entrypoint (referenced by the Dockerfile CMD: app.main.handler)
handler = Mangum(app)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
