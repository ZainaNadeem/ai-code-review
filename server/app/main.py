from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.routers import webhooks

app = FastAPI(title="AI Code Review Assistant", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhooks.router)


class ReviewRequest(BaseModel):
    language: str
    code: str


class ReviewResponse(BaseModel):
    summary: str
    suggestions: list[str]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/review", response_model=ReviewResponse)
def review(payload: ReviewRequest) -> ReviewResponse:
    return ReviewResponse(
        summary=f"Received {len(payload.code)} chars of {payload.language}.",
        suggestions=[],
    )
