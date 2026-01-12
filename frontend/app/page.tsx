"use client"

import { DragonTigerBoard } from "@/components/DragonTigerBoard"
import { AllAssetsChart } from "@/components/AllAssetsChart"

export default function Home() {
  return (
    <div className="space-y-8 p-6">
      {/* 龙虎榜 */}
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
    </div>
  )
}
