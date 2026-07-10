from fastapi import FastAPI

from backend.app.routers.website import router as website_router


app = FastAPI(title="ReviewInsight API")

app.include_router(website_router)
