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
