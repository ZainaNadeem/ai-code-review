"""Retrieval-Augmented Generation over the project's coding style guides.

Pipeline:
  1. Load markdown style guides from ``server/docs``.
  2. Split each into ~500-token chunks and embed them with OpenAI
     ``text-embedding-ada-002``.
  3. Store the vectors in a local FAISS index at ``server/data/index.faiss``
     (chunk texts are persisted alongside it in ``server/data/chunks.json``,
     since FAISS stores only vectors).
  4. ``retrieve(query, k)`` embeds the query and returns the top-k chunk texts.

Build the index once (after adding/editing docs):

    python -m app.rag

``retrieve`` degrades gracefully — if no index has been built (or no API key
is configured) it returns an empty list, so callers can run without context.
"""
import json
import logging
from pathlib import Path

import faiss
import numpy as np
from openai import OpenAI

from app.config import settings

logger = logging.getLogger(__name__)

# server/app/rag.py -> parent.parent == server/
SERVER_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = SERVER_ROOT / "docs"
DATA_DIR = SERVER_ROOT / "data"
INDEX_PATH = DATA_DIR / "index.faiss"
CHUNKS_PATH = DATA_DIR / "chunks.json"

EMBEDDING_MODEL = "text-embedding-ada-002"
CHUNK_TOKENS = 500

# Module-level cache so the index/chunks are read from disk only once.
_index: "faiss.Index | None" = None
_chunks: list[dict] | None = None


# --------------------------------------------------------------------------- #
# Chunking
# --------------------------------------------------------------------------- #
def chunk_text(text: str, max_tokens: int = CHUNK_TOKENS) -> list[str]:
    """Split text into ~``max_tokens``-token segments.

    Uses tiktoken for exact token boundaries, falling back to a ~4-chars/token
    estimate if tiktoken can't be loaded.
    """
    text = text.strip()
    if not text:
        return []
    try:
        import tiktoken

        try:
            encoding = tiktoken.encoding_for_model(EMBEDDING_MODEL)
        except KeyError:
            encoding = tiktoken.get_encoding("cl100k_base")
        token_ids = encoding.encode(text)
        return [
            encoding.decode(token_ids[i : i + max_tokens])
            for i in range(0, len(token_ids), max_tokens)
        ]
    except Exception:
        size = max_tokens * 4
        return [text[i : i + size] for i in range(0, len(text), size)]


# --------------------------------------------------------------------------- #
# Embeddings + index building
# --------------------------------------------------------------------------- #
def _embed(texts: list[str]) -> np.ndarray:
    """Embed texts with OpenAI, returned as a float32 (n, dim) array."""
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    client = OpenAI(api_key=settings.openai_api_key)
    vectors: list[list[float]] = []
    batch_size = 100
    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        response = client.embeddings.create(model=EMBEDDING_MODEL, input=batch)
        vectors.extend(item.embedding for item in response.data)
    return np.asarray(vectors, dtype="float32")


def _load_docs() -> list[tuple[str, str]]:
    """Return ``(source_name, text)`` for every markdown file under DOCS_DIR."""
    if not DOCS_DIR.exists():
        return []
    docs = []
    for path in sorted(DOCS_DIR.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        if text.strip():
            docs.append((path.name, text))
    return docs


def build_index() -> int:
    """(Re)build the FAISS index from the markdown docs. Returns chunk count."""
    docs = _load_docs()
    chunks: list[dict] = []
    for source, text in docs:
        for segment in chunk_text(text):
            chunks.append({"text": segment, "source": source})

    if not chunks:
        logger.warning("No markdown docs found in %s; index not built", DOCS_DIR)
        return 0

    vectors = _embed([c["text"] for c in chunks])
    faiss.normalize_L2(vectors)  # normalize so inner product == cosine similarity

    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(vectors)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(INDEX_PATH))
    CHUNKS_PATH.write_text(json.dumps(chunks), encoding="utf-8")

    # Refresh the in-process cache.
    global _index, _chunks
    _index, _chunks = index, chunks

    logger.info(
        "Built FAISS index: %d chunk(s) from %d doc(s)", len(chunks), len(docs)
    )
    return len(chunks)


# --------------------------------------------------------------------------- #
# Retrieval
# --------------------------------------------------------------------------- #
def _ensure_loaded() -> bool:
    """Load the index + chunks from disk into the cache if available."""
    global _index, _chunks
    if _index is not None and _chunks is not None:
        return True
    if INDEX_PATH.exists() and CHUNKS_PATH.exists():
        _index = faiss.read_index(str(INDEX_PATH))
        _chunks = json.loads(CHUNKS_PATH.read_text(encoding="utf-8"))
        return True
    return False


def retrieve(query: str, k: int = 3) -> list[str]:
    """Return the top-``k`` style-guide chunks most relevant to ``query``.

    Returns an empty list if there's no index, no query, or no API key, so the
    caller can proceed without retrieved context.
    """
    if not query or not query.strip():
        return []
    if not settings.openai_api_key:
        return []
    if not _ensure_loaded():
        logger.info("No FAISS index at %s; returning no context", INDEX_PATH)
        return []

    assert _index is not None and _chunks is not None
    k = min(k, len(_chunks))
    if k <= 0:
        return []

    query_vector = _embed([query])
    faiss.normalize_L2(query_vector)
    _scores, indices = _index.search(query_vector, k)

    results = []
    for idx in indices[0]:
        if 0 <= idx < len(_chunks):
            results.append(_chunks[idx]["text"])
    return results


if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(level=logging.INFO)
    count = build_index()
    print(f"Indexed {count} chunk(s) -> {INDEX_PATH}")
