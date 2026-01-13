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
} from "recharts"
import { dataAPI } from "@/lib/api"
import { formatNumber } from "@/lib/utils"
import { cn } from "@/lib/utils"

interface PERatioChartProps {
  className?: string
}

interface ChartDataPoint {
  date: string
  [key: string]: string | number | null | undefined
}

interface DataPoint {
  date: string
  close_price: number
  change_rate?: number | null
  pe_ratio?: number | null
  pb_ratio?: number | null
}

interface AssetChartData {
  asset_id: number
  code: string
  name: string
  baseline_price?: number
  baseline_date?: string
  data: DataPoint[]
}

export function PERatioChart({
  className,
}: PERatioChartProps) {
  const [chartData, setChartData] = useState<ChartDataPoint[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [assets, setAssets] = useState<AssetChartData[]>([])

  useEffect(() => {
    loadChartData()
  }, [])

  const loadChartData = async () => {
    try {
      setLoading(true)
      const data = await dataAPI.getAllAssetsChartData({
        start_date: "2026-01-05",
      })

      if (!data || data.length === 0) {
        setError("暂无数据")
        return
      }

      setAssets(data)

      // 将所有资产的数据合并到同一个日期轴上
      const dateMap = new Map<string, Record<string, string | number | null>>()

      data.forEach((asset: AssetChartData) => {
        asset.data.forEach((point: DataPoint) => {
          const date = point.date
          if (!dateMap.has(date)) {
            dateMap.set(date, { date })
          }
          const dateData = dateMap.get(date)!

          // 显示 PE 比率
          dateData[asset.code] = point.pe_ratio ?? null
        })
      })

      // 转换为数组并按日期排序
      const chartDataArray = Array.from(dateMap.values()).sort(
        (a: Record<string, string | number | null>, b: Record<string, string | number | null>) => {
          const dateA = typeof a.date === 'string' ? a.date : ''
          const dateB = typeof b.date === 'string' ? b.date : ''
          return new Date(dateA).getTime() - new Date(dateB).getTime()
        }
      )

      // 格式化日期
      const formattedData = chartDataArray.map((item: Record<string, string | number | null>) => {
        const dateStr = typeof item.date === 'string' ? item.date : ''
        return {
          ...item,
          date: new Date(dateStr).toLocaleDateString("zh-CN", {
            month: "short",
            day: "numeric",
          }),
        }
      })

      setChartData(formattedData)
      setError(null)
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : "加载图表数据失败"
      setError(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className={cn("p-8 text-center", className)}>
        <p className="text-muted-foreground">加载图表数据中...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className={cn("p-8 text-center", className)}>
        <p className="text-destructive">{error}</p>
      </div>
    )
  }

  if (chartData.length === 0) {
    return (
      <div className={cn("p-8 text-center", className)}>
        <p className="text-muted-foreground">暂无图表数据</p>
      </div>
    )
  }

  // 生成颜色数组
  const colors = [
    "#8884d8",
    "#82ca9d",
    "#ffc658",
    "#ff7300",
    "#0088fe",
    "#00c49f",
    "#ffbb28",
    "#ff8042",
  ]

  return (
    <div className={cn("w-full", className)}>
      <div className="mb-4">
        <h3 className="text-lg font-semibold">
          市盈率 (P/E) 趋势图
        </h3>
      </div>
      <div className="w-full h-[400px]">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis
              label={{
                value: "市盈率 (P/E)",
                angle: -90,
                position: "insideLeft",
              }}
            />
            <Tooltip
              formatter={(value: number | string, name: string) => {
                const numValue = typeof value === 'number' ? value : parseFloat(String(value))
                if (isNaN(numValue)) return value
                return formatNumber(numValue)
              }}
            />
            <Legend />
            {assets.map((asset: AssetChartData, index: number) => (
              <Line
                key={asset.code}
                type="monotone"
                dataKey={asset.code}
                stroke={colors[index % colors.length]}
                name={asset.code}
                strokeWidth={2}
                dot={false}
                connectNulls
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
