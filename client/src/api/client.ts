import axios from "axios";
import { clearToken, getToken } from "./auth";

export const API_BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

/** Build a ws(s):// URL for a backend path, reusing VITE_API_URL's host. */
export function wsUrl(path: string): string {
  const url = new URL(path, API_BASE_URL);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  return url.toString();
}

const client = axios.create({ baseURL: API_BASE_URL });

// 1 + 2: attach the JWT from localStorage to every request.
client.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 3: on 401, drop the (now invalid) token and send the user to /login.
client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      clearToken();
      if (window.location.pathname !== "/login") {
        window.location.assign("/login");
      }
    }
    return Promise.reject(error);
  },
);

export default client;
