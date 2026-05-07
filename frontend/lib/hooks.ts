/**
 * SWR Hooks 封装
 *
 * 设计原则：
 * 1. 用 SWR 自动做"请求去重 + 缓存 + 后台 revalidate"，避免多个组件重复打同一接口
 * 2. 关键接口（首页排行榜、快照、图表）使用相同的 key，组件就能共享缓存
 * 3. 默认行为：30 秒内同 key 不重复请求；窗口聚焦自动 revalidate
 */
"use client"

import useSWR, { type SWRConfiguration, mutate as globalMutate } from "swr"
import { rankingAPI, dataAPI, assetAPI, userAPI, pkPoolAPI } from "@/lib/api"
import type { RankingResponse, WeeklyRankingItem } from "@/types"

// 默认 SWR 配置
const defaultConfig: SWRConfiguration = {
  // 缓存 30 秒内不重复请求
  dedupingInterval: 30_000,
  // 窗口重获焦点时 revalidate（市场数据有更新需要刷新）
  revalidateOnFocus: true,
  // 网络重连时 revalidate
  revalidateOnReconnect: true,
  // 失败时自动重试（最多 3 次，指数退避由 SWR 内部实现）
  errorRetryCount: 3,
  // 重试间隔基础值（ms），SWR 会指数退避
  errorRetryInterval: 2000,
}

// ========================================================
// SWR Keys（集中管理，方便手动 invalidate）
// ========================================================
export const swrKeys = {
  rankingAll: (date?: string) => ["ranking/all", date ?? "today"] as const,
  rankingAssets: (date?: string) => ["ranking/assets", date ?? "today"] as const,
  rankingUsers: (date?: string) => ["ranking/users", date ?? "today"] as const,
  rankingWeekly: () => ["ranking/weekly"] as const,
  snapshot: () => ["data/snapshot"] as const,
  allAssetsChart: (start?: string, end?: string) =>
    ["data/charts/all", start ?? "", end ?? ""] as const,
  weeklyChart: () => ["data/charts/weekly"] as const,
  users: () => ["users"] as const,
  assets: (params?: { user_id?: number; asset_type?: string }) =>
    ["assets", params?.user_id ?? "", params?.asset_type ?? ""] as const,
  pkPools: () => ["pk-pools"] as const,
}

// ========================================================
// 排名相关 Hooks
// ========================================================
export function useRankings(date?: string, config?: SWRConfiguration) {
  return useSWR<RankingResponse>(
    swrKeys.rankingAll(date),
    () => rankingAPI.getAll(date),
    { ...defaultConfig, ...config }
  )
}

export function useWeeklyRankings(config?: SWRConfiguration) {
  return useSWR<{ items: WeeklyRankingItem[] }>(
    swrKeys.rankingWeekly(),
    () => rankingAPI.getWeekly(),
    { ...defaultConfig, ...config }
  )
}

// ========================================================
// 数据相关 Hooks
// ========================================================
export function useSnapshot(config?: SWRConfiguration) {
  return useSWR<any[]>(
    swrKeys.snapshot(),
    () => dataAPI.getSnapshotData(),
    { ...defaultConfig, ...config }
  )
}

export function useAllAssetsChart(
  params?: { start_date?: string; end_date?: string },
  config?: SWRConfiguration
) {
  return useSWR<any[]>(
    swrKeys.allAssetsChart(params?.start_date, params?.end_date),
    () => dataAPI.getAllAssetsChartData(params),
    { ...defaultConfig, ...config }
  )
}

export function useWeeklyChart(config?: SWRConfiguration) {
  return useSWR<any[]>(
    swrKeys.weeklyChart(),
    () => dataAPI.getWeeklyChartData(),
    { ...defaultConfig, ...config }
  )
}

// ========================================================
// 用户/资产/PK池
// ========================================================
export function useUsers(config?: SWRConfiguration) {
  return useSWR<any[]>(
    swrKeys.users(),
    () => userAPI.getAll(),
    { ...defaultConfig, ...config }
  )
}

export function useAssets(
  params?: { user_id?: number; asset_type?: string },
  config?: SWRConfiguration
) {
  return useSWR<any[]>(
    swrKeys.assets(params),
    () => assetAPI.getAll(params),
    { ...defaultConfig, ...config }
  )
}

export function usePKPools(config?: SWRConfiguration) {
  return useSWR<any[]>(
    swrKeys.pkPools(),
    () => pkPoolAPI.getAll(),
    { ...defaultConfig, ...config }
  )
}

// ========================================================
// 缓存失效辅助函数
// ========================================================

/** 数据更新成功后，主动让所有相关缓存过期 */
export function invalidateAfterDataUpdate() {
  // 凡是 key 第一项以下面这些前缀开头的，都重新拉取
  const prefixes = [
    "ranking/all",
    "ranking/assets",
    "ranking/users",
    "ranking/weekly",
    "data/snapshot",
    "data/charts/all",
    "data/charts/weekly",
  ]
  return globalMutate(
    (key) => Array.isArray(key) && typeof key[0] === "string" && prefixes.some((p) => (key[0] as string).startsWith(p)),
    undefined,
    { revalidate: true }
  )
}

/** 用户/资产数据修改后，刷新对应缓存 */
export function invalidateUsersAndAssets() {
  return globalMutate(
    (key) =>
      Array.isArray(key) &&
      typeof key[0] === "string" &&
      (key[0] === "users" || key[0] === "assets" || (key[0] as string).startsWith("ranking")),
    undefined,
    { revalidate: true }
  )
}
