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
import { formatPercent, formatNumber } from "@/lib/utils"
import { cn } from "@/lib/utils"

interface AllAssetsChartProps {
  showChangeRate?: boolean
  className?: string
}

interface ChartDataPoint {
  date: string
  [key: string]: string | number | undefined
}

interface AssetChartData {
  asset_id: number
  code: string
  name: string
  baseline_price?: number
  baseline_date?: string
  data: Array<{
    date: string
    close_price: number
    change_rate?: number
  }>
}

export function AllAssetsChart({
  showChangeRate = false,
  className,
}: AllAssetsChartProps) {
  const [chartData, setChartData] = useState<ChartDataPoint[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [assets, setAssets] = useState<AssetChartData[]>([])

  useEffect(() => {
    loadChartData()
  }, [showChangeRate])

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
      const dateMap = new Map<string, Record<string, any>>()

      data.forEach((asset) => {
        asset.data.forEach((point) => {
          const date = point.date
          if (!dateMap.has(date)) {
            dateMap.set(date, { date })
          }
          const dateData = dateMap.get(date)!

          if (showChangeRate) {
            // 显示收益率
            dateData[asset.code] = point.change_rate ?? null
          } else {
            // 显示收盘价
            dateData[asset.code] = point.close_price
          }
        })
      })

      // 转换为数组并按日期排序
      const chartDataArray = Array.from(dateMap.values()).sort(
        (a, b) => new Date(a.date).getTime() - new Date(b.date).getTime()
      )

      // 格式化日期
      const formattedData = chartDataArray.map((item) => ({
        ...item,
        date: new Date(item.date).toLocaleDateString("zh-CN", {
          month: "short",
          day: "numeric",
        }),
      }))

      setChartData(formattedData)
      setError(null)
    } catch (err: any) {
      setError(err.message || "加载图表数据失败")
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
          {showChangeRate
            ? "累计收益率趋势追踪图 (自基准日以来)"
            : "收盘价走势图"}
        </h3>
      </div>
      <div className="w-full h-[400px]">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis
              label={{
                value: showChangeRate ? "累计收益率 (%)" : "收盘价 (元)",
                angle: -90,
                position: "insideLeft",
              }}
            />
            <Tooltip
              formatter={(value: number, name: string) => {
                if (showChangeRate) {
                  return formatPercent(value)
                }
                return formatNumber(value)
              }}
            />
            <Legend />
            {assets.map((asset, index) => (
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
