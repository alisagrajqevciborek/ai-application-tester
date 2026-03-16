"use client"

import { Terminal } from "lucide-react"
import { useMemo } from "react"
import { motion } from "framer-motion"
import { cn } from "@/lib/utils"
import { parseConsoleLogs } from "@/lib/report-utils"
import type { ConsoleLog } from "@/lib/report-utils"

interface ConsoleLogViewerProps {
  logs: ConsoleLog[]
  appName: string
}

export function ConsoleLogViewer({ logs, appName }: ConsoleLogViewerProps) {
  const consoleCounts = useMemo(() => parseConsoleLogs(logs), [logs])

  return (
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
          <span className="text-xs font-mono text-muted-foreground ml-2">terminal — {appName}</span>
        </div>

        <div className="p-4 font-mono text-xs overflow-y-auto max-h-[600px] space-y-2 custom-scrollbar">
          {logs.length > 0 ? (
            logs.map((log, i) => (
              <div key={i} className="flex gap-3 group">
                <span className="text-muted-foreground/40 select-none min-w-[20px]">{i + 1}</span>
                <div className="flex flex-col min-w-0">
                  <div className="flex items-center gap-2">
                    <span
                      className={cn(
                        "px-1.5 rounded-[2px] text-[10px] font-bold uppercase",
                        log.type === "error"
                          ? "bg-red-500/20 text-red-400"
                          : log.type === "warning"
                            ? "bg-amber-500/20 text-amber-400"
                            : "bg-blue-500/20 text-blue-400",
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
  )
}
