"use client"

import { motion, AnimatePresence } from "framer-motion"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import {
  ArrowLeft,
  ExternalLink,
  Download,
  AlertTriangle,
  AlertCircle,
  Info,
  ZoomIn,
  X,
  FileText,
  FileSpreadsheet,
  Lightbulb,
  Wrench,
  CheckCircle2,
  Trash2,
  Terminal,
  Code,
  Layout,
  Maximize2,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import type { TestHistory, TestIssue } from "@/lib/types"
import StatusBadge from "@/components/common/status-badge"
import DonutChart from "@/components/charts/donut-chart"
import { useState, useEffect } from "react"
import { cn } from "@/lib/utils"
import { reportsApi, type Report } from "@/lib/api"
import { Loader2 } from "lucide-react"
import { toast } from "sonner"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
// Note: jspdf and xlsx are imported dynamically in functions to avoid SSR issues
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
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion"

interface ReportViewProps {
  test: TestHistory
  onBack: () => void
  onDelete?: (testId: string) => void
}

const mockIssues: TestIssue[] = [
  {
    id: "1",
    title: "Login button unresponsive on mobile",
    severity: "critical",
    description:
      "The login button does not respond to touch events on iOS Safari. Users are unable to authenticate on mobile devices.",
    screenshot: "mobile login button error screenshot showing unresponsive state",
    location: "/login - Mobile View",
  },
  {
    id: "2",
    title: "Form validation message not visible",
    severity: "major",
    description:
      "Error messages for invalid email input are rendered below the fold and not visible to users without scrolling.",
    screenshot: "form validation error message hidden below viewport",
    location: "/signup - Email Field",
  },
  {
    id: "3",
    title: "Slow API response on dashboard load",
    severity: "major",
    description:
      "Dashboard takes 4.2 seconds to load data from the API, exceeding the 3-second threshold for acceptable performance.",
    screenshot: "dashboard loading state with spinner showing delay",
    location: "/dashboard - Initial Load",
  },
  {
    id: "4",
    title: "Missing alt text on product images",
    severity: "minor",
    description: "Product images in the catalog are missing alt attributes, affecting accessibility compliance.",
    screenshot: "product catalog page with images missing alt text",
    location: "/products - Image Grid",
  },
  {
    id: "5",
    title: "Color contrast ratio insufficient",
    severity: "minor",
    description: "Secondary text color has a contrast ratio of 3.8:1, below the WCAG AA standard of 4.5:1.",
    screenshot: "text contrast analysis showing low ratio",
    location: "/about - Body Text",
  },
]

const fixSuggestions: Record<string, { review: string; suggestions: string[] }> = {
  "1": {
    review:
      "The touch event handler is not properly bound on iOS Safari due to a missing touchstart event listener. The button relies solely on click events which have a 300ms delay on mobile Safari.",
    suggestions: [
      "Add explicit touchstart and touchend event listeners to the login button",
      "Use the 'touch-action: manipulation' CSS property to remove the 300ms delay",
      "Consider using a library like FastClick for legacy iOS support",
      "Test with iOS Safari's touch event simulation in dev tools",
    ],
  },
  "2": {
    review:
      "The validation error message container has a fixed position relative to the input field, but the parent container has overflow:hidden which clips the message on smaller viewports.",
    suggestions: [
      "Change the error message positioning to relative instead of absolute",
      "Add sufficient margin-bottom to the form container to accommodate error messages",
      "Consider using inline validation that appears within the input boundary",
      "Implement scroll-into-view behavior when validation errors appear",
    ],
  },
  "3": {
    review:
      "The dashboard makes 12 sequential API calls on initial load, each waiting for the previous to complete. Additionally, there's no caching layer and the backend queries are not optimized.",
    suggestions: [
      "Implement parallel API requests using Promise.all() for independent data",
      "Add a Redis caching layer for frequently accessed dashboard data",
      "Optimize database queries with proper indexing and query batching",
      "Implement skeleton loading states for progressive data display",
    ],
  },
  "4": {
    review:
      "The product image component doesn't enforce alt text requirements, and the CMS allows images to be uploaded without accessibility metadata.",
    suggestions: [
      "Add required 'alt' prop validation to the ProductImage component",
      "Implement CMS-level validation requiring alt text for all uploads",
      "Use AI-generated alt text as a fallback for legacy images",
      "Add ESLint jsx-a11y rules to catch missing alt text during development",
    ],
  },
  "5": {
    review:
      "The secondary text color (#6B7280) against the background (#F9FAFB) results in a contrast ratio of 3.8:1, which fails WCAG AA requirements for normal text.",
    suggestions: [
      "Darken the secondary text color to #4B5563 for a 5.74:1 contrast ratio",
      "Alternatively, darken the background slightly to increase contrast",
      "Use a color contrast checker tool in your design system",
      "Implement automated accessibility testing in your CI/CD pipeline",
    ],
  },
}

const severityConfig = {
  critical: {
    icon: AlertTriangle,
    color: "text-red-400",
    bg: "bg-red-500/10",
    border: "border-red-500/30",
    label: "Critical",
  },
  major: {
    icon: AlertCircle,
    color: "text-amber-400",
    bg: "bg-amber-500/10",
    border: "border-amber-500/30",
    label: "Major",
  },
  minor: {
    icon: Info,
    color: "text-blue-400",
    bg: "bg-blue-500/10",
    border: "border-blue-500/30",
    label: "Minor",
  },
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

  const handleDeleteClick = () => {
    setDeleteDialogOpen(true)
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

  // ── PDF helpers ──────────────────────────────────────────────────────────

  /**
   * Strip long bundler paths like /_next/static/chunks/abc-123.js down to the
   * bare filename so they don't blow out PDF columns.
   */
  const sanitizeStackTrace = (text: string): string =>
    text.replace(/\/_next\/static\/chunks\/[^\s),:\]]+/g, (match) => {
      const filename = match.split('/').pop() ?? match
      // drop query-string / hash fragments (e.g. chunk.js?v=abc123)
      return filename.replace(/[?#].*$/, '')
    })

  /**
   * Insert spaces after common path delimiters in tokens longer than maxLen
   * so jsPDF's splitTextToSize can wrap them instead of overflowing the page.
   */
  const breakLongWords = (text: string, maxLen = 55): string =>
    text.replace(/\S{55,}/g, (word) =>
      word.replace(/([/_.\\-])(?=[A-Za-z0-9])/g, '$1 ').trimEnd()
    )

  /** Sanitize stack traces then force-break any remaining long tokens. */
  const pdfText = (text: string): string =>
    breakLongWords(sanitizeStackTrace(text ?? ''))

  /**
   * Resolve once the network has been idle for `idleMs` milliseconds —
   * equivalent to Puppeteer's waitUntil: 'networkidle0'.
   * Falls back to a plain timeout when PerformanceObserver isn't available.
   */
  const waitForNetworkIdle = (idleMs = 500): Promise<void> =>
    new Promise((resolve) => {
      let timer: ReturnType<typeof setTimeout> = setTimeout(resolve, idleMs)
      try {
        const observer = new PerformanceObserver(() => {
          clearTimeout(timer)
          timer = setTimeout(() => {
            observer.disconnect()
            resolve()
          }, idleMs)
        })
        observer.observe({ entryTypes: ['resource'] })
      } catch {
        // PerformanceObserver not supported — the fallback timer already runs
      }
    })

  // ─────────────────────────────────────────────────────────────────────────

  const handleExportPDF = async () => {
    // Wait for all in-flight assets/scripts to finish (networkidle0 equivalent)
    await waitForNetworkIdle()

    const { default: jsPDF } = await import('jspdf')
    const doc = new jsPDF()
    const pageWidth = doc.internal.pageSize.getWidth()
    const margin = 20
    let yPos = margin

    // Title
    doc.setFontSize(20)
    doc.setTextColor(255, 140, 0) // Orange color
    doc.text("TestFlow - Test Report", margin, yPos)
    yPos += 12

    // Test Information
    doc.setFontSize(12)
    doc.setTextColor(0, 0, 0)
    doc.setFont("helvetica", "bold")
    doc.text("Test Information", margin, yPos)
    yPos += 8

    doc.setFontSize(10)
    doc.setFont("helvetica", "normal")
    const testInfo = [
      ["Application Name", test.appName],
      ["Version", test.versionName],
      ["Test Type", test.testType.charAt(0).toUpperCase() + test.testType.slice(1)],
      ["Test Date", test.date],
      ["Status", test.status.charAt(0).toUpperCase() + test.status.slice(1)],
      ["Pass Rate", `${test.passRate}%`],
      ["Fail Rate", `${test.failRate}%`],
    ]

    testInfo.forEach((row) => {
      if (yPos > doc.internal.pageSize.getHeight() - 30) {
        doc.addPage()
        yPos = margin
      }
      doc.setFont("helvetica", "bold")
      doc.text(row[0] + ":", margin, yPos)
      doc.setFont("helvetica", "normal")
      doc.text(row[1], margin + 60, yPos)
      yPos += 7
    })

    yPos += 5

    // Summary
    if (yPos > doc.internal.pageSize.getHeight() - 50) {
      doc.addPage()
      yPos = margin
    }
    doc.setFontSize(12)
    doc.setFont("helvetica", "bold")
    doc.text("Test Summary", margin, yPos)
    yPos += 8

    doc.setFontSize(10)
    doc.setFont("helvetica", "normal")
    const summaryLines = doc.splitTextToSize(pdfText(summaryText), pageWidth - 2 * margin)
    summaryLines.forEach((line: string) => {
      if (yPos > doc.internal.pageSize.getHeight() - 30) {
        doc.addPage()
        yPos = margin
      }
      doc.text(line, margin, yPos)
      yPos += 6
    })

    yPos += 5

    // Issue Statistics
    if (yPos > doc.internal.pageSize.getHeight() - 50) {
      doc.addPage()
      yPos = margin
    }
    doc.setFontSize(12)
    doc.setFont("helvetica", "bold")
    doc.text("Issue Statistics", margin, yPos)
    yPos += 8

    doc.setFontSize(10)
    doc.setFont("helvetica", "normal")
    const stats = [
      ["Critical Issues", criticalCount.toString()],
      ["Major Issues", majorCount.toString()],
      ["Minor Issues", minorCount.toString()],
      ["Total Issues", issues.length.toString()],
    ]

    stats.forEach((row) => {
      if (yPos > doc.internal.pageSize.getHeight() - 30) {
        doc.addPage()
        yPos = margin
      }
      doc.setFont("helvetica", "bold")
      doc.text(row[0] + ":", margin, yPos)
      doc.setFont("helvetica", "normal")
      doc.text(row[1], margin + 60, yPos)
      yPos += 7
    })

    yPos += 5

    // Detailed Findings
    if (yPos > doc.internal.pageSize.getHeight() - 50) {
      doc.addPage()
      yPos = margin
    }
    doc.setFontSize(12)
    doc.setFont("helvetica", "bold")
    doc.text("Detailed Findings", margin, yPos)
    yPos += 10

    issues.forEach((issue, index) => {
      if (yPos > doc.internal.pageSize.getHeight() - 60) {
        doc.addPage()
        yPos = margin
      }

      // Issue header
      doc.setFontSize(11)
      doc.setFont("helvetica", "bold")
      doc.text(pdfText(`Issue ${index + 1}: ${issue.title}`), margin, yPos)
      yPos += 7

      // Severity
      doc.setFontSize(9)
      doc.setFont("helvetica", "normal")
      doc.text(pdfText(`Severity: ${issue.severity.charAt(0).toUpperCase() + issue.severity.slice(1)}`), margin, yPos)
      yPos += 6

      // Location
      doc.text(pdfText(`Location: ${issue.location}`), margin, yPos)
      yPos += 6

      // Description
      doc.setFontSize(9)
      const descLines = doc.splitTextToSize(pdfText(issue.description), pageWidth - 2 * margin)
      descLines.forEach((line: string) => {
        if (yPos > doc.internal.pageSize.getHeight() - 30) {
          doc.addPage()
          yPos = margin
        }
        doc.text(line, margin, yPos)
        yPos += 5
      })

      yPos += 5
    })

    // Footer
    const totalPages = (doc as any).internal.getNumberOfPages()
    for (let i = 1; i <= totalPages; i++) {
      doc.setPage(i)
      doc.setFontSize(8)
      doc.setTextColor(150, 150, 150)
      doc.text(
        `Page ${i} of ${totalPages} - TestFlow Test Report`,
        pageWidth / 2,
        doc.internal.pageSize.getHeight() - 10,
        { align: "center" }
      )
    }

    doc.save(`testflow-report-${test.versionName.replace(/\s+/g, "-")}-${test.date.replace(/\//g, "-")}.pdf`)
  }

  const handleExportExcel = async () => {
    // xlsx is CommonJS in many setups; Next/TS dynamic import can return { default: ... }
    const XLSXImport = await import("xlsx")
    const XLSX: any = (XLSXImport as any).default ?? XLSXImport

    // Prepare data for Excel
    const excelData = [
      ["TestFlow - Test Report"],
      ["Exported on", new Date().toLocaleString()],
      [""],
      ["Test Information"],
      ["Field", "Value"],
      ["Application Name", test.appName],
      ["Version", test.versionName],
      ["Test Type", test.testType.charAt(0).toUpperCase() + test.testType.slice(1)],
      ["Test Date", test.date],
      ["Status", test.status.charAt(0).toUpperCase() + test.status.slice(1)],
      ["Pass Rate", `${test.passRate}%`],
      ["Fail Rate", `${test.failRate}%`],
      [""],
      ["Test Summary"],
      ["Summary", summaryText],
      [""],
      ["Issue Statistics"],
      ["Severity", "Count"],
      ["Critical", criticalCount.toString()],
      ["Major", majorCount.toString()],
      ["Minor", minorCount.toString()],
      ["Total", issues.length.toString()],
      [""],
      ["Detailed Findings"],
      ["#", "Title", "Severity", "Location", "Description"],
    ]

    // Add issues
    issues.forEach((issue, index) => {
      excelData.push([
        (index + 1).toString(),
        issue.title,
        issue.severity.charAt(0).toUpperCase() + issue.severity.slice(1),
        issue.location,
        issue.description,
      ])
    })

    // Create workbook and worksheet
    const wb = XLSX.utils.book_new()
    const ws = XLSX.utils.aoa_to_sheet(excelData)

    // Set column widths
    ws["!cols"] = [
      { wch: 5 }, // #
      { wch: 40 }, // Title
      { wch: 12 }, // Severity
      { wch: 30 }, // Location
      { wch: 60 }, // Description
    ]

    // Merge cells for headers
    ws["!merges"] = [
      { s: { r: 0, c: 0 }, e: { r: 0, c: 4 } }, // Title row
      { s: { r: 1, c: 0 }, e: { r: 1, c: 4 } }, // Export date row
      { s: { r: 3, c: 0 }, e: { r: 3, c: 1 } }, // Test Information header
      { s: { r: 12, c: 0 }, e: { r: 12, c: 1 } }, // Test Summary header
      { s: { r: 15, c: 0 }, e: { r: 15, c: 1 } }, // Issue Statistics header
      { s: { r: 22, c: 0 }, e: { r: 22, c: 4 } }, // Detailed Findings header
    ]

    // Style header rows
    const headerRows = [0, 1, 3, 12, 15, 22]
    headerRows.forEach((row) => {
      const cellAddress = XLSX.utils.encode_cell({ r: row, c: 0 })
      if (ws[cellAddress]) {
        ws[cellAddress].s = {
          font: { bold: true, color: { rgb: "FF8C00" } },
        }
      }
    })

    // Style issue header row
    const issueHeaderRow = 23
    for (let col = 0; col < 5; col++) {
      const cellAddress = XLSX.utils.encode_cell({ r: issueHeaderRow, c: col })
      if (ws[cellAddress]) {
        ws[cellAddress].s = {
          font: { bold: true },
          fill: { fgColor: { rgb: "FFF4E6" } },
        }
      }
    }

    // Add worksheet to workbook
    XLSX.utils.book_append_sheet(wb, ws, "Test Report")

    // Save file
    XLSX.writeFile(wb, `testflow-report-${test.versionName.replace(/\s+/g, "-")}-${test.date.replace(/\//g, "-")}.xlsx`)
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
    <>
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center justify-between mb-6"
        >
          <Button variant="ghost" onClick={onBack} className="text-muted-foreground hover:text-orange-600 hover:bg-orange-600/10">
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to New Test
          </Button>
          <div className="flex items-center gap-2">
            <StatusBadge
              status={test.status === "running" ? "running" : test.status === "success" ? "success" : "failed"}
              large
            />
            {onDelete && (
              <Button
                variant="ghost"
                size="sm"
                onClick={handleDeleteClick}
                className="text-destructive hover:text-destructive hover:bg-destructive/10"
              >
                <Trash2 className="w-4 h-4 mr-2" />
                Delete
              </Button>
            )}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="sm" className="ml-2">
                  <Download className="w-4 h-4 mr-2" />
                  Export
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent className="bg-popover border-border" align="end">
                <DropdownMenuItem onClick={() => handleExportPDF()} className="cursor-pointer">
                  <FileText className="mr-2 h-4 w-4 text-red-400" />
                  <span>Export as PDF</span>
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => handleExportExcel()} className="cursor-pointer">
                  <FileSpreadsheet className="mr-2 h-4 w-4 text-green-400" />
                  <span>Export as Excel</span>
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={() => handleExportToJira()}
                  className="cursor-pointer"
                  disabled={isExportingToJira}
                >
                  {isExportingToJira ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin text-blue-400" />
                  ) : (
                    <ExternalLink className="mr-2 h-4 w-4 text-blue-400" />
                  )}
                  <span>Export to Jira</span>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </motion.div>

        {/* Title */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
          <div className="mb-2">
            <h1 className="text-3xl font-bold text-foreground mb-1">{test.versionName}</h1>
            <p className="text-sm text-muted-foreground">Base App: {test.appName}</p>
          </div>
          <div className="flex items-center gap-3">
            <p className="text-muted-foreground">Test completed on {test.date}</p>
            <span className="text-xs px-2 py-1 rounded bg-secondary text-muted-foreground capitalize">
              {test.testType} Test
            </span>
          </div>
        </motion.div>

        {/* Metrics Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="glass rounded-2xl p-6"
          >
            <h3 className="text-lg font-semibold text-foreground mb-4">Pass Rate</h3>
            <DonutChart percentage={test.passRate} color="oklch(0.65 0.18 145)" label="Passed" />
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15 }}
            className="glass rounded-2xl p-6"
          >
            <h3 className="text-lg font-semibold text-foreground mb-4">Fail Rate</h3>
            <DonutChart percentage={test.failRate} color="oklch(0.55 0.2 25)" label="Failed" />
          </motion.div>
        </div>

        {/* Summary Card */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="glass rounded-2xl p-6 mb-8"
        >
          <h3 className="text-lg font-semibold text-foreground mb-4">Test Summary</h3>
          <p className="text-muted-foreground leading-relaxed mb-6">{summaryText}</p>

          {/* Issue Count Summary */}
          <div className="flex gap-4 mb-6">
            {criticalCount > 0 && (
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-red-500/10 border border-red-500/30">
                <AlertTriangle className="w-4 h-4 text-red-400" />
                <span className="text-sm text-red-400 font-medium">{criticalCount} Critical</span>
              </div>
            )}
            {majorCount > 0 && (
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-amber-500/10 border border-amber-500/30">
                <AlertCircle className="w-4 h-4 text-amber-400" />
                <span className="text-sm text-amber-400 font-medium">{majorCount} Major</span>
              </div>
            )}
            {minorCount > 0 && (
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-blue-500/10 border border-blue-500/30">
                <Info className="w-4 h-4 text-blue-400" />
                <span className="text-sm text-blue-400 font-medium">{minorCount} Minor</span>
              </div>
            )}
          </div>

          {/* Actions - Updated with dropdown for export */}
        </motion.div>

        {/* Tabs */}
        <div className="flex border-b border-border/50 mb-6 px-1">
          <Button
            variant="ghost"
            onClick={() => setActiveTab("findings")}
            className={cn(
              "relative px-6 py-4 rounded-none h-auto transition-colors",
              activeTab === "findings" ? "text-primary border-b-2 border-primary" : "text-muted-foreground"
            )}
          >
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4" />
              <span>Detailed Findings</span>
              <span className="ml-1 text-xs opacity-60">({issues.length})</span>
            </div>
          </Button>
          <Button
            variant="ghost"
            onClick={() => setActiveTab("logs")}
            className={cn(
              "relative px-6 py-4 rounded-none h-auto transition-colors",
              activeTab === "logs" ? "text-primary border-b-2 border-primary" : "text-muted-foreground"
            )}
          >
            <div className="flex items-center gap-2">
              <Terminal className="w-4 h-4" />
              <span>Console Logs</span>
              {report?.console_logs_json && (
                <span className="ml-1 text-xs opacity-60">({report.console_logs_json.length})</span>
              )}
            </div>
          </Button>
        </div>

        {activeTab === "findings" ? (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.25 }}
            className="mb-8"
          >
            <h3 className="text-lg font-semibold text-foreground mb-4">Detailed Report</h3>
            {isGeneratingReport ? (
              <div className="rounded-xl border border-primary/30 bg-primary/10 p-4 flex items-center gap-4 mb-8">
                <Loader2 className="h-6 w-6 shrink-0 animate-spin text-primary" />
                <p className="font-medium text-foreground">Generating your report</p>
              </div>
            ) : report?.detailed_report && report.detailed_report.length > 100 ? (
              <div className="mb-8">
                {(() => {
                  // 1. Remove the reference section
                  const cleanReport = report.detailed_report.split(/={10,}\s*AUTOMATED TEST FINDINGS \(REFERENCE\)/)[0].trim()

                  // 2. Split by ## headings first (main sections)
                  const mainSections = cleanReport.split(/(?=^## )/m)
                  
                  // Function to create nested accordion for subsections
                  const parseSubsections = (content: string) => {
                    const subsections = content.split(/(?=^### )/m)
                    if (subsections.length <= 1) {
                      return { hasSubsections: false, content }
                    }
                    
                    const parsed = subsections
                      .map((sub, idx) => {
                        const trimmed = sub.trim()
                        if (!trimmed) return null
                        
                        if (trimmed.startsWith('### ')) {
                          const firstLineEnd = trimmed.indexOf('\n')
                          const title = firstLineEnd > 0 
                            ? trimmed.substring(4, firstLineEnd).trim() 
                            : trimmed.substring(4).trim()
                          const content = firstLineEnd > 0 
                            ? trimmed.substring(firstLineEnd + 1).trim() 
                            : ''
                          return { title, content, idx }
                        } else {
                          return { title: null, content: trimmed, idx }
                        }
                      })
                      .filter(Boolean) as Array<{ title: string | null; content: string; idx: number }>
                    
                    return { hasSubsections: true, intro: parsed[0]?.title ? null : parsed[0], subsections: parsed.filter(s => s.title) }
                  }
                  
                  // Parse main sections
                  const parsedSections = mainSections
                    .map((section, idx) => {
                      const trimmed = section.trim()
                      if (!trimmed) return null
                      
                      if (trimmed.startsWith('## ')) {
                        const firstLineEnd = trimmed.indexOf('\n')
                        const title = firstLineEnd > 0 
                          ? trimmed.substring(3, firstLineEnd).trim() 
                          : trimmed.substring(3).trim()
                        const content = firstLineEnd > 0 
                          ? trimmed.substring(firstLineEnd + 1).trim() 
                          : ''
                        
                        const subsectionData = parseSubsections(content)
                        return { title, ...subsectionData, idx }
                      } else {
                        return { title: null, content: trimmed, hasSubsections: false, idx }
                      }
                    })
                    .filter(Boolean) as Array<{ 
                      title: string | null; 
                      content?: string; 
                      hasSubsections: boolean;
                      intro?: any;
                      subsections?: Array<{ title: string; content: string; idx: number }>;
                      idx: number 
                    }>

                  if (parsedSections.length === 0) {
                    return null
                  }

                  // If no sections with headings found, show as single block
                  if (parsedSections.every(s => !s.title)) {
                    return (
                      <div className="p-6 bg-gradient-to-br from-muted/30 to-muted/50 rounded-xl border border-border/50 shadow-lg">
                        <div className="prose prose-invert max-w-none prose-p:text-foreground/85 prose-headings:text-foreground prose-strong:text-foreground prose-code:text-primary prose-ul:list-disc prose-ol:list-decimal">
                          <ReactMarkdown
                            remarkPlugins={[remarkGfm]}
                            components={{
                              h2: ({ ...props }) => <h2 className="text-2xl font-bold mt-8 mb-4 pb-3 border-b-2 border-primary/30" {...props} />,
                              h3: ({ ...props }) => <h3 className="text-xl font-semibold mt-6 mb-3" {...props} />,
                              h4: ({ ...props }) => <h4 className="text-lg font-medium mt-5 mb-2" {...props} />,
                              p: ({ ...props }) => <p className="text-[15px] leading-relaxed mb-4" {...props} />,
                              ul: ({ ...props }) => <ul className="space-y-2 mb-4 ml-6" {...props} />,
                              ol: ({ ...props }) => <ol className="space-y-2 mb-4 ml-6" {...props} />,
                              li: ({ ...props }) => <li className="text-sm leading-relaxed" {...props} />,
                              code: ({ inline, ...props }: any) =>
                                inline ? (
                                  <code className="px-1.5 py-0.5 rounded bg-muted/80 text-xs font-mono" {...props} />
                                ) : (
                                  <pre className="bg-[#0f1115] p-4 rounded-lg border border-border/50 my-4 overflow-x-auto">
                                    <code className="text-sm font-mono text-[#e1e4e8]" {...props} />
                                  </pre>
                                ),
                              hr: () => <hr className="border-t border-border/30 my-6" />,
                              strong: ({ ...props }) => <strong className="font-semibold" {...props} />,
                            }}
                          >
                            {cleanReport}
                          </ReactMarkdown>
                        </div>
                      </div>
                    )
                  }

                  // Extract intro and main sections
                  const intro = parsedSections[0]?.title ? null : parsedSections[0]
                  const sectionsWithHeadings = parsedSections.filter(s => s.title)
                  
                  const defaultExpanded = sectionsWithHeadings.length > 0 ? [`section-0`] : []

                  const markdownComponents = {
                    h2: ({ ...props }: any) => <h2 className="text-2xl font-bold mt-8 mb-4 pb-3 border-b-2 border-primary/30" {...props} />,
                    h3: ({ ...props }: any) => <h3 className="text-xl font-semibold mt-6 mb-3" {...props} />,
                    h4: ({ ...props }: any) => <h4 className="text-lg font-medium mt-5 mb-2" {...props} />,
                    p: ({ ...props }: any) => <p className="text-[15px] leading-relaxed mb-4" {...props} />,
                    ul: ({ ...props }: any) => <ul className="space-y-2 mb-4 ml-6" {...props} />,
                    ol: ({ ...props }: any) => <ol className="space-y-2 mb-4 ml-6" {...props} />,
                    li: ({ ...props }: any) => <li className="text-sm leading-relaxed" {...props} />,
                    code: ({ inline, ...props }: any) =>
                      inline ? (
                        <code className="px-1.5 py-0.5 rounded bg-muted/80 text-xs font-mono" {...props} />
                      ) : (
                        <pre className="bg-[#0f1115] p-4 rounded-lg border border-border/50 my-4 overflow-x-auto">
                          <code className="text-sm font-mono text-[#e1e4e8]" {...props} />
                        </pre>
                      ),
                    hr: () => <hr className="border-t border-border/30 my-6" />,
                    strong: ({ ...props }: any) => <strong className="font-semibold" {...props} />,
                  }

                  return (
                    <div className="space-y-4">
                      {intro && intro.content && (
                        <div className="p-6 bg-gradient-to-br from-muted/30 to-muted/50 rounded-xl border border-border/50 shadow-lg mb-4">
                          <div className="prose prose-invert max-w-none prose-p:text-foreground/85 prose-headings:text-foreground prose-strong:text-foreground prose-code:text-primary">
                            <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                              {intro.content}
                            </ReactMarkdown>
                          </div>
                        </div>
                      )}
                      
                      <Accordion type="multiple" defaultValue={defaultExpanded} className="space-y-4">
                        {sectionsWithHeadings.map((section, idx) => (
                          <AccordionItem
                            key={`section-${idx}`}
                            value={`section-${idx}`}
                            className="glass rounded-xl border-border/50 shadow-sm overflow-hidden"
                          >
                            <AccordionTrigger className="px-6 py-4 hover:bg-muted/30 no-underline hover:no-underline transition-all">
                              <span className="text-lg font-bold text-foreground">{section.title}</span>
                            </AccordionTrigger>
                            <AccordionContent className="px-6 pb-6">
                              {section.hasSubsections ? (
                                <div className="space-y-3">
                                  {section.intro && section.intro.content && (
                                    <div className="prose prose-invert max-w-none prose-p:text-foreground/85 prose-headings:text-foreground prose-strong:text-foreground prose-code:text-primary mb-4">
                                      <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                                        {section.intro.content}
                                      </ReactMarkdown>
                                    </div>
                                  )}
                                  <Accordion type="multiple" defaultValue={[]} className="space-y-2">
                                    {section.subsections?.map((subsection, subIdx) => (
                                      <AccordionItem
                                        key={`subsection-${idx}-${subIdx}`}
                                        value={`subsection-${idx}-${subIdx}`}
                                        className="glass rounded-lg border-border/30 shadow-sm overflow-hidden"
                                      >
                                        <AccordionTrigger className="px-4 py-3 hover:bg-muted/20 no-underline hover:no-underline transition-all text-sm">
                                          <span className="font-semibold text-foreground">{subsection.title}</span>
                                        </AccordionTrigger>
                                        <AccordionContent className="px-4 pb-4">
                                          <div className="prose prose-invert max-w-none prose-p:text-foreground/85 prose-headings:text-foreground prose-strong:text-foreground prose-code:text-primary prose-ul:list-disc prose-ol:list-decimal">
                                            <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                                              {subsection.content}
                                            </ReactMarkdown>
                                          </div>
                                        </AccordionContent>
                                      </AccordionItem>
                                    ))}
                                  </Accordion>
                                </div>
                              ) : (
                                <div className="prose prose-invert max-w-none prose-p:text-foreground/85 prose-headings:text-foreground prose-strong:text-foreground prose-code:text-primary prose-ul:list-disc prose-ol:list-decimal">
                                  <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                                    {section.content || ''}
                                  </ReactMarkdown>
                                </div>
                              )}
                            </AccordionContent>
                          </AccordionItem>
                        ))}
                      </Accordion>
                    </div>
                  )
                })()}
              </div>
            ) : null}

            <h3 className="text-lg font-semibold text-foreground mb-4">Detailed Findings</h3>
            <div className="space-y-4">
              {issues.map((issue, index) => {
                const config = severityConfig[issue.severity]
                const Icon = config.icon
                const isExpanded = expandedIssue === issue.id

                return (
                  <motion.div
                    key={issue.id}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.3 + index * 0.05 }}
                    className={cn("glass rounded-xl overflow-hidden border", config.border)}
                  >
                    {/* Issue Header */}
                    <button
                      onClick={() => setExpandedIssue(isExpanded ? null : issue.id)}
                      className="w-full p-4 flex items-start gap-4 text-left hover:bg-orange-600/10 transition-colors"
                    >
                      <div className={cn("p-2 rounded-lg", config.bg)}>
                        <Icon className={cn("w-5 h-5", config.color)} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className={cn("text-xs font-medium px-2 py-0.5 rounded", config.bg, config.color)}>
                            {config.label}
                          </span>
                          <span className="text-xs text-muted-foreground">{issue.location}</span>
                        </div>
                        <h4 className="font-medium text-foreground">{issue.title}</h4>
                      </div>
                      <motion.div animate={{ rotate: isExpanded ? 180 : 0 }} className="text-muted-foreground">
                        <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                          <path
                            d="M5 7.5L10 12.5L15 7.5"
                            stroke="currentColor"
                            strokeWidth="1.5"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          />
                        </svg>
                      </motion.div>
                    </button>

                    {/* Expanded Content */}
                    <motion.div
                      initial={false}
                      animate={{
                        height: isExpanded ? "auto" : 0,
                        opacity: isExpanded ? 1 : 0,
                      }}
                      className="overflow-hidden"
                    >
                      <div className="px-4 pb-4 pt-0">
                        <div className="border-t border-border/50 pt-4">
                          <div className="text-muted-foreground text-sm mb-4 whitespace-pre-wrap leading-relaxed">
                            {issue.description}
                          </div>

                          {/* CSS Selector Highlight */}
                          {issue.selector && issue.selector !== "unknown" && (
                            <div className="mb-4 p-3 rounded-lg bg-muted/40 border border-border/50">
                              <div className="flex items-center gap-2 mb-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                                <Code className="w-3 h-3" />
                                CSS Selector Path
                              </div>
                              <code className="text-[12px] font-mono whitespace-pre-wrap break-all text-primary/90">
                                {issue.selector}
                              </code>
                            </div>
                          )}

                          {/* Before/After Screenshots for this issue */}
                          {(issue.before_screenshot || issue.after_screenshot) ? (
                            <div className="mt-4 space-y-4">
                              <p className="text-xs font-medium text-muted-foreground mb-3 uppercase tracking-wide flex items-center gap-2">
                                <Layout className="w-3 h-3" />
                                Before & After Screenshots
                              </p>
                              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                {issue.before_screenshot && (
                                  <div>
                                    <p className="text-xs text-muted-foreground mb-2 font-medium">Before</p>
                                    <div className="relative group rounded-lg overflow-hidden border border-border bg-black/20">
                                      <button
                                        type="button"
                                        onClick={() => setActiveScreenshotUrl(issue.before_screenshot || null)}
                                        className="w-full relative"
                                        title="Click to view full size"
                                      >
                                        <img
                                          src={issue.before_screenshot}
                                          alt={`Before screenshot for ${issue.title}`}
                                          className="w-full h-auto object-contain max-h-[300px]"
                                        />
                                        <div className="absolute inset-0 bg-background/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                                          <div className="inline-flex items-center gap-2 px-3 py-2 rounded-md bg-secondary text-secondary-foreground text-sm">
                                            <Maximize2 className="w-4 h-4" />
                                            View Full Size
                                          </div>
                                        </div>
                                      </button>
                                    </div>
                                  </div>
                                )}
                                {issue.after_screenshot && (
                                  <div>
                                    <p className="text-xs text-muted-foreground mb-2 font-medium">After</p>
                                    <div className="relative group rounded-lg overflow-hidden border border-border bg-black/20">
                                      <button
                                        type="button"
                                        onClick={() => setActiveScreenshotUrl(issue.after_screenshot || null)}
                                        className="w-full relative"
                                        title="Click to view full size"
                                      >
                                        <img
                                          src={issue.after_screenshot}
                                          alt={`After screenshot for ${issue.title}`}
                                          className="w-full h-auto object-contain max-h-[300px]"
                                        />
                                        <div className="absolute inset-0 bg-background/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                                          <div className="inline-flex items-center gap-2 px-3 py-2 rounded-md bg-secondary text-secondary-foreground text-sm">
                                            <Maximize2 className="w-4 h-4" />
                                            View Full Size
                                          </div>
                                        </div>
                                      </button>
                                    </div>
                                  </div>
                                )}
                              </div>
                            </div>
                          ) : issue.element_screenshot ? (
                            <div className="mt-4">
                              <p className="text-xs font-medium text-muted-foreground mb-3 uppercase tracking-wide flex items-center gap-2">
                                <Layout className="w-3 h-3" />
                                Annotated Screenshot (Element Highlight)
                              </p>
                              <div className="relative group rounded-lg overflow-hidden border border-border bg-black/20">
                                <button
                                  type="button"
                                  onClick={() => setActiveScreenshotUrl(issue.element_screenshot || null)}
                                  className="w-full relative"
                                  title="Click to view full size"
                                >
                                  <img
                                    src={issue.element_screenshot}
                                    alt={`Highlight for ${issue.title}`}
                                    className="w-full h-auto object-contain max-h-[400px]"
                                  />
                                  <div className="absolute inset-0 bg-background/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                                    <div className="inline-flex items-center gap-2 px-3 py-2 rounded-md bg-secondary text-secondary-foreground text-sm">
                                      <Maximize2 className="w-4 h-4" />
                                      View Full Size
                                    </div>
                                  </div>
                                </button>
                              </div>
                            </div>
                          ) : screenshots.length > 0 ? (
                            <div className="mt-4">
                              <p className="text-xs font-medium text-muted-foreground mb-3 uppercase tracking-wide">
                                Reference Screenshot
                              </p>
                              <div className="relative group rounded-lg overflow-hidden border border-border bg-secondary/20">
                                <button
                                  type="button"
                                  onClick={() => setActiveScreenshotUrl(screenshots[0])}
                                  className="w-full aspect-video relative"
                                  title="Click to view full size"
                                >
                                  <img
                                    src={screenshots[0]}
                                    alt={`Screenshot for ${issue.title}`}
                                    className="w-full h-full object-contain bg-secondary/50"
                                  />
                                  <div className="absolute inset-0 bg-background/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                                    <div className="inline-flex items-center gap-2 px-3 py-2 rounded-md bg-secondary text-secondary-foreground text-sm">
                                      <ZoomIn className="w-4 h-4" />
                                      View Full Size
                                    </div>
                                  </div>
                                </button>
                              </div>
                            </div>
                          ) : (
                            <p className="text-xs text-muted-foreground mt-4 italic">
                              No screenshots were captured for this test run.
                            </p>
                          )}
                        </div>
                      </div>
                    </motion.div>
                  </motion.div>
                )
              })}
            </div>
          </motion.div>
        ) : (
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            className="glass rounded-2xl p-6 mb-8"
          >
            <div className="flex items-center justify-between mb-6">
              <div>
                <h3 className="text-lg font-semibold text-foreground">Console History</h3>
                <p className="text-sm text-muted-foreground">Captured during test execution</p>
              </div>
              <div className="flex gap-4 text-xs font-mono">
                <div className="flex items-center gap-1.5 text-red-400">
                  <div className="w-2 h-2 rounded-full bg-red-500" />
                  <span>{report?.console_logs_json?.filter(l => l.type === 'error').length} Errors</span>
                </div>
                <div className="flex items-center gap-1.5 text-amber-400">
                  <div className="w-2 h-2 rounded-full bg-amber-500" />
                  <span>{report?.console_logs_json?.filter(l => l.type === 'warning').length} Warnings</span>
                </div>
              </div>
            </div>

            <div className="bg-[#0f1115] rounded-xl overflow-hidden border border-border/50">
              <div className="flex items-center gap-2 px-4 py-2 border-b border-border/50 bg-[#1a1d23]">
                <div className="flex gap-1.5">
                  <div className="w-3 h-3 rounded-full bg-red-500/80" />
                  <div className="w-3 h-3 rounded-full bg-amber-500/80" />
                  <div className="w-3 h-3 rounded-full bg-green-500/80" />
                </div>
                <span className="text-xs font-mono text-muted-foreground ml-2">terminal — {test.appName}</span>
              </div>
              <div className="p-4 font-mono text-xs overflow-y-auto max-h-[600px] space-y-2 custom-scrollbar">
                {report?.console_logs_json && report.console_logs_json.length > 0 ? (
                  report.console_logs_json.map((log, i) => (
                    <div key={i} className="flex gap-3 group">
                      <span className="text-muted-foreground/40 select-none min-w-[20px]">{i + 1}</span>
                      <div className="flex flex-col min-w-0">
                        <div className="flex items-center gap-2">
                          <span className={cn(
                            "px-1.5 rounded-[2px] text-[10px] font-bold uppercase",
                            log.type === 'error' ? "bg-red-500/20 text-red-400" :
                              log.type === 'warning' ? "bg-amber-500/20 text-amber-400" :
                                "bg-blue-500/20 text-blue-400"
                          )}>
                            {log.type}
                          </span>
                          <span className="text-[#e1e4e8] break-all leading-relaxed">{log.text}</span>
                        </div>
                        {log.location && (
                          <span className="text-[#6a737d] text-[10px] mt-0.5 group-hover:text-primary transition-colors cursor-pointer truncate">
                            at {log.location}
                          </span>
                        )}
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="flex flex-col items-center justify-center py-12 text-muted-foreground italic">
                    <Terminal className="w-8 h-8 mb-3 opacity-20" />
                    <p>No console messages captured.</p>
                  </div>
                )}
                <div className="pt-2 animate-pulse flex gap-2">
                  <span className="text-primary font-bold">❯</span>
                  <div className="w-2 h-4 bg-primary/40 rounded-sm" />
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </div>

      <AnimatePresence>
        {showFullReport && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-sm"
            onClick={() => setShowFullReport(false)}
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              onClick={(e) => e.stopPropagation()}
              className="w-full max-w-4xl max-h-[85vh] rounded-2xl bg-card border border-border shadow-2xl flex flex-col"
            >
              {/* Modal Header */}
              <div className="flex items-center justify-between p-6 border-b border-border">
                <div>
                  <h2 className="text-xl font-bold text-foreground">Full Test Report</h2>
                  <p className="text-sm text-muted-foreground mt-1">
                    {test.versionName} - {test.date}
                  </p>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setShowFullReport(false)}
                  className="text-muted-foreground hover:text-orange-600 hover:bg-orange-600/10"
                >
                  <X className="w-5 h-5" />
                </Button>
              </div>

              {/* Modal Content */}
              <div className="overflow-y-auto flex-1 p-6 space-y-6">
                {/* Executive Summary */}
                <div className="glass rounded-xl p-5">
                  <div className="flex items-center gap-2 mb-3">
                    <Lightbulb className="w-5 h-5 text-primary" />
                    <h3 className="font-semibold text-foreground">Executive Summary</h3>
                  </div>
                  <p className="text-muted-foreground text-sm leading-relaxed">
                    {summaryText} Our AI analysis has identified specific root causes and actionable remediation steps
                    for each issue. Implementing these fixes is estimated to reduce test failures by 85% and improve
                    overall application stability.
                  </p>
                </div>

                {/* Issues with Reviews and Suggestions */}
                <div className="space-y-4">
                  <h3 className="font-semibold text-foreground flex items-center gap-2">
                    <Wrench className="w-5 h-5 text-primary" />
                    Issues & Remediation
                  </h3>

                  {issues.map((issue) => {
                    const config = severityConfig[issue.severity]
                    const Icon = config.icon
                    const suggestion = fixSuggestions[issue.id]

                    return (
                      <div
                        key={issue.id}
                        className={cn("rounded-xl border overflow-hidden", config.border, "bg-card/50")}
                      >
                        {/* Issue Header */}
                        <div className="p-4 border-b border-border/50">
                          <div className="flex items-start gap-3">
                            <div className={cn("p-2 rounded-lg shrink-0", config.bg)}>
                              <Icon className={cn("w-4 h-4", config.color)} />
                            </div>
                            <div className="flex-1">
                              <div className="flex items-center gap-2 mb-1">
                                <span
                                  className={cn("text-xs font-medium px-2 py-0.5 rounded", config.bg, config.color)}
                                >
                                  {config.label}
                                </span>
                                <span className="text-xs text-muted-foreground">{issue.location}</span>
                              </div>
                              <h4 className="font-medium text-foreground">{issue.title}</h4>
                              <div className="text-sm text-muted-foreground mt-1 whitespace-pre-wrap leading-relaxed">
                                {issue.description}
                              </div>
                            </div>
                          </div>
                        </div>

                        {/* Screenshots note */}
                        <div className="p-4 border-b border-border/50 bg-secondary/20">
                          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                            Screenshots
                          </p>
                          <p className="mt-2 text-sm text-muted-foreground">
                            See the “Screenshots” section in the main report view.
                          </p>
                        </div>

                        {/* AI Review */}
                        {suggestion && (
                          <div className="p-4 space-y-4">
                            <div>
                              <p className="text-xs font-medium text-muted-foreground mb-2 uppercase tracking-wide">
                                AI Analysis
                              </p>
                              <p className="text-sm text-foreground/90 leading-relaxed">{suggestion.review}</p>
                            </div>

                            <div>
                              <p className="text-xs font-medium text-muted-foreground mb-2 uppercase tracking-wide">
                                Recommended Fixes
                              </p>
                              <ul className="space-y-2">
                                {suggestion.suggestions.map((fix, idx) => (
                                  <li key={idx} className="flex items-start gap-2 text-sm text-foreground/80">
                                    <CheckCircle2 className="w-4 h-4 text-primary shrink-0 mt-0.5" />
                                    <span>{fix}</span>
                                  </li>
                                ))}
                              </ul>
                            </div>
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
              </div>

              {/* Modal Footer */}
              <div className="flex items-center justify-end gap-3 p-4 border-t border-border bg-card shrink-0">
                <Button variant="outline" onClick={() => setShowFullReport(false)} className="rounded-xl hover:bg-orange-600/10 hover:text-orange-600 hover:border-orange-600">
                  Close
                </Button>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button className="rounded-xl bg-primary text-primary-foreground hover:bg-orange-600">
                      <Download className="w-4 h-4 mr-2" />
                      Export Report
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent className="bg-popover border-border" align="end">
                    <DropdownMenuItem onClick={() => handleExportPDF()} className="cursor-pointer">
                      <FileText className="mr-2 h-4 w-4 text-red-400" />
                      <span>Export as PDF</span>
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => handleExportExcel()} className="cursor-pointer">
                      <FileSpreadsheet className="mr-2 h-4 w-4 text-green-400" />
                      <span>Export as Excel</span>
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent className="bg-popover border-border">
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Test Run</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete this test run? This action cannot be undone and will permanently remove it from the database.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteConfirm}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Screenshot Modal */}
      <AnimatePresence>
        {activeScreenshotUrl && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-sm"
            onClick={() => setActiveScreenshotUrl(null)}
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              onClick={(e) => e.stopPropagation()}
              className="w-full max-w-5xl max-h-[85vh] rounded-2xl bg-card border border-border shadow-2xl flex flex-col overflow-hidden"
            >
              <div className="flex items-center justify-between p-4 border-b border-border">
                <div className="text-sm text-muted-foreground truncate">Screenshot</div>
                <div className="flex items-center gap-3">
                  <a
                    href={activeScreenshotUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="text-sm text-primary hover:underline"
                  >
                    Open in new tab
                  </a>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => setActiveScreenshotUrl(null)}
                    className="text-muted-foreground hover:text-orange-600 hover:bg-orange-600/10"
                  >
                    <X className="w-5 h-5" />
                  </Button>
                </div>
              </div>
              <div className="p-4 overflow-auto">
                <img
                  src={activeScreenshotUrl}
                  alt="Screenshot"
                  className="w-full h-auto rounded-lg border border-border"
                />
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  )
}
