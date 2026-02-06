"use client"

import { useState } from "react"
import { DragonTigerBoard } from "@/components/DragonTigerBoard"
import { AllAssetsChart } from "@/components/AllAssetsChart"
import { PERatioChart } from "@/components/PERatioChart"
import { PBRatioChart } from "@/components/PBRatioChart"
import { AssetSnapshotTable } from "@/components/AssetSnapshotTable"
import { WeeklySidebar } from "@/components/WeeklySidebar"

const HOME_CHARTS_GROUP_ID = "home-charts"

export default function Home() {
  const [chartRange, setChartRange] = useState<{ startIndex: number; endIndex: number } | null>(null)

  const handleChartRangeChange = (startIndex: number, endIndex: number) => {
    setChartRange({ startIndex, endIndex })
  }

  return (
    <div className="flex gap-4 pl-2 pr-6 py-6 -ml-4">
      {/* 自然周榜单侧边栏：宽度约 240px，lg 以下隐藏，靠左 */}
      <WeeklySidebar />

      <div className="flex-1 min-w-0 space-y-8">
      {/* 核心资产龙虎榜 */}
      <div>
        <DragonTigerBoard />
      </div>

      {/* 收益率走势图 */}
      <div className="border rounded-lg p-6">
        <AllAssetsChart
          showChangeRate={true}
          chartRange={chartRange ?? undefined}
          onChartRangeChange={handleChartRangeChange}
          groupId={HOME_CHARTS_GROUP_ID}
        />
      </div>

      {/* 收盘价走势图 */}
      <div className="border rounded-lg p-6">
        <AllAssetsChart
          showChangeRate={false}
          chartRange={chartRange ?? undefined}
          onChartRangeChange={handleChartRangeChange}
          groupId={HOME_CHARTS_GROUP_ID}
        />
      </div>

      {/* 市盈率 (P/E) 趋势图 */}
      <div className="border rounded-lg p-6">
        <PERatioChart
          chartRange={chartRange ?? undefined}
          onChartRangeChange={handleChartRangeChange}
          groupId={HOME_CHARTS_GROUP_ID}
        />
      </div>

      {/* 市净率 (P/B) 趋势图 */}
      <div className="border rounded-lg p-6">
        <PBRatioChart
          chartRange={chartRange ?? undefined}
          onChartRangeChange={handleChartRangeChange}
          groupId={HOME_CHARTS_GROUP_ID}
        />
      </div>

      {/* 核心资产明细表 */}
      <div className="border rounded-lg p-6">
        <AssetSnapshotTable />
      </div>
      </div>
    </div>
  )
}
