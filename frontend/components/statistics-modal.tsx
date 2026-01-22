"use client"

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import DonutChart from "@/components/donut-chart"
import type { TestRunStats } from "@/lib/api"

interface StatisticsModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  stats: TestRunStats | null
}

export default function StatisticsModal({ open, onOpenChange, stats }: StatisticsModalProps) {
  if (!stats || stats.total === 0) {
    return (
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="w-[95vw] sm:w-[92vw] sm:max-w-6xl max-h-[90vh] overflow-y-auto rounded-2xl bg-background/95 p-6 shadow-2xl backdrop-blur-xl sm:p-8">
          <div className="mx-auto w-full max-w-6xl">
            <DialogHeader className="pr-10">
              <DialogTitle className="text-xl font-semibold tracking-tight sm:text-2xl">Test Statistics</DialogTitle>
          </DialogHeader>
            <div className="rounded-2xl border border-border/60 bg-card/40 px-6 py-14 text-center text-muted-foreground backdrop-blur-sm">
              No test statistics available yet. Run some tests to see statistics here.
            </div>
          </div>
        </DialogContent>
      </Dialog>
    )
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="w-[95vw] sm:w-[92vw] sm:max-w-6xl max-h-[90vh] overflow-y-auto rounded-2xl bg-background/95 p-6 shadow-2xl backdrop-blur-xl sm:p-8">
        <div className="mx-auto w-full max-w-6xl">
          <DialogHeader className="pr-10">
            <DialogTitle className="text-xl font-semibold tracking-tight sm:text-2xl">Test Statistics</DialogTitle>
          </DialogHeader>

          <div className="space-y-6">
            <section className="space-y-4">
              <div className="flex items-center justify-between gap-4">
                <p className="text-xs font-medium tracking-widest text-muted-foreground uppercase">Overview</p>
                <p className="text-xs text-muted-foreground">Total runs: <span className="font-medium text-foreground">{stats.total}</span></p>
              </div>

              <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
                <div className="rounded-2xl border border-border/60 bg-card/40 p-5 backdrop-blur-sm">
                  <div className="flex h-full min-h-[92px] flex-col justify-between">
                    <p className="text-sm text-muted-foreground">Total</p>
                    <p className="text-3xl font-semibold leading-none text-foreground">{stats.total}</p>
                  </div>
                </div>

                <div className="rounded-2xl border border-border/60 bg-card/40 p-5 backdrop-blur-sm">
                  <div className="flex h-full min-h-[92px] flex-col justify-between">
                    <p className="text-sm text-muted-foreground">Successful</p>
                    <p className="text-3xl font-semibold leading-none text-green-500">{stats.success}</p>
                  </div>
                </div>

                <div className="rounded-2xl border border-border/60 bg-card/40 p-5 backdrop-blur-sm">
                  <div className="flex h-full min-h-[92px] flex-col justify-between">
                    <p className="text-sm text-muted-foreground">Failed</p>
                    <p className="text-3xl font-semibold leading-none text-red-500">{stats.failed}</p>
                  </div>
                </div>

                <div className="rounded-2xl border border-border/60 bg-card/40 p-5 backdrop-blur-sm">
                  <div className="flex h-full min-h-[92px] flex-col justify-between">
                    <p className="text-sm text-muted-foreground">Running</p>
                    <p className="text-3xl font-semibold leading-none text-orange-500">{stats.running + stats.pending}</p>
                  </div>
                </div>
              </div>
            </section>

            <div className="h-px bg-border/60" />

            <section className="space-y-4">
              <p className="text-xs font-medium tracking-widest text-muted-foreground uppercase">Rates</p>

              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                <div className="rounded-2xl border border-border/60 bg-card/40 p-6 backdrop-blur-sm">
                  <p className="mb-4 text-sm font-medium text-muted-foreground">Pass</p>
                  <DonutChart
                    percentage={stats.average_pass_rate}
                    color="oklch(0.65 0.18 145)"
                    label="Average pass rate"
                  />
                </div>

                <div className="rounded-2xl border border-border/60 bg-card/40 p-6 backdrop-blur-sm">
                  <p className="mb-4 text-sm font-medium text-muted-foreground">Fail</p>
                  <DonutChart
                    percentage={stats.average_fail_rate}
                    color="oklch(0.55 0.2 25)"
                    label="Average fail rate"
                  />
                </div>
              </div>
            </section>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
