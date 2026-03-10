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
  Video,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import type { TestHistory, TestIssue } from "@/lib/types"
import { useMemo, useState } from "react"
import StatusBadge from "@/components/common/status-badge"
import DonutChart from "@/components/charts/donut-chart"
import { cn } from "@/lib/utils"
import type { Report } from "@/lib/api"
import { Loader2 } from "lucide-react"
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
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion"

type ActiveTab = "findings" | "logs"

interface ReportMainContentProps {
  test: TestHistory
  onBack: () => void
  onDelete?: (testId: string) => void
  summaryText: string
  criticalCount: number
  majorCount: number
  minorCount: number
  issues: TestIssue[]
  screenshots: string[]
  report: Report | null
  isGeneratingReport: boolean
  expandedIssue: string | null
  setExpandedIssue: (value: string | null) => void
  showFullReport: boolean
  setShowFullReport: (value: boolean) => void
  activeScreenshotUrl: string | null
  setActiveScreenshotUrl: (value: string | null) => void
  activeTab: ActiveTab
  setActiveTab: (value: ActiveTab) => void
  deleteDialogOpen: boolean
  setDeleteDialogOpen: (value: boolean) => void
  isExportingToJira: boolean
  onExportPDF: () => Promise<void>
  onExportExcel: () => Promise<void>
  onExportToJira: () => Promise<void>
  onConfirmDelete: () => void
}

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

type ParsedSubsection = { title: string; content: string; idx: number }
type ParsedSection = {
  title: string | null
  content?: string
  hasSubsections: boolean
  intro?: { title: string | null; content: string; idx: number } | null
  subsections?: ParsedSubsection[]
  idx: number
}

const markdownComponents = {
  h2: ({ ...props }: any) => <h2 className="text-base font-semibold mt-5 mb-3 text-foreground" {...props} />,
  h3: ({ ...props }: any) => <h3 className="text-sm font-semibold mt-4 mb-2 text-foreground" {...props} />,
  h4: ({ ...props }: any) => <h4 className="text-sm font-medium mt-3 mb-2 text-foreground" {...props} />,
  p: ({ ...props }: any) => <p className="text-sm text-muted-foreground leading-relaxed mb-3" {...props} />,
  ul: ({ ...props }: any) => <ul className="space-y-2 mb-3 ml-5 list-disc" {...props} />,
  ol: ({ ...props }: any) => <ol className="space-y-2 mb-3 ml-5 list-decimal" {...props} />,
  li: ({ ...props }: any) => <li className="text-sm text-muted-foreground leading-relaxed" {...props} />,
  code: ({ inline, ...props }: any) =>
    inline ? (
      <code className="text-sm font-medium text-foreground" {...props} />
    ) : (
      <pre className="my-2 p-0 bg-transparent border-0 overflow-x-auto whitespace-pre-wrap">
        <code className="text-sm font-normal text-muted-foreground" {...props} />
      </pre>
    ),
  hr: () => <hr className="border-t border-border/30 my-6" />,
  strong: ({ ...props }: any) => <strong className="font-semibold" {...props} />,
  table: ({ ...props }: any) => (
    <details open className="my-3 rounded-xl border border-border/50 bg-muted/10 overflow-hidden">
      <summary className="cursor-pointer px-4 py-2.5 text-xs font-semibold tracking-wide text-foreground/80 border-b border-border/40 hover:bg-orange-600/10 transition-colors">
        Table
      </summary>
      <div className="overflow-x-auto">
        <table className="w-full text-sm" {...props} />
      </div>
    </details>
  ),
  thead: ({ ...props }: any) => <thead className="bg-muted/30 border-b border-border/50" {...props} />,
  tr: ({ ...props }: any) => <tr className="border-b border-border/40 last:border-b-0 align-top" {...props} />,
  th: ({ ...props }: any) => <th className="text-left px-4 py-3 font-semibold text-foreground" {...props} />,
  td: ({ ...props }: any) => (
    <td
      className="px-4 py-3 text-sm text-muted-foreground leading-relaxed align-top whitespace-normal break-words [&_p]:mb-1 [&_p:last-child]:mb-0 [&_ul]:my-1 [&_ol]:my-1 [&_li]:my-0.5 [&_code]:whitespace-nowrap"
      {...props}
    />
  ),
}

const buildFallbackRows = (content: string) => {
  return content
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => Boolean(line) && !line.startsWith("### ") && !line.startsWith("## "))
    .map((line, index) => {
      const normalized = line.replace(/^[-*]\s+/, "").replace(/^\d+\.\s+/, "")
      const boldMatch = normalized.match(/^\*\*(.+?)\*\*\s*:\s*(.+)$/)
      if (boldMatch) {
        return { label: boldMatch[1].trim(), value: boldMatch[2].trim() }
      }

      const keyValueMatch = normalized.match(/^([^:]{2,80}):\s+(.+)$/)
      if (keyValueMatch) {
        return { label: keyValueMatch[1].trim(), value: keyValueMatch[2].trim() }
      }

      return { label: `Item ${index + 1}`, value: normalized }
    })
}

const NumberedSubsectionTable = ({ content }: { content: string }) => {
  const rows = buildFallbackRows(content)

  if (rows.length === 0) {
    return null
  }

  return (
    <details open className="rounded-xl border border-border/50 overflow-hidden bg-muted/10">
      <summary className="cursor-pointer px-4 py-2.5 text-xs font-semibold tracking-wide text-foreground/80 border-b border-border/40 hover:bg-orange-600/10 transition-colors">
        Table
      </summary>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-muted/30 border-b border-border/50">
            <tr>
              <th className="text-left px-4 py-3 font-semibold text-foreground w-[32%]">Category</th>
              <th className="text-left px-4 py-3 font-semibold text-foreground">Details</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, idx) => (
              <tr key={`${row.label}-${idx}`} className="border-b border-border/40 last:border-b-0 align-top">
                <td className="px-4 py-3 font-medium text-foreground">{row.label}</td>
                <td className="px-4 py-3 text-muted-foreground leading-relaxed">{row.value}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  )
}

const hasMarkdownTable = (content: string) => /\|.+\|/.test(content) && /\|\s*[-:]{3,}/.test(content)

const parseDetailedReport = (rawReport: string) => {
  const cleanReport = rawReport.split(/={10,}\s*AUTOMATED TEST FINDINGS \(REFERENCE\)/)[0].trim()
  const mainSections = cleanReport.split(/(?=^## )/m)

  const parseSubsections = (content: string) => {
    const subsections = content.split(/(?=^### )/m)
    if (subsections.length <= 1) {
      return { hasSubsections: false, content }
    }

    const parsed = subsections
      .map((sub, idx) => {
        const trimmed = sub.trim()
        if (!trimmed) return null

        if (trimmed.startsWith("### ")) {
          const firstLineEnd = trimmed.indexOf("\n")
          const title = firstLineEnd > 0 ? trimmed.substring(4, firstLineEnd).trim() : trimmed.substring(4).trim()
          const subContent = firstLineEnd > 0 ? trimmed.substring(firstLineEnd + 1).trim() : ""
          return { title, content: subContent, idx }
        }
        return { title: null, content: trimmed, idx }
      })
      .filter(Boolean) as Array<{ title: string | null; content: string; idx: number }>

    return {
      hasSubsections: true,
      intro: parsed[0]?.title ? null : parsed[0],
      subsections: parsed.filter((s) => Boolean(s.title)) as ParsedSubsection[],
    }
  }

  const parsedSections = mainSections
    .map((section, idx) => {
      const trimmed = section.trim()
      if (!trimmed) return null

      if (trimmed.startsWith("## ")) {
        const firstLineEnd = trimmed.indexOf("\n")
        const title = firstLineEnd > 0 ? trimmed.substring(3, firstLineEnd).trim() : trimmed.substring(3).trim()
        const content = firstLineEnd > 0 ? trimmed.substring(firstLineEnd + 1).trim() : ""

        const subsectionData = parseSubsections(content)
        return { title, ...subsectionData, idx } as ParsedSection
      }

      return { title: null, content: trimmed, hasSubsections: false, idx } as ParsedSection
    })
    .filter(Boolean) as ParsedSection[]

  const hasOnlyPlain = parsedSections.length > 0 && parsedSections.every((s) => !s.title)
  const intro = parsedSections[0]?.title ? null : parsedSections[0]

  // Filter out Screenshot Analysis and Conclusion sections from the accordion
  const excludedSections = ["screenshot analysis", "conclusion", "conclusions"]
  const sectionsWithHeadings = parsedSections.filter(
    (s) => s.title && !excludedSections.includes(s.title.toLowerCase().replace(/^\d+\.\s*/, "").trim())
  )
  const defaultExpanded = sectionsWithHeadings.length > 0 ? ["section-0"] : []

  return { cleanReport, parsedSections, hasOnlyPlain, intro, sectionsWithHeadings, defaultExpanded }
}

export default function ReportMainContent({
  test,
  onBack,
  onDelete,
  summaryText,
  criticalCount,
  majorCount,
  minorCount,
  issues,
  screenshots,
  report,
  isGeneratingReport,
  expandedIssue,
  setExpandedIssue,
  showFullReport,
  setShowFullReport,
  activeScreenshotUrl,
  setActiveScreenshotUrl,
  activeTab,
  setActiveTab,
  deleteDialogOpen,
  setDeleteDialogOpen,
  isExportingToJira,
  onExportPDF,
  onExportExcel,
  onExportToJira,
  onConfirmDelete,
}: ReportMainContentProps) {
  const [isDetailedReportExpanded, setIsDetailedReportExpanded] = useState(true)
  const [expandedReportSections, setExpandedReportSections] = useState<string[]>(["section-0"])
  const [expandedReportSubsections, setExpandedReportSubsections] = useState<string[]>([])

  const parsedDetailedReport = useMemo(() => {
    if (!report?.detailed_report || report.detailed_report.length <= 100) {
      return null
    }
    return parseDetailedReport(report.detailed_report)
  }, [report?.detailed_report])

  const consoleCounts = useMemo(() => {
    const logs = report?.console_logs_json ?? []
    return {
      errors: logs.filter((l) => l.type === "error").length,
      warnings: logs.filter((l) => l.type === "warning").length,
    }
  }, [report?.console_logs_json])

  const videoArtifacts = useMemo(() => {
    const artifacts = report?.artifacts ?? []
    const uniqueByUrl = new Map<string, (typeof artifacts)[number]>()
    for (const artifact of artifacts) {
      if (artifact.kind !== "playwright_video" || !artifact.url) {
        continue
      }
      if (!uniqueByUrl.has(artifact.url)) {
        uniqueByUrl.set(artifact.url, artifact)
      }
    }
    return Array.from(uniqueByUrl.values())
  }, [report?.artifacts])

  return (
    <>
      <div className="max-w-5xl mx-auto">
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
                onClick={() => setDeleteDialogOpen(true)}
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
                <DropdownMenuItem onClick={() => onExportPDF()} className="cursor-pointer">
                  <FileText className="mr-2 h-4 w-4 text-red-400" />
                  <span>Export as PDF</span>
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => onExportExcel()} className="cursor-pointer">
                  <FileSpreadsheet className="mr-2 h-4 w-4 text-green-400" />
                  <span>Export as Excel</span>
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={() => onExportToJira()}
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

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="glass rounded-2xl p-6 mb-8"
        >
          <h3 className="text-lg font-semibold text-foreground mb-4">Test Summary</h3>
          <p className="text-muted-foreground leading-relaxed mb-6">{summaryText}</p>

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
        </motion.div>

        {videoArtifacts.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.18 }}
            className="glass rounded-2xl p-6 mb-8"
          >
            <h3 className="text-lg font-semibold text-foreground mb-4 flex items-center gap-2">
              <Video className="w-5 h-5 text-primary" />
              Test Recording
            </h3>
            <p className="text-sm text-muted-foreground mb-4">
              Screen recording captured during test execution. The main video below shows the full run; additional
              recordings are available when needed.
            </p>
            {(() => {
              const [primary, ...extras] = videoArtifacts
              if (!primary) return null

              return (
                <div className="space-y-4">
                  {/* Primary video */}
                  <div className="rounded-xl overflow-hidden border border-border bg-black/20">
                    <video
                      src={primary.url}
                      controls
                      className="w-full aspect-video object-contain"
                      preload="metadata"
                      playsInline
                    >
                      Your browser does not support the video tag.
                    </video>
                    <div className="flex items-center justify-between gap-2 px-4 py-2 border-t border-border">
                      <div className="flex flex-col">
                        <span className="text-xs font-medium text-foreground">
                          Main recording
                          {primary.step_name ? ` – ${primary.step_name}` : ""}
                        </span>
                      </div>
                      <a
                        href={primary.url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-xs text-primary hover:underline flex items-center gap-1"
                      >
                        <ExternalLink className="w-3 h-3" />
                        Open in new tab
                      </a>
                    </div>
                  </div>

                  {/* Extra recordings, collapsed by default */}
                  {extras.length > 0 && (
                    <Accordion type="single" collapsible className="w-full">
                      <AccordionItem value="extra-recordings" className="border border-border/60 rounded-xl px-3">
                        <AccordionTrigger className="text-sm font-medium text-foreground py-2">
                          More recordings ({extras.length})
                        </AccordionTrigger>
                        <AccordionContent className="space-y-3 pb-3">
                          {extras.map((artifact) => (
                            <div
                              key={`${artifact.id}-${artifact.url}`}
                              className="rounded-lg overflow-hidden border border-border bg-black/20"
                            >
                              <video
                                src={artifact.url}
                                controls
                                className="w-full aspect-video object-contain"
                                preload="metadata"
                                playsInline
                              >
                                Your browser does not support the video tag.
                              </video>
                              <div className="flex items-center justify-between gap-2 px-4 py-2 border-t border-border">
                                <span className="text-xs text-muted-foreground truncate">
                                  {artifact.step_name || "Additional recording"}
                                </span>
                                <a
                                  href={artifact.url}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="text-xs text-primary hover:underline flex items-center gap-1"
                                >
                                  <ExternalLink className="w-3 h-3" />
                                  Open in new tab
                                </a>
                              </div>
                            </div>
                          ))}
                        </AccordionContent>
                      </AccordionItem>
                    </Accordion>
                  )}
                </div>
              )
            })()}
          </motion.div>
        )}

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
            <button
              onClick={() => setIsDetailedReportExpanded((prev) => !prev)}
              className="w-full mb-4 p-4 flex items-center justify-between text-left rounded-xl border border-border/50 glass hover:bg-orange-600/10 transition-colors"
            >
              <h3 className="text-lg font-semibold text-foreground">Detailed Report</h3>
              <motion.div animate={{ rotate: isDetailedReportExpanded ? 180 : 0 }} className="text-muted-foreground">
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

            <motion.div
              initial={false}
              animate={{
                height: isDetailedReportExpanded ? "auto" : 0,
                opacity: isDetailedReportExpanded ? 1 : 0,
              }}
              className="overflow-hidden"
            >
              {isGeneratingReport ? (
                <div className="rounded-xl border border-primary/30 bg-primary/10 p-4 flex items-center gap-4 mb-8">
                  <Loader2 className="h-6 w-6 shrink-0 animate-spin text-primary" />
                  <p className="font-medium text-foreground">Generating your report</p>
                </div>
              ) : parsedDetailedReport ? (
                <div className="mb-8">
                {parsedDetailedReport.hasOnlyPlain ? (
                  <div className="p-6 bg-gradient-to-br from-muted/30 to-muted/50 rounded-xl border border-border/50 shadow-lg">
                    <div className="max-w-none text-sm text-muted-foreground leading-relaxed">
                      <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                        {parsedDetailedReport.cleanReport}
                      </ReactMarkdown>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {parsedDetailedReport.intro?.content && (
                      <div className="p-6 bg-gradient-to-br from-muted/30 to-muted/50 rounded-xl border border-border/50 shadow-lg mb-4">
                        <div className="max-w-none text-sm text-muted-foreground leading-relaxed">
                          <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                            {parsedDetailedReport.intro.content}
                          </ReactMarkdown>
                        </div>
                      </div>
                    )}

                    <div className="space-y-4">
                      {parsedDetailedReport.sectionsWithHeadings.map((section, idx) => {
                        const sectionKey = `section-${idx}`
                        const isSectionExpanded = expandedReportSections.includes(sectionKey)

                        return (
                          <motion.div
                            key={sectionKey}
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: 0.2 + idx * 0.05 }}
                            className="glass rounded-xl overflow-hidden border border-border/50"
                          >
                            <button
                              onClick={() => {
                                setExpandedReportSections((prev) =>
                                  prev.includes(sectionKey)
                                    ? prev.filter((item) => item !== sectionKey)
                                    : [...prev, sectionKey]
                                )
                              }}
                              className="w-full p-4 flex items-start gap-4 text-left hover:bg-orange-600/10 transition-colors"
                            >
                              <div className="p-2 rounded-lg bg-primary/10">
                                <FileText className="w-5 h-5 text-primary" />
                              </div>
                              <div className="flex-1 min-w-0">
                                <h4 className="font-medium text-foreground">{section.title}</h4>
                              </div>
                              <motion.div animate={{ rotate: isSectionExpanded ? 180 : 0 }} className="text-muted-foreground">
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

                            <motion.div
                              initial={false}
                              animate={{
                                height: isSectionExpanded ? "auto" : 0,
                                opacity: isSectionExpanded ? 1 : 0,
                              }}
                              className="overflow-hidden"
                            >
                              <div className="px-4 pb-4 pt-0 border-t border-border/50">
                                {section.hasSubsections ? (
                                  <div className="space-y-3 pt-4">
                                    {section.intro?.content && (
                                      <div className="max-w-none text-sm text-muted-foreground leading-relaxed mb-2">
                                        <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                                          {section.intro.content}
                                        </ReactMarkdown>
                                      </div>
                                    )}

                                    {section.subsections?.map((subsection, subIdx) => {
                                      const subsectionKey = `subsection-${idx}-${subIdx}`
                                      const isSubsectionExpanded = expandedReportSubsections.includes(subsectionKey)
                                      const isNumberedSubsection = /^\d+\./.test(subsection.title)
                                      const shouldRenderAsTable = isNumberedSubsection && !hasMarkdownTable(subsection.content)

                                      return (
                                        <div key={subsectionKey} className="rounded-lg overflow-hidden border border-border/40 bg-muted/10">
                                          <button
                                            onClick={() => {
                                              setExpandedReportSubsections((prev) =>
                                                prev.includes(subsectionKey)
                                                  ? prev.filter((item) => item !== subsectionKey)
                                                  : [...prev, subsectionKey]
                                              )
                                            }}
                                            className="w-full px-4 py-3 flex items-start gap-3 text-left hover:bg-orange-600/10 transition-colors"
                                          >
                                            <div className="p-1.5 rounded-md bg-primary/10 mt-0.5">
                                              <Lightbulb className="w-3.5 h-3.5 text-primary" />
                                            </div>
                                            <div className="flex-1 min-w-0">
                                              <span className="font-semibold text-foreground">{subsection.title}</span>
                                            </div>
                                            <motion.div
                                              animate={{ rotate: isSubsectionExpanded ? 180 : 0 }}
                                              className="text-muted-foreground"
                                            >
                                              <svg width="18" height="18" viewBox="0 0 20 20" fill="none">
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

                                          <motion.div
                                            initial={false}
                                            animate={{
                                              height: isSubsectionExpanded ? "auto" : 0,
                                              opacity: isSubsectionExpanded ? 1 : 0,
                                            }}
                                            className="overflow-hidden"
                                          >
                                            <div className="px-4 pb-4 pt-0 border-t border-border/40">
                                              <div className="pt-4">
                                                {shouldRenderAsTable ? (
                                                  <NumberedSubsectionTable content={subsection.content} />
                                                ) : (
                                                  <div className="max-w-none text-sm text-muted-foreground leading-relaxed">
                                                    <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                                                      {subsection.content}
                                                    </ReactMarkdown>
                                                  </div>
                                                )}
                                              </div>
                                            </div>
                                          </motion.div>
                                        </div>
                                      )
                                    })}
                                  </div>
                                ) : (
                                  <div className="max-w-none text-sm text-muted-foreground leading-relaxed pt-4">
                                    <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                                      {section.content || ""}
                                    </ReactMarkdown>
                                  </div>
                                )}
                              </div>
                            </motion.div>
                          </motion.div>
                        )
                      })}
                    </div>
                  </div>
                )}
                </div>
              ) : null}
            </motion.div>

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
                  <span>{consoleCounts.errors} Errors</span>
                </div>
                <div className="flex items-center gap-1.5 text-amber-400">
                  <div className="w-2 h-2 rounded-full bg-amber-500" />
                  <span>{consoleCounts.warnings} Warnings</span>
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
                          <span
                            className={cn(
                              "px-1.5 rounded-[2px] text-[10px] font-bold uppercase",
                              log.type === "error" ? "bg-red-500/20 text-red-400" :
                                log.type === "warning" ? "bg-amber-500/20 text-amber-400" :
                                  "bg-blue-500/20 text-blue-400"
                            )}
                          >
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

              <div className="overflow-y-auto flex-1 p-6 space-y-6">
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

                        <div className="p-4 border-b border-border/50 bg-secondary/20">
                          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                            Screenshots
                          </p>
                          <p className="mt-2 text-sm text-muted-foreground">
                            See the “Screenshots” section in the main report view.
                          </p>
                        </div>

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
                    <DropdownMenuItem onClick={() => onExportPDF()} className="cursor-pointer">
                      <FileText className="mr-2 h-4 w-4 text-red-400" />
                      <span>Export as PDF</span>
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => onExportExcel()} className="cursor-pointer">
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
              onClick={onConfirmDelete}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

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
