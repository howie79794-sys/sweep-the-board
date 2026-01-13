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
import { type Asset } from "@/types"

interface AssetChartProps {
  asset: Asset
  showChangeRate?: boolean
  className?: string
}

interface ChartDataPoint {
  date: string
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

  useEffect(() => {
    loadChartData()
  }, [asset.id])

  const loadChartData = async () => {
    try {
      setLoading(true)
      const data = await dataAPI.getAssetData(asset.id, {
        start_date: asset.start_date,
        end_date: asset.end_date,
      })

      const baselinePrice = asset.baseline_price ?? 0

      if (baselinePrice > 0 && showChangeRate) {
        // 计算涨跌幅
        const formatted = data.map((item: any) => {
          const changeRate =
            ((item.close_price - baselinePrice) / baselinePrice) * 100
          return {
            date: new Date(item.date).toLocaleDateString("zh-CN", {
              month: "short",
              day: "numeric",
            }),
            price: item.close_price,
            changeRate: changeRate,
          }
        })
        setChartData(formatted)
      } else {
        // 如果没有基准价格或不需要显示涨跌幅，只显示价格
        const formatted = data.map((item: any) => ({
          date: new Date(item.date).toLocaleDateString("zh-CN", {
            month: "short",
            day: "numeric",
          }),
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

  return (
    <div className={`w-full h-[400px] ${className}`}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" />
          <YAxis
            yAxisId="left"
            label={{
              value: showChangeRate ? "涨跌幅 (%)" : "价格 (元)",
              angle: -90,
              position: "insideLeft",
            }}
          />
          <Tooltip
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
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
