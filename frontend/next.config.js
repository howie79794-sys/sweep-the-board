/** @type {import('next').NextConfig} */
const nextConfig = {
  // 生产环境输出模式
  output: 'standalone',
  
  // API 代理转发（开发环境使用，生产环境在 Docker 中直接访问）
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: process.env.NEXT_PUBLIC_API_URL 
          ? `${process.env.NEXT_PUBLIC_API_URL}/api/:path*`
          : 'http://localhost:8000/api/:path*',
      },
    ]
  },
}

module.exports = nextConfig
