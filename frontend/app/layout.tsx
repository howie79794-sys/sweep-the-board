import type { Metadata, Viewport } from "next"
import { Inter } from "next/font/google"
import "./globals.css"

const inter = Inter({ subsets: ["latin"] })

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "https://sweep-the-board.vercel.app"
const siteTitle = "CoolDown 龙虎榜 · 金融资产年度涨幅 PK 平台"
const siteDescription =
  "CoolDown 龙虎榜：跟踪 A 股、基金、期货等多类金融资产的年度涨幅，多人 PK 比拼，实时排行榜与可视化图表。"

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: {
    default: siteTitle,
    template: "%s | CoolDown 龙虎榜",
  },
  description: siteDescription,
  keywords: [
    "龙虎榜",
    "金融资产排行",
    "股票涨幅",
    "PK 比拼",
    "投资比赛",
    "A股",
    "基金",
    "期货",
    "CoolDown",
  ],
  authors: [{ name: "howie79794-sys" }],
  creator: "howie79794-sys",
  alternates: {
    canonical: "/",
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-image-preview": "large",
      "max-snippet": -1,
    },
  },
  openGraph: {
    type: "website",
    locale: "zh_CN",
    url: siteUrl,
    siteName: "CoolDown 龙虎榜",
    title: siteTitle,
    description: siteDescription,
    images: [
      {
        url: "/og-image.png",
        width: 1200,
        height: 630,
        alt: "CoolDown 龙虎榜",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: siteTitle,
    description: siteDescription,
    images: ["/og-image.png"],
  },
  formatDetection: {
    email: false,
    address: false,
    telephone: false,
  },
}

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#ffffff" },
    { media: "(prefers-color-scheme: dark)", color: "#0a0a0a" },
  ],
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
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
            <div className="container mx-auto px-4 py-3 md:py-4">
              <div className="flex items-center justify-between gap-2 flex-wrap">
                <div className="min-w-0">
                  <h1 className="text-xl md:text-3xl font-bold truncate">CoolDown龙虎榜</h1>
                  <p className="text-xs md:text-sm text-muted-foreground mt-0.5 md:mt-1">金融资产排行榜</p>
                </div>
                <nav className="flex gap-1 md:gap-4 text-sm shrink-0">
                  <a
                    href="/"
                    className="px-2 md:px-4 py-2 rounded hover:bg-secondary transition-colors"
                  >
                    首页
                  </a>
                  <a
                    href="/pk-pools"
                    className="px-2 md:px-4 py-2 rounded hover:bg-secondary transition-colors"
                  >
                    自定义 PK
                  </a>
                  <a
                    href="/admin"
                    className="px-2 md:px-4 py-2 rounded hover:bg-secondary transition-colors"
                  >
                    管理
                  </a>
                </nav>
              </div>
            </div>
          </header>
          <main className="w-full px-4 py-8">
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
