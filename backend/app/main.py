from fastapi import FastAPI

from backend.app.routers import health, reviews

app = FastAPI(title="ReviewInsight API")

app.include_router(health.router)
app.include_router(reviews.router)
