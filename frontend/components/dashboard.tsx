"use client"

import { useState, useEffect, useMemo } from "react"
import { motion, AnimatePresence } from "framer-motion"
import TopNav from "@/components/top-nav"
import Sidebar from "@/components/sidebar"
import NewTestForm from "@/components/new-test-form"
import ReportView from "@/components/report-view"
import ProfilePage from "@/components/profile-page"
import VersionCard from "@/components/version-card"
import type { TestHistory } from "@/lib/types"
import { applicationsApi, testRunsApi, type Application, type TestRun } from "@/lib/api"
import { Loader2, Package, ArrowLeft } from "lucide-react"

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

type View = "dashboard" | "profile"

export default function Dashboard() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [selectedTest, setSelectedTest] = useState<TestHistory | null>(null)
  const [selectedApp, setSelectedApp] = useState<string | null>(null)
  const [history, setHistory] = useState<TestHistory[]>([])
  const [applications, setApplications] = useState<Application[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [currentView, setCurrentView] = useState<View>("dashboard")

  useEffect(() => {
    loadApplications()
    loadTestRuns()
  }, [])

  const loadApplications = async () => {
    try {
      setIsLoading(true)
      setError(null)
      const apps = await applicationsApi.list()
      setApplications(apps || [])
    } catch (err) {
      console.error("Error loading applications:", err)
      setError(err instanceof Error ? err.message : "Failed to load applications")
      setApplications([]) // Set empty array on error
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
            // Get all test runs to ensure we have the latest status
            const allRuns = await testRunsApi.list()
            const allHistory = allRuns.map(convertTestRunToHistory)
            setHistory(allHistory)
            
            // Stop polling if no running tests
            const stillRunning = allRuns.filter(tr => tr.status === 'running' || tr.status === 'pending')
            if (stillRunning.length === 0) {
              clearInterval(pollInterval)
            }
          } catch (err) {
            console.error("Error polling test runs:", err)
            clearInterval(pollInterval)
          }
        }, 2000) // Poll every 2 seconds
        
        // Cleanup after 5 minutes (tests can take longer)
        setTimeout(() => clearInterval(pollInterval), 300000)
        
        // Return cleanup function
        return () => clearInterval(pollInterval)
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

  const handleDeleteTest = async (testId: string) => {
    try {
      const testToDelete = history.find(t => t.id === testId)
      await testRunsApi.delete(parseInt(testId))
      // Remove from local state
      const updatedHistory = history.filter(test => test.id !== testId)
      setHistory(updatedHistory)
      
      // If deleted test was selected, clear selection
      if (selectedTest?.id === testId) {
        setSelectedTest(null)
        // If we're viewing an app and it has no more versions, go back to apps view
        if (selectedApp && testToDelete) {
          const remainingVersions = updatedHistory.filter(t => t.appName === testToDelete.appName)
          if (remainingVersions.length === 0) {
            setSelectedApp(null)
          }
        }
      }
      // Reload to ensure sync
      loadTestRuns()
    } catch (err) {
      console.error("Failed to delete test run:", err)
      setError(err instanceof Error ? err.message : "Failed to delete test run")
    }
  }

  const handleSelectTest = (test: TestHistory) => {
    setSelectedTest(test)
    // If we're not already viewing this app, switch to it
    if (selectedApp !== test.appName) {
      setSelectedApp(test.appName)
    }
  }

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <TopNav onNavigateToProfile={() => setCurrentView("profile")} />

      {currentView === "profile" ? (
        <main className="flex-1 overflow-auto p-6 lg:p-8">
          <ProfilePage onBack={() => setCurrentView("dashboard")} />
        </main>
      ) : (
        <div className="flex flex-1 overflow-hidden">
          <Sidebar
            collapsed={sidebarCollapsed}
            onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
            history={history}
            selectedId={selectedApp}
            selectedTestId={selectedTest?.id || null}
            onSelectApp={(appName) => {
              setSelectedApp(appName)
              setSelectedTest(null)
            }}
            onSelectTest={handleSelectTest}
            onDeleteTest={handleDeleteTest}
            onBackToApps={() => {
              setSelectedApp(null)
              setSelectedTest(null)
            }}
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
                    <ReportView 
                      test={selectedTest} 
                      onBack={() => {
                        setSelectedTest(null)
                        // Stay on the app view if we have a selected app
                        if (!selectedApp) {
                          setSelectedApp(null)
                        }
                      }}
                      onDelete={handleDeleteTest}
                    />
                  </motion.div>
                ) : selectedApp ? (
                  <motion.div
                    key="versions"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -20 }}
                    transition={{ duration: 0.2 }}
                    className="space-y-6"
                  >
                    {/* App Header with Back Button */}
                    <div className="flex items-center gap-4">
                      <button
                        onClick={() => {
                          setSelectedApp(null)
                          setSelectedTest(null)
                        }}
                        className="flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors"
                      >
                        <ArrowLeft className="h-5 w-5" />
                        <span className="font-medium">Back to Apps</span>
                      </button>
                    </div>

                    {/* Version Cards for Selected App */}
                    <AppVersionsView 
                      appName={selectedApp}
                      history={history}
                      selectedTestId={selectedTest?.id || null}
                      onSelectTest={handleSelectTest}
                      onDeleteTest={handleDeleteTest}
                    />
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
      )}
    </div>
  )
}

// Component to display version cards for a specific app
interface AppVersionsViewProps {
  appName: string
  history: TestHistory[]
  selectedTestId: string | null
  onSelectTest: (test: TestHistory) => void
  onDeleteTest: (testId: string) => void
}

function AppVersionsView({ appName, history, selectedTestId, onSelectTest, onDeleteTest }: AppVersionsViewProps) {
  // Filter versions for this app and sort by version number (newest first)
  const versions = useMemo(() => {
    return history
      .filter((test) => test.appName === appName)
      .sort((a, b) => b.version - a.version)
  }, [history, appName])

  if (versions.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground">No test versions found for {appName}</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* App Header */}
      <div className="flex items-center gap-2 pb-2 border-b border-border">
        <Package className="h-5 w-5 text-orange-600" />
        <h2 className="text-xl font-semibold text-foreground">{appName}</h2>
        <span className="text-sm text-muted-foreground">({versions.length} version{versions.length !== 1 ? 's' : ''})</span>
      </div>

      {/* Version Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {versions.map((test) => (
          <VersionCard
            key={test.id}
            test={test}
            onSelect={onSelectTest}
            onDelete={onDeleteTest}
            isSelected={selectedTestId === test.id}
          />
        ))}
      </div>
    </div>
  )
}
