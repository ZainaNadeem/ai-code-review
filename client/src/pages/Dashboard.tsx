import { useEffect, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import client from "../api/client";
import { clearToken } from "../api/auth";
import { StatusBadge } from "../components/Badges";
import type { Repo, Review } from "../api/types";

export default function Dashboard() {
  const [reviews, setReviews] = useState<Review[]>([]);
  const [repos, setRepos] = useState<Record<number, Repo>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    async function load() {
      try {
        const [reviewsRes, reposRes] = await Promise.all([
          client.get<Review[]>("/reviews"),
          client.get<Repo[]>("/repos"),
        ]);
        if (!active) return;
        setReviews(reviewsRes.data);
        setRepos(Object.fromEntries(reposRes.data.map((r) => [r.id, r])));
      } catch {
        if (active) setError("Failed to load reviews.");
      } finally {
        if (active) setLoading(false);
      }
    }
    load();
    return () => {
      active = false;
    };
  }, []);

  function logout() {
    clearToken();
    window.location.assign("/login");
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="border-b border-gray-200 bg-white">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
          <h1 className="text-lg font-semibold text-gray-900">Code Reviews</h1>
          <button
            onClick={logout}
            className="rounded-md px-3 py-1.5 text-sm font-medium text-gray-600 hover:bg-gray-100"
          >
            Sign out
          </button>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-6 py-8">
        {loading && <p className="text-sm text-gray-500">Loading…</p>}
        {error && <p className="text-sm text-red-600">{error}</p>}

        {!loading && !error && reviews.length === 0 && (
          <p className="text-sm text-gray-500">No reviews yet.</p>
        )}

        {!loading && !error && reviews.length > 0 && (
          <div className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <Th>Repo</Th>
                  <Th>PR #</Th>
                  <Th>Status</Th>
                  <Th>Date</Th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {reviews.map((review) => (
                  <tr key={review.id} className="hover:bg-gray-50">
                    <Td className="font-medium text-gray-900">
                      {repos[review.repo_id]?.name ?? `repo #${review.repo_id}`}
                    </Td>
                    <Td>#{review.pr_number}</Td>
                    <Td>
                      <StatusBadge status={review.status} />
                    </Td>
                    <Td className="text-gray-500">
                      {new Date(review.created_at).toLocaleString()}
                    </Td>
                    <Td className="text-right">
                      <Link
                        to={`/reviews/${review.id}`}
                        className="rounded-md bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-indigo-500"
                      >
                        View
                      </Link>
                    </Td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </div>
  );
}

function Th({ children }: { children: ReactNode }) {
  return (
    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
      {children}
    </th>
  );
}

function Td({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <td className={`px-4 py-3 text-sm ${className}`}>{children}</td>;
}
