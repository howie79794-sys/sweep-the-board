"use client"

import { useEffect, useState } from "react"
import { pkPoolAPI } from "@/lib/api"
import { type PKPoolDetail } from "@/types"
import { CumulativeReturnChart } from "@/components/CumulativeReturnChart"
import { AssetDetailTable } from "@/components/AssetDetailTable"

interface PKPoolDetailPageProps {
  params: {
    poolId: string
  }
}

export default function PKPoolDetailPage({ params }: PKPoolDetailPageProps) {
  const [detail, setDetail] = useState<PKPoolDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadDetail()
  }, [params.poolId])

  const loadDetail = async () => {
    try {
      setLoading(true)
      const data = await pkPoolAPI.getDetail(Number(params.poolId))
      setDetail(data)
      setError(null)
    } catch (err: any) {
      setError(err.message || "加载PK池详情失败")
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground">加载中...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-4 bg-destructive/10 text-destructive rounded-lg">{error}</div>
    )
  }

  if (!detail) {
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground">PK池不存在</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">{detail.name}</h1>
          <p className="text-muted-foreground mt-1">{detail.description || "暂无描述"}</p>
          <p className="text-sm text-muted-foreground mt-1">
            PK区间: {detail.start_date || "默认"} ~ {detail.end_date || "默认"}
          </p>
        </div>
        <a
          href="/pk-pools"
          className="px-4 py-2 border rounded hover:bg-secondary"
        >
          返回列表
        </a>
      </div>

      <div className="border rounded-lg p-6">
        <CumulativeReturnChart assets={detail.chart_data} showChangeRate={true} />
      </div>

      <div className="border rounded-lg p-6">
        <AssetDetailTable data={detail.snapshot_data} />
      </div>
    </div>
  )
}
