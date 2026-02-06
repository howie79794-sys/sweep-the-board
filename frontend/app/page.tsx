"use client"

import { useState } from "react"
import { DragonTigerBoard } from "@/components/DragonTigerBoard"
import { AllAssetsChart } from "@/components/AllAssetsChart"
import { WeeklyReturnChart } from "@/components/WeeklyReturnChart"
import { PERatioChart } from "@/components/PERatioChart"
import { PBRatioChart } from "@/components/PBRatioChart"
import { AssetSnapshotTable } from "@/components/AssetSnapshotTable"
import { WeeklySidebar } from "@/components/WeeklySidebar"
import { cn } from "@/lib/utils"

const HOME_CHARTS_GROUP_ID = "home-charts"

export default function Home() {
  const [chartRange, setChartRange] = useState<{ startIndex: number; endIndex: number } | null>(null)
  const [moreChartsOpen, setMoreChartsOpen] = useState(false)

  const handleChartRangeChange = (startIndex: number, endIndex: number) => {
    setChartRange({ startIndex, endIndex })
  }

  return (
    <div className="flex gap-4 pl-2 pr-6 py-6 -ml-4">
      {/* 自然周榜单侧边栏：宽度约 240px，lg 以下隐藏，靠左 */}
      <WeeklySidebar />

      <div className="flex-1 min-w-0 flex flex-col">
      {/* 龙虎榜 + 年度图 + 周收益曲线区域 */}
      <div className="flex-1 space-y-8">
      {/* 核心资产龙虎榜 */}
      <div className="flex flex-col items-center">
        <DragonTigerBoard />
      </div>

      {/* 年度收益率追踪图 */}
      <div className="border rounded-lg p-6">
        <AllAssetsChart
          showChangeRate={true}
          chartRange={chartRange ?? undefined}
          onChartRangeChange={handleChartRangeChange}
          groupId={HOME_CHARTS_GROUP_ID}
        />
      </div>

      {/* 周收益曲线（以自然周为维度） */}
      <div className="border rounded-lg p-6">
        <WeeklyReturnChart />
      </div>
      </div>

      {/* 折叠区域：更多分析图表，默认折叠 */}
      <div className="mt-8">
        <button
          type="button"
          onClick={() => setMoreChartsOpen((o) => !o)}
          className={cn(
            "w-full py-3 px-4 rounded-lg border text-sm font-medium transition-colors",
            "bg-muted/50 hover:bg-muted border-border text-foreground"
          )}
        >
          {moreChartsOpen ? "收起详细数据分析" : "展开详细数据分析"}
        </button>
        {moreChartsOpen && (
          <div className="space-y-8 mt-4">
            {/* 股价对数趋势分析图 */}
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
        )}
      </div>
      </div>
    </div>
  )
}
