from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db.session import get_db
from app.models.repo import Repo
from app.models.review import Review
from app.models.user import User
from app.schemas import ReviewDetail, ReviewRead, ReviewStatusUpdate

router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.get("", response_model=list[ReviewRead])
def list_reviews(
    repo_id: int | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Review]:
    """List reviews for the current user's repos, newest first, paginated."""
    stmt = (
        select(Review)
        .join(Repo, Review.repo_id == Repo.id)
        .where(Repo.user_id == current_user.id)
    )
    if repo_id is not None:
        stmt = stmt.where(Review.repo_id == repo_id)
    stmt = stmt.order_by(Review.created_at.desc(), Review.id.desc())
    stmt = stmt.limit(limit).offset(offset)
    return list(db.scalars(stmt).all())


def _get_owned_review(review_id: int, current_user: User, db: Session) -> Review:
    review = db.get(Review, review_id)
    if review is None or review.repo.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Review not found"
        )
    return review


@router.get("/{review_id}", response_model=ReviewDetail)
def get_review(
    review_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Review:
    """Get a single review with all of its ReviewComments."""
    return _get_owned_review(review_id, current_user, db)


@router.patch("/{review_id}", response_model=ReviewRead)
def update_review_status(
    review_id: int,
    payload: ReviewStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Review:
    """Update only the ``status`` field of a review."""
    review = _get_owned_review(review_id, current_user, db)
    review.status = payload.status
    db.commit()
    db.refresh(review)
    return review
