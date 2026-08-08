import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/ask",
        destination: "http://localhost:5050/ask",
      },
      {
        source: "/api/:path*",
        destination: "http://localhost:5050/:path*",
      },
    ];
  },
};

export default nextConfig;
