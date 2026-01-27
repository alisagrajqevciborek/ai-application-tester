"use client"

import { motion } from "framer-motion"
import { Progress } from "@/components/ui/progress"
import { AlertCircle, AlertTriangle, Clock, Terminal } from "lucide-react"
import { cn } from "@/lib/utils"

export interface TestProgressData {
    progress: number // 0-100
    currentStep: string
    warnings: number
    errors: number
    elapsedTime: number // in seconds
    estimatedTime?: number // in seconds
    status: "running" | "completed" | "failed"
}

interface TestProgressIndicatorProps {
    data: TestProgressData
    className?: string
}

export function TestProgressIndicator({ data, className }: TestProgressIndicatorProps) {
    const formatTime = (seconds: number): string => {
        const mins = Math.floor(seconds / 60)
        const secs = seconds % 60
        return `${mins}m ${secs}s`
    }

    const formatThinkingTime = (seconds: number): string => {
        const safeSeconds = Math.max(1, Math.floor(seconds))
        if (safeSeconds < 60) {
            return `${safeSeconds} seconds`
        }
        return formatTime(safeSeconds)
    }

    const getTextProgressBar = (progress: number) => {
        const segments = 10
        const filledSegments = Math.round((progress / 100) * segments)
        return `${"#".repeat(filledSegments)}${"-".repeat(segments - filledSegments)}`
    }

    const getProgressBarSegments = (progress: number) => {
        const segments = 10
        const filledSegments = Math.floor((progress / 100) * segments)
        return Array.from({ length: segments }, (_, i) => i < filledSegments)
    }

    const progressSegments = getProgressBarSegments(data.progress)
    const textProgressBar = getTextProgressBar(data.progress)
    const consoleSummary = `${data.warnings} ${
        data.warnings === 1 ? "warning" : "warnings"
    }, ${data.errors} ${data.errors === 1 ? "error" : "errors"}`

    if (data.status === "running") {
        return (
            <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className={cn(
                    "glass rounded-2xl p-6 space-y-4 border border-border/50",
                    className
                )}
            >
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="w-9 h-9 rounded-full bg-primary/10 flex items-center justify-center">
                            <div className="w-4 h-4 rounded-full border-2 border-primary/40 border-t-primary animate-spin" />
                        </div>
                        <div>
                            <p className="text-sm text-muted-foreground">Tap to view live details</p>
                            <p className="text-lg font-semibold text-foreground">
                                Thinking for {formatThinkingTime(data.elapsedTime)}
                            </p>
                        </div>
                    </div>
                </div>

                <motion.ul
                    key={data.currentStep}
                    initial="hidden"
                    animate="visible"
                    variants={{
                        hidden: {},
                        visible: {
                            transition: {
                                staggerChildren: 0.15,
                                delayChildren: 0.1,
                            },
                        },
                    }}
                    className="space-y-2 text-sm font-mono text-foreground/80"
                >
                    {[
                        `${Math.round(data.progress)}% Test Progress: ${textProgressBar}`,
                        `Current: ${data.currentStep}`,
                        `Console: ${consoleSummary}`,
                        `Time: ${formatTime(data.elapsedTime)}${
                            data.estimatedTime ? ` / ~${formatTime(data.estimatedTime)}` : ""
                        }`,
                    ].map((line) => (
                        <motion.li
                            key={line}
                            variants={{
                                hidden: { opacity: 0, y: 6 },
                                visible: { opacity: 1, y: 0 },
                            }}
                            className="truncate"
                        >
                            {line}
                        </motion.li>
                    ))}
                </motion.ul>
            </motion.div>
        )
    }

    return (
        <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className={cn(
                "glass rounded-2xl p-6 space-y-4 border border-border/50",
                className
            )}
        >
            {/* Header with Status */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <motion.div
                        className={cn(
                            "w-3 h-3 rounded-full",
                            data.status === "completed" && "bg-green-500",
                            data.status === "failed" && "bg-red-500"
                        )}
                    />
                    <h3 className="text-lg font-semibold text-foreground">
                        {data.status === "completed" && "Test Completed"}
                        {data.status === "failed" && "Test Failed"}
                    </h3>
                </div>

                {/* Time Display */}
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Clock className="w-4 h-4" />
                    <span className="font-mono">
                        {formatTime(data.elapsedTime)}
                        {data.estimatedTime && (
                            <span className="text-muted-foreground/60">
                                {" / ~"}
                                {formatTime(data.estimatedTime)}
                            </span>
                        )}
                    </span>
                </div>
            </div>

            {/* Progress Bar with Segments */}
            <div className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                    <span className="text-foreground/80">
                        Test Progress: {Math.round(data.progress)}%
                    </span>
                </div>

                {/* Custom Segmented Progress Bar */}
                <div className="flex gap-1">
                    {progressSegments.map((filled, index) => (
                        <motion.div
                            key={index}
                            initial={{ scaleX: 0 }}
                            animate={{ scaleX: filled ? 1 : 0 }}
                            transition={{ duration: 0.3, delay: index * 0.05 }}
                            className={cn(
                                "h-2 flex-1 rounded-full transition-colors duration-300",
                                filled ? "bg-primary" : "bg-primary/20"
                            )}
                        />
                    ))}
                </div>

                {/* Standard Progress Bar (Alternative) */}
                <Progress value={data.progress} className="h-2 bg-secondary" />
            </div>

            {/* Current Step */}
            <div className="flex items-start gap-3 p-3 bg-secondary/30 rounded-xl border border-border/30">
                <Terminal className="w-5 h-5 text-primary mt-0.5 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                    <p className="text-xs text-muted-foreground mb-1">Current:</p>
                    <p className="text-sm font-medium text-foreground truncate">
                        {data.currentStep}
                    </p>
                </div>
            </div>

            {/* Console Stats */}
            <div className="flex items-center gap-4 p-3 bg-secondary/20 rounded-xl border border-border/30">
                <div className="flex items-center gap-2 flex-1">
                    <Terminal className="w-4 h-4 text-muted-foreground" />
                    <span className="text-sm text-muted-foreground">Console:</span>
                </div>

                <div className="flex items-center gap-4">
                    {/* Warnings */}
                    <motion.div
                        animate={data.warnings > 0 ? { scale: [1, 1.1, 1] } : {}}
                        transition={{ duration: 0.5 }}
                        className="flex items-center gap-1.5"
                    >
                        <AlertTriangle className="w-4 h-4 text-yellow-500" />
                        <span className="text-sm font-medium text-yellow-500">
                            {data.warnings} {data.warnings === 1 ? "warning" : "warnings"}
                        </span>
                    </motion.div>

                    {/* Errors */}
                    <motion.div
                        animate={data.errors > 0 ? { scale: [1, 1.1, 1] } : {}}
                        transition={{ duration: 0.5 }}
                        className="flex items-center gap-1.5"
                    >
                        <AlertCircle className="w-4 h-4 text-red-500" />
                        <span className="text-sm font-medium text-red-500">
                            {data.errors} {data.errors === 1 ? "error" : "errors"}
                        </span>
                    </motion.div>
                </div>
            </div>
        </motion.div>
    )
}

export default TestProgressIndicator
