"use client"

import { useEffect, useState, useRef, useCallback } from "react"
import { useParams, useRouter } from "next/navigation"
import { motion } from "framer-motion"
import { ArrowLeft, Home, Loader2, CheckCircle, Pause, Play, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import TopNav from "@/components/dashboard/top-nav"
import { TestProgressIndicator, type TestProgressData } from "@/components/dashboard/test-progress-indicator"
import { useAuth } from "@/contexts/AuthContext"
import { useData } from "@/contexts/DataContext"
import { testRunsApi } from "@/lib/api"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"

type ViewState = "loading" | "running" | "paused" | "completed" | "error"

export default function TestProgressPage() {
  const { testId } = useParams<{ testId: string }>()
  const { isAuthenticated, isLoading: authLoading, user } = useAuth()
  const { forceRefresh } = useData()
  const router = useRouter()

  const [viewState, setViewState] = useState<ViewState>("loading")
  const [appName, setAppName] = useState("")
  const [testType, setTestType] = useState("")
  const [loadingDots, setLoadingDots] = useState("")
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [stopDialogOpen, setStopDialogOpen] = useState(false)
  const [testProgressData, setTestProgressData] = useState<TestProgressData>({
    progress: 0,
    currentStep: "Attaching to test...",
    warnings: 0,
    errors: 0,
    elapsedTime: 0,
    estimatedTime: 300,
    status: "running",
  })

  const isPausedRef = useRef(false)
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null)
  const timeTrackerRef = useRef<NodeJS.Timeout | null>(null)
  const startTimeRef = useRef<number>(0)
  const isMountedRef = useRef(true)

  // Auth guard
  useEffect(() => {
    if (!authLoading) {
      if (!isAuthenticated) router.push("/login")
      else if (user?.role === "admin") router.push("/admin")
    }
  }, [isAuthenticated, authLoading, user, router])

  // Animated dots while running
  useEffect(() => {
    if (viewState !== "running") { setLoadingDots(""); return }
    const id = setInterval(() => setLoadingDots(prev => prev.length >= 3 ? "" : prev + "."), 500)
    return () => clearInterval(id)
  }, [viewState])

  const stopPolling = useCallback(() => {
    if (pollIntervalRef.current) { clearInterval(pollIntervalRef.current); pollIntervalRef.current = null }
    if (timeTrackerRef.current) { clearInterval(timeTrackerRef.current); timeTrackerRef.current = null }
  }, [])

  // Main polling logic
  const startPolling = useCallback((testRunId: number, startedAt: string) => {
    // Calculate elapsed time from the actual test start time
    const testStart = new Date(startedAt).getTime()
    startTimeRef.current = testStart

    // Start elapsed time tracker
    timeTrackerRef.current = setInterval(() => {
      if (!isMountedRef.current) return
      const elapsed = Math.floor((Date.now() - startTimeRef.current) / 1000)
      setTestProgressData(prev => ({ ...prev, elapsedTime: elapsed }))
    }, 1000)

    pollIntervalRef.current = setInterval(async () => {
      if (isPausedRef.current || !isMountedRef.current) return

      try {
        const run = await testRunsApi.get(testRunId)
        if (!isMountedRef.current) return

        const elapsed = Math.floor((Date.now() - startTimeRef.current) / 1000)

        if (run.status === "running" || run.status === "pending") {
          const steps = run.step_results
          if (steps && steps.length > 0) {
            const done = steps.filter(s => s.status === "success" || s.status === "failed")
            const running = steps.find(s => s.status === "running")
            const pct = Math.max(5, Math.min(95, Math.round((done.length / steps.length) * 100)))
            const stepLabel = running
              ? `Running ${running.step_label}...`
              : done.length === steps.length
                ? "Finalizing results..."
                : `Waiting for step ${done.length + 1}/${steps.length}...`

            setTestProgressData({
              progress: pct,
              currentStep: stepLabel,
              warnings: 0,
              errors: steps.filter(s => s.status === "failed").length,
              elapsedTime: elapsed,
              estimatedTime: 300,
              status: "running",
            })
          } else {
            const estimatedDuration = 120
            const pct = Math.max(5, Math.min(90, Math.round((elapsed / estimatedDuration) * 100)))
            setTestProgressData({
              progress: pct,
              currentStep: run.status === "pending" ? "Queued, waiting for worker..." : "Running tests...",
              warnings: 0,
              errors: 0,
              elapsedTime: elapsed,
              estimatedTime: estimatedDuration,
              status: "running",
            })
          }
        } else if (run.status === "success" || run.status === "failed") {
          stopPolling()
          const finalSteps = run.step_results
          const failedCount = finalSteps ? finalSteps.filter(s => s.status === "failed").length : 0

          setTestProgressData({
            progress: 100,
            currentStep: run.status === "success" ? "Test completed successfully!" : "Test completed with failures",
            warnings: 0,
            errors: failedCount || (run.status === "failed" ? 1 : 0),
            elapsedTime: elapsed,
            estimatedTime: elapsed,
            status: run.status === "success" ? "completed" : "failed",
          })
          setViewState("completed")

          // Refresh data cache then go to report after a short delay
          await forceRefresh()
          setTimeout(() => {
            if (isMountedRef.current) router.push(`/dashboard/reports/${testRunId}`)
          }, 3000)
        }
      } catch (err) {
        console.error("Error polling test run:", err)
      }
    }, 1000)
  }, [stopPolling, forceRefresh, router])

  // Initial fetch — attach to the running test
  useEffect(() => {
    if (authLoading || !isAuthenticated) return

    const id = parseInt(testId, 10)
    if (isNaN(id)) {
      setErrorMsg("Invalid test ID.")
      setViewState("error")
      return
    }

    isMountedRef.current = true

    testRunsApi.get(id)
      .then(run => {
        if (!isMountedRef.current) return

        setAppName(run.application_name)
        setTestType(run.test_type)

        if (run.status === "success" || run.status === "failed") {
          // Already done — go straight to the report
          router.replace(`/dashboard/reports/${id}`)
          return
        }

        // Attach and poll
        setViewState("running")
        startPolling(id, run.started_at)
      })
      .catch(err => {
        if (!isMountedRef.current) return
        setErrorMsg(err instanceof Error ? err.message : "Could not load test run.")
        setViewState("error")
      })

    return () => {
      isMountedRef.current = false
      stopPolling()
    }
  }, [testId, authLoading, isAuthenticated, startPolling, stopPolling, router])

  const togglePause = () => {
    if (viewState === "running") {
      isPausedRef.current = true
      setViewState("paused")
    } else if (viewState === "paused") {
      isPausedRef.current = false
      setViewState("running")
    }
  }

  const handleStopTest = async () => {
    const id = parseInt(testId, 10)
    stopPolling()
    try {
      await testRunsApi.delete(id)
    } catch (err) {
      console.error("Failed to stop test:", err)
    }
    await forceRefresh()
    router.push("/dashboard")
  }

  if (authLoading || !isAuthenticated || user?.role === "admin") {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    )
  }

  const testTypeLabel: Record<string, string> = {
    general: "General",
    functional: "Functional",
    regression: "Regression",
    performance: "Performance",
    accessibility: "Accessibility",
    broken_links: "Broken Links",
    authentication: "Authentication",
  }

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <TopNav />

      <main className="flex-1 overflow-auto p-6 lg:p-8">
        <div className="max-w-2xl mx-auto">
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
                  onClick={() => router.back()}
                  className="flex items-center gap-2 text-muted-foreground hover:text-foreground"
                >
                  <ArrowLeft className="h-4 w-4" />
                  <span>Back</span>
                </Button>
                <Button
                  variant="outline"
                  size="icon"
                  onClick={() => router.push("/dashboard")}
                  className="text-muted-foreground hover:text-foreground"
                  title="Go to Dashboard"
                >
                  <Home className="h-4 w-4" />
                </Button>
              </div>
            </div>

            {/* Progress Card */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="glass rounded-2xl p-6 lg:p-8"
            >
              {viewState === "loading" && (
                <div className="flex flex-col items-center justify-center py-16 gap-4">
                  <Loader2 className="w-10 h-10 animate-spin text-primary" />
                  <p className="text-muted-foreground">Attaching to test...</p>
                </div>
              )}

              {viewState === "error" && (
                <div className="flex flex-col items-center justify-center py-16 gap-4">
                  <p className="text-destructive">{errorMsg}</p>
                  <Button onClick={() => router.push("/dashboard")}>Back to Dashboard</Button>
                </div>
              )}

              {(viewState === "running" || viewState === "paused" || viewState === "completed") && (
                <motion.div
                  key="progress"
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="space-y-6"
                >
                  {/* Icon + title */}
                  <div className="text-center mb-6">
                    <motion.div
                      animate={viewState === "running" ? { scale: [1, 1.1, 1] } : {}}
                      transition={{ repeat: Infinity, duration: 1.5 }}
                      className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-primary/10 mb-4"
                    >
                      {viewState === "running" ? (
                        <Loader2 className="w-10 h-10 text-primary animate-spin" />
                      ) : viewState === "paused" ? (
                        <Pause className="w-10 h-10 text-primary" />
                      ) : (
                        <CheckCircle className="w-10 h-10 text-[oklch(0.65_0.18_145)]" />
                      )}
                    </motion.div>

                    <p className="text-muted-foreground mb-1">
                      {viewState !== "completed"
                        ? `Testing ${appName}${testType ? ` · ${testTypeLabel[testType] ?? testType}` : ""}`
                        : "Generating report..."}
                    </p>
                    <h2 className="text-xl font-semibold text-foreground flex items-center justify-center min-h-[2rem]">
                      {viewState === "running" ? (
                        <span>Testing<span className="inline-block w-[24px] text-left">{loadingDots}</span></span>
                      ) : viewState === "paused" ? (
                        "Test Paused"
                      ) : (
                        "Test Completed!"
                      )}
                    </h2>
                  </div>

                  {/* Detailed progress indicator */}
                  <TestProgressIndicator data={testProgressData} />

                  {/* Controls */}
                  {(viewState === "running" || viewState === "paused") && (
                    <div className="flex justify-center gap-3 mt-6">
                      <Button
                        variant="outline"
                        onClick={togglePause}
                        className="flex items-center gap-2 min-w-[120px]"
                      >
                        {viewState === "running" ? (
                          <><Pause className="w-4 h-4" /> Pause</>
                        ) : (
                          <><Play className="w-4 h-4" /> Resume</>
                        )}
                      </Button>
                      <Button
                        variant="destructive"
                        onClick={() => setStopDialogOpen(true)}
                        className="flex items-center gap-2 min-w-[120px]"
                      >
                        <X className="w-4 h-4" /> Stop
                      </Button>
                    </div>
                  )}

                  {viewState === "completed" && (
                    <div className="flex justify-center">
                      <p className="text-sm text-muted-foreground">Redirecting to report...</p>
                    </div>
                  )}
                </motion.div>
              )}
            </motion.div>
          </motion.div>
        </div>
      </main>

      <AlertDialog open={stopDialogOpen} onOpenChange={setStopDialogOpen}>
        <AlertDialogContent className="bg-popover border-border">
          <AlertDialogHeader>
            <AlertDialogTitle>Stop Current Test?</AlertDialogTitle>
            <AlertDialogDescription>
              This will stop the running test and permanently delete this test run. This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleStopTest}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Stop and Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
