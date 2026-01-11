"use client"

import { useState, useEffect } from "react"
import { userAPI, assetAPI, dataAPI } from "@/lib/api"
import { type User, type Asset } from "@/types"
import { UserAvatar } from "@/components/UserAvatar"
import { cn } from "@/lib/utils"

export default function AdminPage() {
  const [activeTab, setActiveTab] = useState<"users" | "assets" | "data">("users")
  const [users, setUsers] = useState<User[]>([])
  const [assets, setAssets] = useState<Asset[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (activeTab === "users") {
      loadUsers()
    } else if (activeTab === "assets") {
      loadAssets()
    }
  }, [activeTab])

  const loadUsers = async () => {
    try {
      setLoading(true)
      const data = await userAPI.getAll()
      setUsers(data)
      setError(null)
    } catch (err: any) {
      setError(err.message || "加载用户失败")
    } finally {
      setLoading(false)
    }
  }

  const loadAssets = async () => {
    try {
      setLoading(true)
      const data = await assetAPI.getAll()
      setAssets(data)
      setError(null)
    } catch (err: any) {
      setError(err.message || "加载资产失败")
    } finally {
      setLoading(false)
    }
  }

  const handleUpdateData = async () => {
    try {
      setLoading(true)
      setError(null)
      const result = await dataAPI.update()
      alert(`数据更新完成：${result.message || "成功"}`)
      loadAssets()
    } catch (err: any) {
      setError(err.message || "更新数据失败")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold mb-2">管理界面</h1>
        <p className="text-muted-foreground">管理用户、资产和数据</p>
      </div>

      {/* 标签页 */}
      <div className="flex gap-4 border-b">
        <button
          onClick={() => setActiveTab("users")}
          className={cn(
            "px-4 py-2 font-medium border-b-2 transition-colors",
            activeTab === "users"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          )}
        >
          用户管理
        </button>
        <button
          onClick={() => setActiveTab("assets")}
          className={cn(
            "px-4 py-2 font-medium border-b-2 transition-colors",
            activeTab === "assets"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          )}
        >
          资产管理
        </button>
        <button
          onClick={() => setActiveTab("data")}
          className={cn(
            "px-4 py-2 font-medium border-b-2 transition-colors",
            activeTab === "data"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          )}
        >
          数据管理
        </button>
      </div>

      {error && (
        <div className="p-4 bg-destructive/10 text-destructive rounded-lg">
          {error}
        </div>
      )}

      {/* 用户管理 */}
      {activeTab === "users" && (
        <div>
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-2xl font-bold">用户列表</h2>
            <button className="px-4 py-2 bg-primary text-primary-foreground rounded hover:bg-primary/90">
              添加用户
            </button>
          </div>
          {loading ? (
            <div className="text-center py-12">
              <p className="text-muted-foreground">加载中...</p>
            </div>
          ) : (
            <div className="grid gap-4">
              {users.map((user) => (
                <div
                  key={user.id}
                  className="border rounded-lg p-4 flex items-center justify-between"
                >
                  <div className="flex items-center gap-4">
                    <UserAvatar user={user} size="md" />
                    <div>
                      <div className="font-semibold">{user.name}</div>
                      <div className="text-sm text-muted-foreground">
                        ID: {user.id} | 创建于: {new Date(user.created_at).toLocaleDateString("zh-CN")}
                      </div>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <button className="px-4 py-2 border rounded hover:bg-secondary">
                      编辑
                    </button>
                    <button className="px-4 py-2 border rounded hover:bg-destructive/10 text-destructive">
                      删除
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* 资产管理 */}
      {activeTab === "assets" && (
        <div>
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-2xl font-bold">资产列表</h2>
            <button className="px-4 py-2 bg-primary text-primary-foreground rounded hover:bg-primary/90">
              添加资产
            </button>
          </div>
          {loading ? (
            <div className="text-center py-12">
              <p className="text-muted-foreground">加载中...</p>
            </div>
          ) : (
            <div className="grid gap-4">
              {assets.map((asset) => (
                <div
                  key={asset.id}
                  className="border rounded-lg p-4"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="font-semibold text-lg">{asset.name}</div>
                      <div className="text-sm text-muted-foreground">
                        {asset.code} | {asset.market} | {asset.asset_type}
                      </div>
                      <div className="text-sm text-muted-foreground mt-1">
                        用户ID: {asset.user_id} | 基准价: {asset.baseline_price || "未设置"}
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <button className="px-4 py-2 border rounded hover:bg-secondary">
                        编辑
                      </button>
                      <button className="px-4 py-2 border rounded hover:bg-destructive/10 text-destructive">
                        删除
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* 数据管理 */}
      {activeTab === "data" && (
        <div>
          <h2 className="text-2xl font-bold mb-4">数据管理</h2>
          <div className="space-y-4">
            <div className="border rounded-lg p-6">
              <h3 className="text-lg font-semibold mb-4">数据更新</h3>
              <p className="text-muted-foreground mb-4">
                从数据源获取最新数据并更新到数据库
              </p>
              <button
                onClick={handleUpdateData}
                disabled={loading}
                className="px-6 py-3 bg-primary text-primary-foreground rounded hover:bg-primary/90 disabled:opacity-50"
              >
                {loading ? "更新中..." : "更新所有资产数据"}
              </button>
            </div>

            <div className="border rounded-lg p-6">
              <h3 className="text-lg font-semibold mb-4">数据统计</h3>
              <div className="grid grid-cols-3 gap-4">
                <div className="p-4 bg-secondary rounded">
                  <div className="text-2xl font-bold">{users.length}</div>
                  <div className="text-sm text-muted-foreground">用户总数</div>
                </div>
                <div className="p-4 bg-secondary rounded">
                  <div className="text-2xl font-bold">{assets.length}</div>
                  <div className="text-sm text-muted-foreground">资产总数</div>
                </div>
                <div className="p-4 bg-secondary rounded">
                  <div className="text-2xl font-bold">-</div>
                  <div className="text-sm text-muted-foreground">数据记录</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
