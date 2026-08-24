import { HomeClient, type HomeInitialData } from "@/components/HomeClient"

/**
 * 首页：ISR（增量静态再生）
 * - 每 15 分钟在服务端预取全部首屏数据，HTML 直接带内容（不再白屏等 3 秒）
 * - 预取失败（如后端暂时不可用）时降级为客户端渲染，不影响可用性
 */
export const revalidate = 900

const API_BASE =
  process.env.API_BASE_URL ||
  (process.env.NODE_ENV === "development"
    ? "http://localhost:8000"
    : "https://sweep-the-board-api.vercel.app")

async function safeFetch<T>(path: string): Promise<T | null> {
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      next: { revalidate: 900 },
    })
    if (!res.ok) return null
    return (await res.json()) as T
  } catch {
    return null
  }
}

export default async function Home() {
  const [rankings, weeklyRankings, snapshot, allChart, weeklyChart] =
    await Promise.all([
      safeFetch("/api/ranking"),
      safeFetch<{ items: any[] }>("/api/ranking/weekly"),
      safeFetch<any[]>("/api/data/snapshot"),
      safeFetch<any[]>("/api/data/charts/all"),
      safeFetch<any[]>("/api/data/charts/weekly"),
    ])

  const initialData: HomeInitialData = {
    rankings,
    weeklyRankings,
    snapshot,
    allChart,
    weeklyChart,
  }

  return <HomeClient initialData={initialData} />
}
