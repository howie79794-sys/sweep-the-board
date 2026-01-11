/** @type {import('next').NextConfig} */
const nextConfig = {
  // 生产环境输出模式 - 不使用standalone，使用默认模式以支持rewrites
  // output: 'standalone',  // 注释掉，因为standalone模式可能不支持rewrites
  
  // API 代理转发 - 在所有环境中生效
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/api/:path*',
      },
      {
        source: '/avatars/:path*',
        destination: 'http://localhost:8000/avatars/:path*',
      },
    ]
  },
}

module.exports = nextConfig
