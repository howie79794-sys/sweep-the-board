"use client"

import { useState, useEffect } from "react"
import { rankingAPI } from "@/lib/api"
import { UserAvatar } from "@/components/UserAvatar"
import { type WeeklyRankingItem } from "@/types"
import { formatPercent } from "@/lib/utils"
import { cn } from "@/lib/utils"

/** 周一至周四显示「本周领先」，周五至周日显示「本周荣誉之星」 */
function getWeeklyTitle(): string {
  const day = new Date().getDay() // 0=周日, 1=周一, ..., 6=周六
  if (day >= 5) return "本周荣誉之星"
  return "本周领先"
}

interface WeeklySidebarProps {
  className?: string
}

export function WeeklySidebar({ className }: WeeklySidebarProps) {
  const [items, setItems] = useState<WeeklyRankingItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true)
        const res = await rankingAPI.getWeekly()
        setItems(res.items || [])
        setError(null)
      } catch (err: any) {
        setError(err.message || "加载失败")
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  return (
    <aside
      className={cn(
        "hidden lg:block w-[240px] shrink-0 rounded-xl overflow-hidden",
        // Glassmorphism: 半透明白 + 模糊
        "bg-white/70 backdrop-blur-[10px]",
        "border border-white/80 shadow-lg",
        className
      )}
      style={{
        backgroundColor: "rgba(255, 255, 255, 0.7)",
        boxShadow: "0 4px 24px rgba(0,0,0,0.08)",
      }}
    >
      <div className="p-4">
        <h3 className="text-sm font-semibold text-muted-foreground mb-3">
          自然周榜单
        </h3>

        {loading && (
          <p className="text-sm text-muted-foreground">加载中...</p>
        )}

        {error && !loading && (
          <p className="text-sm text-destructive">{error}</p>
        )}

        {!loading && !error && items.length === 0 && (
          <p className="text-sm text-muted-foreground">暂无数据</p>
        )}

        {!loading && !error && items.length > 0 && (
          <ul className="space-y-2">
            {items.map((item) => {
              const isChampion = item.rank === 1
              const isPositive = item.change_rate >= 0

              return (
                <li
                  key={`${item.asset_id}-${item.rank}`}
                  className={cn(
                    "rounded-lg p-2 transition-colors",
                    isChampion
                      ? "bg-gradient-to-r from-amber-50/80 via-yellow-50/80 to-amber-50/80 border-2 border-amber-400/60 shadow-sm"
                      : "bg-white/40 border border-transparent hover:bg-white/60"
                  )}
                >
                  {/* 第一名专属标签 */}
                  {isChampion && (
                    <div className="text-xs font-semibold text-amber-600 mb-2">
                      {getWeeklyTitle()}
                    </div>
                  )}

                  <div className="flex items-center gap-2">
                    {/* 头像 + 星形图标（冠军） */}
                    <div className="relative shrink-0">
                      <UserAvatar
                        user={{
                          id: item.user_id,
                          name: item.user_name,
                          avatar_url: item.avatar_url ?? undefined,
                          created_at: "",
                          is_active: true,
                        }}
                        size="sm"
                      />
                      {isChampion && (
                        <span
                          className="absolute -top-1 -right-1 text-amber-500"
                          aria-hidden
                        >
                          <svg
                            xmlns="http://www.w3.org/2000/svg"
                            viewBox="0 0 24 24"
                            fill="currentColor"
                            className="w-4 h-4 drop-shadow"
                          >
                            <path
                              fillRule="evenodd"
                              d="M10.788 3.21c.448-1.077 1.976-1.077 2.424 0l2.082 5.007 5.404.433c1.164.093 1.636 1.545.749 2.305l-4.117 3.527 1.257 5.273c.271 1.136-.964 2.033-1.96 1.425L12 18.354 7.373 21.18c-.996.608-2.231-.29-1.96-1.425l1.257-5.273-4.117-3.527c-.887-.76-.415-2.212.749-2.305l5.404-.433 2.082-5.006z"
                              clipRule="evenodd"
                            />
                          </svg>
                        </span>
                      )}
                    </div>

                    <div className="min-w-0 flex-1">
                      <div className="flex items-center justify-between gap-1">
                        <span className="text-sm font-medium truncate">
                          {item.user_name}
                        </span>
                        <span
                          className={cn(
                            "text-sm font-semibold shrink-0",
                            isPositive ? "text-red-600" : "text-green-600"
                          )}
                        >
                          {formatPercent(item.change_rate)}
                        </span>
                      </div>
                      <div className="text-xs text-muted-foreground truncate">
                        {item.asset_code}
                      </div>
                    </div>
                  </div>
                </li>
              )
            })}
          </ul>
        )}
      </div>
    </aside>
  )
}
