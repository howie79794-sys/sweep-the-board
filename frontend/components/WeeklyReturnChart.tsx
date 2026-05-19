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
  /** 受控的选中资产代码（与左侧榜单、年度图联动） */
  selectedAssetCode?: string | null
  /** 图例点击时回调，用于同步全局选中状态 */
  onSelectedAssetCodeChange?: (code: string | null) => void
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

export function WeeklyReturnChart({
  className,
  selectedAssetCode: selectedAssetCodeProp,
  onSelectedAssetCodeChange,
}: WeeklyReturnChartProps) {
  const [chartData, setChartData] = useState<ChartDataPoint[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [assets, setAssets] = useState<AssetWeeklyData[]>([])
  const [internalSelected, setInternalSelected] = useState<string | null>(null)
  const selectedAssetCode = selectedAssetCodeProp ?? internalSelected

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
        (a, b) => {
          const ad = String(a.date)
          const bd = String(b.date)
          if (ad === "基准") return -1
          if (bd === "基准") return 1
          return new Date(ad).getTime() - new Date(bd).getTime()
        }
      ) as Record<string, string | number | null>[]

      const formattedData = chartDataArray.map((item) => {
        const dateStr = String(item.date)
        const isBaseline = dateStr === "基准"
        return {
          ...item,
          originalDate: dateStr,
          date: isBaseline ? "" : formatChartAxisDate(dateStr),
        }
      })

      setChartData(formattedData)
      setError(null)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "加载周收益数据失败")
    } finally {
      setLoading(false)
    }
  }

  const handleLegendClick = (e: any) => {
    const clickedCode = e.dataKey || e.value
    const next = selectedAssetCode === clickedCode ? null : clickedCode
    if (onSelectedAssetCodeChange) {
      onSelectedAssetCodeChange(next)
    } else {
      setInternalSelected(next)
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
              domain={[(dataMin: number) => Math.min(0, dataMin - 1), (dataMax: number) => Math.max(0, dataMax + 1)]}
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
                if (!raw || raw === "基准") return "基准 (上周五)"
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
                  // 不 connectNulls：未来日期/缺数据的点保持断开
                  // 让曲线在最后一个有数据的点优雅截断
                  connectNulls={false}
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
