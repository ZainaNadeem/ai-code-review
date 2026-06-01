"""End-to-end AI review pipeline for a pull request.

Given a ``Review`` row, this module:
  1. Fetches the PR diff from the GitHub API (httpx).
  2. Chunks the diff per file, capped at a max token budget per chunk.
  3. Sends each chunk to the OpenAI API with a system prompt that asks for
     structured JSON findings.
  4. Persists the findings as ``ReviewComment`` rows linked to the ``Review``.
  5. Marks the ``Review`` as "complete" (or "failed" on error).

Secrets (GitHub token, OpenAI key) are read from settings, which load from the
``.env`` file via python-dotenv / pydantic-settings. Nothing is hardcoded.
"""
import json
import logging
from urllib.parse import urlparse

import httpx
from openai import OpenAI

from app.config import settings
from app.connections import manager
from app.db.session import SessionLocal
from app.models.review import Review
from app.models.review_comment import ReviewComment
from app.rag import retrieve

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"

SYSTEM_PROMPT = (
    "You are an expert code reviewer. You are given a unified diff for a single "
    "file from a pull request. Identify concrete issues only: bugs, security "
    "vulnerabilities, performance problems, and clear style/maintainability "
    "violations. Do not invent issues.\n\n"
    "Respond with ONLY a JSON object of this exact shape:\n"
    '{"comments": [{"file": "<path>", "line": <integer or null>, '
    '"severity": "info" | "warning" | "error", "comment": "<concise explanation>"}]}\n\n'
    "Use the file path from the diff header. Use the line number in the new "
    "version of the file where the issue occurs, or null if not line-specific. "
    "If you find no issues, return {\"comments\": []}."
)


# --------------------------------------------------------------------------- #
# Token counting + chunking
# --------------------------------------------------------------------------- #
def _token_len(text: str, model: str) -> int:
    """Count tokens with tiktoken, falling back to a ~4-chars/token estimate.

    tiktoken downloads its encoding files on first use; if that isn't possible
    (offline, etc.) we degrade gracefully to a character-based heuristic.
    """
    try:
        import tiktoken

        try:
            encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            encoding = tiktoken.get_encoding("o200k_base")
        return len(encoding.encode(text))
    except Exception:
        return max(1, len(text) // 4)


def _extract_path(segment: str) -> str:
    """Pull the file path out of a 'diff --git a/x b/x' segment header."""
    first_line = segment.splitlines()[0] if segment else ""
    if first_line.startswith("diff --git ") and " b/" in first_line:
        return first_line.split(" b/", 1)[1].strip()
    return "unknown"


def _split_large_segment(
    path: str, segment: str, max_tokens: int, model: str
) -> list[tuple[str, str]]:
    """Split one file's diff that exceeds the budget into multiple chunks.

    The file header (the lines up to and including the ``+++`` line) is repeated
    at the top of every sub-chunk so each chunk is self-describing.
    """
    lines = segment.splitlines(keepends=True)

    header: list[str] = []
    body_start = 0
    for index, line in enumerate(lines):
        header.append(line)
        if line.startswith("+++ "):
            body_start = index + 1
            break
    else:
        # No proper header found; treat the whole thing as body.
        header = []
        body_start = 0

    header_text = "".join(header)
    header_tokens = _token_len(header_text, model)

    chunks: list[tuple[str, str]] = []
    current: list[str] = []
    current_tokens = header_tokens
    for line in lines[body_start:]:
        line_tokens = _token_len(line, model)
        if current and current_tokens + line_tokens > max_tokens:
            chunks.append((path, header_text + "".join(current)))
            current = []
            current_tokens = header_tokens
        current.append(line)
        current_tokens += line_tokens

    if current:
        chunks.append((path, header_text + "".join(current)))
    return chunks


def chunk_diff(
    diff_text: str, max_tokens: int, model: str
) -> list[tuple[str, str]]:
    """Split a unified diff into ``(file_path, chunk_text)`` pairs.

    Each file becomes its own chunk; any file whose diff exceeds ``max_tokens``
    is further split. ``max_tokens`` is a *target* size: chunks are assembled
    greedily by a running token count, so an assembled chunk may land slightly
    above the target (and far below the model's context window).
    """
    if not diff_text.strip():
        return []

    # Break the diff into per-file segments on the "diff --git" marker.
    segments: list[str] = []
    current: list[str] = []
    for line in diff_text.splitlines(keepends=True):
        if line.startswith("diff --git ") and current:
            segments.append("".join(current))
            current = [line]
        else:
            current.append(line)
    if current:
        segments.append("".join(current))

    chunks: list[tuple[str, str]] = []
    for segment in segments:
        path = _extract_path(segment)
        if _token_len(segment, model) <= max_tokens:
            chunks.append((path, segment))
        else:
            chunks.extend(_split_large_segment(path, segment, max_tokens, model))
    return chunks


# --------------------------------------------------------------------------- #
# GitHub + OpenAI calls
# --------------------------------------------------------------------------- #
def _owner_repo_from_url(repo_url: str) -> str:
    """Turn a repo HTML URL into the ``owner/repo`` slug used by the API."""
    path = urlparse(repo_url).path.strip("/")
    if path.endswith(".git"):
        path = path[:-4]
    return path


def fetch_pr_diff(owner_repo: str, pr_number: int) -> str:
    """Fetch a PR's unified diff from the GitHub API using httpx."""
    url = f"{GITHUB_API}/repos/{owner_repo}/pulls/{pr_number}"
    headers = {
        "Accept": "application/vnd.github.diff",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if settings.github_token:
        headers["Authorization"] = f"Bearer {settings.github_token}"

    with httpx.Client(timeout=30.0, follow_redirects=True) as client:
        response = client.get(url, headers=headers)
        response.raise_for_status()
        return response.text


def _safe_int(value: object) -> int | None:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _build_system_prompt(chunk: str) -> str:
    """Augment the base prompt with retrieved style-guide context (RAG)."""
    context_chunks = retrieve(chunk, k=3)
    if not context_chunks:
        return SYSTEM_PROMPT
    context = "\n\n---\n\n".join(context_chunks)
    return (
        SYSTEM_PROMPT
        + "\n\nUse the following project coding style guide excerpts as "
        "authoritative context. Flag code that violates them and reference "
        f"the relevant rule in your comment:\n\n{context}"
    )


def review_chunk(
    client: OpenAI, model: str, file_path: str, chunk: str
) -> list[dict]:
    """Send one diff chunk to OpenAI and return the parsed comment dicts.

    The system prompt is augmented with style-guide context retrieved for this
    specific diff chunk (RAG).
    """
    response = client.chat.completions.create(
        model=model,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": _build_system_prompt(chunk)},
            {"role": "user", "content": f"File: {file_path}\n\nDiff:\n{chunk}"},
        ],
    )
    content = response.choices[0].message.content or "{}"
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        logger.warning("Model returned non-JSON output for %s; skipping", file_path)
        return []
    comments = data.get("comments", [])
    return comments if isinstance(comments, list) else []


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #
def run_review(review_id: int) -> None:
    """Run the full review pipeline for a single ``Review`` row.

    Intended to be queued via FastAPI ``BackgroundTasks``; it owns its own DB
    session because the request-scoped session is already closed by the time
    this executes.
    """
    db = SessionLocal()
    try:
        review = db.get(Review, review_id)
        if review is None:
            logger.warning("Review %s no longer exists; skipping", review_id)
            return
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")

        owner_repo = _owner_repo_from_url(review.repo.github_repo_url)

        review.status = "processing"
        db.commit()

        diff_text = fetch_pr_diff(owner_repo, review.pr_number)
        chunks = chunk_diff(
            diff_text, settings.review_chunk_max_tokens, settings.openai_model
        )

        client = OpenAI(api_key=settings.openai_api_key)
        total_comments = 0
        for file_path, chunk in chunks:
            for raw in review_chunk(client, settings.openai_model, file_path, chunk):
                db.add(
                    ReviewComment(
                        review_id=review.id,
                        file=str(raw.get("file") or file_path),
                        line=_safe_int(raw.get("line")),
                        severity=str(raw.get("severity") or "info"),
                        comment=str(raw.get("comment") or ""),
                    )
                )
                total_comments += 1
        db.commit()

        review.status = "complete"
        review.summary = (
            f"Generated {total_comments} comment(s) across {len(chunks)} chunk(s)."
        )
        db.commit()
        logger.info(
            "Review %s complete: %s comment(s)", review_id, total_comments
        )

        # Notify any subscribed WebSocket clients that the review is done.
        manager.broadcast_threadsafe(
            review.id,
            {
                "review_id": review.id,
                "status": "complete",
                "comment_count": total_comments,
            },
        )
    except Exception:
        logger.exception("Review %s failed", review_id)
        db.rollback()
        review = db.get(Review, review_id)
        if review is not None:
            review.status = "failed"
            db.commit()
    finally:
        db.close()
