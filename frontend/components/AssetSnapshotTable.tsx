"use client"

import { useState, useEffect } from "react"
import { dataAPI } from "@/lib/api"
import { formatPercent, formatNumber } from "@/lib/utils"
import { cn } from "@/lib/utils"

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
  latest_market_cap: number | null
  eps_forecast: number | null
  change_rate: number | null
  pe_ratio: number | null
  pb_ratio: number | null
}

type SortField = "market_cap" | "change_rate" | null
type SortDirection = "asc" | "desc"

export function AssetSnapshotTable({ className }: { className?: string }) {
  const [data, setData] = useState<SnapshotData[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [sortField, setSortField] = useState<SortField>(null)
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

    if (sortField === "market_cap") {
      aValue = a.latest_market_cap
      bValue = b.latest_market_cap
    } else if (sortField === "change_rate") {
      aValue = a.change_rate
      bValue = b.change_rate
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

  return (
    <div className={cn("w-full overflow-x-auto", className)}>
      <div className="mb-4">
        <h3 className="text-lg font-semibold">资产分析明细表</h3>
      </div>
      <table className="w-full border-collapse">
        <thead>
          <tr className="bg-gray-100">
            <th className="border p-2 text-left font-bold">关联用户</th>
            <th className="border p-2 text-left font-bold">股票代码/名称</th>
            <th className="border p-2 text-left font-bold">基准价格</th>
            <th className="border p-2 text-left font-bold">最新收盘价</th>
            <th
              className="border p-2 text-left font-bold cursor-pointer hover:bg-gray-200"
              onClick={() => handleSort("market_cap")}
            >
              最新总市值（亿元）
              {sortField === "market_cap" && (
                <span className="ml-1">{sortDirection === "asc" ? "↑" : "↓"}</span>
              )}
            </th>
            <th className="border p-2 text-left font-bold">EPS 预测</th>
            <th
              className="border p-2 text-left font-bold cursor-pointer hover:bg-gray-200"
              onClick={() => handleSort("change_rate")}
            >
              累计收益
              {sortField === "change_rate" && (
                <span className="ml-1">{sortDirection === "asc" ? "↑" : "↓"}</span>
              )}
            </th>
          </tr>
        </thead>
        <tbody>
          {sortedData.map((item) => (
            <tr key={item.asset_id} className="hover:bg-gray-50">
              <td className="border p-2">{item.user.name}</td>
              <td className="border p-2">
                {item.code} {item.name}
              </td>
              <td className="border p-2">
                {item.baseline_price !== null
                  ? formatNumber(item.baseline_price)
                  : "-"}
              </td>
              <td className="border p-2">
                {item.latest_close_price !== null
                  ? formatNumber(item.latest_close_price)
                  : "-"}
              </td>
              <td className="border p-2">
                {item.latest_market_cap !== null
                  ? formatNumber(item.latest_market_cap)
                  : "-"}
              </td>
              <td className="border p-2">
                {item.eps_forecast !== null
                  ? formatNumber(item.eps_forecast)
                  : "-"}
              </td>
              <td className="border p-2">
                {item.change_rate !== null
                  ? formatPercent(item.change_rate)
                  : "-"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
