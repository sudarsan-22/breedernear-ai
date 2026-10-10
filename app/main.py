from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from google.adk.cli.fast_api import get_fast_api_app

from app.api import router
from app.gatekeeper import Gatekeeper
from app.ratelimit import rate_limit_middleware
from breedernear_core.config import get_settings

ROOT = Path(__file__).resolve().parent.parent

# ADK runtime: /apps/... (sessions), /run, /run_sse. The ADK dev UI is not served (web=False).
app: FastAPI = get_fast_api_app(
    agents_dir=str(ROOT / "agents"),
    web=False,
    use_local_storage=False,
    max_llm_calls=get_settings().max_llm_calls_per_run,
)

app.middleware("http")(rate_limit_middleware)
app.add_middleware(Gatekeeper)                # only the ADK routes the app uses, behind login
app.include_router(router)

# Static web UI, mounted last so it never shadows /api or ADK routes.
app.mount("/", StaticFiles(directory=ROOT / "web", html=True), name="web")
