import logging

from app.db.session import SessionLocal
from app.models.review import Review

logger = logging.getLogger(__name__)


def process_review(review_id: int, diff_url: str, title: str) -> None:
    """Run the (eventual) AI review for a pull request.

    This is executed by FastAPI's ``BackgroundTasks`` *after* the webhook
    response has already been returned, so it must manage its own database
    session — the request-scoped session is closed by the time this runs.

    The actual diff fetching and model call are stubbed out for now; the
    function focuses on driving the ``Review`` row through its status
    lifecycle: ``pending`` → ``processing`` → ``completed`` (or ``failed``).
    """
    db = SessionLocal()
    try:
        review = db.get(Review, review_id)
        if review is None:
            logger.warning("Review %s no longer exists; skipping", review_id)
            return

        review.status = "processing"
        db.commit()

        # TODO: fetch the diff from `diff_url` and run the AI code review.
        # For now we record a placeholder summary so the flow is observable.
        review.summary = f"Queued review for PR: {title} ({diff_url})"
        review.status = "completed"
        db.commit()
        logger.info("Completed review %s for PR '%s'", review_id, title)
    except Exception:
        logger.exception("Failed to process review %s", review_id)
        db.rollback()
        review = db.get(Review, review_id)
        if review is not None:
            review.status = "failed"
            db.commit()
    finally:
        db.close()
