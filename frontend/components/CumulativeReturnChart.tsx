"use client"

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
import { formatPercent, formatNumber } from "@/lib/utils"
import { cn } from "@/lib/utils"
import { UserAvatar } from "@/components/UserAvatar"
import { type PKPoolChartAsset, type User } from "@/types"
import { useState } from "react"

interface CumulativeReturnChartProps {
  assets: PKPoolChartAsset[]
  showChangeRate?: boolean
  className?: string
}

interface ChartDataPoint {
  date: string
  [key: string]: string | number | undefined | null
}

export function CumulativeReturnChart({
  assets,
  showChangeRate = true,
  className,
}: CumulativeReturnChartProps) {
  const [selectedAssetCode, setSelectedAssetCode] = useState<string | null>(null)

  if (!assets || assets.length === 0) {
    return (
      <div className={cn("p-8 text-center", className)}>
        <p className="text-muted-foreground">暂无图表数据</p>
      </div>
    )
  }

  const isWeekday = (dateStr: string): boolean => {
    const date = new Date(dateStr)
    const day = date.getDay()
    return day >= 1 && day <= 5
  }

  const dateMap = new Map<string, Record<string, string | number | null>>()

  assets.forEach((asset) => {
    asset.data.forEach((point) => {
      const date = point.date
      if (!isWeekday(date)) {
        return
      }
      if (!dateMap.has(date)) {
        dateMap.set(date, { date })
      }
      const dateData = dateMap.get(date)!
      if (showChangeRate) {
        dateData[asset.code] = point.change_rate ?? null
      } else {
        dateData[asset.code] = point.close_price
      }
    })
  })

  const chartDataArray = Array.from(dateMap.values()).sort(
    (a, b) => {
      const dateA = typeof a.date === "string" ? a.date : ""
      const dateB = typeof b.date === "string" ? b.date : ""
      return new Date(dateA).getTime() - new Date(dateB).getTime()
    }
  )

  const chartData: ChartDataPoint[] = chartDataArray.map((item) => {
    const dateStr = typeof item.date === "string" ? item.date : ""
    return {
      ...item,
      date: new Date(dateStr).toLocaleDateString("zh-CN", {
        month: "short",
        day: "numeric",
      }),
    }
  })

  if (chartData.length === 0) {
    return (
      <div className={cn("p-8 text-center", className)}>
        <p className="text-muted-foreground">暂无图表数据</p>
      </div>
    )
  }

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

  const handleLegendClick = (e: any) => {
    const clickedCode = e.dataKey || e.value
    if (selectedAssetCode === clickedCode) {
      setSelectedAssetCode(null)
    } else {
      setSelectedAssetCode(clickedCode)
    }
  }

  return (
    <div className={cn("w-full", className)}>
      <div className="mb-4">
        <h3 className="text-lg font-semibold">
          {showChangeRate ? "累计收益率对比曲线" : "收盘价对比曲线"}
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
              formatter={(value: any, name: string) => {
                const numValue = typeof value === "number" ? value : parseFloat(String(value))
                if (Number.isNaN(numValue)) return value
                return showChangeRate ? formatPercent(numValue) : formatNumber(numValue)
              }}
            />
            <Legend
              onClick={handleLegendClick}
              wrapperStyle={{ cursor: "pointer" }}
              content={(props) => {
                const { payload } = props
                if (!payload || !Array.isArray(payload)) return null
                return (
                  <div className="flex flex-wrap items-center justify-center gap-4 mt-4">
                    {payload.map((entry: any, index: number) => {
                      const asset = assets.find((a) => a.code === entry.dataKey)
                      const user = asset?.user
                      return (
                        <div
                          key={`legend-${index}`}
                          onClick={() => handleLegendClick({ dataKey: entry.dataKey })}
                          className="flex items-center gap-2 cursor-pointer hover:opacity-80 transition-opacity"
                          style={{ color: entry.color }}
                        >
                          {user && <UserAvatar user={user as User} size="sm" />}
                          <span className="text-sm font-medium">{entry.dataKey}</span>
                        </div>
                      )
                    })}
                  </div>
                )
              }}
            />
            {assets.map((asset, index) => {
              const isSelected = selectedAssetCode === null || selectedAssetCode === asset.code
              const opacity = selectedAssetCode === null ? 1 : (isSelected ? 1 : 0.3)
              const strokeWidth = isSelected ? 3 : 2
              return (
                <Line
                  key={asset.code}
                  type="monotone"
                  dataKey={asset.code}
                  stroke={colors[index % colors.length]}
                  name={asset.code}
                  strokeWidth={strokeWidth}
                  strokeOpacity={opacity}
                  dot={false}
                  connectNulls
                />
              )
            })}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
