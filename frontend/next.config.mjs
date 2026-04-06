/** @type {import('next').NextConfig} */
const nextConfig = {
  // Proxy /api/* to Python serve.py in development
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.API_BASE_URL || "http://127.0.0.1:8080"}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
