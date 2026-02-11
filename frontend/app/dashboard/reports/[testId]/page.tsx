"use client"

import { useEffect, useState, useCallback } from "react"
import { useRouter, useParams } from "next/navigation"
import { motion } from "framer-motion"
import { Home } from "lucide-react"
import { Button } from "@/components/ui/button"
import TopNav from "@/components/dashboard/top-nav"
import ReportView from "@/components/reports/report-view"
import { useAuth } from "@/contexts/AuthContext"
import { testRunsApi, type TestRun } from "@/lib/api"
import { Loader2 } from "lucide-react"
import type { TestHistory } from "@/lib/types"

// Helper to convert TestRun to TestHistory
const convertTestRunToHistory = (testRun: TestRun): TestHistory => {
  return {
    id: testRun.id.toString(),
    appName: testRun.application_name,
    versionName: testRun.version_name,
    version: testRun.version,
    status: testRun.status === 'success' ? 'success' : testRun.status === 'failed' ? 'failed' : 'running',
    testType: testRun.test_type,
    date: new Date(testRun.started_at).toISOString().split("T")[0],
    passRate: testRun.pass_rate,
    failRate: testRun.fail_rate,
  }
}

export default function ReportPage() {
  const { isAuthenticated, isLoading, user } = useAuth()
  const router = useRouter()
  const params = useParams()
  const testId = params.testId as string
  
  const [test, setTest] = useState<TestHistory | null>(null)
  const [isLoadingTest, setIsLoadingTest] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!isLoading) {
      if (!isAuthenticated) {
        router.push('/login')
      } else if (user?.role === 'admin') {
        router.push('/admin')
      }
    }
  }, [isAuthenticated, isLoading, user, router])

  const loadTest = useCallback(async () => {
    try {
      setIsLoadingTest(true)
      setError(null)
      const testRun = await testRunsApi.get(parseInt(testId))
      const testHistory = convertTestRunToHistory(testRun)
      setTest(testHistory)
    } catch (err) {
      console.error("Failed to load test:", err)
      setError(err instanceof Error ? err.message : "Failed to load test")
    } finally {
      setIsLoadingTest(false)
    }
  }, [testId])

  useEffect(() => {
    if (isAuthenticated) {
      loadTest()
    }
  }, [isAuthenticated, loadTest])

  if (isLoading || !isAuthenticated || user?.role === 'admin') {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    )
  }

  const handleBack = () => {
    // Go back to the app's versions page
    if (test) {
      router.push(`/dashboard/apps/${encodeURIComponent(test.appName)}`)
    } else {
      router.push('/dashboard')
    }
  }

  const handleDelete = async (testId: string) => {
    try {
      await testRunsApi.delete(parseInt(testId))
      // Navigate back to dashboard after deletion
      router.push('/dashboard')
    } catch (err) {
      console.error("Failed to delete test:", err)
    }
  }

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <TopNav />
      
      <main className="flex-1 overflow-auto p-6 lg:p-8">
        {/* Home Button */}
        {!isLoadingTest && !error && test && (
          <div className="mb-4">
            <Button
              variant="outline"
              size="sm"
              onClick={() => router.push('/dashboard')}
              className="flex items-center gap-2 text-muted-foreground hover:text-foreground"
            >
              <Home className="h-4 w-4" />
              <span>Dashboard</span>
            </Button>
          </div>
        )}
        
        {isLoadingTest ? (
          <div className="flex items-center justify-center min-h-[400px]">
            <Loader2 className="w-8 h-8 animate-spin text-primary" />
          </div>
        ) : error ? (
          <div className="max-w-2xl mx-auto">
            <div className="glass rounded-2xl p-6 text-center">
              <p className="text-destructive mb-4">{error}</p>
              <button
                onClick={loadTest}
                className="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90"
              >
                Retry
              </button>
            </div>
          </div>
        ) : test ? (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.2 }}
          >
            <ReportView
              test={test}
              onBack={handleBack}
              onDelete={handleDelete}
            />
          </motion.div>
        ) : (
          <div className="text-center py-12">
            <p className="text-muted-foreground">Test not found</p>
          </div>
        )}
      </main>
    </div>
  )
}
