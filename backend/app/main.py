from fastapi import FastAPI

from backend.app.routers.reviews import router as reviews_router

app = FastAPI(title="ReviewInsight API")

app.include_router(reviews_router)
