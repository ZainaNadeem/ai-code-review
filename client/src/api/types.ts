export type ReviewStatus = "pending" | "processing" | "complete" | "failed";

export type Severity = "error" | "warning" | "info";

export interface Repo {
  id: number;
  user_id: number;
  github_repo_url: string;
  name: string;
}

export interface Review {
  id: number;
  repo_id: number;
  pr_number: number;
  status: ReviewStatus;
  created_at: string;
  summary: string | null;
}

export interface ReviewComment {
  id: number;
  file: string;
  line: number | null;
  severity: Severity;
  comment: string;
}

export interface ReviewDetail extends Review {
  comments: ReviewComment[];
}

export interface Token {
  access_token: string;
  token_type: string;
}

/** Shape of the message broadcast over /ws/reviews/:id. */
export interface ReviewUpdate {
  review_id: number;
  status: ReviewStatus;
  comment_count: number;
}
