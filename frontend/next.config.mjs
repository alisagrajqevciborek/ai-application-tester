/** @type {import('next').NextConfig} */
const nextConfig = {
  typescript: {
    ignoreBuildErrors: false,
  },
  // Performance optimizations
  reactStrictMode: true, // Re-enable strict mode to catch potential issues
  compiler: {
    removeConsole: process.env.NODE_ENV === 'production', // Remove console.logs in production
  },
}

export default nextConfig
