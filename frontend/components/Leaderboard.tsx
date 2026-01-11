"use client"

import { useState, useEffect } from "react"
import { rankingAPI } from "@/lib/api"
import { AssetCard } from "@/components/AssetCard"
import { UserCard } from "@/components/UserCard"
import { type RankingResponse } from "@/types"
import { formatPercent } from "@/lib/utils"
import { cn } from "@/lib/utils"

interface LeaderboardProps {
  className?: string
}

export function Leaderboard({ className }: LeaderboardProps) {
  const [rankings, setRankings] = useState<RankingResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<"assets" | "users">("assets")

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
              {rankings.user_rankings.map((ranking, index) => (
                <div
                  key={ranking.id}
                  className={cn(
                    "border rounded-lg p-4",
                    index === 0
                      ? "bg-gradient-to-r from-yellow-50 to-orange-50 border-yellow-300 shadow-lg"
                      : "bg-card"
                  )}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div
                        className={cn(
                          "text-2xl font-bold",
                          index === 0 ? "text-yellow-600" : "text-muted-foreground"
                        )}
                      >
                        #{ranking.user_rank}
                      </div>
                      <UserCard
                        user={ranking.user}
                        showAvatar={true}
                      />
                    </div>
                    <div className="text-right">
                      <div
                        className={cn(
                          "text-2xl font-bold",
                          ranking.change_rate && ranking.change_rate >= 0
                            ? "text-green-600"
                            : "text-red-600"
                        )}
                      >
                        {formatPercent(ranking.change_rate)}
                      </div>
                      {index === 0 && (
                        <div className="text-sm text-yellow-600 font-semibold mt-1">
                          当日冠军 🏆
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
