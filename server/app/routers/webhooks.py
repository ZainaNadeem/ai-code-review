import json
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.repo import Repo
from app.models.review import Review
from app.review_pipeline import run_review
from app.security import verify_github_signature

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook", tags=["webhooks"])


@router.post("/github")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_github_event: str | None = Header(default=None),
    x_hub_signature_256: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> dict:
    """Receive GitHub webhook deliveries.

    Validates the HMAC-SHA256 signature, handles ``pull_request`` events only,
    persists a pending ``Review``, and queues the actual processing as a
    background task so we can return ``200`` to GitHub immediately.
    """
    # The signature is computed over the raw bytes, so read the body before
    # parsing it as JSON.
    raw_body = await request.body()
    verify_github_signature(raw_body, x_hub_signature_256)

    # Only pull_request events are relevant; acknowledge everything else.
    if x_github_event != "pull_request":
        return {"status": "ignored", "reason": f"unhandled event '{x_github_event}'"}

    payload = json.loads(raw_body)

    # Only act on actions that introduce or update code to review.
    action = payload.get("action")
    if action not in {"opened", "reopened", "synchronize", "ready_for_review"}:
        return {"status": "ignored", "reason": f"unhandled action '{action}'"}

    pull_request = payload["pull_request"]
    repository = payload["repository"]

    pr_number = pull_request["number"]
    repo_name = repository["full_name"]
    repo_url = repository["html_url"]

    # The Review must attach to a tracked repository. Match on the stored URL.
    repo = db.scalar(select(Repo).where(Repo.github_repo_url == repo_url))
    if repo is None:
        logger.info("Ignoring webhook for untracked repo '%s'", repo_name)
        return {"status": "ignored", "reason": "repository not tracked"}

    review = Review(repo_id=repo.id, pr_number=pr_number, status="pending")
    db.add(review)
    db.commit()
    db.refresh(review)

    # Hand off the heavy work; this runs after the response is sent.
    background_tasks.add_task(run_review, review.id)

    logger.info(
        "Queued review %s for PR #%s in '%s'", review.id, pr_number, repo_name
    )
    return {"status": "queued", "review_id": review.id}
