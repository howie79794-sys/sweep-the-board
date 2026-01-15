"use client"

import { BarChart, Bar, XAxis, YAxis, Cell, ResponsiveContainer } from "recharts"

interface MiniHistogramProps {
  dailyReturns: number[]
  width?: number
  height?: number
}

/**
 * 迷你直方图组件
 * 将每日收益率分成7个桶并展示分布
 */
export function MiniHistogram({ dailyReturns, width = 160, height = 60 }: MiniHistogramProps) {
  if (!dailyReturns || dailyReturns.length === 0) {
    return (
      <div className="flex items-center justify-center" style={{ width, height }}>
        <p className="text-xs text-muted-foreground">无数据</p>
      </div>
    )
  }

  // 定义桶的边界（百分比）
  const buckets = [
    { label: "< -2%", min: -Infinity, max: -2, color: "#16a34a" }, // 绿色（负收益）
    { label: "-2% ~ -1%", min: -2, max: -1, color: "#22c55e" },
    { label: "-1% ~ 0%", min: -1, max: 0, color: "#86efac" },
    { label: "0% ~ 1%", min: 0, max: 1, color: "#fca5a5" },
    { label: "1% ~ 2%", min: 1, max: 2, color: "#ef4444" },
    { label: "2% ~ 3%", min: 2, max: 3, color: "#dc2626" },
    { label: "> 3%", min: 3, max: Infinity, color: "#b91c1c" }, // 红色（正收益）
  ]

  // 将收益率分配到各个桶中
  const bucketCounts = buckets.map((bucket) => {
    const count = dailyReturns.filter((r) => r >= bucket.min && r < bucket.max).length
    return {
      label: bucket.label,
      count,
      color: bucket.color,
    }
  })

  return (
    <ResponsiveContainer width={width} height={height}>
      <BarChart data={bucketCounts} margin={{ top: 0, right: 0, bottom: 0, left: 0 }}>
        <XAxis dataKey="label" hide />
        <YAxis hide />
        <Bar dataKey="count" radius={[2, 2, 0, 0]}>
          {bucketCounts.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={entry.color} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
