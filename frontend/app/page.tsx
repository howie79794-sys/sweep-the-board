"use client"

import { DragonTigerBoard } from "@/components/DragonTigerBoard"
import { AllAssetsChart } from "@/components/AllAssetsChart"
import { PERatioChart } from "@/components/PERatioChart"
import { PBRatioChart } from "@/components/PBRatioChart"
import { AssetSnapshotTable } from "@/components/AssetSnapshotTable"

export default function Home() {
  return (
    <div className="space-y-8 p-6">
      {/* 核心资产龙虎榜 */}
      <div>
        <DragonTigerBoard />
      </div>

      {/* 收益率走势图 */}
      <div className="border rounded-lg p-6">
        <AllAssetsChart showChangeRate={true} />
      </div>

      {/* 收盘价走势图 */}
      <div className="border rounded-lg p-6">
        <AllAssetsChart showChangeRate={false} />
      </div>

      {/* 市盈率 (P/E) 趋势图 */}
      <div className="border rounded-lg p-6">
        <PERatioChart />
      </div>

      {/* 市净率 (P/B) 趋势图 */}
      <div className="border rounded-lg p-6">
        <PBRatioChart />
      </div>

      {/* 核心资产明细表 */}
      <div className="border rounded-lg p-6">
        <AssetSnapshotTable />
      </div>
    </div>
  )
}
