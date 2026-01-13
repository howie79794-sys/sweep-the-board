/** @type {import('next').NextConfig} */
const nextConfig = {
  // 生产环境输出模式 - 不使用standalone，使用默认模式以支持rewrites
  // output: 'standalone',  // 注释掉，因为standalone模式可能不支持rewrites
  
  // API 代理转发 - 在所有环境中生效
  async rewrites() {
    // 从环境变量读取后端地址，默认为 localhost:8000
    const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    
    console.log('[Next.js Config] 使用后端地址:', backendUrl)
    
    return [
      {
        source: '/api/:path*',
        destination: `${backendUrl}/api/:path*`,
      },
      {
        source: '/avatars/:path*',
        destination: `${backendUrl}/avatars/:path*`,
      },
    ]
  },
}

module.exports = nextConfig
