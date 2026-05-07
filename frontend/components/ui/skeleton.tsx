import { cn } from "@/lib/utils"

/**
 * 骨架屏组件 - 统一加载占位
 * 用法：<Skeleton className="h-4 w-32" />
 */
export function Skeleton({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("animate-pulse rounded-md bg-muted", className)}
      {...props}
    />
  )
}

/**
 * 排行榜骨架屏（横向滚动）
 */
export function LeaderboardSkeleton() {
  return (
    <div className="flex flex-nowrap gap-3 justify-center overflow-x-auto pb-2">
      {Array.from({ length: 8 }).map((_, i) => (
        <div key={i} className="flex flex-col items-center shrink-0 w-[105px] gap-2">
          <Skeleton className="h-10 w-10 rounded-full" />
          <Skeleton className="h-3 w-16" />
          <Skeleton className="h-3 w-12" />
          <Skeleton className="h-4 w-14" />
          <Skeleton className="h-3 w-10" />
        </div>
      ))}
    </div>
  )
}

/**
 * 卡片列表骨架屏（垂直）
 */
export function CardListSkeleton({ count = 6 }: { count?: number }) {
  return (
    <div className="grid gap-4">
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="border rounded-lg p-4 flex items-center justify-between"
        >
          <div className="flex items-center gap-4 flex-1">
            <Skeleton className="h-8 w-8 rounded" />
            <div className="space-y-2 flex-1">
              <Skeleton className="h-5 w-40" />
              <Skeleton className="h-3 w-24" />
            </div>
          </div>
          <Skeleton className="h-7 w-20" />
        </div>
      ))}
    </div>
  )
}

/**
 * 表格骨架屏
 */
export function TableSkeleton({ rows = 8, cols = 5 }: { rows?: number; cols?: number }) {
  return (
    <div className="space-y-2">
      <div className="flex gap-4 border-b pb-2">
        {Array.from({ length: cols }).map((_, i) => (
          <Skeleton key={i} className="h-4 flex-1" />
        ))}
      </div>
      {Array.from({ length: rows }).map((_, r) => (
        <div key={r} className="flex gap-4 py-2">
          {Array.from({ length: cols }).map((_, c) => (
            <Skeleton key={c} className="h-4 flex-1" />
          ))}
        </div>
      ))}
    </div>
  )
}

/**
 * 图表骨架屏
 */
export function ChartSkeleton({ height = 320 }: { height?: number }) {
  return (
    <div
      className="border rounded-lg p-4 space-y-3"
      style={{ height }}
    >
      <Skeleton className="h-5 w-40" />
      <Skeleton className="h-full w-full" style={{ height: height - 60 }} />
    </div>
  )
}
