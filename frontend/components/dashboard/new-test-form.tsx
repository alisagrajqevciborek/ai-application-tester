"use client"

import { useState, useEffect, useRef } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { Play, Globe, Tag, FileCode, Loader2, CheckCircle, Plus, Pause, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"
import type { TestHistory } from "@/lib/types"
import { Progress } from "@/components/ui/progress"
import { applicationsApi, testRunsApi, type Application, type TestRun } from "@/lib/api"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { AlertCircle, Link as LinkIcon, Lock } from "lucide-react"
import { TestProgressIndicator, type TestProgressData } from "./test-progress-indicator"
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

interface NewTestFormProps {
  onTestComplete: (test: TestHistory) => void
  applications: Application[]
  initialAppName?: string
  initialTestType?: TestType
  autoStart?: boolean
}

type TestState = "idle" | "creating" | "running" | "paused" | "completed"
type TestType = "general" | "functional" | "regression" | "performance" | "accessibility" | "broken_links" | "authentication"

export default function NewTestForm({ onTestComplete, applications, initialAppName, initialTestType, autoStart }: NewTestFormProps) {
  // Find initial app if appName is provided
  const initialApp = initialAppName ? applications.find(app => app.name === initialAppName) : null

  const [selectedAppId, setSelectedAppId] = useState<string>(initialApp?.id.toString() || "")
  const [appName, setAppName] = useState("")
  const [appUrl, setAppUrl] = useState("")
  // Authentication fields
  const [testUsername, setTestUsername] = useState("")
  const [testPassword, setTestPassword] = useState("")
  const [loginUrl, setLoginUrl] = useState("")

  const [testType, setTestType] = useState<TestType | "">(initialTestType || "")

  const [testState, setTestState] = useState<TestState>("idle")
  const [progress, setProgress] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [showNewAppForm, setShowNewAppForm] = useState(false)
  const [showAuthFields, setShowAuthFields] = useState(false)
  const [testProgressData, setTestProgressData] = useState<TestProgressData>({
    progress: 0,
    currentStep: "Initializing...",
    warnings: 0,
    errors: 0,
    elapsedTime: 0,
    estimatedTime: 300, // 5 minutes estimate (can vary based on test type)
    status: "running"
  })
  const [testStartTime, setTestStartTime] = useState<number>(0)
  const [showContinueButton, setShowContinueButton] = useState(false)
  const [completedTestHistory, setCompletedTestHistory] = useState<TestHistory | null>(null)
  const [hasAutoStarted, setHasAutoStarted] = useState(false)
  const [stopDialogOpen, setStopDialogOpen] = useState(false)
  const isPausedRef = useRef(false)
  const testRunIdRef = useRef<number | null>(null)
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null)
  const timeTrackerRef = useRef<NodeJS.Timeout | null>(null)
  const [loadingText, setLoadingText] = useState("Testing")
  const [loadingDots, setLoadingDots] = useState("")

  useEffect(() => {
    if (testState !== "running") {
      setLoadingDots("")
      return
    }

    setLoadingText("Testing")

    const dotsInterval = setInterval(() => {
      setLoadingDots((prev) => (prev.length >= 3 ? "" : prev + "."))
    }, 500)

    return () => {
      clearInterval(dotsInterval)
    }
  }, [testState])

  const togglePause = () => {
    if (testState === "running") {
      setTestState("paused")
      isPausedRef.current = true
    } else if (testState === "paused") {
      setTestState("running")
      isPausedRef.current = false
    }
  }

  const handleStopTest = async () => {
    if (!testRunIdRef.current) return

    try {
      // Delete the test run from the database
      await testRunsApi.delete(testRunIdRef.current)

      // Clear all intervals
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current)
        pollIntervalRef.current = null
      }
      if (timeTrackerRef.current) {
        clearInterval(timeTrackerRef.current)
        timeTrackerRef.current = null
      }

      // Reset state
      testRunIdRef.current = null
      setTestState("idle")
      setProgress(0)
      setTestProgressData({
        progress: 0,
        currentStep: "",
        warnings: 0,
        errors: 0,
        elapsedTime: 0,
        estimatedTime: 0,
        status: "running"
      })
      isPausedRef.current = false
      setError(null)
    } catch (err) {
      console.error("Failed to stop test:", err)
      setError(err instanceof Error ? err.message : "Failed to stop test")
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
      const newApp = await applicationsApi.create(appName, normalizedUrl, {
        test_username: testUsername,
        test_password: testPassword,
        login_url: loginUrl
      })
      setSelectedAppId(newApp.id.toString())
      setAppName("")
      setAppUrl("")
      setTestUsername("")
      setTestPassword("")
      setLoginUrl("")
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
    timeTrackerRef.current = setInterval(() => {
      const elapsed = Math.floor((Date.now() - startTime) / 1000)
      setTestProgressData(prev => ({
        ...prev,
        elapsedTime: elapsed
      }))
    }, 1000)

    try {
      // Create test run via API
      const testRun = await testRunsApi.create(appToTest.id, testType as string)
      testRunIdRef.current = testRun.id // Store the test run ID

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
      const maxPollAttempts = 600 // 10 minutes max (600 seconds = 10 minutes, polling every second)

      pollIntervalRef.current = setInterval(async () => {
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
              estimatedTime: 300, // 5 minutes estimate
              status: "running"
            })
          } else if (updatedTestRun.status === 'success' || updatedTestRun.status === 'failed') {
            if (pollIntervalRef.current) {
              clearInterval(pollIntervalRef.current)
              pollIntervalRef.current = null
            }
            if (timeTrackerRef.current) {
              clearInterval(timeTrackerRef.current)
              timeTrackerRef.current = null
            }
            testRunIdRef.current = null
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

            // Important: avoid falling through to max-attempt logic
            // on the same tick that we detect completion.
            return
          }

          // Stop polling if we've exceeded max attempts (only meaningful while still running)
          if (
            pollAttempts >= maxPollAttempts &&
            (updatedTestRun.status === 'running' || updatedTestRun.status === 'pending')
          ) {
            if (pollIntervalRef.current) {
              clearInterval(pollIntervalRef.current)
              pollIntervalRef.current = null
            }
            if (timeTrackerRef.current) {
              clearInterval(timeTrackerRef.current)
              timeTrackerRef.current = null
            }
            testRunIdRef.current = null
            setError("Test is taking longer than expected. The test may still be running in the background.")
            setTestState("idle")
            setProgress(0)
            return
          }
        } catch (err) {
          console.error("Error polling test run:", err)

          // If we get multiple errors, stop polling but don't show error (test may still be running)
          if (pollAttempts >= 20) { // Increased from 10 to 20 attempts
            if (pollIntervalRef.current) {
              clearInterval(pollIntervalRef.current)
              pollIntervalRef.current = null
            }
            if (timeTrackerRef.current) {
              clearInterval(timeTrackerRef.current)
              timeTrackerRef.current = null
            }
            testRunIdRef.current = null
            const errorMessage = err instanceof Error ? err.message : "Failed to get test status"
            setError(`Error checking test status: ${errorMessage}. The test may still be running in the background.`)
            setShowContinueButton(true)
            setTestState("idle")
            setProgress(0)
            return
          }
        }
      }, 1000) // Poll every second

      // Timeout after 10 minutes (tests can take longer with screenshots, artifacts, etc.)
      setTimeout(() => {
        if (pollIntervalRef.current) {
          clearInterval(pollIntervalRef.current)
          pollIntervalRef.current = null
        }
        if (timeTrackerRef.current) {
          clearInterval(timeTrackerRef.current)
          timeTrackerRef.current = null
        }
        testRunIdRef.current = null
        setTestState((currentState) => {
          if (currentState === "running") {
            setError("Test is taking longer than expected. The test may still be running in the background.")
            setShowContinueButton(true)
            setProgress(0)
            return "idle"
          }
          return currentState
        })
      }, 600000) // 10 minutes
    } catch (err) {
      if (timeTrackerRef.current) {
        clearInterval(timeTrackerRef.current)
        timeTrackerRef.current = null
      }
      testRunIdRef.current = null
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
                <div className="grid grid-cols-[1fr_auto] items-center gap-0 rounded-xl overflow-hidden border border-border/50 bg-input">
                  <Select value={selectedAppId} onValueChange={setSelectedAppId}>
                    <SelectTrigger className="bg-transparent border-0 focus:border-primary h-11 rounded-none rounded-l-xl">
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
                    className="h-11 min-w-[96px] px-3 rounded-none rounded-r-xl border-l border-border/50 bg-transparent hover:bg-secondary text-sm font-medium"
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

                  <div className="pt-2">
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => setShowAuthFields(!showAuthFields)}
                      className="text-xs text-primary hover:bg-primary/10 rounded-lg h-8 px-2"
                    >
                      {showAuthFields ? "- Hide" : "+ Add"} Authentication Credentials (Optional)
                    </Button>
                  </div>

                  <AnimatePresence>
                    {showAuthFields && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: "auto" }}
                        exit={{ opacity: 0, height: 0 }}
                        className="space-y-4 pt-2 overflow-hidden"
                      >
                        <div className="grid grid-cols-2 gap-4">
                          <div className="space-y-2">
                            <Label htmlFor="testUsername" className="text-xs text-foreground/60">Test Username</Label>
                            <Input
                              id="testUsername"
                              placeholder="test_user"
                              value={testUsername}
                              onChange={(e) => setTestUsername(e.target.value)}
                              className="bg-input border-border/30 focus:border-primary h-10 rounded-lg text-sm"
                            />
                          </div>
                          <div className="space-y-2">
                            <Label htmlFor="testPassword" className="text-xs text-foreground/60">Test Password</Label>
                            <Input
                              id="testPassword"
                              type="password"
                              placeholder="••••••••"
                              value={testPassword}
                              onChange={(e) => setTestPassword(e.target.value)}
                              className="bg-input border-border/30 focus:border-primary h-10 rounded-lg text-sm"
                            />
                          </div>
                        </div>
                        <div className="space-y-2">
                          <Label htmlFor="loginUrl" className="text-xs text-foreground/60">Login Page URL</Label>
                          <Input
                            id="loginUrl"
                            placeholder="https://myapp.com/login"
                            value={loginUrl}
                            onChange={(e) => setLoginUrl(e.target.value)}
                            className="bg-input border-border/30 focus:border-primary h-10 rounded-lg text-sm"
                          />
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
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
                    <SelectItem value="general">General (Full Suite)</SelectItem>
                    <SelectItem value="functional">Functional Testing</SelectItem>
                    <SelectItem value="regression">Regression Testing</SelectItem>
                    <SelectItem value="performance">Performance Testing</SelectItem>
                    <SelectItem value="accessibility">Accessibility Testing</SelectItem>
                    <SelectItem value="broken_links">Broken Link Check</SelectItem>
                    <SelectItem value="authentication">Authentication Flow</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <Button
                onClick={handleStartTest}
                disabled={
                  (!selectedApp && !appName && !appUrl) ||
                  !testType ||
                  testState !== "idle" ||
                  (testType === 'authentication' && (selectedApp ? (!selectedApp.login_url || !selectedApp.test_username) : (!loginUrl || !testUsername)))
                }
                className="w-full h-11 rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 font-semibold text-base transition-all duration-200 mt-4"
              >
                <Play className="w-5 h-5 mr-2" />
                {testType === 'authentication' && (selectedApp ? (!selectedApp.login_url || !selectedApp.test_username) : (!loginUrl || !testUsername))
                  ? "Set Credentials First"
                  : "Start Test"}
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

                <p className="text-muted-foreground mb-1">
                  {testState === "running" || testState === "paused"
                    ? `Testing ${selectedApp?.name || appName || "application"}`
                    : "Generating report..."}
                </p>
                <h2 className="text-xl font-semibold text-foreground flex items-center justify-center min-h-[2rem]">
                  {testState === "running" ? (
                    <span>
                      {loadingText}
                      <span className="inline-block w-[24px] text-left">{loadingDots}</span>
                    </span>
                  ) : testState === "paused" ? (
                    "Test Paused"
                  ) : (
                    "Test Completed!"
                  )}
                </h2>
              </div>

              {/* Detailed Progress Indicator */}
              <TestProgressIndicator data={testProgressData} />

              {testState === "running" || testState === "paused" ? (
                <div className="flex justify-center gap-3 mt-6">
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
                  <Button
                    variant="destructive"
                    onClick={() => setStopDialogOpen(true)}
                    className="flex items-center gap-2 min-w-[120px]"
                  >
                    <X className="w-4 h-4" /> Stop
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
      </motion.div >

      <AlertDialog open={stopDialogOpen} onOpenChange={setStopDialogOpen}>
        <AlertDialogContent className="bg-popover border-border">
          <AlertDialogHeader>
            <AlertDialogTitle>Stop Current Test?</AlertDialogTitle>
            <AlertDialogDescription>
              This will stop the running test and permanently delete this test run.
              This action cannot be undone.
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
    </div >
  )
}
