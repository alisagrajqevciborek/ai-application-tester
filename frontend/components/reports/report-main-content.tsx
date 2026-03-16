"use client"

import { AlertCircle, Terminal } from "lucide-react"
import { Button } from "@/components/ui/button"
import { motion } from "framer-motion"
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
import { cn } from "@/lib/utils"
import type { TestHistory, TestIssue } from "@/lib/types"
import type { Report } from "@/lib/api"

import { ReportHeader } from "./sub/ReportHeader"
import { ReportStats } from "./sub/ReportStats"
import { ReportVideoArtifacts } from "./sub/ReportVideoArtifacts"
import { DetailedReportSection } from "./sub/DetailedReportSection"
import { IssueFindingsList } from "./sub/IssueFindingsList"
import { ConsoleLogViewer } from "./sub/ConsoleLogViewer"
import { FullReportModal } from "./sub/FullReportModal"
import { ScreenshotLightbox } from "./sub/ScreenshotLightbox"

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
  const logCount = report?.console_logs_json?.length ?? 0

  return (
    <>
      <div className="max-w-5xl mx-auto">
        <ReportHeader
          test={test}
          onBack={onBack}
          onDelete={onDelete}
          setDeleteDialogOpen={setDeleteDialogOpen}
          isExportingToJira={isExportingToJira}
          onExportPDF={onExportPDF}
          onExportExcel={onExportExcel}
          onExportToJira={onExportToJira}
        />

        <ReportStats
          test={test}
          summaryText={summaryText}
          criticalCount={criticalCount}
          majorCount={majorCount}
          minorCount={minorCount}
        />

        <ReportVideoArtifacts artifacts={report?.artifacts} />

        {/* Tab bar */}
        <div className="flex border-b border-border/50 mb-6 px-1">
          <Button
            variant="ghost"
            onClick={() => setActiveTab("findings")}
            className={cn(
              "relative px-6 py-4 rounded-none h-auto transition-colors",
              activeTab === "findings" ? "text-primary border-b-2 border-primary" : "text-muted-foreground",
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
              activeTab === "logs" ? "text-primary border-b-2 border-primary" : "text-muted-foreground",
            )}
          >
            <div className="flex items-center gap-2">
              <Terminal className="w-4 h-4" />
              <span>Console Logs</span>
              {logCount > 0 && <span className="ml-1 text-xs opacity-60">({logCount})</span>}
            </div>
          </Button>
        </div>

        {/* Tab content */}
        {activeTab === "findings" ? (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.25 }}
            className="mb-8"
          >
            <DetailedReportSection report={report} isGeneratingReport={isGeneratingReport} />

            <h3 className="text-lg font-semibold text-foreground mb-4">Detailed Findings</h3>
            <IssueFindingsList
              issues={issues}
              screenshots={screenshots}
              expandedIssue={expandedIssue}
              setExpandedIssue={setExpandedIssue}
              setActiveScreenshotUrl={setActiveScreenshotUrl}
            />
          </motion.div>
        ) : (
          <ConsoleLogViewer
            logs={report?.console_logs_json ?? []}
            appName={test.appName}
          />
        )}
      </div>

      {/* Modals & overlays */}
      <FullReportModal
        show={showFullReport}
        onClose={() => setShowFullReport(false)}
        test={test}
        summaryText={summaryText}
        issues={issues}
        onExportPDF={onExportPDF}
        onExportExcel={onExportExcel}
      />

      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent className="bg-popover border-border">
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Test Run</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete this test run? This action cannot be undone and will permanently remove it
              from the database.
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

      <ScreenshotLightbox url={activeScreenshotUrl} onClose={() => setActiveScreenshotUrl(null)} />
    </>
  )
}
