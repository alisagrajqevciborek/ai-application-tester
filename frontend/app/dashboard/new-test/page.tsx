"use client"

import { useEffect, useState, useCallback } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { motion } from "framer-motion"
import { ArrowLeft, BarChart3, Home } from "lucide-react"
import { Button } from "@/components/ui/button"
import NewTestForm from "@/components/dashboard/new-test-form"
import TopNav from "@/components/dashboard/top-nav"
import { useAuth } from "@/contexts/AuthContext"
import { applicationsApi, testRunsApi, type Application, type TestRunStats } from "@/lib/api"
import { Loader2 } from "lucide-react"
import type { TestHistory } from "@/lib/types"
import dynamic from "next/dynamic"

const StatisticsModal = dynamic(() => import("@/components/charts/statistics-modal"), {
  ssr: false,
})

export default function NewTestPage() {
  const { isAuthenticated, isLoading, user } = useAuth()
  const router = useRouter()
  const searchParams = useSearchParams()
  const [applications, setApplications] = useState<Application[]>([])
  const [stats, setStats] = useState<TestRunStats | null>(null)
  const [statsModalOpen, setStatsModalOpen] = useState(false)
  const [isLoadingApps, setIsLoadingApps] = useState(true)

  // Get URL params for pre-filling the form
  const initialAppName = searchParams.get('app')
  const initialTestType = searchParams.get('testType') as any

  useEffect(() => {
    if (!isLoading) {
      if (!isAuthenticated) {
        router.push('/login')
      } else if (user?.role === 'admin') {
        router.push('/admin')
      }
    }
  }, [isAuthenticated, isLoading, user, router])

  const loadApplications = useCallback(async () => {
    try {
      setIsLoadingApps(true)
      const apps = await applicationsApi.list()
      setApplications(apps || [])
    } catch (err) {
      console.error("Error loading applications:", err)
      setApplications([])
    } finally {
      setIsLoadingApps(false)
    }
  }, [])

  const loadStats = useCallback(async () => {
    try {
      const statsData = await testRunsApi.stats()
      setStats(statsData)
    } catch (err) {
      console.error("Error loading stats:", err)
    }
  }, [])

  useEffect(() => {
    if (isAuthenticated) {
      loadApplications()
      loadStats()
    }
  }, [isAuthenticated, loadApplications, loadStats])

  if (isLoading || !isAuthenticated || user?.role === 'admin') {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    )
  }

  const handleTestComplete = async (test: TestHistory) => {
    // Navigate to the test report
    router.push(`/dashboard/reports/${test.id}`)
  }

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <TopNav />
      
      <main className="flex-1 overflow-auto p-6 lg:p-8">
        <div className="max-w-4xl mx-auto">
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

            {/* New Test Form */}
            {isLoadingApps ? (
              <div className="flex items-center justify-center min-h-[400px]">
                <Loader2 className="w-8 h-8 animate-spin text-primary" />
              </div>
            ) : (
              <NewTestForm
                onTestComplete={handleTestComplete}
                applications={applications}
                initialAppName={initialAppName || undefined}
                initialTestType={initialTestType}
                autoStart={false}
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
