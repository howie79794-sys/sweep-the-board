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

/** 首页服务端预取的数据集（page.tsx ISR 拉取后传入） */
export interface HomeInitialData {
  rankings?: any | null
  weeklyRankings?: { items: any[] } | null
  snapshot?: any[] | null
  allChart?: any[] | null
  weeklyChart?: any[] | null
}

export function HomeClient({ initialData }: { initialData: HomeInitialData }) {
  const [chartRange, setChartRange] = useState<{ startIndex: number; endIndex: number } | null>(null)
  const [moreChartsOpen, setMoreChartsOpen] = useState(false)
  /** 全局选中的资产代码：左侧榜单、年度图、周收益图联动高亮 */
  const [selectedAssetCode, setSelectedAssetCode] = useState<string | null>(null)

  const handleChartRangeChange = (startIndex: number, endIndex: number) => {
    setChartRange({ startIndex, endIndex })
  }

  return (
    <div className="flex flex-col lg:flex-row gap-4 py-4 lg:py-6 lg:pl-2 lg:pr-6 lg:-ml-4">
      {/* 自然周榜单：移动端为顶部横向滚动条，lg 以上为左侧 240px 侧栏 */}
      <WeeklySidebar
        selectedAssetCode={selectedAssetCode}
        onSelectAssetCode={setSelectedAssetCode}
        initialData={initialData.weeklyRankings ?? undefined}
      />

      <div className="flex-1 min-w-0 flex flex-col">
      {/* 龙虎榜 + 年度图 + 周收益曲线区域 */}
      <div className="flex-1 space-y-6 lg:space-y-8">
      {/* 核心资产龙虎榜 */}
      <div className="flex flex-col items-center">
        <DragonTigerBoard initialData={initialData.rankings ?? undefined} />
      </div>

      {/* 年度收益率追踪图 */}
      <div className="border rounded-lg p-3 md:p-6">
        <AllAssetsChart
          showChangeRate={true}
          chartRange={chartRange ?? undefined}
          onChartRangeChange={handleChartRangeChange}
          groupId={HOME_CHARTS_GROUP_ID}
          selectedAssetCode={selectedAssetCode}
          onSelectedAssetCodeChange={setSelectedAssetCode}
          initialData={initialData.allChart ?? undefined}
        />
      </div>

      {/* 周收益曲线（以自然周为维度） */}
      <div className="border rounded-lg p-3 md:p-6">
        <WeeklyReturnChart
          selectedAssetCode={selectedAssetCode}
          onSelectedAssetCodeChange={setSelectedAssetCode}
          initialData={initialData.weeklyChart ?? undefined}
        />
      </div>
      </div>

      {/* 核心资产明细表：始终展示，不放入折叠 */}
      <div className="mt-6 lg:mt-8 border rounded-lg p-3 md:p-6">
        <AssetSnapshotTable initialData={initialData.snapshot ?? undefined} />
      </div>

      {/* 折叠区域：更多分析图表，放在核心资产明细表下方，默认折叠 */}
      <div className="mt-6 lg:mt-8">
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
          <div className="space-y-6 lg:space-y-8 mt-4">
            {/* 股价对数趋势分析图 */}
            <div className="border rounded-lg p-3 md:p-6">
              <AllAssetsChart
                showChangeRate={false}
                chartRange={chartRange ?? undefined}
                onChartRangeChange={handleChartRangeChange}
                groupId={HOME_CHARTS_GROUP_ID}
                selectedAssetCode={selectedAssetCode}
                onSelectedAssetCodeChange={setSelectedAssetCode}
                initialData={initialData.allChart ?? undefined}
              />
            </div>

            {/* 市盈率 (P/E) 趋势图 */}
            <div className="border rounded-lg p-3 md:p-6">
              <PERatioChart
                chartRange={chartRange ?? undefined}
                onChartRangeChange={handleChartRangeChange}
                groupId={HOME_CHARTS_GROUP_ID}
                initialData={initialData.allChart ?? undefined}
              />
            </div>

            {/* 市净率 (P/B) 趋势图 */}
            <div className="border rounded-lg p-3 md:p-6">
              <PBRatioChart
                chartRange={chartRange ?? undefined}
                onChartRangeChange={handleChartRangeChange}
                groupId={HOME_CHARTS_GROUP_ID}
                initialData={initialData.allChart ?? undefined}
              />
            </div>
          </div>
        )}
      </div>
      </div>
    </div>
  )
}
