"use client"

import { useState } from "react"
import { Info } from "lucide-react"
import { MiniHistogram } from "./MiniHistogram"

interface StabilityTooltipProps {
  stabilityScore: number | null | undefined
  annualVolatility: number | null | undefined
  dailyReturns: number[] | null | undefined
  children?: React.ReactNode
}

/**
 * 稳健度Tooltip组件
 * 显示稳健性评分、年化波动率和收益分布直方图
 */
export function StabilityTooltip({
  stabilityScore,
  annualVolatility,
  dailyReturns,
  children,
}: StabilityTooltipProps) {
  const [isOpen, setIsOpen] = useState(false)

  // 如果没有稳健度数据，显示默认内容
  if (stabilityScore === null || stabilityScore === undefined) {
    return <span className="text-muted-foreground">--</span>
  }

  return (
    <div className="relative inline-block">
      <div
        className="flex items-center gap-1 cursor-pointer hover:opacity-80"
        onMouseEnter={() => setIsOpen(true)}
        onMouseLeave={() => setIsOpen(false)}
      >
        {children || (
          <>
            <span>{stabilityScore.toFixed(2)}</span>
            <Info className="w-4 h-4 text-blue-500" />
          </>
        )}
      </div>

      {isOpen && (
        <div
          className="absolute z-50 bg-white border border-gray-200 rounded-lg shadow-lg p-4 w-64"
          style={{
            top: "calc(100% + 8px)",
            left: "50%",
            transform: "translateX(-50%)",
          }}
          onMouseEnter={() => setIsOpen(true)}
          onMouseLeave={() => setIsOpen(false)}
        >
          {/* 标题 */}
          <h4 className="text-sm font-bold mb-3 text-gray-900">稳健性深度分析</h4>

          {/* 数值显示 */}
          <div className="space-y-2 mb-3">
            <div className="flex justify-between text-sm">
              <span className="text-gray-600">稳健性评分：</span>
              <span className="font-semibold text-gray-900">{stabilityScore.toFixed(2)}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-600">年化波动率：</span>
              <span className="font-semibold text-gray-900">
                {annualVolatility !== null && annualVolatility !== undefined
                  ? `${annualVolatility.toFixed(2)}%`
                  : "--"}
              </span>
            </div>
          </div>

          {/* 公式展示 */}
          <div className="mb-3 p-2 bg-gray-50 rounded text-xs text-gray-700">
            <div className="font-mono">Score = 100 × (1 - σ)</div>
            <div className="text-[10px] text-gray-500 mt-1">σ为年化波动率</div>
          </div>

          {/* 直方图 */}
          {dailyReturns && dailyReturns.length > 0 && (
            <div>
              <div className="text-xs font-semibold text-gray-600 mb-2">20日收益分布</div>
              <div className="flex justify-center">
                <MiniHistogram dailyReturns={dailyReturns} width={220} height={80} />
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
