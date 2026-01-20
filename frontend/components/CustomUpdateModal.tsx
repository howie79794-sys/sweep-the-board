"use client"

import { useState, useEffect } from "react"
import { dataAPI } from "@/lib/api"
import { type Asset } from "@/types"
import { cn } from "@/lib/utils"

interface CustomUpdateModalProps {
  isOpen: boolean
  onClose: () => void
  assets: Asset[]
  onSuccess?: () => void
  onError?: (message: string) => void
}

export function CustomUpdateModal({
  isOpen,
  onClose,
  assets,
  onSuccess,
  onError,
}: CustomUpdateModalProps) {
  const [selectedAssetId, setSelectedAssetId] = useState<string>("")
  const [targetDate, setTargetDate] = useState<string>("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // 调试：检查资产数据
  useEffect(() => {
    if (isOpen) {
      console.log('[CustomUpdateModal] 资产数据:', assets)
      console.log('[CustomUpdateModal] 资产数量:', assets?.length || 0)
    }
  }, [isOpen, assets])

  // 初始化日期为今天（YYYY-MM-DD格式）
  useEffect(() => {
    if (isOpen && !targetDate) {
      const today = new Date()
      const year = today.getFullYear()
      const month = String(today.getMonth() + 1).padStart(2, '0')
      const day = String(today.getDate()).padStart(2, '0')
      setTargetDate(`${year}-${month}-${day}`)
    }
  }, [isOpen, targetDate])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!selectedAssetId) {
      setError("请选择资产")
      return
    }
    
    if (!targetDate) {
      setError("请选择日期")
      return
    }
    
    // 验证日期格式 YYYY-MM-DD
    const dateRegex = /^\d{4}-\d{2}-\d{2}$/
    if (!dateRegex.test(targetDate)) {
      setError("日期格式错误，必须是 YYYY-MM-DD 格式")
      return
    }
    
    try {
      setLoading(true)
      setError(null)
      
      const result = await dataAPI.customUpdate(parseInt(selectedAssetId), targetDate)
      
      if (result.success) {
        // 显示成功消息（通过 onSuccess 回调，由父组件显示 toast）
        if (onSuccess) {
          onSuccess()
        }
        // 延迟关闭弹窗，让用户看到成功消息
        setTimeout(() => {
          handleClose()
        }, 500)
      } else {
        const errorMsg = result.message || "校准失败"
        setError(errorMsg)
        if (onError) {
          onError(errorMsg)
        }
      }
    } catch (err: any) {
      const errorMsg = err?.message || err?.toString() || "校准失败"
      setError(errorMsg)
      console.error("单点数据校准错误:", err)
      if (onError) {
        onError(errorMsg)
      }
    } finally {
      setLoading(false)
    }
  }

  const handleClose = () => {
    setSelectedAssetId("")
    setTargetDate("")
    setError(null)
    onClose()
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={handleClose}>
      <div className="bg-white rounded-lg p-6 w-full max-w-md shadow-xl" onClick={(e) => e.stopPropagation()}>
        <h2 className="text-xl font-bold mb-4">单点数据校准</h2>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* 资产选择器 */}
          <div>
            <label className="block text-sm font-medium mb-2">
              选择资产 <span className="text-red-500">*</span>
            </label>
            <select
              value={selectedAssetId}
              onChange={(e) => setSelectedAssetId(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md bg-white text-gray-900 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
              disabled={loading}
              required
            >
              <option value="">请选择资产</option>
              {assets && assets.length > 0 ? (
                assets.map((asset) => (
                  <option key={asset.id} value={asset.id.toString()}>
                    {asset.name} ({asset.code}) - {asset.user?.name || `用户ID: ${asset.user_id}`}
                  </option>
                ))
              ) : (
                <option value="" disabled>暂无资产数据，请先在"资产管理"标签页创建资产</option>
              )}
            </select>
            {assets && assets.length === 0 && (
              <p className="text-xs text-muted-foreground mt-1">
                提示：请先在"资产管理"标签页创建资产
              </p>
            )}
          </div>

          {/* 日期选择器 */}
          <div>
            <label className="block text-sm font-medium mb-2">
              选择日期 <span className="text-red-500">*</span>
            </label>
            <input
              type="date"
              value={targetDate}
              onChange={(e) => setTargetDate(e.target.value)}
              className="w-full px-3 py-2 border rounded-md"
              disabled={loading}
              required
            />
            <p className="text-xs text-muted-foreground mt-1">
              格式：YYYY-MM-DD
            </p>
          </div>

          {/* 错误提示 */}
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded text-red-600 text-sm">
              {error}
            </div>
          )}

          {/* 按钮 */}
          <div className="flex gap-2 justify-end pt-4">
            <button
              type="button"
              onClick={handleClose}
              className="px-4 py-2 border rounded hover:bg-secondary"
              disabled={loading}
            >
              取消
            </button>
            <button
              type="submit"
              className="px-4 py-2 bg-primary text-primary-foreground rounded hover:bg-primary/90 disabled:opacity-50 flex items-center gap-2"
              disabled={loading}
            >
              {loading && (
                <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
              )}
              {loading ? "校准中..." : "开始校准"}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
