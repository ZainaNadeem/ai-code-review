from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    repo_id: Mapped[int] = mapped_column(
        ForeignKey("repos.id", ondelete="CASCADE"), index=True, nullable=False
    )
    pr_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    repo: Mapped["Repo"] = relationship(back_populates="reviews")
    comments: Mapped[list["ReviewComment"]] = relationship(
        back_populates="review", cascade="all, delete-orphan"
    )
