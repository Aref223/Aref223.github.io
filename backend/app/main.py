from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .db import init_db
from .api.routes import auth as auth_route
from .api.routes import cards as cards_route
from .api.routes import visas as visas_route
from .api.routes import scraping as scraping_route
from .logging_conf import configure_logging

configure_logging()

app = FastAPI(title="Visa & Debit Card Scraper API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.ALLOWED_ORIGINS.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def on_startup() -> None:
    init_db()

# Routers
app.include_router(auth_route.router, prefix="/auth", tags=["auth"])
app.include_router(cards_route.router, prefix="/cards", tags=["cards"])
app.include_router(visas_route.router, prefix="/visas", tags=["visas"])
app.include_router(scraping_route.router, prefix="/scrape", tags=["scrape"])

@app.get("/health")
async def health():
    return {"status": "ok"}