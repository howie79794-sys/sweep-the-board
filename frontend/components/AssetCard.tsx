"use client"

import { type Asset } from "@/types"
import { UserAvatar } from "@/components/UserAvatar"
import { formatPercent, formatNumber } from "@/lib/utils"
import { cn } from "@/lib/utils"

interface AssetCardProps {
  asset: Asset & { user?: { id: number; name: string; avatar_url?: string } }
  rank?: number
  changeRate?: number
  currentPrice?: number
  highlight?: boolean
  className?: string
}

const assetTypeLabels: Record<string, string> = {
  stock: "股票",
  fund: "基金",
  futures: "期货",
  forex: "外汇",
}

export function AssetCard({
  asset,
  rank,
  changeRate,
  currentPrice,
  highlight = false,
  className,
}: AssetCardProps) {
  return (
    <div
      className={cn(
        "border rounded-lg p-4 transition-all",
        highlight
          ? "bg-gradient-to-r from-yellow-50 to-orange-50 border-yellow-300 shadow-lg"
          : "bg-card hover:shadow-md",
        className
      )}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4 flex-1">
          {rank !== undefined && (
            <div
              className={cn(
                "text-2xl font-bold",
                highlight ? "text-yellow-600" : "text-muted-foreground"
              )}
            >
              #{rank}
            </div>
          )}
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <div className="font-semibold text-lg">{asset.name}</div>
              {asset.is_core && (
                <span className="text-xs px-2 py-0.5 bg-amber-500 text-white rounded">
                  核心
                </span>
              )}
              <span className="text-xs px-2 py-0.5 bg-secondary rounded">
                {assetTypeLabels[asset.asset_type] || asset.asset_type}
              </span>
              {asset.is_core && (
                <span className="text-xs px-2 py-0.5 bg-gradient-to-r from-yellow-400 to-orange-400 text-white font-semibold rounded">
                  核心
                </span>
              )}
            </div>
            <div className="text-sm text-muted-foreground space-y-1">
              <div>
                {asset.code} | {asset.market}
              </div>
              {asset.user && (
                <div className="flex items-center gap-2">
                  <UserAvatar
                    user={{
                      id: asset.user.id,
                      name: asset.user.name,
                      avatar_url: asset.user.avatar_url,
                      created_at: "",
                      is_active: true,
                    }}
                    size="sm"
                  />
                  <span>{asset.user.name}</span>
                </div>
              )}
            </div>
          </div>
        </div>
        <div className="text-right">
          {changeRate !== undefined && changeRate !== null ? (
            <>
              <div
                className={cn(
                  "text-2xl font-bold",
                  changeRate >= 0 ? "text-green-600" : "text-red-600"
                )}
              >
                {formatPercent(changeRate)}
              </div>
              {highlight && (
                <div className="text-sm text-yellow-600 font-semibold mt-1">
                  当日冠军 🏆
                </div>
              )}
            </>
          ) : (
            <>
              {currentPrice !== undefined && currentPrice !== null ? (
                <>
                  <div className="text-xl font-semibold text-foreground">
                    {formatNumber(currentPrice)}
                  </div>
                  <div className="text-sm text-muted-foreground mt-1">
                    缺少基准价
                  </div>
                </>
              ) : (
                <div className="text-sm text-muted-foreground">
                  计算中...
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
