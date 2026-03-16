"use client"

import { ArrowLeft, Download, ExternalLink, FileSpreadsheet, FileText, Loader2, Trash2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
import { motion } from "framer-motion"
import StatusBadge from "@/components/common/status-badge"
import type { TestHistory } from "@/lib/types"

interface ReportHeaderProps {
  test: TestHistory
  onBack: () => void
  onDelete?: (testId: string) => void
  setDeleteDialogOpen: (open: boolean) => void
  isExportingToJira: boolean
  onExportPDF: () => Promise<void>
  onExportExcel: () => Promise<void>
  onExportToJira: () => Promise<void>
}

export function ReportHeader({
  test,
  onBack,
  onDelete,
  setDeleteDialogOpen,
  isExportingToJira,
  onExportPDF,
  onExportExcel,
  onExportToJira,
}: ReportHeaderProps) {
  return (
    <>
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between mb-6"
      >
        <Button
          variant="ghost"
          onClick={onBack}
          className="text-muted-foreground hover:text-orange-600 hover:bg-orange-600/10"
        >
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
    </>
  )
}
