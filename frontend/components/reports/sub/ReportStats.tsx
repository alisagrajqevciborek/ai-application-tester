"use client"

import { AlertCircle, AlertTriangle, Info } from "lucide-react"
import { motion } from "framer-motion"
import DonutChart from "@/components/charts/donut-chart"
import type { TestHistory } from "@/lib/types"

interface ReportStatsProps {
  test: TestHistory
  summaryText: string
  criticalCount: number
  majorCount: number
  minorCount: number
}

export function ReportStats({ test, summaryText, criticalCount, majorCount, minorCount }: ReportStatsProps) {
  return (
    <>
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
    </>
  )
}
