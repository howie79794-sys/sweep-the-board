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
  Brush,
} from "recharts"
import { formatPercent, formatNumber, formatChartAxisDate, formatTooltipDate, CHART_DEFAULT_VISIBLE_POINTS, cn } from "@/lib/utils"
import { UserAvatar } from "@/components/UserAvatar"
import { type PKPoolChartAsset, type User } from "@/types"
import { useState, useEffect } from "react"

interface CumulativeReturnChartProps {
  assets: PKPoolChartAsset[]
  showChangeRate?: boolean
  className?: string
}

interface ChartDataPoint {
  date: string
  originalDate: string
  [key: string]: string | number | undefined | null
}

// 高区分度配色：深色系、白底对比度高，避免默认浅黄等低对比色
const LINE_COLORS = [
  "#2563eb", // 蓝
  "#dc2626", // 红
  "#059669", // 绿
  "#9333ea", // 紫
  "#ea580c", // 橙
  "#0891b2", // 青
  "#db2777", // 玫红
  "#ca8a04", // 深黄（可读）
]

// 曲线末端标签的最小纵向间距（px）
const END_LABEL_MIN_GAP = 18

export function CumulativeReturnChart({
  assets,
  showChangeRate = true,
  className,
}: CumulativeReturnChartProps) {
  const [selectedAssetCode, setSelectedAssetCode] = useState<string | null>(null)
  const [range, setRange] = useState({ startIndex: 0, endIndex: 0 })

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
      originalDate: dateStr,
      date: formatChartAxisDate(dateStr),
    }
  })

  const totalPoints = chartData.length
  const effectiveRange =
    range.endIndex <= 0
      ? { startIndex: Math.max(0, totalPoints - CHART_DEFAULT_VISIBLE_POINTS), endIndex: totalPoints }
      : range

  useEffect(() => {
    if (totalPoints === 0) return
    setRange((prev) => {
      if (prev.endIndex > totalPoints || prev.startIndex >= totalPoints) {
        return {
          startIndex: Math.max(0, totalPoints - CHART_DEFAULT_VISIBLE_POINTS),
          endIndex: totalPoints,
        }
      }
      return prev
    })
  }, [totalPoints])

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

  if (chartData.length === 0) {
    return (
      <div className={cn("p-8 text-center", className)}>
        <p className="text-muted-foreground">暂无图表数据</p>
      </div>
    )
  }

  const handleLegendClick = (e: any) => {
    const clickedCode = e.dataKey || e.value
    if (selectedAssetCode === clickedCode) {
      setSelectedAssetCode(null)
    } else {
      setSelectedAssetCode(clickedCode)
    }
  }

  // 可视窗口内的数据点数（label 只收到窗口内的点，末点 index = visibleCount - 1）
  const visibleCount = Math.max(1, effectiveRange.endIndex - effectiveRange.startIndex)

  // 每次渲染重置末端标签占位（父组件每次 render 创建新数组，标签闭包捕获本回合的数组）
  const endLabelSlots: { y: number; code: string }[] = []

  // 为每条曲线生成末端标签渲染函数：
  // - 仅在「可视窗口最后一个数据点」渲染（label 收到的 index 为窗口内相对索引）
  // - 防重叠：与已占用的 y 槽位间距小于 END_LABEL_MIN_GAP 时，按相对方位向上/向下推开，保持纵向顺序与曲线终点一致
  // - 返回空 <g/> 而非 null（recharts 类型要求 ReactElement）
  const makeEndLabelContent = (assetCode: string, assetName: string, color: string) => {
    let settledY: number | null = null
    return (props: any) => {
      const vb = props?.viewBox
      if (
        !vb ||
        props.index !== visibleCount - 1 ||
        props.value == null
      ) {
        return <g key={`end-label-${assetCode}`} />
      }
      // 首次有效解算后锁定 y（recharts 同参数内部重渲染时直接复用，避免重复占位）；
      // 几何未就绪（测量期退化坐标）时返回空，等下一轮再解算
      let finalY: number
      if (settledY != null) {
        finalY = settledY
      } else {
        if (!Number.isFinite(vb.y) || vb.y <= 0 || vb.y >= 400) {
          return <g key={`end-label-${assetCode}`} />
        }
        let y = vb.y
        for (let iter = 0; iter < 3; iter++) {
          for (const slot of endLabelSlots) {
            if (Math.abs(y - slot.y) < END_LABEL_MIN_GAP) {
              y = y <= slot.y ? slot.y - END_LABEL_MIN_GAP : slot.y + END_LABEL_MIN_GAP
            }
          }
        }
        endLabelSlots.push({ y, code: assetCode })
        settledY = y
        finalY = y
      }
      return (
        <text
          key={`end-label-${assetCode}`}
          x={vb.x + 6}
          y={finalY}
          textAnchor="start"
          dominantBaseline="middle"
          fill={color}
          fontSize={12}
          fontWeight={600}
          stroke="#ffffff"
          strokeWidth={3}
          paintOrder="stroke"
        >
          {assetName}
        </text>
      )
    }
  }

  const endLabelContents = assets.map((asset, i) =>
    makeEndLabelContent(asset.code, asset.name, LINE_COLORS[i % LINE_COLORS.length])
  )

  // 图例卡片：取全量数据的最后一个非空值作为「最终收益/最新价」
  const getFinalValue = (asset: PKPoolChartAsset): number | null => {
    for (let i = asset.data.length - 1; i >= 0; i--) {
      const p = asset.data[i]
      const v = showChangeRate ? p.change_rate : p.close_price
      if (v != null) return v as number
    }
    return null
  }

  return (
    <div className={cn("w-full", className)}>
      <div className="mb-4">
        <h3 className="text-lg font-semibold">
          {showChangeRate ? "累计收益率对比曲线" : "收盘价对比曲线"}
        </h3>
      </div>
      <div className="w-full h-[400px]" onWheel={handleWheel} style={{ overflow: "hidden" }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 10, right: 90, left: 10, bottom: 80 }}>
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
              label={{
                value: showChangeRate ? "累计收益率 (%)" : "收盘价 (元)",
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
                  <div className="flex flex-wrap items-center justify-center gap-2 mt-4">
                    {payload.map((entry: any, index: number) => {
                      const asset = assets.find((a) => a.code === entry.dataKey)
                      const user = asset?.user
                      const finalValue = asset ? getFinalValue(asset) : null
                      const isDimmed = selectedAssetCode !== null && selectedAssetCode !== entry.dataKey
                      return (
                        <div
                          key={`legend-${index}`}
                          onClick={() => handleLegendClick({ dataKey: entry.dataKey })}
                          className={cn(
                            "flex items-center gap-2 px-2.5 py-1.5 rounded-lg border border-border/60 cursor-pointer transition-opacity hover:bg-muted/50",
                            isDimmed && "opacity-40"
                          )}
                        >
                          <span
                            className="h-2.5 w-2.5 rounded-sm shrink-0"
                            style={{ backgroundColor: entry.color }}
                          />
                          {user && <UserAvatar user={user as User} size="sm" />}
                          <span className="text-sm font-medium text-foreground">
                            {asset?.name ?? entry.dataKey}
                          </span>
                          <span className="text-xs text-muted-foreground">{entry.dataKey}</span>
                          {finalValue != null && (
                            <span
                              className={cn(
                                "text-sm font-semibold tabular-nums",
                                showChangeRate
                                  ? finalValue >= 0
                                    ? "text-red-600"
                                    : "text-green-600"
                                  : "text-foreground"
                              )}
                            >
                              {showChangeRate ? formatPercent(finalValue) : formatNumber(finalValue)}
                            </span>
                          )}
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
                  stroke={LINE_COLORS[index % LINE_COLORS.length]}
                  name={asset.name || asset.code}
                  strokeWidth={strokeWidth}
                  strokeOpacity={opacity}
                  dot={false}
                  connectNulls
                  isAnimationActive={false}
                  label={{ content: endLabelContents[index] }}
                />
              )
            })}
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
    </div>
  )
}
