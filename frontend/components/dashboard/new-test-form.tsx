"use client"

import { useState, useEffect, useRef } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { Play, Globe, Tag, FileCode, Loader2, CheckCircle, Plus, Pause } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import type { TestHistory } from "@/lib/types"
import { Progress } from "@/components/ui/progress"
import { applicationsApi, testRunsApi, type Application, type TestRun } from "@/lib/api"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { AlertCircle } from "lucide-react"
import { TestProgressIndicator, type TestProgressData } from "./test-progress-indicator"

interface NewTestFormProps {
  onTestComplete: (test: TestHistory) => void
  applications: Application[]
  initialAppName?: string
  initialTestType?: TestType
  autoStart?: boolean
}

type TestState = "idle" | "creating" | "running" | "paused" | "completed"
type TestType = "functional" | "regression" | "performance" | "accessibility"

export default function NewTestForm({ onTestComplete, applications, initialAppName, initialTestType, autoStart }: NewTestFormProps) {
  // Find initial app if appName is provided
  const initialApp = initialAppName ? applications.find(app => app.name === initialAppName) : null

  const [selectedAppId, setSelectedAppId] = useState<string>(initialApp?.id.toString() || "")
  const [appName, setAppName] = useState("")
  const [appUrl, setAppUrl] = useState("")
  const [testType, setTestType] = useState<TestType | "">(initialTestType || "")
  const [testState, setTestState] = useState<TestState>("idle")
  const [progress, setProgress] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [showNewAppForm, setShowNewAppForm] = useState(false)
  const [testProgressData, setTestProgressData] = useState<TestProgressData>({
    progress: 0,
    currentStep: "Initializing...",
    warnings: 0,
    errors: 0,
    elapsedTime: 0,
    estimatedTime: 120, // 2 minutes estimate
    status: "running"
  })
  const [testStartTime, setTestStartTime] = useState<number>(0)
  const [showContinueButton, setShowContinueButton] = useState(false)
  const [completedTestHistory, setCompletedTestHistory] = useState<TestHistory | null>(null)
  const [hasAutoStarted, setHasAutoStarted] = useState(false)
  const isPausedRef = useRef(false)

  const togglePause = () => {
    if (testState === "running") {
      setTestState("paused")
      isPausedRef.current = true
    } else if (testState === "paused") {
      setTestState("running")
      isPausedRef.current = false
    }
  }

  const selectedApp = applications.find((app) => app.id.toString() === selectedAppId)

  const handleCreateApplication = async (): Promise<Application> => {
    if (!appName || !appUrl) {
      setError("Please fill in both application name and URL")
      throw new Error("Please fill in both application name and URL")
    }

    // Validate and normalize URL
    let normalizedUrl = appUrl.trim()
    if (!normalizedUrl.startsWith('http://') && !normalizedUrl.startsWith('https://')) {
      normalizedUrl = `https://${normalizedUrl}`
    }

    setError(null)
    setTestState("creating")

    try {
      const newApp = await applicationsApi.create(appName, normalizedUrl)
      setSelectedAppId(newApp.id.toString())
      setAppName("")
      setAppUrl("")
      setShowNewAppForm(false)
      setTestState("idle")
      return newApp
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to create application"
      setError(errorMessage)
      setTestState("idle")
      throw err
    }
  }

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

  const handleStartTest = async () => {
    if (!selectedApp && (!appName || !appUrl)) {
      setError("Please select an application or create a new one")
      return
    }
    if (!testType) {
      setError("Please select a test type")
      return
    }

    setError(null)

    // If creating new app, do that first
    let appToTest = selectedApp
    if (!selectedApp && appName && appUrl) {
      try {
        const newApp = await handleCreateApplication()
        appToTest = newApp
        setSelectedAppId(newApp.id.toString())
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to create application")
        setTestState("idle")
        return
      }
    } else {
      appToTest = applications.find((app) => app.id.toString() === selectedAppId)
    }

    if (!appToTest) {
      setError("Application not found")
      return
    }

    setTestState("running")
    setProgress(0)
    setShowContinueButton(false)
    setCompletedTestHistory(null)
    const startTime = Date.now()
    setTestStartTime(startTime)

    // Initialize progress data
    setTestProgressData({
      progress: 0,
      currentStep: "Initializing test environment...",
      warnings: 0,
      errors: 0,
      elapsedTime: 0,
      estimatedTime: 120,
      status: "running"
    })

    // Start elapsed time tracker
    const timeTracker = setInterval(() => {
      const elapsed = Math.floor((Date.now() - startTime) / 1000)
      setTestProgressData(prev => ({
        ...prev,
        elapsedTime: elapsed
      }))
    }, 1000)

    try {
      // Create test run via API
      const testRun = await testRunsApi.create(appToTest.id, testType as string)

      // Define test steps for progress tracking
      const testSteps = [
        { progress: 10, step: "Loading application...", warnings: 0, errors: 0 },
        { progress: 20, step: "Analyzing page structure...", warnings: 1, errors: 0 },
        { progress: 35, step: "Running functional tests...", warnings: 1, errors: 0 },
        { progress: 50, step: "Checking responsive design...", warnings: 2, errors: 0 },
        { progress: 65, step: "Testing user interactions...", warnings: 2, errors: 1 },
        { progress: 80, step: "Checking accessibility...", warnings: 3, errors: 1 },
        { progress: 90, step: "Generating test report...", warnings: 3, errors: 1 },
        { progress: 100, step: "Finalizing results...", warnings: 3, errors: 1 }
      ]

      let currentStepIndex = 0

      // Poll for test completion
      let pollAttempts = 0
      const maxPollAttempts = 120 // 2 minutes max

      const pollInterval = setInterval(async () => {
        if (isPausedRef.current) return

        pollAttempts++
        const elapsedSeconds = Math.floor((Date.now() - startTime) / 1000)

        try {
          const updatedTestRun = await testRunsApi.get(testRun.id)

          // Update progress based on status
          if (updatedTestRun.status === 'running' || updatedTestRun.status === 'pending') {
            // Simulate progressive steps
            if (currentStepIndex < testSteps.length - 1) {
              const stepDuration = 3 // seconds per step
              if (pollAttempts % stepDuration === 0) {
                currentStepIndex++
              }
            }

            const currentStep = testSteps[Math.min(currentStepIndex, testSteps.length - 1)]
            setProgress(currentStep.progress)

            setTestProgressData({
              progress: currentStep.progress,
              currentStep: currentStep.step,
              warnings: currentStep.warnings,
              errors: currentStep.errors,
              elapsedTime: elapsedSeconds,
              estimatedTime: 120,
              status: "running"
            })
          } else if (updatedTestRun.status === 'success' || updatedTestRun.status === 'failed') {
            clearInterval(pollInterval)
            clearInterval(timeTracker)
            setProgress(100)

            setTestProgressData({
              progress: 100,
              currentStep: updatedTestRun.status === 'success' ? "Test completed successfully!" : "Test completed with failures",
              warnings: 3,
              errors: updatedTestRun.status === 'failed' ? 2 : 1,
              elapsedTime: elapsedSeconds,
              estimatedTime: elapsedSeconds,
              status: updatedTestRun.status === 'success' ? "completed" : "failed"
            })

            setTestState("completed")

            // Convert to TestHistory format and complete
            const testHistory = convertTestRunToHistory(updatedTestRun)
            setCompletedTestHistory(testHistory)
            setTimeout(() => {
              setShowContinueButton(true)
            }, 3000)
          }

          // Stop polling if we've exceeded max attempts
          if (pollAttempts >= maxPollAttempts) {
            clearInterval(pollInterval)
            clearInterval(timeTracker)
            setError("Test is taking longer than expected. The test may still be running in the background.")
            setTestState("idle")
            setProgress(0)
          }
        } catch (err) {
          console.error("Error polling test run:", err)

          // If we get multiple errors, stop polling
          if (pollAttempts >= 10) {
            clearInterval(pollInterval)
            clearInterval(timeTracker)
            const errorMessage = err instanceof Error ? err.message : "Failed to get test status"
            setError(`Error checking test status: ${errorMessage}. The test may still be running.`)
            setTestState("idle")
            setProgress(0)
          }
        }
      }, 1000) // Poll every second

      // Timeout after 2 minutes
      setTimeout(() => {
        clearInterval(pollInterval)
        clearInterval(timeTracker)
        setTestState((currentState) => {
          if (currentState === "running") {
            setError("Test is taking longer than expected. Please check the test run status.")
            setProgress(0)
            return "idle"
          }
          return currentState
        })
      }, 120000)
    } catch (err) {
      clearInterval(timeTracker)
      setError(err instanceof Error ? err.message : "Failed to start test")
      setTestState("idle")
      setProgress(0)
    }
  }

  // Auto-start test if initial values are provided
  useEffect(() => {
    if (autoStart && initialApp && initialTestType && !hasAutoStarted && testState === "idle") {
      setHasAutoStarted(true)
      // Small delay to ensure form is rendered
      setTimeout(() => {
        handleStartTest()
      }, 200)
    }
  }, [autoStart, initialApp, initialTestType, hasAutoStarted, testState])

  return (
    <div className="max-w-2xl mx-auto">
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="text-center mb-8">
        <h1 className="text-3xl font-bold text-foreground mb-2">Start a New Test</h1>
        <p className="text-muted-foreground">Configure and run AI-powered tests on your application</p>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="glass rounded-2xl p-6 lg:p-8"
      >
        <AnimatePresence mode="wait">
          {testState === "idle" && (
            <motion.div
              key="form"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="space-y-6"
            >
              {error && (
                <Alert variant="destructive" className="bg-red-500/10 border-red-500/30">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription className="text-red-400">{error}</AlertDescription>
                </Alert>
              )}

              <div className="space-y-2">
                <Label htmlFor="appSelect" className="text-foreground/80 flex items-center gap-2">
                  <Tag className="w-4 h-4" />
                  Select Application
                </Label>
                <div className="flex gap-2">
                  <Select value={selectedAppId} onValueChange={setSelectedAppId}>
                    <SelectTrigger className="bg-input border-border/50 focus:border-primary h-12 rounded-xl flex-1">
                      <SelectValue placeholder="Choose an application" />
                    </SelectTrigger>
                    <SelectContent className="bg-popover border-border">
                      {applications.map((app) => (
                        <SelectItem key={app.id} value={app.id.toString()}>
                          {app.name} - {app.url}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => {
                      setShowNewAppForm(!showNewAppForm)
                      setSelectedAppId("")
                    }}
                    className="h-12 rounded-xl border-border hover:bg-secondary"
                  >
                    <Plus className="w-4 h-4 mr-2" />
                    New
                  </Button>
                </div>
              </div>

              {showNewAppForm && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  className="space-y-4 p-4 bg-secondary/30 rounded-xl border border-border/50"
                >
                  <div className="space-y-2">
                    <Label htmlFor="appName" className="text-foreground/80 flex items-center gap-2">
                      <Tag className="w-4 h-4" />
                      Application Name
                    </Label>
                    <Input
                      id="appName"
                      placeholder="My Awesome App"
                      value={appName}
                      onChange={(e) => setAppName(e.target.value)}
                      className="bg-input border-border/50 focus:border-primary h-12 rounded-xl"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="appUrl" className="text-foreground/80 flex items-center gap-2">
                      <Globe className="w-4 h-4" />
                      Application URL
                    </Label>
                    <Input
                      id="appUrl"
                      placeholder="https://myapp.com"
                      value={appUrl}
                      onChange={(e) => setAppUrl(e.target.value)}
                      className="bg-input border-border/50 focus:border-primary h-12 rounded-xl"
                    />
                  </div>
                </motion.div>
              )}

              <div className="space-y-2">
                <Label htmlFor="testType" className="text-foreground/80 flex items-center gap-2">
                  <FileCode className="w-4 h-4" />
                  Test Type
                </Label>
                <Select value={testType} onValueChange={(value: TestType) => setTestType(value)}>
                  <SelectTrigger className="bg-input border-border/50 focus:border-primary h-12 rounded-xl">
                    <SelectValue placeholder="Select test type" />
                  </SelectTrigger>
                  <SelectContent className="bg-popover border-border">
                    <SelectItem value="functional">Functional Testing</SelectItem>
                    <SelectItem value="regression">Regression Testing</SelectItem>
                    <SelectItem value="performance">Performance Testing</SelectItem>
                    <SelectItem value="accessibility">Accessibility Testing</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <Button
                onClick={handleStartTest}
                disabled={(!selectedApp && !appName && !appUrl) || !testType || testState !== "idle"}
                className="w-full h-14 rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 font-semibold text-lg transition-all duration-200 mt-4"
              >
                <Play className="w-5 h-5 mr-2" />
                Start Test
              </Button>
            </motion.div>
          )}

          {(testState === "running" || testState === "paused" || testState === "completed") && (
            <motion.div
              key="running"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0 }}
              className="space-y-6"
            >
              <div className="text-center mb-6">
                <motion.div
                  animate={testState === "running" ? { scale: [1, 1.1, 1] } : {}}
                  transition={{ repeat: Number.POSITIVE_INFINITY, duration: 1.5 }}
                  className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-primary/10 mb-4"
                >
                  {testState === "running" ? (
                    <Loader2 className="w-10 h-10 text-primary animate-spin" />
                  ) : testState === "paused" ? (
                    <Pause className="w-10 h-10 text-primary" />
                  ) : (
                    <CheckCircle className="w-10 h-10 text-[oklch(0.65_0.18_145)]" />
                  )}
                </motion.div>

                <h2 className="text-xl font-semibold text-foreground mb-2">
                  {testState === "running" ? "Running Tests..." : testState === "paused" ? "Test Paused" : "Test Completed!"}
                </h2>
                <p className="text-muted-foreground">
                  {testState === "running" || testState === "paused"
                    ? `Testing ${selectedApp?.name || appName || "application"}`
                    : "Generating report..."}
                </p>
              </div>

              {/* Detailed Progress Indicator */}
              <TestProgressIndicator data={testProgressData} />

              {testState === "running" || testState === "paused" ? (
                <div className="flex justify-center mt-6">
                  <Button
                    variant="outline"
                    onClick={togglePause}
                    className="flex items-center gap-2 min-w-[120px]"
                  >
                    {testState === "running" ? (
                      <>
                        <Pause className="w-4 h-4" /> Pause
                      </>
                    ) : (
                      <>
                        <Play className="w-4 h-4" /> Resume
                      </>
                    )}
                  </Button>
                </div>
              ) : null}

              {testState === "completed" && (
                <div className="flex justify-center">
                  {showContinueButton ? (
                    <Button
                      onClick={() => {
                        if (!completedTestHistory) return
                        onTestComplete(completedTestHistory)
                        setSelectedAppId("")
                        setTestType("")
                        setTestState("idle")
                        setProgress(0)
                        setShowContinueButton(false)
                        setCompletedTestHistory(null)
                      }}
                      className="h-12 px-8 rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 font-semibold"
                    >
                      Continue
                    </Button>
                  ) : (
                    <p className="text-sm text-muted-foreground">Generating report...</p>
                  )}
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </div>
  )
}
