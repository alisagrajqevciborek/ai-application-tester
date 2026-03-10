"use client"

import { useState, useEffect, useRef } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { Sparkles, Loader2, Send, CheckCircle2, X, Edit2, RefreshCw, Copy, Play, Tag, CheckCircle, Pause } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { testCaseApi, testRunsApi, type GeneratedTestCase, type TestCaseStep, type TestRun } from "@/lib/api"
import type { Application } from "@/lib/api"
import type { TestHistory } from "@/lib/types"
import { cn } from "@/lib/utils"
import { TestProgressIndicator, type TestProgressData } from "./test-progress-indicator"

interface AITestCaseGeneratorProps {
  application: Application | null
  applications?: Application[]
  onTestCaseGenerated?: (testCase: GeneratedTestCase) => void
  onTestComplete?: (test: TestHistory) => void
}

type TestState = "idle" | "running" | "completed"

export default function AITestCaseGenerator({ 
  application: initialApplication, 
  applications = [],
  onTestCaseGenerated,
  onTestComplete
}: AITestCaseGeneratorProps) {
  const [selectedAppId, setSelectedAppId] = useState<string>(initialApplication?.id.toString() || "")
  const [prompt, setPrompt] = useState("")
  const [testType, setTestType] = useState<string>("functional")
  // "none" = no script, JSON-only test case
  const [scriptFramework, setScriptFramework] = useState<string>("none")
  const [isGenerating, setIsGenerating] = useState(false)
  const [generatedTestCase, setGeneratedTestCase] = useState<GeneratedTestCase | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [refinementPrompt, setRefinementPrompt] = useState("")
  const [isRefining, setIsRefining] = useState(false)
  const [expandedStep, setExpandedStep] = useState<number | null>(null)
  
  // Test run state
  const [testState, setTestState] = useState<TestState>("idle")
  const [testProgressData, setTestProgressData] = useState<TestProgressData>({
    progress: 0,
    currentStep: "Initializing...",
    warnings: 0,
    errors: 0,
    elapsedTime: 0,
    estimatedTime: 300,
    status: "running"
  })
  const [showContinueButton, setShowContinueButton] = useState(false)
  const [completedTestHistory, setCompletedTestHistory] = useState<TestHistory | null>(null)
  const [loadingText, setLoadingText] = useState("Testing")
  const [loadingDots, setLoadingDots] = useState("")

  // Get selected application
  const application = applications.find(app => app.id.toString() === selectedAppId) || initialApplication

  // Update selected app when applications change
  useEffect(() => {
    if (applications.length > 0 && !selectedAppId) {
      setSelectedAppId(applications[0].id.toString())
    }
  }, [applications, selectedAppId])

  // Loading dots animation
  useEffect(() => {
    if (testState !== "running") {
      setLoadingDots("")
      return
    }

    const dotsInterval = setInterval(() => {
      setLoadingDots((prev) => (prev.length >= 3 ? "" : prev + "."))
    }, 500)

    return () => {
      clearInterval(dotsInterval)
    }
  }, [testState])

  const handleGenerate = async () => {
    if (!prompt.trim()) {
      setError("Please enter a test description")
      return
    }

    if (!application) {
      setError("Please select an application first")
      return
    }

    setIsGenerating(true)
    setError(null)
    setGeneratedTestCase(null)

    try {
      const framework =
        scriptFramework === "none" ? undefined : (scriptFramework as 'playwright' | 'selenium' | 'cypress')
      const testCase = await testCaseApi.generate(
        prompt,
        application.id,
        testType,
        framework
      )
      setGeneratedTestCase(testCase)
      setPrompt("") // Clear prompt after generation
      onTestCaseGenerated?.(testCase)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to generate test case")
    } finally {
      setIsGenerating(false)
    }
  }

  const handleRefine = async () => {
    if (!refinementPrompt.trim() || !generatedTestCase) {
      setError("Please enter a refinement request")
      return
    }

    setIsRefining(true)
    setError(null)

    try {
      console.log("Starting refine request with prompt:", refinementPrompt)
      console.log("Current test case:", generatedTestCase)
      const refined = await testCaseApi.refine(generatedTestCase, refinementPrompt)
      console.log("Refined test case received:", refined)
      setGeneratedTestCase(refined)
      setRefinementPrompt("")
    } catch (err) {
      console.error("Refine error:", err)
      setError(err instanceof Error ? err.message : "Failed to refine test case")
    } finally {
      setIsRefining(false)
    }
  }

  const handleCopySteps = () => {
    if (!generatedTestCase) return
    
    const stepsText = generatedTestCase.steps
      .map((step, idx) => `${idx + 1}. ${step.action}: ${step.description}`)
      .join('\n')
    
    navigator.clipboard.writeText(stepsText)
  }

  const getActionIcon = (action: string) => {
    switch (action) {
      case 'navigate': return ''
      case 'click': return ''
      case 'fill': return ''
      case 'wait': return ''
      case 'assert': return ''
      case 'check': return ''
      case 'select': return ''
      case 'hover': return ''
      case 'scroll': return ''
      case 'screenshot': return ''
      default: return ''
    }
  }

  const getActionColor = (action: string) => {
    switch (action) {
      case 'navigate': return 'bg-blue-500/20 text-blue-400'
      case 'click': return 'bg-green-500/20 text-green-400'
      case 'fill': return 'bg-purple-500/20 text-purple-400'
      case 'wait': return 'bg-yellow-500/20 text-yellow-400'
      case 'assert': return 'bg-orange-500/20 text-orange-400'
      default: return 'bg-gray-500/20 text-gray-400'
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

  const handleRunTest = async () => {
    if (!generatedTestCase || !application) return
    
    setError(null)
    setTestState("running")
    setShowContinueButton(false)
    setCompletedTestHistory(null)
    
    const startTime = Date.now()
    
    // Initialize progress data
    setTestProgressData({
      progress: 0,
      currentStep: "Saving test case...",
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
      // Save the test case first
      setTestProgressData(prev => ({ ...prev, progress: 10, currentStep: "Saving test case..." }))
      const savedTestCase = await testCaseApi.save(application.id, generatedTestCase)
      
      if (!savedTestCase.id) {
        throw new Error("Failed to save test case")
      }
      
      // Run the saved test case
      setTestProgressData(prev => ({ ...prev, progress: 20, currentStep: "Starting test execution..." }))
      const testRun = await testCaseApi.run(savedTestCase.id)
      
      // Poll for test completion using real step_results from API
      let pollAttempts = 0
      const maxPollAttempts = 600 // 10 minutes max
      
      const pollInterval = setInterval(async () => {
        pollAttempts++
        const elapsedSeconds = Math.floor((Date.now() - startTime) / 1000)
        
        try {
          const updatedTestRun = await testRunsApi.get(testRun.id)
          
          // Update progress based on status
          if (updatedTestRun.status === 'running' || updatedTestRun.status === 'pending') {
            // Use real step_results from API when available (parallel general runs)
            const steps = updatedTestRun.step_results
            if (steps && steps.length > 0) {
              const completedSteps = steps.filter(
                (s) => s.status === 'success' || s.status === 'failed'
              )
              const runningStep = steps.find((s) => s.status === 'running')
              const realProgress = Math.max(5, Math.min(95, Math.round((completedSteps.length / steps.length) * 100)))
              const currentStepLabel = runningStep
                ? `Running ${runningStep.step_label}...`
                : completedSteps.length === steps.length
                  ? "Finalizing results..."
                  : `Waiting for step ${completedSteps.length + 1}/${steps.length}...`
              const errorCount = steps.filter((s) => s.status === 'failed').length

              setTestProgressData({
                progress: realProgress,
                currentStep: currentStepLabel,
                warnings: 0,
                errors: errorCount,
                elapsedTime: elapsedSeconds,
                estimatedTime: 300,
                status: "running"
              })
            } else {
              // Fallback for non-parallel (single suite / generated test) runs
              const estimatedDuration = 120
              const timeProgress = Math.max(5, Math.min(90, Math.round((elapsedSeconds / estimatedDuration) * 100)))

              setTestProgressData({
                progress: timeProgress,
                currentStep: updatedTestRun.status === 'pending' ? "Queued, waiting for worker..." : "Running tests...",
                warnings: 0,
                errors: 0,
                elapsedTime: elapsedSeconds,
                estimatedTime: estimatedDuration,
                status: "running"
              })
            }
          } else if (updatedTestRun.status === 'success' || updatedTestRun.status === 'failed') {
            clearInterval(pollInterval)
            clearInterval(timeTracker)
            
            const finalSteps = updatedTestRun.step_results
            const failedStepCount = finalSteps ? finalSteps.filter((s) => s.status === 'failed').length : 0

            setTestProgressData({
              progress: 100,
              currentStep: updatedTestRun.status === 'success' ? "Test completed successfully!" : "Test completed with failures",
              warnings: 0,
              errors: failedStepCount || (updatedTestRun.status === 'failed' ? 1 : 0),
              elapsedTime: elapsedSeconds,
              estimatedTime: elapsedSeconds,
              status: updatedTestRun.status === 'success' ? "completed" : "failed"
            })
            
            setTestState("completed")
            
            // Convert to TestHistory format
            const testHistory = convertTestRunToHistory(updatedTestRun)
            setCompletedTestHistory(testHistory)
            
            setTimeout(() => {
              setShowContinueButton(true)
            }, 2000)
            
            return
          }
          
          // Stop polling if we've exceeded max attempts
          if (pollAttempts >= maxPollAttempts) {
            clearInterval(pollInterval)
            clearInterval(timeTracker)
            setError("Test is taking longer than expected. The test may still be running in the background.")
            setTestState("idle")
            return
          }
        } catch (err) {
          console.error("Error polling test run:", err)
          
          if (pollAttempts >= 20) {
            clearInterval(pollInterval)
            clearInterval(timeTracker)
            setError("Error checking test status. The test may still be running in the background.")
            setTestState("idle")
            return
          }
        }
      }, 1000)
      
      // Timeout after 10 minutes
      setTimeout(() => {
        clearInterval(pollInterval)
        clearInterval(timeTracker)
        setTestState((currentState) => {
          if (currentState === "running") {
            setError("Test is taking longer than expected. The test may still be running in the background.")
            return "idle"
          }
          return currentState
        })
      }, 600000)
      
    } catch (err) {
      clearInterval(timeTracker)
      setError(err instanceof Error ? err.message : "Failed to run test case")
      setTestState("idle")
    }
  }

  // If test is running or completed, show progress view
  if (testState === "running" || testState === "completed") {
    return (
      <div className="max-w-2xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass rounded-2xl p-6 lg:p-8"
        >
          <div className="space-y-6">
            <div className="text-center mb-6">
              <motion.div
                animate={testState === "running" ? { scale: [1, 1.1, 1] } : {}}
                transition={{ repeat: Number.POSITIVE_INFINITY, duration: 1.5 }}
                className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-primary/10 mb-4"
              >
                {testState === "running" ? (
                  <Loader2 className="w-10 h-10 text-primary animate-spin" />
                ) : (
                  <CheckCircle className="w-10 h-10 text-[oklch(0.65_0.18_145)]" />
                )}
              </motion.div>

              <p className="text-muted-foreground mb-1">
                {testState === "running"
                  ? `Testing ${application?.name || "application"}`
                  : "Test completed!"}
              </p>
              <h2 className="text-xl font-semibold text-foreground flex items-center justify-center min-h-[2rem]">
                {testState === "running" ? (
                  <span>
                    {loadingText}
                    <span className="inline-block w-[24px] text-left">{loadingDots}</span>
                  </span>
                ) : (
                  "Test Completed!"
                )}
              </h2>
            </div>

            {/* Detailed Progress Indicator */}
            <TestProgressIndicator data={testProgressData} />

            {testState === "completed" && (
              <div className="flex justify-center">
                {showContinueButton ? (
                  <Button
                    onClick={() => {
                      if (!completedTestHistory) return
                      onTestComplete?.(completedTestHistory)
                      setTestState("idle")
                      setGeneratedTestCase(null)
                      setShowContinueButton(false)
                      setCompletedTestHistory(null)
                    }}
                    className="h-12 px-8 rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 font-semibold"
                  >
                    View Report
                  </Button>
                ) : (
                  <p className="text-sm text-muted-foreground">Generating report...</p>
                )}
              </div>
            )}
          </div>
        </motion.div>
      </div>
    )
  }

  return (
    <div className="space-y-4 max-w-2xl mx-auto">
      <Card className="border-border bg-card">
        <CardHeader>
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-primary" />
            <CardTitle>AI Test Case Generator</CardTitle>
          </div>
          <CardDescription>
            Describe what you want to test in natural language, and AI will generate a complete test case
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {applications.length === 0 ? (
            <Alert>
              <AlertDescription>
                Please create an application first using the Quick Test tab to generate test cases
              </AlertDescription>
            </Alert>
          ) : (
            <>
              {/* Application Selector */}
              <div className="space-y-2">
                <Label htmlFor="app-select" className="flex items-center gap-2">
                  <Tag className="w-4 h-4" />
                  Select Application
                </Label>
                <Select value={selectedAppId} onValueChange={setSelectedAppId}>
                  <SelectTrigger id="app-select">
                    <SelectValue placeholder="Choose an application" />
                  </SelectTrigger>
                  <SelectContent>
                    {applications.map((app) => (
                      <SelectItem key={app.id} value={app.id.toString()}>
                        {app.name} - {app.url}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="test-type">Test Type</Label>
                <Select value={testType} onValueChange={setTestType}>
                  <SelectTrigger id="test-type">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="functional">Functional</SelectItem>
                    <SelectItem value="regression">Regression</SelectItem>
                    <SelectItem value="performance">Performance</SelectItem>
                    <SelectItem value="accessibility">Accessibility</SelectItem>
                    <SelectItem value="broken_links">Broken Links</SelectItem>
                    <SelectItem value="authentication">Authentication</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="script-framework">Script Framework (optional)</Label>
                <Select
                  value={scriptFramework}
                  onValueChange={setScriptFramework}
                >
                  <SelectTrigger id="script-framework">
                    <SelectValue placeholder="No script (JSON test case only)" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">No script (JSON only)</SelectItem>
                    <SelectItem value="playwright">Playwright (TypeScript)</SelectItem>
                    <SelectItem value="selenium">Selenium (Python)</SelectItem>
                    <SelectItem value="cypress">Cypress (JavaScript)</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="test-prompt">What do you want to test?</Label>
                <Textarea
                  id="test-prompt"
                  placeholder="e.g., Test the login form with invalid credentials, Check if the shopping cart updates when items are added, Verify that the contact form sends emails correctly..."
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  className="min-h-[100px] resize-none"
                  disabled={isGenerating || !application}
                />
              </div>

              {error && (
                <Alert variant="destructive">
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}

              <Button
                onClick={handleGenerate}
                disabled={isGenerating || !application || !prompt.trim()}
                className="w-full"
              >
                {isGenerating ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Generating...
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4 mr-2" />
                    Generate Test Case
                  </>
                )}
              </Button>
            </>
          )}
        </CardContent>
      </Card>

      <AnimatePresence>
        {generatedTestCase && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="space-y-4"
          >
            <Card className="border-border bg-card">
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <CardTitle className="text-lg">{generatedTestCase.name}</CardTitle>
                      {generatedTestCase.fallback && (
                        <Badge variant="outline" className="text-xs">Fallback</Badge>
                      )}
                    </div>
                    <CardDescription>{generatedTestCase.description}</CardDescription>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={handleCopySteps}
                      title="Copy steps"
                    >
                      <Copy className="w-4 h-4" />
                    </Button>
                    <Button
                      variant="default"
                      size="sm"
                      onClick={handleRunTest}
                      title="Run this test"
                    >
                      <Play className="w-4 h-4 mr-1" />
                      Run Test
                    </Button>
                  </div>
                </div>
                <div className="flex flex-wrap gap-2 mt-3">
                  {generatedTestCase.tags.map((tag, idx) => (
                    <Badge key={idx} variant="secondary" className="text-xs">
                      {tag}
                    </Badge>
                  ))}
                  <Badge variant="outline" className="text-xs">
                    {generatedTestCase.estimated_duration}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <h4 className="text-sm font-semibold mb-2">Expected Results</h4>
                  <p className="text-sm text-muted-foreground">{generatedTestCase.expected_results}</p>
                </div>

                <div>
                  <h4 className="text-sm font-semibold mb-3">Test Steps</h4>
                  <ScrollArea className="h-[400px] pr-4">
                    <div className="space-y-2">
                      {generatedTestCase.steps.map((step, idx) => (
                        <motion.div
                          key={idx}
                          initial={{ opacity: 0, x: -10 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ delay: idx * 0.05 }}
                          className={cn(
                            "p-3 rounded-lg border border-border bg-secondary/30",
                            expandedStep === idx && "bg-secondary/50"
                          )}
                        >
                          <div
                            className="flex items-start gap-3 cursor-pointer"
                            onClick={() => setExpandedStep(expandedStep === idx ? null : idx)}
                          >
                            <div className={cn(
                              "flex items-center justify-center w-8 h-8 rounded-full text-sm font-semibold flex-shrink-0",
                              getActionColor(step.action)
                            )}>
                              {step.order}
                            </div>
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2 mb-1">
                                {getActionIcon(step.action) && (
                                  <span className="text-lg">{getActionIcon(step.action)}</span>
                                )}
                                <Badge variant="outline" className="text-xs">
                                  {step.action}
                                </Badge>
                                <span className="text-sm font-medium text-foreground">
                                  {step.description}
                                </span>
                              </div>
                              {expandedStep === idx && (
                                <motion.div
                                  initial={{ opacity: 0, height: 0 }}
                                  animate={{ opacity: 1, height: "auto" }}
                                  className="mt-2 space-y-2 text-xs text-muted-foreground"
                                >
                                  {step.selector && (
                                    <div>
                                      <span className="font-medium">Selector:</span>{" "}
                                      <code className="bg-muted px-1.5 py-0.5 rounded">{step.selector}</code>
                                    </div>
                                  )}
                                  {step.value && (
                                    <div>
                                      <span className="font-medium">Value:</span>{" "}
                                      <code className="bg-muted px-1.5 py-0.5 rounded">{step.value}</code>
                                    </div>
                                  )}
                                  <div>
                                    <span className="font-medium">Expected:</span> {step.expected_result}
                                  </div>
                                </motion.div>
                              )}
                            </div>
                          </div>
                        </motion.div>
                      ))}
                    </div>
                  </ScrollArea>
                </div>

                {generatedTestCase.script_code && (
                  <div className="pt-4 border-t border-border space-y-2">
                    <div className="flex items-center justify-between">
                      <h4 className="text-sm font-semibold">
                        Generated Script ({generatedTestCase.script_framework})
                      </h4>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          navigator.clipboard.writeText(generatedTestCase.script_code || "")
                        }}
                        title="Copy script"
                      >
                        <Copy className="w-4 h-4 mr-1" />
                        Copy Script
                      </Button>
                    </div>
                    <ScrollArea className="h-[300px] rounded-md border border-border bg-muted/40 p-3">
                      <pre className="text-xs font-mono whitespace-pre overflow-x-auto">
                        {generatedTestCase.script_code}
                      </pre>
                    </ScrollArea>
                  </div>
                )}

                {/* Refinement Section */}
                <div className="pt-4 border-t border-border">
                  <h4 className="text-sm font-semibold mb-2">Refine Test Case</h4>
                  <div className="space-y-2">
                    <Textarea
                      placeholder="e.g., Add a step to check error message, Remove step 3, Change the email to test@example.com..."
                      value={refinementPrompt}
                      onChange={(e) => setRefinementPrompt(e.target.value)}
                      className="min-h-[80px] resize-none text-sm"
                      disabled={isRefining}
                    />
                    <Button
                      onClick={handleRefine}
                      disabled={isRefining || !refinementPrompt.trim()}
                      variant="outline"
                      size="sm"
                      className="w-full"
                    >
                      {isRefining ? (
                        <>
                          <Loader2 className="w-3 h-3 mr-2 animate-spin" />
                          Refining...
                        </>
                      ) : (
                        <>
                          <RefreshCw className="w-3 h-3 mr-2" />
                          Refine
                        </>
                      )}
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
