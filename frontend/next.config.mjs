/** @type {import('next').NextConfig} */
const nextConfig = {
  typescript: {
    ignoreBuildErrors: true,
  },
  // Performance optimizations
  reactStrictMode: false, // Disable strict mode to avoid double renders in dev
  compiler: {
    removeConsole: process.env.NODE_ENV === 'production', // Remove console.logs in production
  },
}

export default nextConfig
