"use client"

import { motion } from "framer-motion"
import { Clock, Trash2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import type { TestHistory } from "@/lib/types"
import StatusBadge from "@/components/status-badge"
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
import { useState } from "react"

interface VersionCardProps {
  test: TestHistory
  onSelect: (test: TestHistory) => void
  onDelete?: (testId: string) => void
  isSelected?: boolean
}

export default function VersionCard({ test, onSelect, onDelete, isSelected }: VersionCardProps) {
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)

  const handleDeleteClick = (e: React.MouseEvent) => {
    e.stopPropagation()
    setDeleteDialogOpen(true)
  }

  const handleDeleteConfirm = () => {
    if (onDelete) {
      onDelete(test.id)
    }
    setDeleteDialogOpen(false)
  }

  const getTestTypeColor = (type: string) => {
    switch (type) {
      case "functional":
        return "bg-blue-500/10 text-blue-600 border-blue-500/20"
      case "regression":
        return "bg-purple-500/10 text-purple-600 border-purple-500/20"
      case "performance":
        return "bg-green-500/10 text-green-600 border-green-500/20"
      case "accessibility":
        return "bg-orange-500/10 text-orange-600 border-orange-500/20"
      default:
        return "bg-gray-500/10 text-gray-600 border-gray-500/20"
    }
  }

  return (
    <>
      <motion.div
        onClick={() => onSelect(test)}
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
        className={cn(
          "relative p-4 rounded-lg border-2 cursor-pointer transition-all group",
          "bg-card hover:bg-accent/50",
          isSelected ? "border-orange-600 shadow-lg shadow-orange-600/20" : "border-border hover:border-orange-600/50",
        )}
      >
        {/* Header with version name and status */}
        <div className="flex items-start justify-between mb-3">
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-base text-foreground truncate mb-1">
              {test.versionName}
            </h3>
            <div className="flex items-center gap-2">
              <StatusBadge status={test.status} />
            </div>
          </div>
          {onDelete && (
            <Button
              variant="ghost"
              size="sm"
              onClick={handleDeleteClick}
              className="opacity-0 group-hover:opacity-100 transition-opacity h-7 w-7 p-0 text-destructive hover:text-destructive hover:bg-destructive/10 flex-shrink-0"
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          )}
        </div>

        {/* Test type badge */}
        <div className="mb-3">
          <span
            className={cn(
              "inline-block px-2.5 py-1 text-xs font-medium rounded-md border capitalize",
              getTestTypeColor(test.testType),
            )}
          >
            {test.testType}
          </span>
        </div>

        {/* Date */}
        <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <Clock className="h-3.5 w-3.5" />
          <span>{test.date}</span>
        </div>

        {/* Pass/Fail rates */}
        <div className="mt-3 pt-3 border-t border-border">
          <div className="flex items-center justify-between text-xs">
            <span className="text-muted-foreground">Pass Rate</span>
            <span className="font-medium text-green-600">{test.passRate}%</span>
          </div>
          <div className="flex items-center justify-between text-xs mt-1">
            <span className="text-muted-foreground">Fail Rate</span>
            <span className="font-medium text-red-600">{test.failRate}%</span>
          </div>
        </div>
      </motion.div>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent className="bg-popover border-border">
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Test Version</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete {test.versionName}? This action cannot be undone and will permanently remove this test run and its reports.
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
