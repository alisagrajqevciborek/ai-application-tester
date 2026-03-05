"use client"

import { useState } from "react"
import { useRouter, usePathname } from "next/navigation"
import { motion, AnimatePresence } from "framer-motion"
import { Activity, ChevronDown, ChevronUp, ExternalLink, Loader2 } from "lucide-react"
import { useActiveTests } from "@/contexts/ActiveTestsContext"
import type { TestRun } from "@/lib/api"
import { calculateTestProgress, getTestTypeLabel } from "@/lib/test-progress-utils"

export default function ActiveTestsWidget() {
  const { activeTests, isLoading } = useActiveTests()
  const [expanded, setExpanded] = useState(false)
  const router = useRouter()
  const pathname = usePathname()

  // Don't render anything while loading or when there are no active tests
  if (isLoading || activeTests.length === 0) return null

  // Don't show the widget on pages that already show test progress
  if (
    pathname === "/dashboard/new-test" ||
    pathname.startsWith("/dashboard/test-progress/")
  ) return null

  const handleNavigate = (testId: number) => {
    router.push(`/dashboard/test-progress/${testId}`)
  }

  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col items-end gap-2">
      <AnimatePresence>
        {expanded && (
          <motion.div
            key="panel"
            initial={{ opacity: 0, y: 12, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 12, scale: 0.95 }}
            transition={{ duration: 0.2 }}
            className="w-80 rounded-xl border border-border bg-popover/95 backdrop-blur-lg shadow-2xl overflow-hidden"
          >
            {/* Header */}
            <div className="px-4 py-3 border-b border-border flex items-center justify-between">
              <span className="text-sm font-semibold text-foreground">
                Active Tests ({activeTests.length})
              </span>
              <button
                onClick={() => setExpanded(false)}
                className="text-muted-foreground hover:text-foreground transition-colors"
              >
                <ChevronDown className="w-4 h-4" />
              </button>
            </div>

            {/* Test list */}
            <div className="max-h-72 overflow-y-auto divide-y divide-border">
              {activeTests.map((tr) => {
                const progress = calculateTestProgress(tr)
                return (
                  <div
                    key={tr.id}
                    onClick={() => handleNavigate(tr.id)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault()
                        handleNavigate(tr.id)
                      }
                    }}
                    role="button"
                    tabIndex={0}
                    className="w-full text-left px-4 py-3 hover:bg-accent/50 transition-colors group cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/60"
                  >
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-sm font-medium text-foreground truncate max-w-[180px]">
                        {tr.application_name}
                      </span>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation()
                          handleNavigate(tr.id)
                        }}
                        className="inline-flex items-center gap-1.5 rounded-md border border-primary/30 px-2.5 py-1 text-xs font-medium text-primary hover:bg-primary/10 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/60"
                        aria-label={`View progress for ${tr.application_name}`}
                      >
                        <ExternalLink className="w-3 h-3" />
                        View
                      </button>
                    </div>

                    <div className="flex items-center gap-2 mb-1.5">
                      <span className="text-xs text-muted-foreground">
                        {getTestTypeLabel(tr.test_type)}
                      </span>
                      <span className="text-xs px-1.5 py-0.5 rounded-full bg-primary/10 text-primary font-medium">
                        {tr.status === "pending" ? "Queued" : "Running"}
                      </span>
                    </div>

                    {/* Progress bar */}
                    <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
                      <motion.div
                        className="h-full rounded-full bg-primary"
                        initial={{ width: 0 }}
                        animate={{ width: `${progress}%` }}
                        transition={{ duration: 0.5, ease: "easeOut" }}
                      />
                    </div>
                    <div className="flex items-center justify-between mt-1">
                      <span className="text-[10px] text-muted-foreground">
                        {progress}% complete
                      </span>
                      {tr.step_results && tr.step_results.length > 0 && (
                        <span className="text-[10px] text-muted-foreground">
                          {tr.step_results.filter(
                            (s) => s.status === "success" || s.status === "failed"
                          ).length}
                          /{tr.step_results.length} steps
                        </span>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Floating pill button */}
      <motion.button
        layout
        onClick={() => setExpanded((prev) => !prev)}
        className="flex items-center gap-2.5 px-4 py-2.5 rounded-full bg-primary text-primary-foreground shadow-lg hover:shadow-xl hover:scale-105 transition-all"
        whileTap={{ scale: 0.95 }}
      >
        {/* Animated spinner */}
        <span className="relative flex h-5 w-5 items-center justify-center">
          <Loader2 className="h-5 w-5 animate-spin" />
          <span className="absolute inset-0 flex items-center justify-center text-[9px] font-bold">
            {activeTests.length}
          </span>
        </span>

        <span className="text-sm font-medium whitespace-nowrap">
          {activeTests.length === 1 ? "1 test running" : `${activeTests.length} tests running`}
        </span>

        {expanded ? (
          <ChevronDown className="w-4 h-4" />
        ) : (
          <ChevronUp className="w-4 h-4" />
        )}
      </motion.button>
    </div>
  )
}

