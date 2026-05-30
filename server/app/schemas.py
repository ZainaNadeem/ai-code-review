from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr

# Allowed review lifecycle states (see review_pipeline.run_review).
ReviewStatus = Literal["pending", "processing", "complete", "failed"]


# --------------------------------------------------------------------------- #
# Auth
# --------------------------------------------------------------------------- #
class UserCreate(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# --------------------------------------------------------------------------- #
# Repos
# --------------------------------------------------------------------------- #
class RepoCreate(BaseModel):
    github_repo_url: str
    # Optional; derived from the URL's "owner/repo" path when omitted.
    name: str | None = None


class RepoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    github_repo_url: str
    name: str


# --------------------------------------------------------------------------- #
# Reviews
# --------------------------------------------------------------------------- #
class ReviewCommentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    file: str
    line: int | None
    severity: str
    comment: str


class ReviewRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    repo_id: int
    pr_number: int
    status: str
    created_at: datetime
    summary: str | None


class ReviewDetail(ReviewRead):
    comments: list[ReviewCommentRead] = []


class ReviewStatusUpdate(BaseModel):
    status: ReviewStatus
