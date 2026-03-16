"use client"

import { Download, FileSpreadsheet, FileText, Lightbulb, Wrench, X } from "lucide-react"
import { AnimatePresence, motion } from "framer-motion"
import { Button } from "@/components/ui/button"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
import { cn } from "@/lib/utils"
import { severityConfig } from "@/lib/report-utils"
import type { TestHistory, TestIssue } from "@/lib/types"

interface FullReportModalProps {
  show: boolean
  onClose: () => void
  test: TestHistory
  summaryText: string
  issues: TestIssue[]
  onExportPDF: () => Promise<void>
  onExportExcel: () => Promise<void>
}

export function FullReportModal({
  show,
  onClose,
  test,
  summaryText,
  issues,
  onExportPDF,
  onExportExcel,
}: FullReportModalProps) {
  return (
    <AnimatePresence>
      {show && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-sm"
          onClick={onClose}
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            onClick={(e) => e.stopPropagation()}
            className="w-full max-w-4xl max-h-[85vh] rounded-2xl bg-card border border-border shadow-2xl flex flex-col"
          >
            {/* Header */}
            <div className="flex items-center justify-between p-6 border-b border-border">
              <div>
                <h2 className="text-xl font-bold text-foreground">Full Test Report</h2>
                <p className="text-sm text-muted-foreground mt-1">
                  {test.versionName} — {test.date}
                </p>
              </div>
              <Button
                variant="ghost"
                size="icon"
                onClick={onClose}
                className="text-muted-foreground hover:text-orange-600 hover:bg-orange-600/10"
              >
                <X className="w-5 h-5" />
              </Button>
            </div>

            {/* Body */}
            <div className="overflow-y-auto flex-1 p-6 space-y-6">
              {/* Executive summary */}
              <div className="glass rounded-xl p-5">
                <div className="flex items-center gap-2 mb-3">
                  <Lightbulb className="w-5 h-5 text-primary" />
                  <h3 className="font-semibold text-foreground">Executive Summary</h3>
                </div>
                <p className="text-muted-foreground text-sm leading-relaxed">{summaryText}</p>
              </div>

              {/* Issues list */}
              {issues.length > 0 && (
                <div className="space-y-4">
                  <h3 className="font-semibold text-foreground flex items-center gap-2">
                    <Wrench className="w-5 h-5 text-primary" />
                    Issues &amp; Findings
                  </h3>

                  {issues.map((issue) => {
                    const config = severityConfig[issue.severity]
                    const Icon = config.icon

                    return (
                      <div
                        key={issue.id}
                        className={cn("rounded-xl border overflow-hidden", config.border, "bg-card/50")}
                      >
                        <div className="p-4">
                          <div className="flex items-start gap-3">
                            <div className={cn("p-2 rounded-lg shrink-0", config.bg)}>
                              <Icon className={cn("w-4 h-4", config.color)} />
                            </div>
                            <div className="flex-1">
                              <div className="flex items-center gap-2 mb-1">
                                <span
                                  className={cn(
                                    "text-xs font-medium px-2 py-0.5 rounded",
                                    config.bg,
                                    config.color,
                                  )}
                                >
                                  {config.label}
                                </span>
                                {issue.location && (
                                  <span className="text-xs text-muted-foreground">{issue.location}</span>
                                )}
                              </div>
                              <h4 className="font-medium text-foreground mb-1">{issue.title}</h4>
                              <p className="text-sm text-muted-foreground whitespace-pre-wrap leading-relaxed">
                                {issue.description}
                              </p>
                            </div>
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}

              {issues.length === 0 && (
                <p className="text-sm text-muted-foreground text-center py-4">
                  No issues were found in this test run.
                </p>
              )}
            </div>

            {/* Footer */}
            <div className="flex items-center justify-end gap-3 p-4 border-t border-border bg-card shrink-0">
              <Button
                variant="outline"
                onClick={onClose}
                className="rounded-xl hover:bg-orange-600/10 hover:text-orange-600 hover:border-orange-600"
              >
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
  )
}
