"use client"

import { UserAvatar } from "@/components/UserAvatar"
import { LeaderboardSkeleton } from "@/components/ui/skeleton"
import { useRankings } from "@/lib/hooks"
import {
  formatPercent,
  cn,
  getChangeArrow,
  getHeatmapColor,
  getMedalConfig,
  isTopThree,
} from "@/lib/utils"

interface DragonTigerBoardProps {
  className?: string
}

export function DragonTigerBoard({ className }: DragonTigerBoardProps) {
  const { data: rankings, error: swrError, isLoading, mutate } = useRankings()
  const error = swrError ? (swrError.message || "加载排名失败") : null

  const loadRankings = () => mutate()

  if (isLoading && !rankings) {
    return (
      <div className={cn("space-y-4", className)}>
        <h2 className="text-2xl font-bold">核心资产龙虎榜</h2>
        <LeaderboardSkeleton />
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
      <h2 className="text-2xl font-bold">核心资产龙虎榜</h2>
      <div className="flex flex-nowrap gap-3 justify-center overflow-x-auto pb-2">
        {userRankingsWithAssets.map((ranking) => {
          const rank = ranking.user_rank
          const isMedal = isTopThree(rank)
          const medalConfig = getMedalConfig(rank)
          const changeRate = ranking.change_rate ?? 0

          return (
            <div
              key={ranking.id}
              className={cn(
                "group flex flex-col items-center shrink-0 w-[110px] rounded-xl p-2 transition-all duration-300",
                isMedal && medalConfig
                  ? cn(
                      medalConfig.bgClass,
                      "border-2",
                      medalConfig.borderClass,
                      medalConfig.ringClass,
                      "shadow-md hover:shadow-xl hover:-translate-y-1"
                    )
                  : "border border-transparent hover:border-muted hover:bg-muted/30"
              )}
            >
              {/* 奖牌（前三名） / 序号（其他） */}
              <div className="mb-1 h-5 flex items-center justify-center">
                {isMedal && medalConfig ? (
                  <span
                    className="text-xl leading-none animate-bounce-slow"
                    aria-label={`第${rank}名：${medalConfig.label}`}
                  >
                    {medalConfig.emoji}
                  </span>
                ) : rank ? (
                  <span className="text-[10px] text-muted-foreground font-medium">
                    No.{rank}
                  </span>
                ) : null}
              </div>

              {/* 用户头像 */}
              <UserAvatar
                user={ranking.user}
                size="sm"
                className={cn(
                  "mb-1 transition-transform group-hover:scale-110",
                  isMedal && "ring-2 ring-offset-1",
                  isMedal && rank === 1 && "ring-amber-400",
                  isMedal && rank === 2 && "ring-slate-400",
                  isMedal && rank === 3 && "ring-orange-400"
                )}
              />

              {/* 用户名称 */}
              <div
                className={cn(
                  "text-xs font-semibold mb-0.5 text-center truncate w-full",
                  isMedal && medalConfig?.textClass
                )}
              >
                {ranking.user.name}
              </div>

              {/* 资产代码 */}
              {(ranking as any).asset && (
                <div className="text-[10px] text-muted-foreground mb-0.5">
                  {(ranking as any).asset.code}
                </div>
              )}

              {/* 资产价格 */}
              {(ranking as any).current_price !== undefined && (
                <div className="text-sm font-bold mb-1">
                  ¥{((ranking as any).current_price as number).toFixed(2)}
                </div>
              )}

              {/* 涨跌幅热力色徽章（核心视觉升级） */}
              <div
                className={cn(
                  "px-2 py-0.5 rounded-full text-xs font-bold inline-flex items-center gap-0.5",
                  getHeatmapColor(changeRate)
                )}
                title={`${formatPercent(changeRate)}`}
              >
                <span aria-hidden="true">{getChangeArrow(changeRate)}</span>
                <span>{formatPercent(changeRate)}</span>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
