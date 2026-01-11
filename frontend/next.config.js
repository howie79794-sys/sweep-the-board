/** @type {import('next').NextConfig} */
const nextConfig = {
  // 生产环境输出模式
  output: 'standalone',
  
  // API 代理转发 - 在生产环境中也生效
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/api/:path*',
      },
    ]
  },
}

module.exports = nextConfig
