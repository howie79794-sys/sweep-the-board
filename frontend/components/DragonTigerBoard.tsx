"use client"

import { useState, useEffect } from "react"
import { rankingAPI } from "@/lib/api"
import { UserAvatar } from "@/components/UserAvatar"
import { type RankingResponse } from "@/types"
import { formatPercent } from "@/lib/utils"
import { cn } from "@/lib/utils"

interface DragonTigerBoardProps {
  className?: string
}

export function DragonTigerBoard({ className }: DragonTigerBoardProps) {
  const [rankings, setRankings] = useState<RankingResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadRankings()
  }, [])

  const loadRankings = async () => {
    try {
      setLoading(true)
      const data = await rankingAPI.getAll()
      setRankings(data)
      setError(null)
    } catch (err: any) {
      setError(err.message || "加载排名失败")
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className={cn("text-center py-12", className)}>
        <p className="text-muted-foreground">加载中...</p>
      </div>
    )
  }

  if (error) {
    // 检查是否是连接错误
    const isConnectionError = error.includes('ECONNREFUSED') || 
                              error.includes('Failed to fetch') || 
                              error.includes('无法连接到后端服务')
    
    if (isConnectionError) {
      return (
        <div className={cn("py-12", className)}>
          <div className="p-6 bg-destructive/10 border border-destructive/20 rounded-lg">
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
                </ul>
              </div>
              
              <div className="p-3 bg-muted rounded text-xs font-mono text-muted-foreground break-all">
                {error}
              </div>

              <button
                onClick={loadRankings}
                className="px-4 py-2 bg-primary text-primary-foreground rounded hover:bg-primary/90 transition-colors"
              >
                重试
              </button>
            </div>
          </div>
        </div>
      )
    }
    
    return (
      <div className={cn("text-center py-12", className)}>
        <p className="text-destructive mb-4">错误：{error}</p>
        <button
          onClick={loadRankings}
          className="px-4 py-2 bg-primary text-primary-foreground rounded hover:bg-primary/90"
        >
          重试
        </button>
      </div>
    )
  }

  if (!rankings || rankings.user_rankings.length === 0) {
    return (
      <div className={cn("text-center py-12", className)}>
        <p className="text-muted-foreground">暂无数据</p>
      </div>
    )
  }

  // 用户排名已经包含资产信息
  const userRankingsWithAssets = rankings.user_rankings

  return (
    <div className={cn("space-y-4", className)}>
      <h2 className="text-2xl font-bold">龙虎榜</h2>
      <div className="flex flex-wrap gap-6 justify-center">
        {userRankingsWithAssets.map((ranking, index) => {
          const rank = ranking.user_rank
          const showRankBadge = rank !== null && rank !== undefined && rank <= 3
          const changeRate = ranking.change_rate ?? 0
          const isPositive = changeRate >= 0

          return (
            <div
              key={ranking.id}
              className="flex flex-col items-center w-[140px]"
            >
              {/* 用户头像 */}
              <UserAvatar
                user={ranking.user}
                size="md"
                className="mb-2"
              />
              
              {/* 用户名称 */}
              <div className="text-sm font-semibold mb-1 text-center">
                {ranking.user.name}
              </div>
              
              {/* 资产代码 */}
              {(ranking as any).asset && (
                <div className="text-xs text-muted-foreground mb-1">
                  {(ranking as any).asset.code}
                </div>
              )}
              
              {/* 资产价格 */}
              {(ranking as any).current_price !== undefined && (
                <div className="text-lg font-bold mb-1">
                  ¥{((ranking as any).current_price as number).toFixed(2)}
                </div>
              )}
              
              {/* 收益率 */}
              <div
                className={cn(
                  "text-sm font-semibold",
                  isPositive ? "text-red-600" : "text-green-600"
                )}
              >
                {formatPercent(changeRate)}
              </div>
              
              {/* 排名徽章 */}
              {showRankBadge && (
                <div className="mt-1 text-xs font-semibold text-yellow-600">
                  No.{rank}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
