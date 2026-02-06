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
import { formatPercent, formatChartAxisDate, formatTooltipDate, cn } from "@/lib/utils"
import { UserAvatar } from "@/components/UserAvatar"
import { type User } from "@/types"

interface WeeklyReturnChartProps {
  className?: string
}

interface DataPoint {
  date: string
  change_rate: number
}

interface AssetWeeklyData {
  asset_id: number
  code: string
  name: string
  user?: {
    id: number
    name: string
    avatar_url?: string | null
  }
  data: DataPoint[]
}

interface ChartDataPoint {
  date: string
  originalDate: string
  [key: string]: string | number | undefined
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

export function WeeklyReturnChart({ className }: WeeklyReturnChartProps) {
  const [chartData, setChartData] = useState<ChartDataPoint[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [assets, setAssets] = useState<AssetWeeklyData[]>([])
  const [selectedAssetCode, setSelectedAssetCode] = useState<string | null>(null)

  useEffect(() => {
    loadChartData()
  }, [])

  const loadChartData = async () => {
    try {
      setLoading(true)
      const data = await dataAPI.getWeeklyChartData()
      if (!data || data.length === 0) {
        setError("暂无数据")
        return
      }
      setAssets(data)

      const dateMap = new Map<string, Record<string, string | number | null>>()
      data.forEach((asset: AssetWeeklyData) => {
        asset.data.forEach((point: DataPoint) => {
          const date = point.date
          if (!dateMap.has(date)) {
            dateMap.set(date, { date })
          }
          const dateData = dateMap.get(date)!
          dateData[asset.code] = point.change_rate
        })
      })

      const chartDataArray = Array.from(dateMap.values()).sort(
        (a, b) =>
          new Date(String(a.date)).getTime() - new Date(String(b.date)).getTime()
      ) as Record<string, string | number | null>[]

      const formattedData = chartDataArray.map((item) => {
        const dateStr = String(item.date)
        return {
          ...item,
          originalDate: dateStr,
          date: formatChartAxisDate(dateStr),
        }
      })

      // 前置 0 点：所有收益率从 0 开始，0 点不展示日期（不算横轴第一格）
      const zeroPoint: ChartDataPoint = {
        date: "",
        originalDate: "",
      }
      assets.forEach((a: AssetWeeklyData) => {
        zeroPoint[a.code] = 0
      })
      setChartData([zeroPoint, ...formattedData])
      setError(null)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "加载周收益数据失败")
    } finally {
      setLoading(false)
    }
  }

  const handleLegendClick = (e: any) => {
    const clickedCode = e.dataKey || e.value
    if (selectedAssetCode === clickedCode) {
      setSelectedAssetCode(null)
    } else {
      setSelectedAssetCode(clickedCode)
    }
  }

  if (loading) {
    return (
      <div className={cn("p-8 text-center", className)}>
        <p className="text-muted-foreground">加载周收益数据中...</p>
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
        <p className="text-muted-foreground">暂无周收益数据</p>
      </div>
    )
  }

  const totalPoints = chartData.length
  const brushStart = 0
  const brushEnd = Math.max(0, totalPoints - 1)

  return (
    <div className={cn("w-full", className)}>
      <div className="mb-4">
        <h3 className="text-lg font-semibold">周收益曲线（以自然周为维度）</h3>
      </div>
      <div className="w-full h-[400px]" style={{ overflow: "hidden" }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={chartData}
            margin={{ top: 10, right: 20, left: 10, bottom: 80 }}
          >
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 12 }}
              interval={0}
              tickFormatter={(value, index) => (index === 0 ? "" : value)}
            />
            <YAxis
              scale="linear"
              tickFormatter={(v) => `${v}%`}
              label={{
                value: "周收益率 (%)",
                angle: -90,
                position: "insideLeft",
              }}
            />
            <Tooltip
              labelFormatter={(_, payload) => {
                const raw = (Array.isArray(payload) && payload[0]?.payload?.originalDate) as string | undefined
                if (!raw) return "基准 (上周五)"
                return formatTooltipDate(raw)
              }}
              formatter={(value: any) => {
                const numValue = typeof value === "number" ? value : parseFloat(String(value))
                if (isNaN(numValue)) return value
                return formatPercent(numValue)
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
                          {user && (
                            <UserAvatar user={user as User} size="sm" />
                          )}
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
              const opacity = selectedAssetCode === null ? 1 : isSelected ? 1 : 0.3
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
                  dot={{ r: 3 }}
                  connectNulls
                />
              )
            })}
            <Brush
              dataKey="date"
              height={28}
              stroke="#8884d8"
              startIndex={brushStart}
              endIndex={brushEnd}
              tickFormatter={(value, index) => (index === 0 ? "" : value)}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
