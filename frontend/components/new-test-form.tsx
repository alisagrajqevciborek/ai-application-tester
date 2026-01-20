"use client"

import { useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { Play, Globe, Tag, FileCode, Loader2, CheckCircle, Plus } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import type { TestHistory } from "@/lib/types"
import { Progress } from "@/components/ui/progress"
import { applicationsApi, testRunsApi, type Application, type TestRun } from "@/lib/api"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { AlertCircle } from "lucide-react"

interface NewTestFormProps {
  onTestComplete: (test: TestHistory) => void
  applications: Application[]
}

type TestState = "idle" | "creating" | "running" | "completed"
type TestType = "functional" | "regression" | "performance" | "accessibility"

export default function NewTestForm({ onTestComplete, applications }: NewTestFormProps) {
  const [selectedAppId, setSelectedAppId] = useState<string>("")
  const [appName, setAppName] = useState("")
  const [appUrl, setAppUrl] = useState("")
  const [testType, setTestType] = useState<TestType | "">("")
  const [testState, setTestState] = useState<TestState>("idle")
  const [progress, setProgress] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [showNewAppForm, setShowNewAppForm] = useState(false)

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

    try {
      // Create test run via API
      const testRun = await testRunsApi.create(appToTest.id, testType as string)
      
      // Poll for test completion
      let pollAttempts = 0
      const maxPollAttempts = 60 // 60 seconds max
      
      const pollInterval = setInterval(async () => {
        pollAttempts++
        try {
          const updatedTestRun = await testRunsApi.get(testRun.id)
          
          // Update progress based on status
          if (updatedTestRun.status === 'running' || updatedTestRun.status === 'pending') {
            setProgress((prev) => Math.min(prev + 10, 90))
          } else if (updatedTestRun.status === 'success' || updatedTestRun.status === 'failed') {
            clearInterval(pollInterval)
            setProgress(100)
            setTestState("completed")
            
            // Convert to TestHistory format and complete
            const testHistory = convertTestRunToHistory(updatedTestRun)
            
            // Short delay to show completed state
            await new Promise((resolve) => setTimeout(resolve, 500))
            onTestComplete(testHistory)
            
            // Reset form
            setSelectedAppId("")
            setTestType("")
            setTestState("idle")
            setProgress(0)
          }
          
          // Stop polling if we've exceeded max attempts
          if (pollAttempts >= maxPollAttempts) {
            clearInterval(pollInterval)
            setError("Test is taking longer than expected. The test may still be running in the background.")
            setTestState("idle")
            setProgress(0)
          }
        } catch (err) {
          console.error("Error polling test run:", err)
          pollAttempts++
          
          // If we get multiple errors, stop polling
          if (pollAttempts >= 10) {
            clearInterval(pollInterval)
            const errorMessage = err instanceof Error ? err.message : "Failed to get test status"
            setError(`Error checking test status: ${errorMessage}. The test may still be running.`)
            setTestState("idle")
            setProgress(0)
          }
        }
      }, 1000) // Poll every second

      // Timeout after 30 seconds
      setTimeout(() => {
        clearInterval(pollInterval)
        setTestState((currentState) => {
          if (currentState === "running") {
            setError("Test is taking longer than expected. Please check the test run status.")
            setProgress(0)
            return "idle"
          }
          return currentState
        })
      }, 30000)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start test")
      setTestState("idle")
      setProgress(0)
    }
  }

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

          {(testState === "running" || testState === "completed") && (
            <motion.div
              key="running"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0 }}
              className="py-8 text-center"
            >
              <motion.div
                animate={testState === "running" ? { scale: [1, 1.1, 1] } : {}}
                transition={{ repeat: Number.POSITIVE_INFINITY, duration: 1.5 }}
                className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-primary/10 mb-6"
              >
                {testState === "running" ? (
                  <Loader2 className="w-10 h-10 text-primary animate-spin" />
                ) : (
                  <CheckCircle className="w-10 h-10 text-[oklch(0.65_0.18_145)]" />
                )}
              </motion.div>

              <h2 className="text-xl font-semibold text-foreground mb-2">
                {testState === "running" ? "Running Tests..." : "Test Completed!"}
              </h2>
              <p className="text-muted-foreground mb-6">
                {testState === "running"
                  ? `Testing ${selectedApp?.name || appName || "application"}`
                  : "Generating report..."}
              </p>

              <div className="max-w-md mx-auto">
                <Progress value={Math.min(progress, 100)} className="h-2 bg-secondary" />
                <p className="text-sm text-muted-foreground mt-2">{Math.min(Math.round(progress), 100)}% complete</p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </div>
  )
}
