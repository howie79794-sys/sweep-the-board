"use client"

import { cn } from "@/lib/utils"
import { getMedalConfig, isTopThree } from "@/lib/utils"

interface MedalBadgeProps {
  rank: number | null | undefined
  /** 显示模式：'icon' 只显示奖牌；'full' 显示奖牌+名次文字 */
  variant?: "icon" | "full"
  /** 尺寸 */
  size?: "xs" | "sm" | "md" | "lg"
  className?: string
}

/**
 * 金银铜徽章
 *  - 第 1 名：🥇 金色
 *  - 第 2 名：🥈 银色
 *  - 第 3 名：🥉 铜色
 *  - 其他：返回普通 #N 数字徽章
 */
export function MedalBadge({
  rank,
  variant = "full",
  size = "sm",
  className,
}: MedalBadgeProps) {
  const sizeClasses: Record<string, string> = {
    xs: "text-[10px] px-1.5 py-0.5",
    sm: "text-xs px-2 py-0.5",
    md: "text-sm px-2.5 py-1",
    lg: "text-base px-3 py-1.5",
  }

  const emojiSize: Record<string, string> = {
    xs: "text-sm",
    sm: "text-base",
    md: "text-lg",
    lg: "text-2xl",
  }

  if (!rank) return null

  // 前三名：金银铜
  if (isTopThree(rank)) {
    const config = getMedalConfig(rank)!
    return (
      <span
        className={cn(
          "inline-flex items-center gap-1 rounded-full font-semibold",
          config.bgClass,
          config.textClass,
          "border",
          config.borderClass,
          sizeClasses[size],
          className
        )}
        aria-label={`第${rank}名：${config.label}`}
        title={`第${rank}名：${config.label}`}
      >
        <span className={emojiSize[size]} aria-hidden="true">
          {config.emoji}
        </span>
        {variant === "full" && <span>No.{rank}</span>}
      </span>
    )
  }

  // 其他名次：普通灰色 #N
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full bg-muted text-muted-foreground font-medium",
        sizeClasses[size],
        className
      )}
      aria-label={`第${rank}名`}
    >
      #{rank}
    </span>
  )
}
