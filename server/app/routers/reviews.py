from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db.session import get_db
from app.models.repo import Repo
from app.models.review import Review
from app.models.user import User
from app.schemas import ReviewDetail, ReviewRead

router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.get("", response_model=list[ReviewRead])
def list_reviews(
    repo_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Review]:
    """List reviews belonging to the current user's repos, optionally filtered."""
    stmt = (
        select(Review)
        .join(Repo, Review.repo_id == Repo.id)
        .where(Repo.user_id == current_user.id)
    )
    if repo_id is not None:
        stmt = stmt.where(Review.repo_id == repo_id)
    return list(db.scalars(stmt).all())


@router.get("/{review_id}", response_model=ReviewDetail)
def get_review(
    review_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Review:
    review = db.get(Review, review_id)
    if review is None or review.repo.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Review not found"
        )
    return review
