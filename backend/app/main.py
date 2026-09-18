"""FastAPI application entrypoint."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, contacts, jobs, metrics, oauth_email, outreach, resumes, users
from app.core.config import get_settings
from app.core.database import Base, engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info("Starting Job Outreach Agent API (env=%s, llm=%s)", settings.app_env, settings.llm_provider)
    # Create tables (Alembic preferred in prod; create_all for MVP bootstrap)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title="AI Job Outreach & Resume Tailoring Agent",
    version="0.1.0",
    lifespan=lifespan,
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list or ["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(resumes.router)
app.include_router(jobs.router)
app.include_router(contacts.router)
app.include_router(outreach.router)
app.include_router(metrics.router)
app.include_router(oauth_email.router)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "llm_provider": get_settings().llm_provider,
        "gmail_configured": get_settings().gmail_configured,
        "microsoft_configured": get_settings().microsoft_configured,
    }
