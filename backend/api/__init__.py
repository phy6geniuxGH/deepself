"""Aggregate API router. Mounted under /api by main.py."""

from fastapi import APIRouter

from backend.api import idea, journal

api_router = APIRouter(prefix="/api")
api_router.include_router(journal.router)
api_router.include_router(idea.router)
