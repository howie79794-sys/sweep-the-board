import type { Config } from "tailwindcss"

const config = {
  darkMode: ["class"],
  content: [
    './pages/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './app/**/*.{ts,tsx}',
    './src/**/*.{ts,tsx}',
    './lib/**/*.{ts,tsx}',
  ],
  // 兜底 safelist：动态/工具函数返回的 class 必须显式列出
  // （Tailwind JIT 静态扫描可能识别不到字符串模板里的 class）
  safelist: [
    // 涨跌热力色（getHeatmapColor）
    "bg-red-100", "bg-red-300", "bg-red-500", "bg-red-600",
    "bg-green-100", "bg-green-300", "bg-green-500", "bg-green-600",
    "text-red-700", "text-red-900", "text-green-700", "text-green-900",
    // 涨跌文字色（getChangeColor）
    "text-red-600", "text-green-600",
    // 奖牌徽章（getMedalConfig）
    "ring-amber-400", "ring-slate-400", "ring-orange-400",
    "ring-amber-300", "ring-slate-300", "ring-orange-300",
    "border-amber-400", "border-slate-400", "border-orange-400",
    "text-amber-700", "text-slate-700", "text-orange-700",
    // 奖牌渐变背景（getMedalConfig）
    "bg-gradient-to-br",
    "from-yellow-50", "via-amber-50", "to-orange-100",
    "from-slate-50", "via-zinc-50", "to-slate-100",
    "from-orange-50", "to-yellow-100",
    // bg-muted 兜底（中性色 / 0%）
    "bg-muted", "text-muted-foreground",
  ],
  prefix: "",
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: {
        "2xl": "1400px",
      },
    },
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      keyframes: {
        "accordion-down": {
          from: { height: "0" },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: "0" },
        },
        "bounce-slow": {
          "0%, 100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-3px)" },
        },
        "shimmer": {
          "100%": { transform: "translateX(100%)" },
        },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
        "bounce-slow": "bounce-slow 2.5s ease-in-out infinite",
        "shimmer": "shimmer 2s linear infinite",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
} satisfies Config

export default config
