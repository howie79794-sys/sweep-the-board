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

interface DataPoint {
  date: string
  close_price: number
  change_rate?: number | null
}

interface AssetChartData {
  asset_id: number
  code: string
  name: string
  baseline_price?: number
  baseline_date?: string
  data: DataPoint[]
}

export function AllAssetsChart({
  showChangeRate = false,
  className,
}: AllAssetsChartProps) {
  const [chartData, setChartData] = useState<ChartDataPoint[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [assets, setAssets] = useState<AssetChartData[]>([])
  const [selectedAssetCode, setSelectedAssetCode] = useState<string | null>(null)

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

      // 辅助函数：判断是否为工作日（周一到周五）
      const isWeekday = (dateStr: string): boolean => {
        const date = new Date(dateStr)
        const day = date.getDay() // 0 = 周日, 6 = 周六
        return day >= 1 && day <= 5 // 周一到周五
      }

      // 将所有资产的数据合并到同一个日期轴上，只包含工作日
      const dateMap = new Map<string, Record<string, string | number | null>>()

      data.forEach((asset: AssetChartData) => {
        asset.data.forEach((point: DataPoint) => {
          const date = point.date
          // 跳过周末（非工作日）
          if (!isWeekday(date)) {
            return
          }
          
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

  // 计算对数坐标的 domain（仅在显示收盘价时使用）
  const getLogDomain = () => {
    if (showChangeRate) return undefined
    
    // 从图表数据中找出最小和最大价格
    let minPrice = Infinity
    let maxPrice = -Infinity
    
    chartData.forEach((point) => {
      assets.forEach((asset) => {
        const price = point[asset.code]
        if (typeof price === 'number' && price > 0) {
          minPrice = Math.min(minPrice, price)
          maxPrice = Math.max(maxPrice, price)
        }
      })
    })
    
    // 如果没有有效数据，使用默认范围
    if (minPrice === Infinity || maxPrice === -Infinity) {
      return [0.1, 200]
    }
    
    // 设置合适的 domain，确保最小值至少为 0.1，最大值向上取整
    const minDomain = Math.max(0.1, Math.floor(minPrice * 0.9 * 10) / 10)
    const maxDomain = Math.ceil(maxPrice * 1.1)
    
    return [minDomain, maxDomain]
  }

  // 对数坐标的刻度格式化函数
  const formatLogTick = (value: number) => {
    if (value < 1) {
      return value.toFixed(1)
    } else if (value < 10) {
      return value.toFixed(1)
    } else {
      return Math.round(value).toString()
    }
  }

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
          {showChangeRate
            ? "累计收益率趋势追踪图 (自基准日以来)"
            : "股价对数趋势分析图 (Log-Scale)"}
        </h3>
      </div>
      <div className="w-full h-[400px]">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis
              scale={showChangeRate ? "linear" : "log"}
              domain={showChangeRate ? undefined : getLogDomain()}
              tickFormatter={showChangeRate ? undefined : formatLogTick}
              label={{
                value: showChangeRate ? "累计收益率 (%)" : "收盘价 (元)",
                angle: -90,
                position: "insideLeft",
              }}
            />
            <Tooltip
              formatter={(value: any, name: string) => {
                const numValue = typeof value === 'number' ? value : parseFloat(String(value))
                if (isNaN(numValue)) return value
                if (showChangeRate) {
                  return formatPercent(numValue)
                }
                return formatNumber(numValue)
              }}
            />
            <Legend 
              onClick={handleLegendClick}
              wrapperStyle={{ cursor: 'pointer' }}
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
