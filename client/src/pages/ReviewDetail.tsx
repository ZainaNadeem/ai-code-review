import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import client, { wsUrl } from "../api/client";
import { SeverityBadge, StatusBadge } from "../components/Badges";
import type { ReviewDetail as ReviewDetailType, ReviewStatus, ReviewUpdate } from "../api/types";

export default function ReviewDetail() {
  const { id } = useParams<{ id: string }>();
  const [review, setReview] = useState<ReviewDetailType | null>(null);
  const [status, setStatus] = useState<ReviewStatus | null>(null);
  const [live, setLive] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const socketRef = useRef<WebSocket | null>(null);

  // Fetch the review (with comments).
  useEffect(() => {
    if (!id) return;
    let active = true;
    setLoading(true);
    client
      .get<ReviewDetailType>(`/reviews/${id}`)
      .then(({ data }) => {
        if (!active) return;
        setReview(data);
        setStatus(data.status);
      })
      .catch(() => active && setError("Failed to load review."))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [id]);

  // Subscribe to live status updates over the WebSocket.
  useEffect(() => {
    if (!id) return;
    const socket = new WebSocket(wsUrl(`/ws/reviews/${id}`));
    socketRef.current = socket;
    socket.onopen = () => setLive(true);
    socket.onclose = () => setLive(false);
    socket.onmessage = (event) => {
      try {
        const update: ReviewUpdate = JSON.parse(event.data);
        setStatus(update.status);
      } catch {
        // ignore malformed messages
      }
    };
    return () => {
      socket.onclose = null; // avoid setState after unmount
      socket.close();
      socketRef.current = null;
    };
  }, [id]);

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="border-b border-gray-200 bg-white">
        <div className="mx-auto flex max-w-3xl items-center justify-between px-6 py-4">
          <Link to="/dashboard" className="text-sm font-medium text-indigo-600 hover:text-indigo-500">
            ← Back to reviews
          </Link>
          {live && (
            <span className="flex items-center gap-1.5 text-xs text-gray-500">
              <span className="h-2 w-2 animate-pulse rounded-full bg-green-500" />
              live
            </span>
          )}
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-6 py-8">
        {loading && <p className="text-sm text-gray-500">Loading…</p>}
        {error && <p className="text-sm text-red-600">{error}</p>}

        {review && (
          <>
            <div className="mb-6 flex items-center justify-between">
              <div>
                <h1 className="text-xl font-semibold text-gray-900">
                  Review of PR #{review.pr_number}
                </h1>
                {review.summary && (
                  <p className="mt-1 text-sm text-gray-500">{review.summary}</p>
                )}
              </div>
              {status && <StatusBadge status={status} />}
            </div>

            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-500">
              Comments ({review.comments.length})
            </h2>

            {review.comments.length === 0 ? (
              <p className="text-sm text-gray-500">No comments for this review.</p>
            ) : (
              <ul className="space-y-3">
                {review.comments.map((comment) => (
                  <li
                    key={comment.id}
                    className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm"
                  >
                    <div className="mb-2 flex items-center justify-between gap-3">
                      <code className="truncate font-mono text-sm text-gray-800">
                        {comment.file}
                        {comment.line !== null && (
                          <span className="text-gray-400">:{comment.line}</span>
                        )}
                      </code>
                      <SeverityBadge severity={comment.severity} />
                    </div>
                    <p className="text-sm text-gray-700">{comment.comment}</p>
                  </li>
                ))}
              </ul>
            )}
          </>
        )}
      </main>
    </div>
  );
}
