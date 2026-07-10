from pydantic import BaseModel, Field


class WebsiteAnalysisRequest(BaseModel):
    url: str = Field(..., description="Public website URL containing customer reviews.")
