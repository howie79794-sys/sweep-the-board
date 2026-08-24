"use client"

import { useState, useEffect } from "react"
import { ADMIN_KEY_STORAGE } from "@/lib/api"
import { cn } from "@/lib/utils"

/**
 * 管理密钥输入条：保存到 localStorage 后，所有写请求自动携带 X-Admin-Key。
 * 后端对所有 POST/PUT/PATCH/DELETE 校验该密钥。
 */
export function AdminKeyBar() {
  const [key, setKey] = useState("")
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    try {
      const existing = window.localStorage.getItem(ADMIN_KEY_STORAGE)
      if (existing) {
        setKey(existing)
        setSaved(true)
      }
    } catch {
      // localStorage 不可用（隐私模式等）
    }
  }, [])

  const save = () => {
    try {
      if (key.trim()) {
        window.localStorage.setItem(ADMIN_KEY_STORAGE, key.trim())
      } else {
        window.localStorage.removeItem(ADMIN_KEY_STORAGE)
      }
      setSaved(Boolean(key.trim()))
    } catch {
      // ignore
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-2 p-3 border rounded-lg bg-muted/30">
      <span className="text-sm font-medium shrink-0">管理密钥</span>
      <input
        type="password"
        value={key}
        onChange={(e) => {
          setKey(e.target.value)
          setSaved(false)
        }}
        onKeyDown={(e) => e.key === "Enter" && save()}
        placeholder="写操作必填（X-Admin-Key）"
        className="flex-1 min-w-[200px] px-3 py-1.5 text-sm border rounded bg-background"
        autoComplete="off"
      />
      <button
        type="button"
        onClick={save}
        className="px-3 py-1.5 text-sm font-medium rounded bg-primary text-primary-foreground hover:bg-primary/90 shrink-0"
      >
        保存
      </button>
      <span
        className={cn(
          "text-xs shrink-0",
          saved ? "text-green-600" : "text-muted-foreground"
        )}
      >
        {saved ? "✓ 已保存，写操作将自动携带" : "保存到本机后自动携带"}
      </span>
    </div>
  )
}
