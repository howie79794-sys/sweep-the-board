import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatPercent(value: number | null | undefined): string {
  if (value === null || value === undefined) return "--"
  return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`
}

export function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined) return "--"
  if (value === 0) return "--"
  return value.toLocaleString('zh-CN', { maximumFractionDigits: 2 })
}

export function formatNumberAllowZero(value: number | null | undefined): string {
  if (value === null || value === undefined) return "--"
  return value.toLocaleString('zh-CN', { maximumFractionDigits: 2 })
}

/** 图表缩放：默认展示的交易日数量（最近 N 个点） */
export const CHART_DEFAULT_VISIBLE_POINTS = 25

/** X 轴标签格式：MM-DD */
export function formatChartAxisDate(dateStr: string): string {
  if (!dateStr) return ""
  const d = new Date(dateStr)
  const m = String(d.getMonth() + 1).padStart(2, "0")
  const day = String(d.getDate()).padStart(2, "0")
  return `${m}-${day}`
}

/** Tooltip 日期格式：YYYY-MM-DD */
export function formatTooltipDate(dateStr: string): string {
  if (!dateStr) return ""
  const d = new Date(dateStr)
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, "0")
  const day = String(d.getDate()).padStart(2, "0")
  return `${y}-${m}-${day}`
}

// ============================================================
// 涨跌颜色工具（统一 A 股惯例：红涨绿跌）
// ============================================================

/**
 * 获取涨跌颜色 className（A股惯例：红涨绿跌）
 * @param value 涨跌幅数值，null/undefined 返回灰色
 * @param variant "text"（文字）或 "bg"（背景）
 */
export function getChangeColor(
  value: number | null | undefined,
  variant: "text" | "bg" = "text"
): string {
  if (value === null || value === undefined) {
    return variant === "text" ? "text-muted-foreground" : "bg-muted"
  }
  if (value > 0) {
    return variant === "text" ? "text-red-600" : "bg-red-100"
  }
  if (value < 0) {
    return variant === "text" ? "text-green-600" : "bg-green-100"
  }
  return variant === "text" ? "text-muted-foreground" : "bg-muted"
}

/**
 * 涨跌幅热力色（A 股惯例）
 * 根据涨跌幅强度返回从浅到深的红/绿颜色，用于排行榜热力可视化
 *
 * 阈值：
 *  - |value| ≥ 10%  → 深色（最强）
 *  - |value| ≥ 5%   → 中色
 *  - |value| ≥ 2%   → 浅色
 *  - |value| < 2%   → 极浅
 */
export function getHeatmapColor(value: number | null | undefined): string {
  if (value === null || value === undefined) return "bg-muted text-muted-foreground"
  const abs = Math.abs(value)
  if (value > 0) {
    // 涨：红色系
    if (abs >= 10) return "bg-red-600 text-white"
    if (abs >= 5) return "bg-red-500 text-white"
    if (abs >= 2) return "bg-red-300 text-red-900"
    return "bg-red-100 text-red-700"
  }
  if (value < 0) {
    // 跌：绿色系
    if (abs >= 10) return "bg-green-600 text-white"
    if (abs >= 5) return "bg-green-500 text-white"
    if (abs >= 2) return "bg-green-300 text-green-900"
    return "bg-green-100 text-green-700"
  }
  return "bg-muted text-muted-foreground"
}

/** 涨跌方向箭头（无障碍：颜色之外的额外语义） */
export function getChangeArrow(value: number | null | undefined): string {
  if (value === null || value === undefined) return ""
  if (value > 0) return "↑"
  if (value < 0) return "↓"
  return ""
}

// ============================================================
// 排名徽章工具（金银铜）
// ============================================================

/** 是否为前三名 */
export function isTopThree(rank: number | null | undefined): boolean {
  return rank !== null && rank !== undefined && rank >= 1 && rank <= 3
}

/**
 * 获取金银铜徽章配置
 * 1 = 金, 2 = 银, 3 = 铜
 */
export function getMedalConfig(rank: number | null | undefined): {
  emoji: string
  label: string
  bgClass: string
  borderClass: string
  textClass: string
  ringClass: string
} | null {
  if (!isTopThree(rank)) return null
  const configs = {
    1: {
      emoji: "🥇",
      label: "冠军",
      bgClass: "bg-gradient-to-br from-yellow-50 via-amber-50 to-orange-100",
      borderClass: "border-amber-400",
      textClass: "text-amber-700",
      ringClass: "ring-2 ring-amber-300",
    },
    2: {
      emoji: "🥈",
      label: "亚军",
      bgClass: "bg-gradient-to-br from-slate-50 via-zinc-50 to-slate-100",
      borderClass: "border-slate-400",
      textClass: "text-slate-700",
      ringClass: "ring-2 ring-slate-300",
    },
    3: {
      emoji: "🥉",
      label: "季军",
      bgClass: "bg-gradient-to-br from-orange-50 via-amber-50 to-yellow-100",
      borderClass: "border-orange-400",
      textClass: "text-orange-700",
      ringClass: "ring-2 ring-orange-300",
    },
  } as const
  return configs[rank as 1 | 2 | 3]
}
