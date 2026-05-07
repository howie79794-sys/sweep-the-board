"use client"

import { useState } from "react"
import { AssetCard } from "@/components/AssetCard"
import { UserCard } from "@/components/UserCard"
import { MedalBadge } from "@/components/ui/medal-badge"
import { CardListSkeleton } from "@/components/ui/skeleton"
import { useRankings } from "@/lib/hooks"
import {
  formatPercent,
  cn,
  getChangeColor,
  getChangeArrow,
  getMedalConfig,
} from "@/lib/utils"

interface LeaderboardProps {
  className?: string
}

export function Leaderboard({ className }: LeaderboardProps) {
  const { data: rankings, error: swrError, isLoading, mutate } = useRankings()
  const error = swrError ? (swrError.message || "加载排名失败") : null
  const [activeTab, setActiveTab] = useState<"assets" | "users">("assets")
  const loadRankings = () => mutate()

  if (isLoading && !rankings) {
    return (
      <div className={cn("space-y-6", className)}>
        <div className="flex gap-4 border-b">
          <div className="px-4 py-2 border-b-2 border-primary text-primary font-medium">
            资产排名
          </div>
          <div className="px-4 py-2 text-muted-foreground">用户排名</div>
        </div>
        <CardListSkeleton count={6} />
      </div>
    )
  }

  if (error) {
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

  if (!rankings) {
    return (
      <div className={cn("text-center py-12", className)}>
        <p className="text-muted-foreground">暂无数据</p>
      </div>
    )
  }

  return (
    <div className={cn("space-y-6", className)}>
      {/* 标签页切换 */}
      <div className="flex gap-4 border-b">
        <button
          onClick={() => setActiveTab("assets")}
          className={cn(
            "px-4 py-2 font-medium border-b-2 transition-colors",
            activeTab === "assets"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          )}
        >
          资产排名
        </button>
        <button
          onClick={() => setActiveTab("users")}
          className={cn(
            "px-4 py-2 font-medium border-b-2 transition-colors",
            activeTab === "users"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          )}
        >
          用户排名
        </button>
      </div>

      {/* 资产排名 */}
      {activeTab === "assets" && (
        <div>
          <h2 className="text-2xl font-bold mb-4">资产排名</h2>
          {rankings.asset_rankings.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              暂无资产排名数据
            </div>
          ) : (
            <div className="grid gap-4">
              {rankings.asset_rankings.map((ranking, index) => (
                <AssetCard
                  key={ranking.id}
                  asset={{
                    ...ranking.asset,
                    user: ranking.user,
                  }}
                  rank={ranking.asset_rank || undefined}
                  changeRate={ranking.change_rate ?? undefined}
                  currentPrice={(ranking as any).current_price ?? undefined}
                  highlight={index === 0 && ranking.asset_rank !== null && ranking.asset_rank !== undefined}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {/* 用户排名 */}
      {activeTab === "users" && (
        <div>
          <h2 className="text-2xl font-bold mb-4">用户排名</h2>
          {rankings.user_rankings.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              暂无用户排名数据
            </div>
          ) : (
            <div className="grid gap-4">
              {rankings.user_rankings.map((ranking) => {
                const medalConfig = getMedalConfig(ranking.user_rank)
                const isMedal = medalConfig !== null
                return (
                  <div
                    key={ranking.id}
                    className={cn(
                      "border rounded-lg p-4 transition-all",
                      isMedal
                        ? cn(medalConfig.bgClass, medalConfig.borderClass, "shadow-lg")
                        : "bg-card hover:shadow-md"
                    )}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-4">
                        <MedalBadge rank={ranking.user_rank} variant="full" size="md" />
                        <UserCard user={ranking.user} showAvatar={true} />
                      </div>
                      <div className="text-right">
                        <div
                          className={cn(
                            "text-2xl font-bold inline-flex items-center gap-1",
                            getChangeColor(ranking.change_rate)
                          )}
                        >
                          <span aria-hidden="true">{getChangeArrow(ranking.change_rate)}</span>
                          <span>{formatPercent(ranking.change_rate)}</span>
                        </div>
                        {isMedal && (
                          <div className={cn("text-sm font-semibold mt-1", medalConfig.textClass)}>
                            {medalConfig.emoji} {medalConfig.label}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
