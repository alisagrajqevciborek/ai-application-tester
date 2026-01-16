"use client"

import { useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { Play, Globe, Tag, FileCode, Loader2, CheckCircle } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import type { TestHistory } from "@/lib/types"
import { Progress } from "@/components/ui/progress"

interface NewTestFormProps {
  onTestComplete: (test: TestHistory) => void
}

type TestState = "idle" | "running" | "completed"
type TestType = "functional" | "regression" | "performance" | "accessibility"

export default function NewTestForm({ onTestComplete }: NewTestFormProps) {
  const [appName, setAppName] = useState("")
  const [appUrl, setAppUrl] = useState("")
  const [testType, setTestType] = useState<TestType | "">("")
  const [testState, setTestState] = useState<TestState>("idle")
  const [progress, setProgress] = useState(0)

  const handleStartTest = async () => {
    if (!appName || !appUrl || !testType) return

    setTestState("running")
    setProgress(0)

    // Simulate test progress
    const interval = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 100) {
          clearInterval(interval)
          return 100
        }
        return prev + Math.random() * 15
      })
    }, 300)

    // Complete test after 3 seconds
    await new Promise((resolve) => setTimeout(resolve, 3000))
    clearInterval(interval)
    setProgress(100)
    setTestState("completed")

    // Generate random results
    const passRate = Math.floor(Math.random() * 40) + 60
    const newTest: TestHistory = {
      id: Date.now().toString(),
      appName,
      status: passRate > 70 ? "success" : "failed",
      testType: testType as TestType,
      date: new Date().toISOString().split("T")[0],
      passRate,
      failRate: 100 - passRate,
    }

    // Short delay to show completed state
    await new Promise((resolve) => setTimeout(resolve, 500))
    onTestComplete(newTest)

    // Reset form
    setAppName("")
    setAppUrl("")
    setTestType("")
    setTestState("idle")
    setProgress(0)
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
                disabled={!appName || !appUrl || !testType}
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
                {testState === "running" ? `Testing ${appName}` : "Generating report..."}
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
