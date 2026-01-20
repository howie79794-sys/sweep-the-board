"use client"

import { useState, useEffect } from "react"
import { dataAPI } from "@/lib/api"
import { formatPercent, formatNumber } from "@/lib/utils"
import { cn } from "@/lib/utils"
import { UserAvatar } from "@/components/UserAvatar"
import { StabilityTooltip } from "@/components/StabilityTooltip"

interface SnapshotData {
  asset_id: number
  code: string
  name: string
  user: {
    id: number
    name: string
    avatar_url?: string | null
  }
  baseline_price: number | null
  baseline_date: string
  latest_date: string
  latest_close_price: number | null
  yesterday_close_price: number | null
  daily_change_rate: number | null
  latest_market_cap: number | null
  eps_forecast: number | null
  change_rate: number | null
  pe_ratio: number | null
  pb_ratio: number | null
  baseline_pe_ratio: number | null
  stability_score: number | null
  annual_volatility: number | null
  daily_returns: number[] | null
}

type SortField = "baseline_price" | "latest_close_price" | "market_cap" | "eps_forecast" | "change_rate" | "daily_change_rate" | "stability_score" | null
type SortDirection = "asc" | "desc"

export function AssetSnapshotTable({ className }: { className?: string }) {
  const [data, setData] = useState<SnapshotData[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  // 默认按累计收益从高到低排序
  const [sortField, setSortField] = useState<SortField>("change_rate")
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc")

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      setLoading(true)
      const snapshotData = await dataAPI.getSnapshotData()
      setData(snapshotData)
      setError(null)
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : "加载数据失败"
      setError(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      // 切换排序方向
      setSortDirection(sortDirection === "asc" ? "desc" : "asc")
    } else {
      // 设置新的排序字段
      setSortField(field)
      setSortDirection("desc")
    }
  }

  const sortedData = [...data].sort((a, b) => {
    if (!sortField) return 0

    let aValue: number | null = null
    let bValue: number | null = null

    if (sortField === "baseline_price") {
      aValue = a.baseline_price
      bValue = b.baseline_price
    } else if (sortField === "latest_close_price") {
      aValue = a.latest_close_price
      bValue = b.latest_close_price
    } else if (sortField === "market_cap") {
      aValue = a.latest_market_cap
      bValue = b.latest_market_cap
    } else if (sortField === "eps_forecast") {
      aValue = a.eps_forecast
      bValue = b.eps_forecast
    } else if (sortField === "change_rate") {
      aValue = a.change_rate
      bValue = b.change_rate
    } else if (sortField === "daily_change_rate") {
      aValue = a.daily_change_rate
      bValue = b.daily_change_rate
    } else if (sortField === "stability_score") {
      aValue = a.stability_score
      bValue = b.stability_score
    }

    // 处理 null 值
    if (aValue === null && bValue === null) return 0
    if (aValue === null) return 1
    if (bValue === null) return -1

    const comparison = aValue - bValue
    return sortDirection === "asc" ? comparison : -comparison
  })

  if (loading) {
    return (
      <div className={cn("p-8 text-center", className)}>
        <p className="text-muted-foreground">加载数据中...</p>
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

  if (data.length === 0) {
    return (
      <div className={cn("p-8 text-center", className)}>
        <p className="text-muted-foreground">暂无数据</p>
      </div>
    )
  }

  // 格式化市值（亿元，保留两位小数）
  const formatMarketCap = (value: number | null | undefined): string => {
    if (value === null || value === undefined) return "--"
    return `${value.toFixed(2)} 亿元`
  }

  return (
    <div className={cn("w-full overflow-x-auto", className)}>
      <div className="mb-4">
        <h3 className="text-lg font-semibold">核心资产明细表</h3>
      </div>
      <table className="w-full border-collapse">
        <thead>
          <tr className="bg-gray-100">
            <th className="border p-2 text-left font-bold">关联用户</th>
            <th className="border p-2 text-left font-bold">股票代码</th>
            <th className="border p-2 text-left font-bold">名称</th>
            <th
              className="border p-2 text-left font-bold cursor-pointer hover:bg-gray-200"
              onClick={() => handleSort("baseline_price")}
            >
              基准价格
              {sortField === "baseline_price" && (
                <span className="ml-1">{sortDirection === "asc" ? "↑" : "↓"}</span>
              )}
            </th>
            <th
              className="border p-2 text-left font-bold cursor-pointer hover:bg-gray-200"
              onClick={() => handleSort("latest_close_price")}
            >
              最新收盘价
              {sortField === "latest_close_price" && (
                <span className="ml-1">{sortDirection === "asc" ? "↑" : "↓"}</span>
              )}
            </th>
            <th
              className="border p-2 text-left font-bold cursor-pointer hover:bg-gray-200"
              onClick={() => handleSort("daily_change_rate")}
            >
              涨跌幅
              {sortField === "daily_change_rate" && (
                <span className="ml-1">{sortDirection === "asc" ? "↑" : "↓"}</span>
              )}
            </th>
            <th
              className="border p-2 text-left font-bold cursor-pointer hover:bg-gray-200"
              onClick={() => handleSort("market_cap")}
            >
              最新总市值（亿元）
              {sortField === "market_cap" && (
                <span className="ml-1">{sortDirection === "asc" ? "↑" : "↓"}</span>
              )}
            </th>
            <th
              className="border p-2 text-left font-bold cursor-pointer hover:bg-gray-200"
              onClick={() => handleSort("eps_forecast")}
            >
              EPS 预测
              {sortField === "eps_forecast" && (
                <span className="ml-1">{sortDirection === "asc" ? "↑" : "↓"}</span>
              )}
            </th>
            <th
              className="border p-2 text-left font-bold cursor-pointer hover:bg-gray-200"
              onClick={() => handleSort("change_rate")}
            >
              累计收益
              {sortField === "change_rate" && (
                <span className="ml-1">{sortDirection === "asc" ? "↑" : "↓"}</span>
              )}
            </th>
            <th
              className="border p-2 text-left font-bold cursor-pointer hover:bg-gray-200"
              onClick={() => handleSort("stability_score")}
            >
              稳健度
              {sortField === "stability_score" && (
                <span className="ml-1">{sortDirection === "asc" ? "↑" : "↓"}</span>
              )}
            </th>
          </tr>
        </thead>
        <tbody>
          {sortedData.map((item) => {
            // 累计收益颜色：正数或0为红色，负数为绿色
            const changeRateColor = item.change_rate !== null && item.change_rate < 0 ? "text-green-600" : "text-red-600"
            
            // 涨跌幅颜色：正数为红色，负数为绿色
            const dailyChangeRateColor = item.daily_change_rate !== null && item.daily_change_rate < 0 ? "text-green-600" : "text-red-600"
            
            // 稳健度颜色：>80分绿色，60-80分黄色，<60分红色
            const stabilityColor = 
              item.stability_score !== null && item.stability_score > 80 
                ? "text-green-600" 
                : item.stability_score !== null && item.stability_score >= 60 
                ? "text-yellow-600" 
                : "text-red-600"
            
            return (
              <tr key={item.asset_id} className="hover:bg-gray-50">
                <td className="border p-2">
                  <div className="flex items-center gap-2">
                    <UserAvatar 
                      user={{
                        id: item.user.id,
                        name: item.user.name,
                        avatar_url: item.user.avatar_url || undefined,
                        created_at: "",
                        is_active: true
                      }} 
                      size="sm" 
                    />
                    <span>{item.user.name}</span>
                  </div>
                </td>
                <td className="border p-2">{item.code}</td>
                <td className="border p-2">{item.name}</td>
                <td className="border p-2">
                  {formatNumber(item.baseline_price)}
                </td>
                <td className="border p-2">
                  {formatNumber(item.latest_close_price)}
                </td>
                <td className={`border p-2 ${dailyChangeRateColor}`}>
                  {item.daily_change_rate !== null ? formatPercent(item.daily_change_rate) : "--"}
                </td>
                <td className="border p-2">
                  {formatMarketCap(item.latest_market_cap)}
                </td>
                <td className="border p-2">
                  {formatNumber(item.eps_forecast)}
                </td>
                <td className={`border p-2 ${changeRateColor}`}>
                  {formatPercent(item.change_rate)}
                </td>
                <td className={`border p-2 ${stabilityColor}`}>
                  <StabilityTooltip
                    stabilityScore={item.stability_score}
                    annualVolatility={item.annual_volatility}
                    dailyReturns={item.daily_returns || []}
                  />
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
