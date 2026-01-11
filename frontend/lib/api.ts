/** API调用封装 */
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

async function fetchAPI<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: '请求失败' }))
    throw new Error(error.message || error.detail || '请求失败')
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
    const response = await fetch(`${API_BASE_URL}/api/users/${id}/avatar`, {
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
    body: JSON.stringify({ asset_ids: assetIds, force }),
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
