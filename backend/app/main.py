from fastapi import FastAPI

from backend.app.routers.reviews import router as reviews_router


# This file creates the FastAPI app and adds the review routes.
app = FastAPI(title="ReviewInsight API")

app.include_router(reviews_router)
