"use client"

import { useState, useEffect } from "react"
import { motion, AnimatePresence } from "framer-motion"
import TopNav from "@/components/top-nav"
import Sidebar from "@/components/sidebar"
import NewTestForm from "@/components/new-test-form"
import ReportView from "@/components/report-view"
import type { TestHistory } from "@/lib/types"
import { applicationsApi, testRunsApi, type Application, type TestRun } from "@/lib/api"
import { Loader2 } from "lucide-react"

// Helper to convert TestRun to TestHistory
const convertTestRunToHistory = (testRun: TestRun): TestHistory => {
  return {
    id: testRun.id.toString(),
    appName: testRun.application_name,
    status: testRun.status === 'success' ? 'success' : testRun.status === 'failed' ? 'failed' : 'running',
    testType: testRun.test_type,
    date: new Date(testRun.started_at).toISOString().split("T")[0],
    passRate: testRun.pass_rate,
    failRate: testRun.fail_rate,
  }
}

export default function Dashboard() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [selectedTest, setSelectedTest] = useState<TestHistory | null>(null)
  const [history, setHistory] = useState<TestHistory[]>([])
  const [applications, setApplications] = useState<Application[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadApplications()
    loadTestRuns()
  }, [])

  const loadApplications = async () => {
    try {
      setIsLoading(true)
      setError(null)
      const apps = await applicationsApi.list()
      setApplications(apps)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load applications")
    } finally {
      setIsLoading(false)
    }
  }

  const loadTestRuns = async () => {
    try {
      const testRuns = await testRunsApi.list()
      const testHistory = testRuns.map(convertTestRunToHistory)
      setHistory(testHistory)
      
      // Poll for running tests
      const runningTests = testRuns.filter(tr => tr.status === 'running' || tr.status === 'pending')
      if (runningTests.length > 0) {
        const pollInterval = setInterval(async () => {
          try {
            const updatedRuns = await Promise.all(
              runningTests.map(tr => testRunsApi.get(tr.id))
            )
            const updatedHistory = updatedRuns.map(convertTestRunToHistory)
            const allRuns = await testRunsApi.list()
            const allHistory = allRuns.map(convertTestRunToHistory)
            setHistory(allHistory)
            
            // Stop polling if no running tests
            const stillRunning = updatedRuns.filter(tr => tr.status === 'running' || tr.status === 'pending')
            if (stillRunning.length === 0) {
              clearInterval(pollInterval)
            }
          } catch (err) {
            console.error("Error polling test runs:", err)
            clearInterval(pollInterval)
          }
        }, 2000) // Poll every 2 seconds
        
        // Cleanup after 60 seconds
        setTimeout(() => clearInterval(pollInterval), 60000)
      }
    } catch (err) {
      console.error("Failed to load test runs:", err)
    }
  }

  const handleNewTestComplete = (newTest: TestHistory) => {
    setHistory([newTest, ...history])
    setSelectedTest(newTest)
    // Reload test runs to get latest data
    loadTestRuns()
    // Reload applications after creating a new one
    loadApplications()
  }

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <TopNav />

      <div className="flex flex-1 overflow-hidden">
        <Sidebar
          collapsed={sidebarCollapsed}
          onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
          history={history}
          selectedId={selectedTest?.id || null}
          onSelectTest={setSelectedTest}
        />

        <main className="flex-1 overflow-auto p-6 lg:p-8">
          {isLoading ? (
            <div className="flex items-center justify-center min-h-[400px]">
              <Loader2 className="w-8 h-8 animate-spin text-primary" />
            </div>
          ) : error ? (
            <div className="max-w-2xl mx-auto">
              <div className="glass rounded-2xl p-6 text-center">
                <p className="text-destructive mb-4">{error}</p>
                <button
                  onClick={loadApplications}
                  className="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90"
                >
                  Retry
                </button>
              </div>
            </div>
          ) : (
            <AnimatePresence mode="wait">
              {selectedTest ? (
                <motion.div
                  key="report"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  transition={{ duration: 0.2 }}
                >
                  <ReportView test={selectedTest} onBack={() => setSelectedTest(null)} />
                </motion.div>
              ) : (
                <motion.div
                  key="new-test"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  transition={{ duration: 0.2 }}
                >
                  <NewTestForm onTestComplete={handleNewTestComplete} applications={applications} />
                </motion.div>
              )}
            </AnimatePresence>
          )}
        </main>
      </div>
    </div>
  )
}
