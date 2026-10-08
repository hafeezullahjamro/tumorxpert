/** @type {import('next').NextConfig} */
const nextConfig = {
  skipMiddlewareUrlNormalize: true,
  experimental: {
    proxyTimeout: 3600000
  },
  images: {
    remotePatterns: []
  },
  async rewrites() {
    const backendUrl = (process.env.API_BACKEND_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "");
    return [{ source: "/api/:path*", destination: `${backendUrl}/:path*` }];
  }
};

export default nextConfig;
