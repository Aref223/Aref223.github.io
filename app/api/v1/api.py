"""
Main API router for v1 endpoints.

This module contains the main API router that includes all sub-routers
for different API endpoints.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, users, scraping, validation, cards, jobs

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(scraping.router, prefix="/scraping", tags=["scraping"])
api_router.include_router(validation.router, prefix="/validation", tags=["validation"])
api_router.include_router(cards.router, prefix="/cards", tags=["cards"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])