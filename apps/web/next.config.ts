import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Required for the Docker multi-stage Dockerfile (copies standalone output)
  output: "standalone",

  // Allow fetching images from the API host in future phases
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "*.onrender.com",
      },
    ],
  },
};

export default nextConfig;
