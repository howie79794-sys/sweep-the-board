"use client"

import { useState, useRef, useEffect } from "react"
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
 * 优化：向左弹出，自动避让，限制宽度，毛玻璃效果
 */
export function StabilityTooltip({
  stabilityScore,
  annualVolatility,
  dailyReturns,
  children,
}: StabilityTooltipProps) {
  const [isOpen, setIsOpen] = useState(false)
  const tooltipRef = useRef<HTMLDivElement>(null)
  const triggerRef = useRef<HTMLDivElement>(null)

  // 如果没有稳健度数据，显示默认内容
  if (stabilityScore === null || stabilityScore === undefined) {
    return <span className="text-muted-foreground">--</span>
  }

  // 碰撞检测和自动避让
  useEffect(() => {
    if (!isOpen || !tooltipRef.current || !triggerRef.current) return

    const updatePosition = () => {
      const tooltip = tooltipRef.current
      const trigger = triggerRef.current
      if (!tooltip || !trigger) return

      // 先设置默认位置（向左弹出），然后测量
      tooltip.style.visibility = "hidden"
      tooltip.style.top = "50%"
      tooltip.style.right = "calc(100% + 10px)"
      tooltip.style.left = "auto"
      tooltip.style.bottom = "auto"
      tooltip.style.transform = "translateY(-50%)"

      // 强制重排以获取实际尺寸
      void tooltip.offsetHeight

      const tooltipRect = tooltip.getBoundingClientRect()
      const triggerRect = trigger.getBoundingClientRect()
      const viewportHeight = window.innerHeight

      // 水平方向碰撞检测（默认向左弹出）
      const spaceOnLeft = triggerRect.left
      const tooltipWidth = tooltipRect.width || 240

      if (spaceOnLeft >= tooltipWidth + 20) {
        // 左侧有足够空间，保持向左弹出
        tooltip.style.right = "calc(100% + 10px)"
        tooltip.style.left = "auto"
      } else {
        // 左侧空间不足，改为右侧弹出
        tooltip.style.right = "auto"
        tooltip.style.left = "calc(100% + 10px)"
      }

      // 垂直方向碰撞检测
      const tooltipHeight = tooltipRect.height || 300
      const spaceAbove = triggerRect.top
      const spaceBelow = viewportHeight - triggerRect.bottom

      if (spaceBelow < tooltipHeight && spaceAbove > spaceBelow) {
        // 下方空间不足，且上方空间更大，改为向上弹出
        tooltip.style.top = "auto"
        tooltip.style.bottom = "calc(100% + 10px)"
        tooltip.style.transform = "translateY(0)"
      } else if (spaceAbove < tooltipHeight && spaceBelow > spaceAbove) {
        // 上方空间不足，且下方空间更大，改为向下弹出
        tooltip.style.top = "calc(100% + 10px)"
        tooltip.style.bottom = "auto"
        tooltip.style.transform = "translateY(0)"
      } else {
        // 默认垂直居中
        tooltip.style.top = "50%"
        tooltip.style.bottom = "auto"
        tooltip.style.transform = "translateY(-50%)"
      }

      tooltip.style.visibility = "visible"
    }

    // 使用 requestAnimationFrame 确保 DOM 已更新
    const timeoutId = setTimeout(() => {
      updatePosition()
    }, 0)

    // 监听窗口大小变化和滚动
    window.addEventListener("resize", updatePosition)
    window.addEventListener("scroll", updatePosition, true)

    return () => {
      clearTimeout(timeoutId)
      window.removeEventListener("resize", updatePosition)
      window.removeEventListener("scroll", updatePosition, true)
    }
  }, [isOpen])

  return (
    <div className="relative inline-block">
      <div
        ref={triggerRef}
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
          ref={tooltipRef}
          className="absolute z-50 bg-white/95 backdrop-blur-sm border border-gray-200 rounded-lg shadow-xl p-4 max-w-[240px]"
          style={{
            top: "50%",
            right: "calc(100% + 10px)",
            transform: "translateY(-50%)",
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
                <MiniHistogram dailyReturns={dailyReturns} width={200} height={80} />
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
