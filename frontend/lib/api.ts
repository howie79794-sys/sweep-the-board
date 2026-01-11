/** API调用封装 */
// 在浏览器环境中，使用相对路径（通过Next.js rewrites代理）
// 在服务器端渲染时，使用环境变量或默认值
const getAPIBaseURL = () => {
  if (typeof window !== 'undefined') {
    // 浏览器环境：使用相对路径，通过Next.js rewrites代理到后端
    return ''
  }
  // 服务器端渲染：使用环境变量或默认值
  return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
}

const API_BASE_URL = getAPIBaseURL()

async function fetchAPI<T>(endpoint: string, options?: RequestInit): Promise<T> {
  // 如果是相对路径，直接使用；如果是绝对路径，使用API_BASE_URL
  const url = endpoint.startsWith('http') 
    ? endpoint 
    : `${API_BASE_URL}${endpoint}`
  
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  })

  if (!response.ok) {
    let errorMessage = '请求失败'
    try {
      const errorData = await response.json()
      // 处理各种错误格式
      if (typeof errorData === 'string') {
        errorMessage = errorData
      } else if (errorData?.message) {
        errorMessage = errorData.message
      } else if (errorData?.detail) {
        // FastAPI 错误格式
        if (typeof errorData.detail === 'string') {
          errorMessage = errorData.detail
        } else if (Array.isArray(errorData.detail)) {
          // FastAPI 验证错误格式
          errorMessage = errorData.detail.map((e: any) => 
            `${e.loc?.join('.')}: ${e.msg}`
          ).join(', ')
        } else {
          errorMessage = JSON.stringify(errorData.detail)
        }
      } else if (errorData?.error) {
        errorMessage = errorData.error
      } else {
        // 尝试序列化整个错误对象
        errorMessage = JSON.stringify(errorData)
      }
    } catch (e) {
      // 如果 JSON 解析失败，尝试获取文本
      try {
        const text = await response.text()
        errorMessage = text || `HTTP ${response.status}: ${response.statusText}`
      } catch {
        errorMessage = `HTTP ${response.status}: ${response.statusText}`
      }
    }
    const error = new Error(errorMessage)
    ;(error as any).status = response.status
    ;(error as any).response = response
    throw error
  }

  return response.json()
}

// 用户API
export const userAPI = {
  getAll: () => fetchAPI<any[]>('/api/users'),
  getById: (id: number) => fetchAPI<any>(`/api/users/${id}`),
  create: (data: any) => fetchAPI<any>('/api/users', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  update: (id: number, data: any) => fetchAPI<any>(`/api/users/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  }),
  delete: (id: number) => fetchAPI<any>(`/api/users/${id}`, {
    method: 'DELETE',
  }),
  uploadAvatar: async (id: number, file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    const url = typeof window !== 'undefined'
      ? `/api/users/${id}/avatar`
      : `${API_BASE_URL}/api/users/${id}/avatar`
    const response = await fetch(url, {
      method: 'POST',
      body: formData,
    })
    if (!response.ok) throw new Error('上传失败')
    return response.json()
  },
}

// 资产API
export const assetAPI = {
  getAll: (params?: { user_id?: number; asset_type?: string }) => {
    const query = new URLSearchParams()
    if (params?.user_id) query.append('user_id', params.user_id.toString())
    if (params?.asset_type) query.append('asset_type', params.asset_type)
    return fetchAPI<any[]>(`/api/assets?${query}`)
  },
  getById: (id: number) => fetchAPI<any>(`/api/assets/${id}`),
  create: (data: any) => fetchAPI<any>('/api/assets', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  update: (id: number, data: any) => fetchAPI<any>(`/api/assets/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  }),
  delete: (id: number) => fetchAPI<any>(`/api/assets/${id}`, {
    method: 'DELETE',
  }),
}

// 数据API
export const dataAPI = {
  getAssetData: (assetId: number, params?: { start_date?: string; end_date?: string }) => {
    const query = new URLSearchParams()
    if (params?.start_date) query.append('start_date', params.start_date)
    if (params?.end_date) query.append('end_date', params.end_date)
    return fetchAPI<any[]>(`/api/data/assets/${assetId}?${query}`)
  },
  getLatestData: (assetId: number) => fetchAPI<any>(`/api/data/assets/${assetId}/latest`),
  getBaselinePrice: (assetId: number) => fetchAPI<any>(`/api/data/assets/${assetId}/baseline`),
  update: (assetIds?: number[], force?: boolean) => fetchAPI<any>('/api/data/update', {
    method: 'POST',
    body: JSON.stringify({ 
      asset_ids: assetIds || null, 
      force: force ?? false 
    }),
  }),
}

// 排名API
export const rankingAPI = {
  getAll: (date?: string) => {
    const query = date ? `?ranking_date=${date}` : ''
    return fetchAPI<any>(`/api/ranking${query}`)
  },
  getAssetRankings: (date?: string) => {
    const query = date ? `?ranking_date=${date}` : ''
    return fetchAPI<any[]>(`/api/ranking/assets${query}`)
  },
  getUserRankings: (date?: string) => {
    const query = date ? `?ranking_date=${date}` : ''
    return fetchAPI<any[]>(`/api/ranking/users${query}`)
  },
  getHistory: (params?: { asset_id?: number; user_id?: number }) => {
    const query = new URLSearchParams()
    if (params?.asset_id) query.append('asset_id', params.asset_id.toString())
    if (params?.user_id) query.append('user_id', params.user_id.toString())
    return fetchAPI<any[]>(`/api/ranking/history?${query}`)
  },
  getUserHistory: (userId: number) => fetchAPI<any[]>(`/api/ranking/users/${userId}`),
}
