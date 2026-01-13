"use client"

import { cn } from "@/lib/utils"

interface ConnectionErrorProps {
  error?: string | null
  onRetry?: () => void
  className?: string
}

export function ConnectionError({ error, onRetry, className }: ConnectionErrorProps) {
  // 检查是否是连接错误
  const isConnectionError = error && (
    error.includes('ECONNREFUSED') ||
    error.includes('Failed to fetch') ||
    error.includes('无法连接到后端服务') ||
    error.includes('NetworkError')
  )

  if (!isConnectionError) {
    return null
  }

  return (
    <div className={cn("p-6 bg-destructive/10 border border-destructive/20 rounded-lg", className)}>
      <div className="space-y-4">
        <div>
          <h3 className="text-lg font-semibold text-destructive mb-2">
            无法连接到后端服务
          </h3>
          <p className="text-sm text-muted-foreground mb-2">
            前端无法连接到后端 API 服务。请检查以下事项：
          </p>
          <ul className="list-disc list-inside text-sm text-muted-foreground space-y-1 ml-4">
            <li>确保后端服务正在运行在 <code className="bg-muted px-1 rounded">http://localhost:8000</code></li>
            <li>检查后端服务是否正常启动（查看后端日志）</li>
            <li>确认端口 8000 没有被其他程序占用</li>
            <li>如果使用容器环境，检查容器网络配置</li>
          </ul>
        </div>
        
        {error && (
          <div className="mt-4 p-3 bg-muted rounded text-xs font-mono text-muted-foreground break-all">
            {error}
          </div>
        )}

        {onRetry && (
          <button
            onClick={onRetry}
            className="mt-4 px-4 py-2 bg-primary text-primary-foreground rounded hover:bg-primary/90 transition-colors"
          >
            重试
          </button>
        )}

        <div className="mt-4 text-xs text-muted-foreground">
          <p>提示：可以通过以下命令检查后端服务：</p>
          <code className="block mt-1 p-2 bg-muted rounded">
            curl http://localhost:8000/api/health
          </code>
        </div>
      </div>
    </div>
  )
}
