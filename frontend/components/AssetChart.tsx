"use client"

import { useState, useEffect } from "react"
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Brush,
} from "recharts"
import { dataAPI } from "@/lib/api"
import { formatPercent, formatNumber, formatChartAxisDate, formatTooltipDate, CHART_DEFAULT_VISIBLE_POINTS } from "@/lib/utils"
import { type Asset } from "@/types"

interface AssetChartProps {
  asset: Asset
  showChangeRate?: boolean
  className?: string
}

interface ChartDataPoint {
  date: string
  originalDate: string
  price: number
  changeRate?: number
}

export function AssetChart({
  asset,
  showChangeRate = false,
  className,
}: AssetChartProps) {
  const [chartData, setChartData] = useState<ChartDataPoint[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [range, setRange] = useState({ startIndex: 0, endIndex: 0 })

  useEffect(() => {
    loadChartData()
  }, [asset.id])

  useEffect(() => {
    if (chartData.length === 0) return
    const totalPoints = chartData.length
    setRange((prev) => {
      if (prev.endIndex > totalPoints || prev.startIndex >= totalPoints) {
        return {
          startIndex: Math.max(0, totalPoints - CHART_DEFAULT_VISIBLE_POINTS),
          endIndex: totalPoints,
        }
      }
      return prev
    })
  }, [chartData.length])

  const loadChartData = async () => {
    try {
      setLoading(true)
      const data = await dataAPI.getAssetData(asset.id, {
        start_date: asset.start_date,
        end_date: asset.end_date,
      })

      // 辅助函数：判断是否为工作日（周一到周五）
      const isWeekday = (dateStr: string): boolean => {
        const date = new Date(dateStr)
        const day = date.getDay() // 0 = 周日, 6 = 周六
        return day >= 1 && day <= 5 // 周一到周五
      }

      // 过滤掉周末（非工作日）
      const weekdayData = data.filter((item: any) => isWeekday(item.date))

      const baselinePrice = asset.baseline_price ?? 0

      if (baselinePrice > 0 && showChangeRate) {
        const formatted = weekdayData.map((item: any) => {
          const changeRate =
            ((item.close_price - baselinePrice) / baselinePrice) * 100
          return {
            originalDate: item.date,
            date: formatChartAxisDate(item.date),
            price: item.close_price,
            changeRate: changeRate,
          }
        })
        setChartData(formatted)
      } else {
        const formatted = weekdayData.map((item: any) => ({
          originalDate: item.date,
          date: formatChartAxisDate(item.date),
          price: item.close_price,
        }))
        setChartData(formatted)
      }

      setError(null)
    } catch (err: any) {
      setError(err.message || "加载图表数据失败")
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className={`p-8 text-center ${className}`}>
        <p className="text-muted-foreground">加载图表数据中...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className={`p-8 text-center ${className}`}>
        <p className="text-destructive">{error}</p>
      </div>
    )
  }

  if (chartData.length === 0) {
    return (
      <div className={`p-8 text-center ${className}`}>
        <p className="text-muted-foreground">暂无图表数据</p>
      </div>
    )
  }

  const totalPoints = chartData.length
  const effectiveRange =
    range.endIndex <= 0
      ? { startIndex: Math.max(0, totalPoints - CHART_DEFAULT_VISIBLE_POINTS), endIndex: totalPoints }
      : range

  const handleBrushChange = (newStart: number, newEnd: number) => {
    setRange({ startIndex: newStart, endIndex: newEnd })
  }

  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault()
    const delta = e.deltaY > 0 ? 1 : -1
    const step = Math.max(1, Math.floor((effectiveRange.endIndex - effectiveRange.startIndex) * 0.1))
    setRange((prev) => {
      const start = prev.endIndex <= 0 ? effectiveRange.startIndex : prev.startIndex
      const end = prev.endIndex <= 0 ? effectiveRange.endIndex : prev.endIndex
      if (delta > 0) {
        const newStart = Math.min(start + step, end - 5)
        const newEnd = Math.max(end - step, start + 5)
        return { startIndex: newStart, endIndex: newEnd }
      }
      const newStart = Math.max(0, start - step)
      const newEnd = Math.min(totalPoints, end + step)
      return { startIndex: newStart, endIndex: newEnd }
    })
  }

  return (
    <div className={`w-full h-[400px] ${className}`} onWheel={handleWheel} style={{ overflow: "hidden" }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData} margin={{ top: 10, right: 20, left: 10, bottom: 80 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey="date"
            domain={[
              chartData[effectiveRange.startIndex]?.date ?? chartData[0]?.date,
              chartData[effectiveRange.endIndex - 1]?.date ?? chartData[chartData.length - 1]?.date,
            ]}
            allowDataOverflow
            interval="preserveStartEnd"
            tick={{ fontSize: 12 }}
          />
          <YAxis
            yAxisId="left"
            label={{
              value: showChangeRate ? "涨跌幅 (%)" : "价格 (元)",
              angle: -90,
              position: "insideLeft",
            }}
          />
          <Tooltip
            labelFormatter={(_, payload) => {
              const raw = (Array.isArray(payload) && payload[0]?.payload?.originalDate) as string | undefined
              return raw ? formatTooltipDate(raw) : ""
            }}
            formatter={(value: any, name: string) => {
              if (name === "changeRate") {
                return formatPercent(value)
              }
              return formatNumber(value)
            }}
          />
          <Legend />
          {showChangeRate && (asset.baseline_price ?? 0) > 0 ? (
            <Line
              yAxisId="left"
              type="monotone"
              dataKey="changeRate"
              stroke="#8884d8"
              name="涨跌幅"
              strokeWidth={2}
            />
          ) : (
            <Line
              yAxisId="left"
              type="monotone"
              dataKey="price"
              stroke="#8884d8"
              name="收盘价"
              strokeWidth={2}
            />
          )}
          <Brush
            dataKey="date"
            height={28}
            stroke="#8884d8"
            startIndex={effectiveRange.startIndex}
            endIndex={effectiveRange.endIndex}
            onChange={(newIndex) => {
              const start = newIndex?.startIndex ?? 0
              const end = newIndex?.endIndex ?? totalPoints
              handleBrushChange(start, end)
            }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
