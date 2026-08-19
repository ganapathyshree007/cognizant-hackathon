/**
 * Central API base URL utility.
 * In dev: Vite proxies /api/* → localhost:8000 (empty string base URL)
 * In production: Fallback to the deployed Render backend if not running on localhost.
 */
export const API_BASE =
  (import.meta.env.VITE_API_URL as string) ||
  (typeof window !== "undefined" && !window.location.hostname.includes("localhost") && !window.location.hostname.includes("127.0.0.1")
    ? "https://carepath-backend-uv06.onrender.com"
    : "");

export const apiUrl = (path: string) => `${API_BASE}${path}`;
