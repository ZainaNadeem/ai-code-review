import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.connections import manager
from app.routers import auth, repos, reviews, webhooks, ws


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Capture the running event loop so background threads (the review
    # pipeline) can broadcast to WebSocket clients.
    manager.set_loop(asyncio.get_running_loop())
    yield


app = FastAPI(title="AI Code Review Assistant", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(repos.router)
app.include_router(reviews.router)
app.include_router(webhooks.router)
app.include_router(ws.router)


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
