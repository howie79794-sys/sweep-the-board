"use client"

import { useEffect, useMemo, useState } from "react"
import { assetAPI, pkPoolAPI } from "@/lib/api"
import { type Asset, type PKPool } from "@/types"
import { cn } from "@/lib/utils"

interface PoolFormState {
  name: string
  description: string
  asset_ids: number[]
  start_date: string
  end_date: string
}

export default function PKPoolsPage() {
  const [pools, setPools] = useState<PKPool[]>([])
  const [assets, setAssets] = useState<Asset[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showDialog, setShowDialog] = useState(false)
  const [editingPool, setEditingPool] = useState<PKPool | null>(null)
  const [form, setForm] = useState<PoolFormState>({
    name: "",
    description: "",
    asset_ids: [],
    start_date: "",
    end_date: "",
  })

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      setLoading(true)
      const [poolData, assetData] = await Promise.all([
        pkPoolAPI.getAll(),
        assetAPI.getAll(),
      ])
      setPools(poolData)
      setAssets(assetData)
      setError(null)
    } catch (err: any) {
      setError(err.message || "加载数据失败")
    } finally {
      setLoading(false)
    }
  }

  const sortedAssets = useMemo(() => {
    return [...assets].sort((a, b) => a.name.localeCompare(b.name, "zh-CN"))
  }, [assets])

  const openCreateDialog = () => {
    setEditingPool(null)
    setForm({ name: "", description: "", asset_ids: [], start_date: "", end_date: "" })
    setShowDialog(true)
  }

  const openEditDialog = async (pool: PKPool) => {
    try {
      setLoading(true)
      const detail = await pkPoolAPI.getById(pool.id)
      const assetIds = (detail.assets || []).map((asset: Asset) => asset.id)
      setEditingPool(pool)
      setForm({
        name: pool.name,
        description: pool.description || "",
        asset_ids: assetIds,
        start_date: pool.start_date || "",
        end_date: pool.end_date || "",
      })
      setShowDialog(true)
    } catch (err: any) {
      setError(err.message || "加载PK池详情失败")
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async () => {
    if (!form.name.trim()) {
      setError("池名称不能为空")
      return
    }
    if (form.asset_ids.length === 0) {
      setError("请至少选择一个资产")
      return
    }

    try {
      setLoading(true)
      setError(null)
      if (editingPool) {
        await pkPoolAPI.update(editingPool.id, {
          name: form.name.trim(),
          description: form.description.trim() || undefined,
          asset_ids: form.asset_ids,
          start_date: form.start_date || null,
          end_date: form.end_date || null,
        })
      } else {
        await pkPoolAPI.create({
          name: form.name.trim(),
          description: form.description.trim() || undefined,
          asset_ids: form.asset_ids,
          start_date: form.start_date || null,
          end_date: form.end_date || null,
        })
      }
      setShowDialog(false)
      setEditingPool(null)
      setForm({ name: "", description: "", asset_ids: [], start_date: "", end_date: "" })
      await loadData()
    } catch (err: any) {
      setError(err.message || "保存失败")
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (pool: PKPool) => {
    if (!confirm(`确定删除 PK 池「${pool.name}」吗？`)) return
    try {
      setLoading(true)
      setError(null)
      await pkPoolAPI.delete(pool.id)
      await loadData()
    } catch (err: any) {
      setError(err.message || "删除失败")
    } finally {
      setLoading(false)
    }
  }

  const toggleAsset = (assetId: number) => {
    setForm((prev) => {
      const exists = prev.asset_ids.includes(assetId)
      const next = exists
        ? prev.asset_ids.filter((id) => id !== assetId)
        : [...prev.asset_ids, assetId]
      return { ...prev, asset_ids: next }
    })
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">自定义 PK 池</h1>
          <p className="text-muted-foreground mt-1">管理对比池并选择参与资产</p>
        </div>
        <button
          onClick={openCreateDialog}
          className="px-4 py-2 bg-primary text-primary-foreground rounded hover:bg-primary/90"
        >
          新建 PK 池
        </button>
      </div>

      {error && (
        <div className="p-4 bg-destructive/10 text-destructive rounded-lg">{error}</div>
      )}

      {loading ? (
        <div className="text-center py-12">
          <p className="text-muted-foreground">加载中...</p>
        </div>
      ) : (
        <div className="grid gap-4">
          {pools.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">暂无 PK 池</div>
          ) : (
            pools.map((pool) => (
              <div key={pool.id} className="border rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-semibold text-lg">{pool.name}</div>
                    <div className="text-sm text-muted-foreground">
                      {pool.description || "暂无描述"}
                    </div>
                    <div className="text-sm text-muted-foreground mt-1">
                      资产数量: {pool.asset_count}
                    </div>
                    <div className="text-sm text-muted-foreground mt-1">
                      PK区间: {pool.start_date || "默认"} ~ {pool.end_date || "默认"}
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <a
                      href={`/pk-pools/${pool.id}`}
                      className="px-4 py-2 border rounded hover:bg-secondary"
                    >
                      查看详情
                    </a>
                    <button
                      onClick={() => openEditDialog(pool)}
                      className="px-4 py-2 border rounded hover:bg-secondary"
                    >
                      编辑
                    </button>
                    <button
                      onClick={() => handleDelete(pool)}
                      className="px-4 py-2 border rounded hover:bg-destructive/10 text-destructive"
                    >
                      删除
                    </button>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {showDialog && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-background border rounded-lg p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <h3 className="text-xl font-bold mb-4">
              {editingPool ? "编辑 PK 池" : "新建 PK 池"}
            </h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2">池名称</label>
                <input
                  type="text"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  className="w-full px-3 py-2 border rounded-md"
                  placeholder="例如：科技龙头对比"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">描述</label>
                <textarea
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                  className="w-full px-3 py-2 border rounded-md"
                  placeholder="输入PK池描述（可选）"
                  rows={3}
                />
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-2">开始时间</label>
                  <input
                    type="date"
                    value={form.start_date}
                    onChange={(e) => setForm({ ...form, start_date: e.target.value })}
                    className="w-full px-3 py-2 border rounded-md"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">结束时间</label>
                  <input
                    type="date"
                    value={form.end_date}
                    onChange={(e) => setForm({ ...form, end_date: e.target.value })}
                    className="w-full px-3 py-2 border rounded-md"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">选择资产</label>
                <div className="border rounded-md p-3 max-h-72 overflow-y-auto space-y-2">
                  {sortedAssets.map((asset) => {
                    const checked = form.asset_ids.includes(asset.id)
                    return (
                      <label key={asset.id} className="flex items-center gap-2 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={() => toggleAsset(asset.id)}
                          className="w-4 h-4"
                        />
                        <span className={cn(checked ? "font-medium" : "")}>
                          {asset.name} ({asset.code}) - {asset.market}
                        </span>
                      </label>
                    )
                  })}
                  {sortedAssets.length === 0 && (
                    <div className="text-sm text-muted-foreground">暂无资产可选</div>
                  )}
                </div>
                <p className="text-xs text-muted-foreground mt-2">
                  已选择 {form.asset_ids.length} 个资产
                </p>
              </div>
              <div className="flex gap-2 justify-end">
                <button
                  onClick={() => {
                    setShowDialog(false)
                    setEditingPool(null)
                    setForm({ name: "", description: "", asset_ids: [], start_date: "", end_date: "" })
                    setError(null)
                  }}
                  className="px-4 py-2 border rounded hover:bg-secondary"
                  disabled={loading}
                >
                  取消
                </button>
                <button
                  onClick={handleSubmit}
                  className="px-4 py-2 bg-primary text-primary-foreground rounded hover:bg-primary/90 disabled:opacity-50"
                  disabled={loading}
                >
                  {loading ? "保存中..." : "保存"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
