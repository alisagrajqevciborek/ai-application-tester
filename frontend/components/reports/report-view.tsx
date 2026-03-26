"use client"

import { Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import type { TestHistory, TestIssue } from "@/lib/types"
import { useState, useEffect } from "react"
import { reportsApi, type Report } from "@/lib/api"
import { toast } from "sonner"
import { exportReportExcel, exportReportPdf } from "@/lib/report-export"
import ReportMainContent from "@/components/reports/report-main-content"
import { ErrorBoundary } from "@/components/common/error-boundary"

interface ReportViewProps {
  test: TestHistory
  onBack: () => void
  onDelete?: (testId: string) => void
}

export default function ReportView({ test, onBack, onDelete }: ReportViewProps) {
  const [expandedIssue, setExpandedIssue] = useState<string | null>(null)
  const [showFullReport, setShowFullReport] = useState(false)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [report, setReport] = useState<Report | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [activeScreenshotUrl, setActiveScreenshotUrl] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<"findings" | "logs">("findings")
  const [isExportingToJira, setIsExportingToJira] = useState(false)
  const [refreshAttempts, setRefreshAttempts] = useState(0)

  useEffect(() => {
    setRefreshAttempts(0)
    loadReport()
  }, [test.id])

  useEffect(() => {
    if (!report) return

    const hasMeaningfulContent =
      (report.detailed_report && report.detailed_report.length > 100) ||
      (report.issues_json?.length ?? 0) > 0 ||
      (report.console_logs_json?.length ?? 0) > 0
    if (hasMeaningfulContent) return
    if (refreshAttempts >= 24) return

    const timer = setTimeout(() => {
      setRefreshAttempts((prev) => prev + 1)
      loadReport(true)
    }, 5000)

    return () => clearTimeout(timer)
  }, [report, refreshAttempts])

  const loadReport = async (silent = false) => {
    try {
      if (!silent) {
        setIsLoading(true)
      }
      setError(null)
      const reportData = await reportsApi.get(parseInt(test.id))
      setReport(reportData)
      // Debug: Log screenshots received
      if (reportData.screenshots && reportData.screenshots.length > 0) {
        console.log("Screenshots received:", reportData.screenshots)
      } else {
        console.log("No screenshots in report data")
      }
    } catch (err) {
      console.error("Error loading report:", err)
      setError(err instanceof Error ? err.message : "Failed to load report")
    } finally {
      setIsLoading(false)
    }
  }

  const handleDeleteConfirm = () => {
    if (onDelete) {
      onDelete(test.id)
      onBack() // Go back after deletion
    }
    setDeleteDialogOpen(false)
  }

  // Use real issues from report instead of mockIssues
  const issues: TestIssue[] = report?.issues_json?.map((issue, idx) => ({
    id: idx.toString(),
    title: issue.title,
    severity: issue.severity,
    description: issue.description,
    screenshot: issue.element_screenshot || "",
    location: issue.location,
    selector: issue.selector,
    element_screenshot: issue.element_screenshot,
    before_screenshot: issue.before_screenshot,
    after_screenshot: issue.after_screenshot,
    reference_screenshot: issue.reference_screenshot,
    context_screenshot: issue.context_screenshot,
    all_screenshots: issue.all_screenshots,
  })) || []

  const criticalCount = issues.filter((i) => i.severity === "critical").length
  const majorCount = issues.filter((i) => i.severity === "major").length
  const minorCount = issues.filter((i) => i.severity === "minor").length
  const screenshots = report?.screenshots ?? []

  // Use report summary if available, otherwise fallback to generated text
  const summaryText = report?.summary || (
    test.status === "success"
      ? `The test suite completed successfully with a ${test.passRate}% pass rate. All critical user flows were validated, and no blocking issues were found. ${minorCount} minor improvements are suggested for accessibility compliance.`
      : `The test suite encountered ${test.failRate}% failures. ${criticalCount} critical and ${majorCount} major issues were found that require immediate attention. Review the detailed findings below.`
  )

  // Report is still being generated when we have a report row but no meaningful content yet
  const hasMeaningfulReport =
    (report?.detailed_report && report.detailed_report.length > 100) ||
    (report?.issues_json?.length ?? 0) > 0 ||
    (report?.console_logs_json?.length ?? 0) > 0
  const isGeneratingReport = Boolean(report && !hasMeaningfulReport)

  // Show loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  // Show error state
  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4">
        <p className="text-destructive">{error}</p>
        <Button onClick={onBack}>Go Back</Button>
      </div>
    )
  }

  const handleExportPDF = async () => {
    await exportReportPdf({
      test,
      summaryText,
      issues,
      criticalCount,
      majorCount,
      minorCount,
    })
  }

  const handleExportExcel = async () => {
    await exportReportExcel({
      test,
      summaryText,
      issues,
      criticalCount,
      majorCount,
      minorCount,
    })
  }

  const handleExportToJira = async () => {
    try {
      setIsExportingToJira(true)
      const result = await reportsApi.exportToJira(parseInt(test.id))

      if (result.error) {
        toast.error("Export Failed", {
          description: result.error,
        })
        return
      }

      // Build success message with ticket links
      const messages: string[] = []
      if (result.error_ticket) {
        messages.push(`Error ticket: ${result.error_ticket.key} (${result.errors_exported || 0} errors)`)
      }
      if (result.warning_ticket) {
        messages.push(`Warning ticket: ${result.warning_ticket.key} (${result.warnings_exported || 0} warnings)`)
      }

      if (messages.length > 0) {
        toast.success("✅ Ticket Created - Check Jira!", {
          description: messages.join(", "),
          duration: 5000,
          action: result.error_ticket || result.warning_ticket ? {
            label: "View Tickets",
            onClick: () => {
              if (result.error_ticket) {
                window.open(result.error_ticket.url, '_blank')
              } else if (result.warning_ticket) {
                window.open(result.warning_ticket.url, '_blank')
              }
            }
          } : undefined,
        })
      } else {
        toast.info("No tickets created", {
          description: "No errors or warnings found to export.",
        })
      }
    } catch (err) {
      console.error("Error exporting to Jira:", err)
      toast.error("Export Failed", {
        description: err instanceof Error ? err.message : "Failed to export to Jira. Please check your Jira configuration.",
      })
    } finally {
      setIsExportingToJira(false)
    }
  }

  return (
    <ErrorBoundary>
      <ReportMainContent
        test={test}
        onBack={onBack}
        onDelete={onDelete}
        summaryText={summaryText}
        criticalCount={criticalCount}
        majorCount={majorCount}
        minorCount={minorCount}
        issues={issues}
        screenshots={screenshots}
        report={report}
        isGeneratingReport={isGeneratingReport}
        expandedIssue={expandedIssue}
        setExpandedIssue={setExpandedIssue}
        showFullReport={showFullReport}
        setShowFullReport={setShowFullReport}
        activeScreenshotUrl={activeScreenshotUrl}
        setActiveScreenshotUrl={setActiveScreenshotUrl}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        deleteDialogOpen={deleteDialogOpen}
        setDeleteDialogOpen={setDeleteDialogOpen}
        isExportingToJira={isExportingToJira}
        onExportPDF={handleExportPDF}
        onExportExcel={handleExportExcel}
        onExportToJira={handleExportToJira}
        onConfirmDelete={handleDeleteConfirm}
      />
    </ErrorBoundary>
  )
}
