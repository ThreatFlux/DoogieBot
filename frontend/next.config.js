/** @type {import('next').NextConfig} */
const isDev = process.env.NODE_ENV !== 'production';

const nextConfig = {
  // Enable React strict mode in production, disable in development to prevent double renders
  reactStrictMode: !isDev,
  // Production-specific optimizations
  productionBrowserSourceMaps: false,
  // API rewrites for both dev and prod
  async rewrites() {
    return [
      {
        source: '/api/v1/:path*',
        destination: 'http://127.0.0.1:8000/api/v1/:path*', // Proxy regular API requests
      },
      {
        source: '/api/v1/:path*/',
        destination: 'http://127.0.0.1:8000/api/v1/:path*/', // Handle trailing slashes
      },
      {
        source: '/v1/:path*',
        destination: 'http://127.0.0.1:8000/api/v1/:path*', // Proxy EventSource requests
      },
    ];
  },
};

module.exports = nextConfig;
