"use client"

import { useState } from "react"
import { motion } from "framer-motion"
import { ChevronLeft, ChevronRight, History, Clock, Search, Filter, X, Trash2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
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

interface SidebarProps {
  collapsed: boolean
  onToggle: () => void
  history: TestHistory[]
  selectedId: string | null
  onSelectTest: (test: TestHistory) => void
  onDeleteTest?: (testId: string) => void
}

const statusOptions = [
  { value: "all", label: "All Status" },
  { value: "success", label: "Passed" },
  { value: "failed", label: "Failed" },
  { value: "running", label: "Running" },
]

const typeOptions = [
  { value: "all", label: "All Types" },
  { value: "functional", label: "Functional" },
  { value: "regression", label: "Regression" },
  { value: "performance", label: "Performance" },
  { value: "accessibility", label: "Accessibility" },
]

export default function Sidebar({ collapsed, onToggle, history, selectedId, onSelectTest, onDeleteTest }: SidebarProps) {
  const [searchQuery, setSearchQuery] = useState("")
  const [statusFilter, setStatusFilter] = useState("all")
  const [typeFilter, setTypeFilter] = useState("all")
  const [showFilters, setShowFilters] = useState(false)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [testToDelete, setTestToDelete] = useState<string | null>(null)

  const filteredHistory = history.filter((item) => {
    const matchesSearch = item.appName.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesStatus = statusFilter === "all" || item.status === statusFilter
    const matchesType = typeFilter === "all" || item.testType === typeFilter
    return matchesSearch && matchesStatus && matchesType
  })

  const hasActiveFilters = statusFilter !== "all" || typeFilter !== "all" || searchQuery !== ""

  const clearFilters = () => {
    setSearchQuery("")
    setStatusFilter("all")
    setTypeFilter("all")
  }

  const handleDeleteClick = (e: React.MouseEvent, testId: string) => {
    e.stopPropagation()
    setTestToDelete(testId)
    setDeleteDialogOpen(true)
  }

  const handleDeleteConfirm = () => {
    if (testToDelete && onDeleteTest) {
      onDeleteTest(testToDelete)
    }
    setDeleteDialogOpen(false)
    setTestToDelete(null)
  }

  return (
    <motion.aside
      initial={false}
      animate={{ width: collapsed ? 64 : 300 }}
      transition={{ duration: 0.3, ease: "easeInOut" }}
      className="h-[calc(100vh-64px)] bg-sidebar border-r border-sidebar-border flex flex-col"
    >
      {/* Toggle Button */}
      <div className="p-3 border-b border-sidebar-border">
        <Button
          variant="ghost"
          size="sm"
          onClick={onToggle}
          className="w-full justify-center hover:bg-orange-600/10 hover:text-orange-600 text-sidebar-foreground"
        >
          {collapsed ? <ChevronRight className="h-5 w-5" /> : <ChevronLeft className="h-5 w-5" />}
        </Button>
      </div>

      {/* History Header with Filter Toggle */}
      {!collapsed && (
        <div className="px-4 py-3 border-b border-sidebar-border">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-sidebar-foreground">
              <History className="h-4 w-4 text-muted-foreground" />
              <span className="font-medium text-sm">Test History</span>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowFilters(!showFilters)}
              className={cn("h-7 w-7 p-0 hover:bg-orange-600/10 hover:text-orange-600", showFilters && "bg-sidebar-accent")}
            >
              <Filter className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}

      {!collapsed && showFilters && (
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: "auto", opacity: 1 }}
          exit={{ height: 0, opacity: 0 }}
          className="px-3 py-3 border-b border-sidebar-border space-y-3"
        >
          {/* Search Input */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search tests..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9 h-9 bg-sidebar-accent border-sidebar-border text-sm"
            />
          </div>

          {/* Status Filter */}
          <div>
            <label className="text-xs text-muted-foreground mb-1.5 block">Status</label>
            <div className="flex flex-wrap gap-1.5">
              {statusOptions.map((option) => (
                <button
                  key={option.value}
                  onClick={() => setStatusFilter(option.value)}
                  className={cn(
                    "px-2.5 py-1 text-xs rounded-md transition-colors",
                    statusFilter === option.value
                      ? "bg-orange-600 text-white"
                      : "bg-sidebar-accent text-sidebar-foreground hover:bg-orange-600/10 hover:text-orange-600",
                  )}
                >
                  {option.label}
                </button>
              ))}
            </div>
          </div>

          {/* Type Filter */}
          <div>
            <label className="text-xs text-muted-foreground mb-1.5 block">Test Type</label>
            <div className="flex flex-wrap gap-1.5">
              {typeOptions.map((option) => (
                <button
                  key={option.value}
                  onClick={() => setTypeFilter(option.value)}
                  className={cn(
                    "px-2.5 py-1 text-xs rounded-md transition-colors",
                    typeFilter === option.value
                      ? "bg-orange-600 text-white"
                      : "bg-sidebar-accent text-sidebar-foreground hover:bg-orange-600/10 hover:text-orange-600",
                  )}
                >
                  {option.label}
                </button>
              ))}
            </div>
          </div>

          {/* Clear Filters */}
          {hasActiveFilters && (
            <Button
              variant="ghost"
              size="sm"
              onClick={clearFilters}
              className="w-full h-8 text-xs text-muted-foreground hover:text-orange-600 hover:bg-orange-600/10"
            >
              <X className="h-3 w-3 mr-1" />
              Clear filters
            </Button>
          )}
        </motion.div>
      )}

      {/* Results count */}
      {!collapsed && hasActiveFilters && (
        <div className="px-4 py-2 text-xs text-muted-foreground">
          {filteredHistory.length} result{filteredHistory.length !== 1 ? "s" : ""} found
        </div>
      )}

      {/* History List */}
      <div className="flex-1 overflow-y-auto py-2">
        {filteredHistory.length === 0
          ? !collapsed && (
              <div className="px-4 py-8 text-center text-muted-foreground text-sm">No tests match your filters</div>
            )
          : filteredHistory.map((item) => (
              <div
                key={item.id}
                className={cn(
                  "w-full px-3 py-2 mx-2 rounded-lg transition-colors group",
                  "hover:bg-orange-600/10",
                  selectedId === item.id && "bg-orange-600/20",
                )}
                style={{ width: "calc(100% - 16px)" }}
              >
                {collapsed ? (
                  <div className="flex justify-center">
                    <StatusBadge status={item.status} compact />
                  </div>
                ) : (
                  <div className="flex items-start gap-2">
                    <motion.button
                      onClick={() => onSelectTest(item)}
                      whileHover={{ scale: 1.01 }}
                      whileTap={{ scale: 0.99 }}
                      className="flex-1 text-left flex flex-col gap-1"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-medium text-sm text-sidebar-foreground truncate max-w-[140px]">
                          {item.appName}
                        </span>
                        <StatusBadge status={item.status} />
                      </div>
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-1 text-xs text-muted-foreground">
                          <Clock className="h-3 w-3" />
                          <span>{item.date}</span>
                        </div>
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-secondary text-muted-foreground capitalize">
                          {item.testType}
                        </span>
                      </div>
                    </motion.button>
                    {onDeleteTest && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={(e) => handleDeleteClick(e, item.id)}
                        className="opacity-0 group-hover:opacity-100 transition-opacity h-8 w-8 p-0 text-destructive hover:text-destructive hover:bg-destructive/10"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    )}
                  </div>
                )}
              </div>
            ))}
      </div>

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
    </motion.aside>
  )
}
