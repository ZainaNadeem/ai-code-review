from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db.session import get_db
from app.models.repo import Repo
from app.models.user import User
from app.schemas import RepoCreate, RepoRead

router = APIRouter(prefix="/repos", tags=["repos"])


def _name_from_url(url: str) -> str:
    """Derive a display name ("owner/repo") from a GitHub URL."""
    path = urlparse(url).path.strip("/")
    if path.endswith(".git"):
        path = path[:-4]
    return path or url


@router.post("", response_model=RepoRead, status_code=status.HTTP_201_CREATED)
def create_repo(
    payload: RepoCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Repo:
    repo = Repo(
        user_id=current_user.id,
        github_repo_url=payload.github_repo_url,
        name=payload.name or _name_from_url(payload.github_repo_url),
    )
    db.add(repo)
    db.commit()
    db.refresh(repo)
    return repo


@router.get("", response_model=list[RepoRead])
def list_repos(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Repo]:
    return list(
        db.scalars(select(Repo).where(Repo.user_id == current_user.id)).all()
    )


@router.get("/{repo_id}", response_model=RepoRead)
def get_repo(
    repo_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Repo:
    repo = db.get(Repo, repo_id)
    if repo is None or repo.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Repo not found"
        )
    return repo
