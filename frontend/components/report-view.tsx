"use client"

import { motion, AnimatePresence } from "framer-motion"
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
} from "lucide-react"
import { Button } from "@/components/ui/button"
import type { TestHistory, TestIssue } from "@/lib/types"
import StatusBadge from "@/components/status-badge"
import DonutChart from "@/components/donut-chart"
import { useState } from "react"
import { cn } from "@/lib/utils"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
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

  // Filter issues based on test status
  const issues = test.status === "success" ? mockIssues.filter((i) => i.severity === "minor").slice(0, 2) : mockIssues

  const criticalCount = issues.filter((i) => i.severity === "critical").length
  const majorCount = issues.filter((i) => i.severity === "major").length
  const minorCount = issues.filter((i) => i.severity === "minor").length

  const summaryText =
    test.status === "success"
      ? `The test suite completed successfully with a ${test.passRate}% pass rate. All critical user flows were validated, and no blocking issues were found. ${minorCount} minor improvements are suggested for accessibility compliance.`
      : `The test suite encountered ${test.failRate}% failures. ${criticalCount} critical and ${majorCount} major issues were found that require immediate attention. Review the detailed findings below.`

  const handleExportPDF = () => {
    alert("Exporting report as PDF...")
  }

  const handleExportExcel = () => {
    alert("Exporting report as Excel...")
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
          </div>
        </motion.div>

        {/* Title */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
          <h1 className="text-3xl font-bold text-foreground mb-2">{test.appName}</h1>
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
          <div className="flex flex-col sm:flex-row gap-3">
            <Button
              onClick={() => setShowFullReport(true)}
              className="flex-1 h-12 rounded-xl bg-primary text-primary-foreground hover:bg-orange-600"
            >
              <ExternalLink className="w-4 h-4 mr-2" />
              View Full Report
            </Button>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="outline"
                  className="flex-1 h-12 rounded-xl border-border hover:bg-orange-600/10 hover:text-orange-600 hover:border-orange-600 bg-transparent"
                >
                  <Download className="w-4 h-4 mr-2" />
                  Export Report
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent className="w-48 bg-popover border-border" align="end">
                <DropdownMenuItem onClick={handleExportPDF} className="cursor-pointer">
                  <FileText className="mr-2 h-4 w-4 text-red-400" />
                  <span>Export as PDF</span>
                </DropdownMenuItem>
                <DropdownMenuItem onClick={handleExportExcel} className="cursor-pointer">
                  <FileSpreadsheet className="mr-2 h-4 w-4 text-green-400" />
                  <span>Export as Excel</span>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.25 }}
          className="mb-8"
        >
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
                        <p className="text-muted-foreground text-sm mb-4">{issue.description}</p>

                        {/* Individual Screenshot */}
                        <div className="relative group rounded-xl overflow-hidden bg-secondary/50 aspect-video">
                          <img
                            src={`/.jpg?height=300&width=500&query=${issue.screenshot}`}
                            alt={`Screenshot: ${issue.title}`}
                            className="w-full h-full object-cover"
                          />
                          <div className="absolute inset-0 bg-background/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                            <Button size="sm" variant="secondary" className="gap-2 hover:bg-orange-600 hover:text-white">
                              <ZoomIn className="w-4 h-4" />
                              View Full Screenshot
                            </Button>
                          </div>
                          <div className="absolute bottom-0 left-0 right-0 p-3 bg-gradient-to-t from-background/90 to-transparent">
                            <p className="text-xs text-muted-foreground">Screenshot captured during test execution</p>
                          </div>
                        </div>
                      </div>
                    </div>
                  </motion.div>
                </motion.div>
              )
            })}
          </div>
        </motion.div>
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
                    {test.appName} - {test.date}
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
                              <p className="text-sm text-muted-foreground mt-1">{issue.description}</p>
                            </div>
                          </div>
                        </div>

                        {/* Screenshot */}
                        <div className="p-4 border-b border-border/50 bg-secondary/20">
                          <p className="text-xs font-medium text-muted-foreground mb-2 uppercase tracking-wide">
                            Screenshot Evidence
                          </p>
                          <div className="rounded-lg overflow-hidden bg-secondary/50 aspect-video max-w-md">
                            <img
                              src={`/.jpg?height=200&width=350&query=${issue.screenshot}`}
                              alt={`Screenshot: ${issue.title}`}
                              className="w-full h-full object-cover"
                            />
                          </div>
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
                    <DropdownMenuItem onClick={handleExportPDF} className="cursor-pointer">
                      <FileText className="mr-2 h-4 w-4 text-red-400" />
                      <span>Export as PDF</span>
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={handleExportExcel} className="cursor-pointer">
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
    </>
  )
}
