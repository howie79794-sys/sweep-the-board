import type { Metadata } from "next"
import { Inter } from "next/font/google"
import "./globals.css"

const inter = Inter({ subsets: ["latin"] })

export const metadata: Metadata = {
  title: "CoolDown龙虎榜",
  description: "金融资产排行榜",
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="zh-CN">
      <body className={inter.className}>
        <div className="min-h-screen bg-background">
          <header className="border-b">
            <div className="container mx-auto px-4 py-4">
              <div className="flex items-center justify-between">
                <div>
                  <h1 className="text-3xl font-bold">CoolDown龙虎榜</h1>
                  <p className="text-muted-foreground mt-1">金融资产排行榜</p>
                </div>
                <nav className="flex gap-4">
                  <a
                    href="/"
                    className="px-4 py-2 rounded hover:bg-secondary transition-colors"
                  >
                    首页
                  </a>
                  <a
                    href="/pk-pools"
                    className="px-4 py-2 rounded hover:bg-secondary transition-colors"
                  >
                    自定义 PK
                  </a>
                  <a
                    href="/admin"
                    className="px-4 py-2 rounded hover:bg-secondary transition-colors"
                  >
                    管理
                  </a>
                </nav>
              </div>
            </div>
          </header>
          <main className="container mx-auto px-4 py-8">
            {children}
          </main>
          <footer className="border-t mt-12 py-4">
            <div className="container mx-auto px-4 text-center text-muted-foreground text-sm">
              <p>数据追踪期间：2026年1月5日 - 2026年12月31日 | 基准日期：2026年1月5日</p>
            </div>
          </footer>
        </div>
      </body>
    </html>
  )
}
