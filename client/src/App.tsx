import { useEffect, useState } from "react";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export default function App() {
  const [status, setStatus] = useState<string>("checking...");

  useEffect(() => {
    fetch(`${API_URL}/health`)
      .then((r) => r.json())
      .then((data) => setStatus(data.status ?? "unknown"))
      .catch(() => setStatus("unreachable"));
  }, []);

  return (
    <main>
      <h1>AI Code Review Assistant</h1>
      <p>
        Server status: <strong>{status}</strong>
      </p>
    </main>
  );
}
