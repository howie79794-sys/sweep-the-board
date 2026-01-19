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
  is_core: boolean;  // 是否为核心资产
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
  stability_score?: number;
  annual_volatility?: number;
  daily_returns?: number[];
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

// PK 池类型
export interface PKPool {
  id: number;
  name: string;
  description?: string;
  created_at: string;
  start_date?: string | null;
  end_date?: string | null;
  asset_count: number;
}

export interface PKPoolDetail {
  id: number;
  name: string;
  description?: string;
  created_at: string;
  start_date?: string | null;
  end_date?: string | null;
  assets: Asset[];
  chart_data: PKPoolChartAsset[];
  snapshot_data: PKPoolSnapshot[];
}

export interface PKPoolChartAsset {
  asset_id: number;
  code: string;
  name: string;
  baseline_price?: number;
  baseline_date?: string;
  user?: {
    id: number;
    name: string;
    avatar_url?: string | null;
  };
  data: Array<{
    date: string;
    close_price: number;
    change_rate?: number | null;
    pe_ratio?: number | null;
    pb_ratio?: number | null;
    market_cap?: number | null;
    eps_forecast?: number | null;
  }>;
}

export interface PKPoolSnapshot {
  asset_id: number;
  code: string;
  name: string;
  user?: {
    id: number;
    name: string;
    avatar_url?: string | null;
  };
  baseline_price: number | null;
  baseline_date: string;
  latest_date: string;
  latest_close_price: number | null;
  yesterday_close_price: number | null;
  daily_change_rate: number | null;
  latest_market_cap: number | null;
  eps_forecast: number | null;
  change_rate: number | null;
  pe_ratio: number | null;
  pb_ratio: number | null;
  baseline_pe_ratio: number | null;
  stability_score: number | null;
  annual_volatility: number | null;
  daily_returns: number[] | null;
}
