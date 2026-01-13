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
