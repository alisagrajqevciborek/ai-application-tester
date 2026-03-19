import type React from "react"
import type { Metadata } from "next"
import { Inter, Geist_Mono, Sora } from "next/font/google"
import { Analytics } from "@vercel/analytics/next"
import { AuthProvider } from "@/contexts/AuthContext"
import { DataProvider } from "@/contexts/DataContext"
import { ActiveTestsProvider } from "@/contexts/ActiveTestsContext"
import ActiveTestsWidget from "@/components/active-tests-widget"
import { ThemeProvider } from "@/components/theme-provider"
import ThemeToggle from "@/components/theme-toggle"
import { Toaster as SonnerToaster } from "@/components/ui/sonner"
import { Toaster } from "@/components/ui/toaster"
import "./globals.css"

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" })
const geistMono = Geist_Mono({ subsets: ["latin"] })
const sora = Sora({ subsets: ["latin"], variable: "--font-sora", weight: ["600", "700", "800"] })

export const metadata: Metadata = {
  title: "TestFlow - AI-Powered Application Testing",
  description: "Intelligent automated testing powered by AI",
  generator: 'v0.app'
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.className} ${sora.variable} font-sans antialiased`}>
        <ThemeProvider attribute="class" defaultTheme="dark" enableSystem={false}>
          <AuthProvider>
            <DataProvider>
              <ActiveTestsProvider>
                {children}
                <ActiveTestsWidget />
                <ThemeToggle />
              </ActiveTestsProvider>
            </DataProvider>
          </AuthProvider>
          <Toaster />
          <SonnerToaster />
        </ThemeProvider>
        <Analytics />
      </body>
    </html>
  )
}
