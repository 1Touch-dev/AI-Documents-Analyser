import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  experimental: {
    // The app proxies /api/backend/* to the FastAPI backend.
    // This prevents Next from buffering only a truncated prefix of large upload bodies.
    proxyClientMaxBodySize: "1gb",
  },
};

export default nextConfig;
