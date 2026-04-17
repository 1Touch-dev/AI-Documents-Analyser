import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Route static asset requests through api.intellifundit.site (served by Nginx directly)
  // instead of intellifundit.site (CloudFront blocks /_next/static/* with a broken cache behavior).
  assetPrefix: process.env.NODE_ENV === "production" ? "https://api.intellifundit.site" : undefined,
  experimental: {
    // The app proxies /api/backend/* to the FastAPI backend.
    // This prevents Next from buffering only a truncated prefix of large upload bodies.
    proxyClientMaxBodySize: "1gb",
  },
};

export default nextConfig;
