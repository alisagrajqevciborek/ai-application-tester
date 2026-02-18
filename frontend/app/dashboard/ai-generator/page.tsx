"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { motion } from "framer-motion"
import { ArrowLeft, BarChart3, Home } from "lucide-react"
import { Button } from "@/components/ui/button"
import TopNav from "@/components/dashboard/top-nav"
import { useAuth } from "@/contexts/AuthContext"
import { useData } from "@/contexts/DataContext"
import { Loader2 } from "lucide-react"
import type { TestHistory } from "@/lib/types"
import dynamic from "next/dynamic"

const StatisticsModal = dynamic(() => import("@/components/charts/statistics-modal"), {
  ssr: false,
})

const AITestCaseGenerator = dynamic(() => import("@/components/dashboard/ai-test-case-generator"), {
  loading: () => <div className="flex items-center justify-center min-h-[200px]"><Loader2 className="w-8 h-8 animate-spin text-primary" /></div>
})

export default function AIGeneratorPage() {
  const { isAuthenticated, isLoading, user } = useAuth()
  const { applications, stats, isLoading: isLoadingData, forceRefresh } = useData()
  const router = useRouter()
  const [statsModalOpen, setStatsModalOpen] = useState(false)

  useEffect(() => {
    if (!isLoading) {
      if (!isAuthenticated) {
        router.push('/login')
      } else if (user?.role === 'admin') {
        router.push('/admin')
      }
    }
  }, [isAuthenticated, isLoading, user, router])

  if (isLoading || !isAuthenticated || user?.role === 'admin') {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    )
  }

  const handleTestComplete = async (test: TestHistory) => {
    // Force refresh so dashboard shows the new test immediately
    await forceRefresh()
    router.push(`/dashboard/reports/${test.id}`)
  }

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <TopNav />
      
      <main className="flex-1 overflow-auto p-6 lg:p-8">
        <div className="max-w-6xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.2 }}
            className="space-y-8"
          >
            {/* Header */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  onClick={() => router.push('/dashboard')}
                  className="flex items-center gap-2 text-muted-foreground hover:text-foreground"
                >
                  <ArrowLeft className="h-4 w-4" />
                  <span>Back</span>
                </Button>
                <Button
                  variant="outline"
                  size="icon"
                  onClick={() => router.push('/dashboard')}
                  className="text-muted-foreground hover:text-foreground"
                  title="Go to Dashboard"
                >
                  <Home className="h-4 w-4" />
                </Button>
              </div>

              <Button
                onClick={() => setStatsModalOpen(true)}
                className="flex items-center gap-2"
              >
                <BarChart3 className="h-5 w-5" />
                <span>View Statistics</span>
              </Button>
            </div>

            {/* Page Title */}
            <div>
              <h1 className="text-3xl font-bold text-foreground mb-2">AI Test Case Generator</h1>
              <p className="text-muted-foreground">
                Describe what you want to test in natural language, and AI will generate a complete test case
              </p>
            </div>

            {/* AI Test Case Generator */}
            {isLoadingData ? (
              <div className="flex items-center justify-center min-h-[400px]">
                <Loader2 className="w-8 h-8 animate-spin text-primary" />
              </div>
            ) : (
              <AITestCaseGenerator
                application={applications.length > 0 ? applications[0] : null}
                applications={applications}
                onTestCaseGenerated={(testCase) => {
                  console.log("Test case generated:", testCase)
                }}
                onTestComplete={handleTestComplete}
              />
            )}
          </motion.div>
        </div>
      </main>

      {/* Statistics Modal */}
      <StatisticsModal
        open={statsModalOpen}
        onOpenChange={setStatsModalOpen}
        stats={stats}
      />
    </div>
  )
}
