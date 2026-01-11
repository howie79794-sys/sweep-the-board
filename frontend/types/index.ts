// 用户类型
export interface User {
  id: number;
  name: string;
  avatar_url?: string;
  created_at: string;
  is_active: boolean;
}

// 资产类型
export interface Asset {
  id: number;
  user_id: number;
  asset_type: 'stock' | 'fund' | 'futures' | 'forex';
  market: string;
  code: string;
  name: string;
  baseline_price?: number;
  baseline_date: string;
  start_date: string;
  end_date: string;
  created_at: string;
  user?: User;
}

// 市场数据类型
export interface MarketData {
  id: number;
  asset_id: number;
  date: string;
  close_price: number;
  volume?: number;
  turnover_rate?: number;
  pe_ratio?: number;
  market_cap?: number;
  additional_data?: Record<string, any>;
  created_at: string;
}

// 排名类型
export interface Ranking {
  id: number;
  date: string;
  asset_id: number;
  user_id: number;
  asset_rank?: number;
  user_rank?: number;
  change_rate?: number;
  rank_type?: string;
  created_at: string;
  asset?: Asset;
  user?: User;
}

// 排名响应类型
export interface RankingResponse {
  asset_rankings: (Ranking & { asset: Asset; user: User })[];
  user_rankings: (Ranking & { user: User })[];
  date: string | null;
}

// API响应类型
export interface ApiResponse<T> {
  data?: T;
  error?: string;
  message?: string;
}

// 资产详情（包含最新数据和涨跌幅）
export interface AssetDetail extends Asset {
  latest_data?: MarketData;
  change_rate?: number;
  current_price?: number;
}

// 用户详情（包含所有资产）
export interface UserDetail extends User {
  assets: AssetDetail[];
  best_change_rate?: number;
  average_change_rate?: number;
}
