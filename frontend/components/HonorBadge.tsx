"use client"

import { UserAvatar } from "@/components/UserAvatar"
import { type User } from "@/types"
import { formatPercent } from "@/lib/utils"
import { cn } from "@/lib/utils"

interface HonorBadgeProps {
  user: User
  changeRate: number
  rank: number
  title?: string
  className?: string
}

export function HonorBadge({
  user,
  changeRate,
  rank,
  title = "当日冠军",
  className,
}: HonorBadgeProps) {
  return (
    <div
      className={cn(
        "relative border-2 rounded-lg p-6 bg-gradient-to-r from-yellow-50 via-orange-50 to-yellow-50 border-yellow-400 shadow-xl",
        "animate-pulse",
        className
      )}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="relative">
            <UserAvatar user={user} size="lg" />
            <div className="absolute -top-2 -right-2 bg-yellow-500 text-white rounded-full w-8 h-8 flex items-center justify-center text-sm font-bold">
              {rank}
            </div>
          </div>
          <div>
            <div className="flex items-center gap-2 mb-1">
              <div className="text-2xl font-bold text-yellow-700">
                {user.name}
              </div>
              <span className="px-3 py-1 bg-yellow-400 text-yellow-900 rounded-full text-sm font-semibold">
                {title} 🏆
              </span>
            </div>
            <div className="text-sm text-muted-foreground">
              涨跌幅表现最佳
            </div>
          </div>
        </div>
        <div className="text-right">
          <div
            className={cn(
              "text-4xl font-bold mb-2",
              changeRate >= 0 ? "text-green-600" : "text-red-600"
            )}
          >
            {formatPercent(changeRate)}
          </div>
          <div className="text-sm text-muted-foreground">
            相对基准日涨幅
          </div>
        </div>
      </div>
      
      {/* 装饰性元素 */}
      <div className="absolute top-0 right-0 w-32 h-32 bg-yellow-200/20 rounded-full -mr-16 -mt-16" />
      <div className="absolute bottom-0 left-0 w-24 h-24 bg-orange-200/20 rounded-full -ml-12 -mb-12" />
    </div>
  )
}
