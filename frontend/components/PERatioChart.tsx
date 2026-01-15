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
import { UserAvatar } from "@/components/UserAvatar"
import { type User } from "@/types"

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
  user?: {
    id: number
    name: string
    avatar_url?: string | null
  }
  data: DataPoint[]
}

export function PERatioChart({
  className,
}: PERatioChartProps) {
  const [chartData, setChartData] = useState<ChartDataPoint[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [assets, setAssets] = useState<AssetChartData[]>([])
  const [selectedAssetCode, setSelectedAssetCode] = useState<string | null>(null)

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

      // 辅助函数：判断是否为工作日（周一到周五）
      const isWeekday = (dateStr: string): boolean => {
        const date = new Date(dateStr)
        const day = date.getDay() // 0 = 周日, 6 = 周六
        return day >= 1 && day <= 5 // 周一到周五
      }

      // 将所有资产的数据合并到同一个日期轴上，只包含工作日
      const dateMap = new Map<string, Record<string, string | number | null>>()
      // 存储每个资产代码的最近有效值，用于兜底
      const lastValidValues = new Map<string, Map<string, number>>()

      data.forEach((asset: AssetChartData) => {
        if (!lastValidValues.has(asset.code)) {
          lastValidValues.set(asset.code, new Map())
        }
        const assetLastValues = lastValidValues.get(asset.code)!

        asset.data.forEach((point: DataPoint) => {
          const date = point.date
          // 跳过周末（非工作日）
          if (!isWeekday(date)) {
            return
          }
          
          if (!dateMap.has(date)) {
            dateMap.set(date, { date, originalDate: date })
          }
          const dateData = dateMap.get(date)!

          // 显示 PE 比率
          const peValue = point.pe_ratio ?? null
          dateData[asset.code] = peValue
          
          // 更新最近有效值（用于兜底）
          if (peValue !== null && peValue !== undefined && peValue !== 0) {
            assetLastValues.set('pe_ratio', peValue as number)
          }
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

      // 格式化日期，保留原始日期用于 Tooltip 兜底逻辑
      const formattedData = chartDataArray.map((item: Record<string, string | number | null>) => {
        const dateStr = typeof item.date === 'string' ? item.date : ''
        const originalDate = item.originalDate || dateStr
        return {
          ...item,
          originalDate: originalDate, // 保留原始日期
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

  // 处理图例点击事件
  const handleLegendClick = (e: any) => {
    const clickedCode = e.dataKey || e.value
    if (selectedAssetCode === clickedCode) {
      // 取消选中
      setSelectedAssetCode(null)
    } else {
      // 选中新的股票
      setSelectedAssetCode(clickedCode)
    }
  }

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
              formatter={(value: any, name: string, props: any) => {
                // 处理 null 或 undefined
                if (value === null || value === undefined) {
                  // 尝试查找最近的有效值
                  const asset = assets.find(a => a.code === name)
                  if (asset) {
                    // 在当前数据点之前查找最近的有效值
                    const currentDate = props.payload?.originalDate || props.payload?.date
                    if (currentDate) {
                      const currentDateObj = new Date(currentDate)
                      // 向前查找最近的有效值
                      for (let i = chartData.length - 1; i >= 0; i--) {
                        const point = chartData[i]
                        const pointDate = new Date(point.originalDate || point.date)
                        if (pointDate < currentDateObj && point[name] !== null && point[name] !== undefined && point[name] !== 0) {
                          return `${formatNumber(point[name] as number)} (最近有效值)`
                        }
                      }
                    }
                  }
                  return "非交易日"
                }
                // 转换为数字
                const numValue = typeof value === 'number' ? value : parseFloat(String(value))
                // 处理 NaN
                if (isNaN(numValue)) return "N/A"
                // 检查是否为 0（可能是非交易日填充的值）
                if (numValue === 0) {
                  // 检查是否是周末
                  const currentDate = props.payload?.originalDate || props.payload?.date
                  if (currentDate) {
                    const dateObj = new Date(currentDate)
                    const weekday = dateObj.getDay()
                    if (weekday === 0 || weekday === 6) {
                      // 周末，尝试查找最近的有效值
                      const asset = assets.find(a => a.code === name)
                      if (asset) {
                        for (let i = chartData.length - 1; i >= 0; i--) {
                          const point = chartData[i]
                          const pointDate = new Date(point.originalDate || point.date)
                          if (pointDate < dateObj && point[name] !== null && point[name] !== undefined && point[name] !== 0) {
                            return `${formatNumber(point[name] as number)} (最近有效值)`
                          }
                        }
                      }
                      return "非交易日"
                    }
                  }
                }
                // 正常显示数值
                return formatNumber(numValue)
              }}
            />
            <Legend 
              onClick={handleLegendClick}
              wrapperStyle={{ cursor: 'pointer' }}
              content={(props) => {
                const { payload } = props
                if (!payload || !Array.isArray(payload)) return null
                
                return (
                  <div className="flex flex-wrap items-center justify-center gap-4 mt-4">
                    {payload.map((entry: any, index: number) => {
                      const asset = assets.find((a: AssetChartData) => a.code === entry.dataKey)
                      const user = asset?.user
                      
                      return (
                        <div
                          key={`legend-${index}`}
                          onClick={() => handleLegendClick({ dataKey: entry.dataKey })}
                          className="flex items-center gap-2 cursor-pointer hover:opacity-80 transition-opacity"
                          style={{ color: entry.color }}
                        >
                          {user && (
                            <UserAvatar
                              user={user as User}
                              size="sm"
                            />
                          )}
                          <span className="text-sm font-medium">{entry.dataKey}</span>
                        </div>
                      )
                    })}
                  </div>
                )
              }}
            />
            {assets.map((asset: AssetChartData, index: number) => {
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
