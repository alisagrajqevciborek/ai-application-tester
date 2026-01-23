"use client"

import { cn } from "@/lib/utils"
import { motion } from "framer-motion"

interface StatusBadgeProps {
  status: "success" | "failed" | "running"
  compact?: boolean
  large?: boolean
}

export default function StatusBadge({ status, compact, large }: StatusBadgeProps) {
  const config = {
    success: {
      label: "Passed",
      bg: "bg-[oklch(0.65_0.18_145)]/20",
      text: "text-[oklch(0.65_0.18_145)]",
      dot: "bg-[oklch(0.65_0.18_145)]",
    },
    failed: {
      label: "Failed",
      bg: "bg-[oklch(0.55_0.2_25)]/20",
      text: "text-[oklch(0.55_0.2_25)]",
      dot: "bg-[oklch(0.55_0.2_25)]",
    },
    running: {
      label: "Running",
      bg: "bg-[oklch(0.6_0.15_250)]/20",
      text: "text-[oklch(0.6_0.15_250)]",
      dot: "bg-[oklch(0.6_0.15_250)]",
    },
  }

  const { label, bg, text, dot } = config[status]

  if (compact) {
    return (
      <div className="relative w-3 h-3">
        <div className={cn("absolute inset-0 w-3 h-3 rounded-full", dot)} />
        {status === "running" && (
          <motion.div
            className={cn("absolute inset-0 w-3 h-3 rounded-full", dot)}
            animate={{ scale: [1, 1.5, 1], opacity: [1, 0.5, 1] }}
            transition={{ repeat: Number.POSITIVE_INFINITY, duration: 1.5 }}
          />
        )}
      </div>
    )
  }

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full font-medium",
        bg,
        text,
        large ? "text-sm px-4 py-1.5" : "text-xs",
      )}
    >
      <span className="relative inline-block w-2 h-2">
        <span className={cn("absolute inset-0 w-2 h-2 rounded-full", dot)} />
        {status === "running" && (
          <motion.span
            className={cn("absolute inset-0 block w-2 h-2 rounded-full", dot)}
            animate={{ scale: [1, 1.5, 1], opacity: [1, 0.5, 1] }}
            transition={{ repeat: Number.POSITIVE_INFINITY, duration: 1.5 }}
          />
        )}
      </span>
      {label}
    </span>
  )
}
