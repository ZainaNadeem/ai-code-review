import hashlib
import hmac

from fastapi import HTTPException, status

from app.config import settings


def verify_github_signature(payload_body: bytes, signature_header: str | None) -> None:
    """Verify a GitHub webhook's HMAC-SHA256 signature.

    GitHub signs each webhook delivery with the configured secret and sends the
    result in the ``X-Hub-Signature-256`` header as ``sha256=<hexdigest>``. We
    recompute the digest over the raw request body and compare it in constant
    time.

    Raises an ``HTTPException`` if the secret is unset, the header is missing, or
    the signature does not match.
    """
    if not settings.github_webhook_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="GITHUB_WEBHOOK_SECRET is not configured",
        )

    if not signature_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Hub-Signature-256 header",
        )

    expected = "sha256=" + hmac.new(
        key=settings.github_webhook_secret.encode("utf-8"),
        msg=payload_body,
        digestmod=hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected, signature_header):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )
