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
  const [showUserDialog, setShowUserDialog] = useState(false)
  const [showAssetDialog, setShowAssetDialog] = useState(false)
  const [editingUser, setEditingUser] = useState<User | null>(null)
  const [editingAsset, setEditingAsset] = useState<Asset | null>(null)
  const [userForm, setUserForm] = useState({ name: "" })
  const [uploadingAvatar, setUploadingAvatar] = useState(false)
  const [avatarPreview, setAvatarPreview] = useState<string | null>(null)
  const [selectedAvatarFile, setSelectedAvatarFile] = useState<File | null>(null)
  const [assetForm, setAssetForm] = useState({
    user_id: "",
    asset_type: "stock",
    market: "",
    code: "",
    name: "",
  })

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
      // 构建详细的消息
      let message = result.message || "数据更新完成"
      if (result.total !== undefined) {
        message += `\n总计: ${result.total}，成功: ${result.success}，失败: ${result.failed}`
        if (result.details && result.details.length > 0) {
          const failedDetails = result.details
            .filter((d: any) => !d.result?.success)
            .map((d: any) => `${d.asset_name}: ${d.result?.message || "失败"}`)
          if (failedDetails.length > 0) {
            message += `\n\n失败详情:\n${failedDetails.join('\n')}`
          }
        }
      }
      alert(message)
      loadAssets()
    } catch (err: any) {
      // 确保显示真实的错误信息
      const errorMsg = err?.message || err?.toString() || "更新数据失败"
      console.error("更新数据错误:", err)
      setError(errorMsg)
      alert(`更新数据失败: ${errorMsg}`)
    } finally {
      setLoading(false)
    }
  }

  const handleCreateUser = async () => {
    if (!userForm.name.trim()) {
      setError("用户名不能为空")
      return
    }
    try {
      setLoading(true)
      setError(null)
      
      // 先创建用户
      const newUser = await userAPI.create({ name: userForm.name.trim() })
      
      // 如果选择了头像，上传头像
      if (selectedAvatarFile && newUser.id) {
        try {
          await handleAvatarUpload(newUser.id)
        } catch (avatarErr: any) {
          // 头像上传失败不影响用户创建，但显示错误提示
          console.error("头像上传失败:", avatarErr)
          setError(`用户创建成功，但头像上传失败：${avatarErr?.message || "未知错误"}`)
        }
      }
      
      // 清理状态
      setShowUserDialog(false)
      setUserForm({ name: "" })
      setEditingUser(null)
      clearAvatarSelection()
      
      await loadUsers()
    } catch (err: any) {
      setError(err.message || "创建用户失败")
    } finally {
      setLoading(false)
    }
  }

  const handleEditUser = (user: User) => {
    setEditingUser(user)
    setUserForm({ name: user.name })
    
    // 清理之前可能存在的blob URL
    if (avatarPreview && avatarPreview.startsWith('blob:')) {
      URL.revokeObjectURL(avatarPreview)
    }
    
    // 加载当前头像预览（如果存在）
    if (user.avatar_url) {
      setAvatarPreview(user.avatar_url)
    } else {
      setAvatarPreview(null)
    }
    
    // 清空选中的新文件
    setSelectedAvatarFile(null)
    setShowUserDialog(true)
  }

  const handleUpdateUser = async () => {
    if (!editingUser || !userForm.name.trim()) {
      setError("用户名不能为空")
      return
    }
    try {
      setLoading(true)
      setError(null)
      
      // 先更新用户信息
      await userAPI.update(editingUser.id, { name: userForm.name.trim() })
      
      // 如果选择了新头像，上传头像
      if (selectedAvatarFile) {
        try {
          await handleAvatarUpload(editingUser.id)
        } catch (avatarErr: any) {
          // 头像上传失败不影响用户更新，但显示错误提示
          console.error("头像上传失败:", avatarErr)
          setError(`用户信息更新成功，但头像上传失败：${avatarErr?.message || "未知错误"}`)
        }
      }
      
      // 清理状态
      setShowUserDialog(false)
      setUserForm({ name: "" })
      setEditingUser(null)
      clearAvatarSelection()
      
      await loadUsers()
    } catch (err: any) {
      setError(err.message || "更新用户失败")
    } finally {
      setLoading(false)
    }
  }

  const handleDeleteUser = async (id: number) => {
    if (!confirm("确定要删除这个用户吗？")) return
    try {
      setLoading(true)
      setError(null)
      await userAPI.delete(id)
      await loadUsers()
      await loadAssets() // 重新加载资产列表
    } catch (err: any) {
      setError(err.message || "删除用户失败")
    } finally {
      setLoading(false)
    }
  }

  const handleAvatarSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    // 验证文件类型
    const allowedExtensions = ['.jpg', '.jpeg', '.png', '.webp']
    const fileExtension = '.' + file.name.split('.').pop()?.toLowerCase()
    if (!allowedExtensions.includes(fileExtension)) {
      setError(`不支持的文件格式。支持格式：${allowedExtensions.join(', ')}`)
      event.target.value = '' // 清空input
      return
    }

    // 验证文件大小（5MB）
    const maxSize = 5 * 1024 * 1024 // 5MB
    if (file.size > maxSize) {
      setError(`文件大小超过限制。最大大小：5MB`)
      event.target.value = '' // 清空input
      return
    }

    // 存储文件并生成预览
    setSelectedAvatarFile(file)
    setError(null)
    
    // 创建预览URL
    const previewUrl = URL.createObjectURL(file)
    setAvatarPreview(previewUrl)
  }

  const handleAvatarUpload = async (userId: number) => {
    if (!selectedAvatarFile) {
      setError("请先选择头像文件")
      return
    }

    try {
      setUploadingAvatar(true)
      setError(null)
      const result = await userAPI.uploadAvatar(userId, selectedAvatarFile)
      
      // 清理预览URL（如果是新选择的文件）
      if (avatarPreview && avatarPreview.startsWith('blob:')) {
        URL.revokeObjectURL(avatarPreview)
      }
      
      // 更新预览为上传后的头像URL
      if (result.avatar_url) {
        setAvatarPreview(result.avatar_url)
      }
      
      // 重置选中的文件（但保留预览）
      setSelectedAvatarFile(null)
      
      // 刷新用户列表
      await loadUsers()
    } catch (err: any) {
      const errorMessage = err?.message || "上传头像失败，请检查网络连接或文件格式"
      setError(errorMessage)
      throw err // 重新抛出以便调用者处理
    } finally {
      setUploadingAvatar(false)
    }
  }

  const clearAvatarSelection = () => {
    // 清理预览URL（只清理blob URL，不清理服务器URL）
    if (avatarPreview && avatarPreview.startsWith('blob:')) {
      URL.revokeObjectURL(avatarPreview)
    }
    setAvatarPreview(null)
    setSelectedAvatarFile(null)
  }

  const handleCreateAsset = async () => {
    if (!assetForm.user_id || !assetForm.market.trim() || !assetForm.code.trim() || !assetForm.name.trim()) {
      setError("请填写所有必填字段")
      return
    }
    try {
      setLoading(true)
      setError(null)
      await assetAPI.create({
        user_id: parseInt(assetForm.user_id),
        asset_type: assetForm.asset_type,
        market: assetForm.market.trim(),
        code: assetForm.code.trim(),
        name: assetForm.name.trim(),
      })
      setShowAssetDialog(false)
      setAssetForm({ user_id: "", asset_type: "stock", market: "", code: "", name: "" })
      setEditingAsset(null)
      await loadAssets()
    } catch (err: any) {
      setError(err.message || "创建资产失败")
    } finally {
      setLoading(false)
    }
  }

  const handleEditAsset = (asset: Asset) => {
    setEditingAsset(asset)
    setAssetForm({
      user_id: asset.user_id.toString(),
      asset_type: asset.asset_type,
      market: asset.market,
      code: asset.code,
      name: asset.name,
    })
    setShowAssetDialog(true)
  }

  const handleUpdateAsset = async () => {
    if (!editingAsset || !assetForm.user_id || !assetForm.market.trim() || !assetForm.code.trim() || !assetForm.name.trim()) {
      setError("请填写所有必填字段")
      return
    }
    try {
      setLoading(true)
      setError(null)
      await assetAPI.update(editingAsset.id, {
        user_id: parseInt(assetForm.user_id),
        asset_type: assetForm.asset_type,
        market: assetForm.market.trim(),
        code: assetForm.code.trim(),
        name: assetForm.name.trim(),
      })
      setShowAssetDialog(false)
      setAssetForm({ user_id: "", asset_type: "stock", market: "", code: "", name: "" })
      setEditingAsset(null)
      await loadAssets()
    } catch (err: any) {
      setError(err.message || "更新资产失败")
    } finally {
      setLoading(false)
    }
  }

  const handleDeleteAsset = async (id: number) => {
    if (!confirm("确定要删除这个资产吗？")) return
    try {
      setLoading(true)
      setError(null)
      await assetAPI.delete(id)
      await loadAssets()
    } catch (err: any) {
      setError(err.message || "删除资产失败")
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
            <button
              onClick={() => setShowUserDialog(true)}
              className="px-4 py-2 bg-primary text-primary-foreground rounded hover:bg-primary/90"
            >
              添加用户
            </button>
          </div>
          
          {/* 添加/编辑用户对话框 */}
          {showUserDialog && (
            <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
              <div className="bg-background border rounded-lg p-6 w-full max-w-md">
                <h3 className="text-xl font-bold mb-4">{editingUser ? "编辑用户" : "添加用户"}</h3>
                <div className="space-y-4">
                  {/* 头像上传区域 */}
                  <div>
                    <label className="block text-sm font-medium mb-2">头像</label>
                    <div className="flex items-center gap-4">
                      {/* 头像预览 */}
                      <div className="flex-shrink-0">
                        {avatarPreview ? (
                          <img
                            src={avatarPreview}
                            alt="头像预览"
                            className="w-20 h-20 rounded-full object-cover border-2 border-border"
                          />
                        ) : (
                          <div className="w-20 h-20 rounded-full bg-muted flex items-center justify-center border-2 border-border">
                            <span className="text-muted-foreground text-sm">无头像</span>
                          </div>
                        )}
                      </div>
                      
                      {/* 文件选择和上传按钮 */}
                      <div className="flex-1 space-y-2">
                        <div className="flex gap-2">
                          <label className="px-4 py-2 border rounded hover:bg-secondary cursor-pointer text-sm">
                            选择文件
                            <input
                              type="file"
                              accept=".jpg,.jpeg,.png,.webp"
                              onChange={handleAvatarSelect}
                              className="hidden"
                              disabled={loading || uploadingAvatar}
                            />
                          </label>
                          {selectedAvatarFile && editingUser && (
                            <button
                              onClick={() => handleAvatarUpload(editingUser.id)}
                              disabled={loading || uploadingAvatar}
                              className="px-4 py-2 bg-primary text-primary-foreground rounded hover:bg-primary/90 disabled:opacity-50 text-sm"
                            >
                              {uploadingAvatar ? "上传中..." : "上传头像"}
                            </button>
                          )}
                        </div>
                        <p className="text-xs text-muted-foreground">
                          支持格式: jpg, jpeg, png, webp | 最大大小: 5MB
                        </p>
                        {selectedAvatarFile && (
                          <p className="text-xs text-muted-foreground">
                            已选择: {selectedAvatarFile.name} ({(selectedAvatarFile.size / 1024 / 1024).toFixed(2)} MB)
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                  
                  {/* 用户名输入 */}
                  <div>
                    <label className="block text-sm font-medium mb-2">用户名</label>
                    <input
                      type="text"
                      value={userForm.name}
                      onChange={(e) => setUserForm({ name: e.target.value })}
                      className="w-full px-3 py-2 border rounded-md"
                      placeholder="请输入用户名"
                      autoFocus
                      disabled={loading || uploadingAvatar}
                    />
                  </div>
                  
                  {/* 操作按钮 */}
                  <div className="flex gap-2 justify-end">
                    <button
                      onClick={() => {
                        setShowUserDialog(false)
                        setUserForm({ name: "" })
                        setEditingUser(null)
                        setError(null)
                        clearAvatarSelection()
                      }}
                      className="px-4 py-2 border rounded hover:bg-secondary"
                      disabled={loading || uploadingAvatar}
                    >
                      取消
                    </button>
                    <button
                      onClick={editingUser ? handleUpdateUser : handleCreateUser}
                      className="px-4 py-2 bg-primary text-primary-foreground rounded hover:bg-primary/90 disabled:opacity-50"
                      disabled={loading || uploadingAvatar}
                    >
                      {loading || uploadingAvatar
                        ? (editingUser ? "更新中..." : "创建中...")
                        : (editingUser ? "更新" : "创建")}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}
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
                    <button
                      onClick={() => handleEditUser(user)}
                      className="px-4 py-2 border rounded hover:bg-secondary disabled:opacity-50"
                      disabled={loading}
                    >
                      编辑
                    </button>
                    <button
                      onClick={() => handleDeleteUser(user.id)}
                      className="px-4 py-2 border rounded hover:bg-destructive/10 text-destructive disabled:opacity-50"
                      disabled={loading}
                    >
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
            <button
              onClick={() => setShowAssetDialog(true)}
              className="px-4 py-2 bg-primary text-primary-foreground rounded hover:bg-primary/90"
            >
              添加资产
            </button>
          </div>
          
          {/* 添加/编辑资产对话框 */}
          {showAssetDialog && (
            <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
              <div className="bg-background border rounded-lg p-6 w-full max-w-md max-h-[90vh] overflow-y-auto">
                <h3 className="text-xl font-bold mb-4">{editingAsset ? "编辑资产" : "添加资产"}</h3>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium mb-2">用户</label>
                    <select
                      value={assetForm.user_id}
                      onChange={(e) => setAssetForm({ ...assetForm, user_id: e.target.value })}
                      className="w-full px-3 py-2 border rounded-md"
                    >
                      <option value="">请选择用户</option>
                      {users.map((user) => (
                        <option key={user.id} value={user.id}>
                          {user.name} (ID: {user.id})
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2">资产类型</label>
                    <select
                      value={assetForm.asset_type}
                      onChange={(e) => setAssetForm({ ...assetForm, asset_type: e.target.value })}
                      className="w-full px-3 py-2 border rounded-md"
                    >
                      <option value="stock">股票</option>
                      <option value="fund">基金</option>
                      <option value="futures">期货</option>
                      <option value="forex">外汇</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2">市场</label>
                    <input
                      type="text"
                      value={assetForm.market}
                      onChange={(e) => setAssetForm({ ...assetForm, market: e.target.value })}
                      className="w-full px-3 py-2 border rounded-md"
                      placeholder="例如：上海、深圳"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2">代码</label>
                    <input
                      type="text"
                      value={assetForm.code}
                      onChange={(e) => setAssetForm({ ...assetForm, code: e.target.value })}
                      className="w-full px-3 py-2 border rounded-md"
                      placeholder="例如：600580"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2">名称</label>
                    <input
                      type="text"
                      value={assetForm.name}
                      onChange={(e) => setAssetForm({ ...assetForm, name: e.target.value })}
                      className="w-full px-3 py-2 border rounded-md"
                      placeholder="例如：卧龙电驱"
                    />
                  </div>
                  <div className="flex gap-2 justify-end">
                    <button
                      onClick={() => {
                        setShowAssetDialog(false)
                        setAssetForm({ user_id: "", asset_type: "stock", market: "", code: "", name: "" })
                        setEditingAsset(null)
                        setError(null)
                      }}
                      className="px-4 py-2 border rounded hover:bg-secondary"
                      disabled={loading}
                    >
                      取消
                    </button>
                    <button
                      onClick={editingAsset ? handleUpdateAsset : handleCreateAsset}
                      className="px-4 py-2 bg-primary text-primary-foreground rounded hover:bg-primary/90 disabled:opacity-50"
                      disabled={loading}
                    >
                      {loading ? (editingAsset ? "更新中..." : "创建中...") : (editingAsset ? "更新" : "创建")}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}
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
                        关联用户: {asset.user?.name || `用户ID: ${asset.user_id}`} | 基准价: {asset.baseline_price || "未设置"}
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleEditAsset(asset)}
                        className="px-4 py-2 border rounded hover:bg-secondary disabled:opacity-50"
                        disabled={loading}
                      >
                        编辑
                      </button>
                      <button
                        onClick={() => handleDeleteAsset(asset.id)}
                        className="px-4 py-2 border rounded hover:bg-destructive/10 text-destructive disabled:opacity-50"
                        disabled={loading}
                      >
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
