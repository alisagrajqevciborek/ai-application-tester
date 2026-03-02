/** @type {import('next').NextConfig} */
const nextConfig = {
  typescript: {
    // Re-enable TypeScript checks for production builds only
    // This catches errors in CI/production without slowing down dev
    ignoreBuildErrors: process.env.NODE_ENV === 'development',
  },
  // Performance optimizations
  reactStrictMode: true, // Re-enable strict mode to catch potential issues
  compiler: {
    removeConsole: process.env.NODE_ENV === 'production', // Remove console.logs in production
  },
}

export default nextConfig
