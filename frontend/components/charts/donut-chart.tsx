"use client"

import { motion } from "framer-motion"

interface DonutChartProps {
  percentage: number
  color: string
  label: string
}

export default function DonutChart({ percentage, color, label }: DonutChartProps) {
  const radius = 44
  const strokeWidth = 10
  const size = 112
  const center = size / 2
  const circumference = 2 * Math.PI * radius
  const strokeDashoffset = circumference - (percentage / 100) * circumference

  return (
    <div className="flex flex-col sm:flex-row items-center sm:items-center gap-4 sm:gap-6">
      <div className="relative" style={{ width: size, height: size }}>
        <svg
          className="-rotate-90"
          width={size}
          height={size}
          viewBox={`0 0 ${size} ${size}`}
        >
          {/* Background circle */}
          <circle
            cx={center}
            cy={center}
            r={radius}
            fill="none"
            stroke="currentColor"
            strokeWidth={strokeWidth}
            className="text-secondary/40"
          />
          {/* Progress circle */}
          <motion.circle
            cx={center}
            cy={center}
            r={radius}
            fill="none"
            stroke={color}
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeDasharray={circumference}
            initial={{ strokeDashoffset: circumference }}
            animate={{ strokeDashoffset }}
            transition={{ duration: 0.9, ease: "easeOut" }}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <motion.span
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.2 }}
            className="text-3xl font-semibold text-foreground"
          >
            {percentage}%
          </motion.span>
        </div>
      </div>
      <div className="text-center sm:text-left">
        <p className="text-base font-semibold text-foreground">{label}</p>
        <p className="text-sm text-muted-foreground">{percentage}% of all tests</p>
      </div>
    </div>
  )
}
