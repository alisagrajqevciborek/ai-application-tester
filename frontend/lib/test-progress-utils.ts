/**
 * Shared utility functions for calculating and managing test progress.
 * Ensures consistent progress calculation across all components.
 */

import type { TestRun, TestRunStepResult } from "./api"

/**
 * Calculate test progress percentage from step results.
 * Returns a value between 5 and 95 to avoid showing 0% or 100% while running.
 *
 * @param testRun - The test run object containing step_results
 * @returns Progress percentage (5-95)
 */
export function calculateTestProgress(testRun: TestRun): number {
  const steps = testRun.step_results
  
  // If no steps available, use basic status-based estimation
  if (!steps || steps.length === 0) {
    return getBasicProgressFromStatus(testRun.status)
  }
  
  // Count completed steps (success or failed)
  const completedSteps = steps.filter(
    (s) =>
      s.status === "success" ||
      s.status === "failed"
  ).length
  
  // Calculate raw progress
  const rawProgress = (completedSteps / steps.length) * 100
  
  // Clamp between 5 and 95 so it never looks "done" while still running
  return Math.max(5, Math.min(95, Math.round(rawProgress)))
}

/**
 * Get basic progress estimate from test status when steps aren't available.
 *
 * @param status - The test run status
 * @returns Progress percentage
 */
function getBasicProgressFromStatus(
  status: "pending" | "running" | "completed" | "failed" | "canceled" | string
): number {
  const statusProgress: Record<string, number> = {
    pending: 5,
    running: 50,
    completed: 100,
    failed: 100,
    canceled: 100,
  }
  
  return statusProgress[status] ?? 5
}

/**
 * Get human-readable label for test type.
 *
 * @param testType - The test type identifier
 * @returns Human-readable label
 */
export function getTestTypeLabel(testType: string): string {
  const labels: Record<string, string> = {
    general: "General",
    functional: "Functional",
    regression: "Regression",
    performance: "Performance",
    accessibility: "Accessibility",
    broken_links: "Broken Links",
    authentication: "Authentication",
  }
  
  return labels[testType] ?? testType
}

/**
 * Calculate elapsed time from test start.
 *
 * @param startedAt - ISO timestamp when test started
 * @returns Elapsed seconds
 */
export function calculateElapsedTime(startedAt: string): number {
  const testStart = new Date(startedAt).getTime()
  return Math.floor((Date.now() - testStart) / 1000)
}

/**
 * Format seconds to human-readable duration.
 *
 * @param seconds - Duration in seconds
 * @returns Formatted string (e.g., "2m 30s")
 */
export function formatDuration(seconds: number): string {
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const secs = seconds % 60
  
  if (hours > 0) {
    return `${hours}h ${minutes}m ${secs}s`
  }
  if (minutes > 0) {
    return `${minutes}m ${secs}s`
  }
  return `${secs}s`
}

/**
 * Estimate remaining time based on current progress and elapsed time.
 *
 * @param progress - Current progress (0-100)
 * @param elapsedSeconds - Elapsed time in seconds
 * @returns Estimated remaining seconds
 */
export function estimateRemainingTime(
  progress: number,
  elapsedSeconds: number
): number {
  if (progress <= 0) return 300 // Default 5 minutes
  if (progress >= 100) return 0
  
  const estimatedTotal = (elapsedSeconds / progress) * 100
  return Math.max(0, Math.round(estimatedTotal - elapsedSeconds))
}

/**
 * Determine if a test is actively running.
 *
 * @param status - Test status
 * @returns True if test is running
 */
export function isTestActive(
  status: "pending" | "running" | "completed" | "failed" | "canceled" | string
): boolean {
  return status === "running" || status === "pending"
}

/**
 * Get current step information from a test run.
 *
 * @param testRun - The test run object
 * @returns Object with current step info
 */
export function getCurrentStepInfo(testRun: TestRun): {
  currentStep: string
  stepNumber: number
  totalSteps: number
} {
  const steps = testRun.step_results || []
  
  if (steps.length === 0) {
    return {
      currentStep: "Initializing test...",
      stepNumber: 0,
      totalSteps: 0,
    }
  }
  
  // Find the first non-completed step
  const currentStepIndex = steps.findIndex(
    (s) =>
      s.status === "running" ||
      s.status === "pending"
  )
  
  if (currentStepIndex === -1) {
    // All steps complete
    return {
      currentStep: "Finalizing results...",
      stepNumber: steps.length,
      totalSteps: steps.length,
    }
  }
  
  const currentStep = steps[currentStepIndex]
  
  return {
    currentStep: currentStep.step_label || `Step ${currentStepIndex + 1}`,
    stepNumber: currentStepIndex + 1,
    totalSteps: steps.length,
  }
}

/**
 * Count warnings and errors from step results.
 *
 * @param testRun - The test run object
 * @returns Object with warning and error counts
 */
export function countIssues(testRun: TestRun): {
  warnings: number
  errors: number
} {
  const steps = testRun.step_results || []
  
  const errors = steps.filter((s) => s.status === "failed").length
  // Warnings can be derived from pass_rate - steps that partially succeeded
  const warnings = steps.filter((s) => s.pass_rate > 0 && s.pass_rate < 100).length
  
  return { warnings, errors }
}
