export const BACKEND_API_BASE_URL =
  process.env.NEXT_PUBLIC_BACKEND_API_URL ?? "https://api.intellifundit.site/api";

// Use same-origin Next.js route handler to avoid browser extension/CORS interference.
export const API_PROXY_BASE_URL = "/api/backend";

