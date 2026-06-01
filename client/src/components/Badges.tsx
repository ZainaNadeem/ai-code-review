import type { ReviewStatus, Severity } from "../api/types";

const STATUS_STYLES: Record<ReviewStatus, string> = {
  pending: "bg-gray-100 text-gray-700 ring-gray-300",
  processing: "bg-blue-100 text-blue-700 ring-blue-300",
  complete: "bg-green-100 text-green-700 ring-green-300",
  failed: "bg-red-100 text-red-700 ring-red-300",
};

export function StatusBadge({ status }: { status: ReviewStatus }) {
  const style = STATUS_STYLES[status] ?? STATUS_STYLES.pending;
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ring-1 ring-inset ${style}`}
    >
      {status}
    </span>
  );
}

const SEVERITY_STYLES: Record<Severity, string> = {
  error: "bg-red-100 text-red-700 ring-red-300",
  warning: "bg-amber-100 text-amber-800 ring-amber-300",
  info: "bg-sky-100 text-sky-700 ring-sky-300",
};

export function SeverityBadge({ severity }: { severity: Severity }) {
  const style = SEVERITY_STYLES[severity] ?? SEVERITY_STYLES.info;
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wide ring-1 ring-inset ${style}`}
    >
      {severity}
    </span>
  );
}
