import type { NextConfig } from "next";

const backend = process.env.BACKEND_INTERNAL_URL ?? "http://localhost:8000";
const storage = process.env.STORAGE_INTERNAL_URL ?? "http://storage:8333";

const nextConfig: NextConfig = {
  output: "standalone",
  skipTrailingSlashRedirect: true,
  async redirects() {
    return [
      { source: "/dashboard/applications/:path*", destination: "/applications/:path*", permanent: false },
      { source: "/dashboard/contracts/:path*", destination: "/contracts/:path*", permanent: false },
      { source: "/dashboard/prisoners/:path*", destination: "/prisoners/:path*", permanent: false },
      { source: "/dashboard/profile", destination: "/profile", permanent: false },
    ];
  },
  async rewrites() {
    return [
      { source: "/backend/:path*/", destination: `${backend}/api/:path*/` },
      { source: "/media/:path*", destination: `${backend}/media/:path*` },
      { source: "/storage/:path*", destination: `${storage}/:path*` },
    ];
  },
};

export default nextConfig;
