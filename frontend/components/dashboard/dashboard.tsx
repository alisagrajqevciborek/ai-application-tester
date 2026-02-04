"use client"

import { useState, useEffect, useMemo, useCallback, useRef } from "react"
import { motion, AnimatePresence } from "framer-motion"
import TopNav from "@/components/dashboard/top-nav"
import Sidebar from "@/components/dashboard/sidebar"
import NewTestForm from "@/components/dashboard/new-test-form"
import VersionCard from "@/components/reports/version-card"
import type { TestHistory } from "@/lib/types"
import { applicationsApi, testRunsApi, type Application, type TestRun, type TestRunStats } from "@/lib/api"
import { Loader2, Package, ArrowLeft, BarChart3, Play, ChevronDown, Sparkles, Zap } from "lucide-react"
import { Button } from "@/components/ui/button"
import dynamic from "next/dynamic"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

// Lazy load heavy components that are conditionally rendered
const ReportView = dynamic(() => import("@/components/reports/report-view"), {
  loading: () => <div className="flex items-center justify-center min-h-[400px]"><Loader2 className="w-8 h-8 animate-spin text-primary" /></div>
})

const ProfilePage = dynamic(() => import("@/components/profile/profile-page"), {
  loading: () => <div className="flex items-center justify-center min-h-[400px]"><Loader2 className="w-8 h-8 animate-spin text-primary" /></div>
})

const StatisticsModal = dynamic(() => import("@/components/charts/statistics-modal"), {
  ssr: false,
})

const AITestCaseGenerator = dynamic(() => import("@/components/dashboard/ai-test-case-generator"), {
  loading: () => <div className="flex items-center justify-center min-h-[200px]"><Loader2 className="w-8 h-8 animate-spin text-primary" /></div>
})

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
  const [stats, setStats] = useState<TestRunStats | null>(null)
  const [statsModalOpen, setStatsModalOpen] = useState(false)
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null)
  const pollTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  const loadStats = useCallback(async () => {
    try {
      const statsData = await testRunsApi.stats()
      setStats(statsData)
    } catch (err) {
      console.error("Error loading stats:", err)
    }
  }, [])

  const loadApplications = useCallback(async () => {
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
  }, [])

  const loadTestRuns = useCallback(async () => {
    try {
      const testRuns = await testRunsApi.list()
      const testHistory = testRuns.map(convertTestRunToHistory)
      setHistory(testHistory)

      // Poll for running tests
      const runningTests = testRuns.filter(tr => tr.status === 'running' || tr.status === 'pending')
      if (runningTests.length > 0) {
        // Clear any existing polling
        if (pollIntervalRef.current) {
          clearInterval(pollIntervalRef.current)
        }
        if (pollTimeoutRef.current) {
          clearTimeout(pollTimeoutRef.current)
        }

        pollIntervalRef.current = setInterval(async () => {
          try {
            // Get all test runs to ensure we have the latest status
            const allRuns = await testRunsApi.list()
            const allHistory = allRuns.map(convertTestRunToHistory)
            setHistory(allHistory)

            // Stop polling if no running tests
            const stillRunning = allRuns.filter(tr => tr.status === 'running' || tr.status === 'pending')
            if (stillRunning.length === 0) {
              if (pollIntervalRef.current) {
                clearInterval(pollIntervalRef.current)
                pollIntervalRef.current = null
              }
              if (pollTimeoutRef.current) {
                clearTimeout(pollTimeoutRef.current)
                pollTimeoutRef.current = null
              }
            }
          } catch (err) {
            console.error("Error polling test runs:", err)
            if (pollIntervalRef.current) {
              clearInterval(pollIntervalRef.current)
              pollIntervalRef.current = null
            }
            if (pollTimeoutRef.current) {
              clearTimeout(pollTimeoutRef.current)
              pollTimeoutRef.current = null
            }
          }
        }, 2000) // Poll every 2 seconds

        // Cleanup after 5 minutes (tests can take longer)
        pollTimeoutRef.current = setTimeout(() => {
          if (pollIntervalRef.current) {
            clearInterval(pollIntervalRef.current)
            pollIntervalRef.current = null
          }
          pollTimeoutRef.current = null
        }, 300000)
      }
    } catch (err) {
      console.error("Failed to load test runs:", err)
    }
  }, [])

  useEffect(() => {
    loadApplications()
    loadTestRuns()
    loadStats()

    // Cleanup function
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current)
        pollIntervalRef.current = null
      }
      if (pollTimeoutRef.current) {
        clearTimeout(pollTimeoutRef.current)
        pollTimeoutRef.current = null
      }
    }
  }, [loadApplications, loadTestRuns, loadStats])

  const handleNewTestComplete = (newTest: TestHistory) => {
    setHistory([newTest, ...history])
    setSelectedTest(newTest)
    // Reload test runs to get latest data
    loadTestRuns()
    // Reload applications after creating a new one
    loadApplications()
    // Reload stats to update dashboard
    loadStats()
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
      // Reload stats after deletion
      loadStats()
    } catch (err) {
      console.error("Failed to delete test run:", err)
      setError(err instanceof Error ? err.message : "Failed to delete test run")
    }
  }

  const handleDeleteApp = async (applicationId: number, appName: string) => {
    try {
      await applicationsApi.delete(applicationId)

      // Clear selections if they reference the deleted app
      if (selectedApp === appName) {
        setSelectedApp(null)
        setSelectedTest(null)
      }

      // Remove all local history entries for this app
      setHistory((prev) => prev.filter((t) => t.appName !== appName))

      // Reload to ensure sync across API + stats
      loadApplications()
      loadTestRuns()
      loadStats()
    } catch (err) {
      console.error("Failed to delete application:", err)
      setError(err instanceof Error ? err.message : "Failed to delete application")
    }
  }

  const handleSelectTest = (test: TestHistory) => {
    setSelectedTest(test)
    // If we're not already viewing this app, switch to it
    if (selectedApp !== test.appName) {
      setSelectedApp(test.appName)
    }
  }

  const [initialTestAppName, setInitialTestAppName] = useState<string | undefined>(undefined)
  const [initialTestType, setInitialTestType] = useState<"functional" | "regression" | "performance" | "accessibility" | "broken_links" | "authentication" | undefined>(undefined)
  const [autoStartTest, setAutoStartTest] = useState(false)

  const handleRunTestFromCard = (appName: string, testType: string) => {
    // Find the application by name
    const app = applications.find(a => a.name === appName)
    if (app) {
      // Navigate to new test form and pre-select the app
      setSelectedApp(null)
      setSelectedTest(null)
      // Set initial values for the form
      setInitialTestAppName(appName)
      setInitialTestType(testType as "functional" | "regression" | "performance" | "accessibility")
      setAutoStartTest(true)
      // Scroll to the form
      setTimeout(() => {
        window.scrollTo({ top: 0, behavior: 'smooth' })
      }, 100)
    }
  }

  return (
    <div className="h-screen bg-background flex flex-col overflow-hidden">
      <TopNav onNavigateToProfile={() => setCurrentView("profile")} />

      {currentView === "profile" ? (
        <main className="flex-1 overflow-auto p-6 lg:p-8">
          <ProfilePage onBack={() => setCurrentView("dashboard")} />
        </main>
      ) : (
        <div className="flex flex-1 overflow-hidden min-h-0">
          <Sidebar
            collapsed={sidebarCollapsed}
            onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
            history={history}
            applications={applications}
            selectedId={selectedApp}
            selectedTestId={selectedTest?.id || null}
            onSelectApp={(appName) => {
              setSelectedApp(appName)
              setSelectedTest(null)
            }}
            onSelectTest={handleSelectTest}
            onDeleteTest={handleDeleteTest}
            onDeleteApp={handleDeleteApp}
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
                      selectedTestId={(selectedTest as TestHistory | null)?.id ?? null}
                      onSelectTest={handleSelectTest}
                      onDeleteTest={handleDeleteTest}
                      onRunTest={handleRunTestFromCard}
                    />
                  </motion.div>
                ) : (
                  <motion.div
                    key="dashboard-content"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -20 }}
                    transition={{ duration: 0.2 }}
                    className="space-y-8"
                  >
                    {/* Statistics Button */}
                    <div className="flex justify-end">
                      <Button
                        onClick={() => setStatsModalOpen(true)}
                        className="flex items-center gap-2"
                      >
                        <BarChart3 className="h-5 w-5" />
                        <span>View Statistics</span>
                      </Button>
                    </div>

                    {/* Tabs for Quick Test and AI Generator */}
                    <Tabs defaultValue="quick-test" className="w-full">
                      <TabsList className="grid w-full grid-cols-2 mb-6">
                        <TabsTrigger value="quick-test" className="flex items-center gap-2">
                          <Zap className="w-4 h-4" />
                          Quick Test
                        </TabsTrigger>
                        <TabsTrigger value="ai-generator" className="flex items-center gap-2">
                          <Sparkles className="w-4 h-4" />
                          AI Test Generator
                        </TabsTrigger>
                      </TabsList>
                      
                      <TabsContent value="quick-test">
                        {/* New Test Form */}
                        <NewTestForm
                          onTestComplete={(test) => {
                            handleNewTestComplete(test)
                            // Reset initial values after test completes
                            setInitialTestAppName(undefined)
                            setInitialTestType(undefined)
                            setAutoStartTest(false)
                          }}
                          applications={applications}
                          initialAppName={initialTestAppName}
                          initialTestType={initialTestType}
                          autoStart={autoStartTest}
                        />
                      </TabsContent>
                      
                      <TabsContent value="ai-generator">
                        <AITestCaseGenerator
                          application={applications.length > 0 ? applications[0] : null}
                          applications={applications}
                          onTestCaseGenerated={(testCase) => {
                            console.log("Test case generated:", testCase)
                          }}
                          onTestComplete={(testHistory) => {
                            // When test completes, add to history and navigate to it
                            handleNewTestComplete(testHistory)
                          }}
                        />
                      </TabsContent>
                    </Tabs>
                  </motion.div>
                )}
              </AnimatePresence>
            )}
          </main>
        </div>
      )}

      {/* Statistics Modal */}
      <StatisticsModal
        open={statsModalOpen}
        onOpenChange={setStatsModalOpen}
        stats={stats}
      />
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
  onRunTest?: (appName: string, testType: string) => void
}

function AppVersionsView({ appName, history, selectedTestId, onSelectTest, onDeleteTest, onRunTest }: AppVersionsViewProps) {
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
      <div className="flex items-center justify-between pb-2 border-b border-border">
        <div className="flex items-center gap-2">
          <Package className="h-5 w-5 text-orange-600" />
          <h2 className="text-xl font-semibold text-foreground">{appName}</h2>
          <span className="text-sm text-muted-foreground">({versions.length} version{versions.length !== 1 ? 's' : ''})</span>
        </div>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button className="bg-primary text-primary-foreground hover:bg-primary/90">
              <Play className="w-4 h-4 mr-2" />
              Run New Test
              <ChevronDown className="w-4 h-4 ml-2 opacity-50" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="bg-popover border-border">
            <DropdownMenuItem onClick={() => onRunTest && onRunTest(appName, "functional")}>
              Functional Testing
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => onRunTest && onRunTest(appName, "regression")}>
              Regression Testing
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => onRunTest && onRunTest(appName, "performance")}>
              Performance Testing
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => onRunTest && onRunTest(appName, "accessibility")}>
              Accessibility Testing
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {/* Version Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {versions.map((test) => (
          <VersionCard
            key={test.id}
            test={test}
            onSelect={onSelectTest}
            onDelete={onDeleteTest}
            onRunTest={onRunTest}
            isSelected={selectedTestId === test.id}
          />
        ))}
      </div>
    </div>
  )
}