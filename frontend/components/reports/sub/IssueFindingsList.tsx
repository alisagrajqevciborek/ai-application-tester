"use client"

import { Code, Layout, Maximize2, ZoomIn } from "lucide-react"
import { motion } from "framer-motion"
import { cn } from "@/lib/utils"
import { severityConfig } from "@/lib/report-utils"
import type { TestIssue } from "@/lib/types"

interface IssueFindingsListProps {
  issues: TestIssue[]
  screenshots: string[]
  expandedIssue: string | null
  setExpandedIssue: (id: string | null) => void
  setActiveScreenshotUrl: (url: string | null) => void
}

const ChevronIcon = () => (
  <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
    <path
      d="M5 7.5L10 12.5L15 7.5"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
)

interface ScreenshotButtonProps {
  src: string
  alt: string
  onClick: () => void
  maxHeight?: string
}

function ScreenshotButton({ src, alt, onClick, maxHeight = "300px" }: ScreenshotButtonProps) {
  return (
    <div className="relative group rounded-lg overflow-hidden border border-border bg-black/20">
      <button type="button" onClick={onClick} className="w-full relative" title="Click to view full size">
        <img src={src} alt={alt} className="w-full h-auto object-contain" style={{ maxHeight }} />
        <div className="absolute inset-0 bg-background/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
          <div className="inline-flex items-center gap-2 px-3 py-2 rounded-md bg-secondary text-secondary-foreground text-sm">
            <Maximize2 className="w-4 h-4" />
            View Full Size
          </div>
        </div>
      </button>
    </div>
  )
}

export function IssueFindingsList({
  issues,
  screenshots,
  expandedIssue,
  setExpandedIssue,
  setActiveScreenshotUrl,
}: IssueFindingsListProps) {
  return (
    <div className="space-y-4">
      {issues.map((issue, index) => {
        const config = severityConfig[issue.severity]
        const Icon = config.icon
        const isExpanded = expandedIssue === issue.id
        const fallbackScreenshot =
          screenshots.length > 0 ? screenshots[index % screenshots.length] : null

        return (
          <motion.div
            key={issue.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 + index * 0.05 }}
            className={cn("glass rounded-xl overflow-hidden border", config.border)}
          >
            <button
              onClick={() => setExpandedIssue(isExpanded ? null : issue.id)}
              className="w-full p-4 flex items-start gap-4 text-left hover:bg-orange-600/10 transition-colors"
            >
              <div className={cn("p-2 rounded-lg", config.bg)}>
                <Icon className={cn("w-5 h-5", config.color)} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className={cn("text-xs font-medium px-2 py-0.5 rounded", config.bg, config.color)}>
                    {config.label}
                  </span>
                  <span className="text-xs text-muted-foreground">{issue.location}</span>
                </div>
                <h4 className="font-medium text-foreground">{issue.title}</h4>
              </div>
              <motion.div animate={{ rotate: isExpanded ? 180 : 0 }} className="text-muted-foreground">
                <ChevronIcon />
              </motion.div>
            </button>

            <motion.div
              initial={false}
              animate={{ height: isExpanded ? "auto" : 0, opacity: isExpanded ? 1 : 0 }}
              className="overflow-hidden"
            >
              <div className="px-4 pb-4 pt-0">
                <div className="border-t border-border/50 pt-4">
                  <div className="text-muted-foreground text-sm mb-4 whitespace-pre-wrap leading-relaxed">
                    {issue.description}
                  </div>

                  {issue.selector && issue.selector !== "unknown" && (
                    <div className="mb-4 p-3 rounded-lg bg-muted/40 border border-border/50">
                      <div className="flex items-center gap-2 mb-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                        <Code className="w-3 h-3" />
                        CSS Selector Path
                      </div>
                      <code className="text-[12px] font-mono whitespace-pre-wrap break-all text-primary/90">
                        {issue.selector}
                      </code>
                    </div>
                  )}

                  {/* Before/After screenshots take priority */}
                  {issue.before_screenshot || issue.after_screenshot ? (
                    <div className="mt-4 space-y-4">
                      <p className="text-xs font-medium text-muted-foreground mb-3 uppercase tracking-wide flex items-center gap-2">
                        <Layout className="w-3 h-3" />
                        Before &amp; After Screenshots
                      </p>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {issue.before_screenshot && (
                          <div>
                            <p className="text-xs text-muted-foreground mb-2 font-medium">Before</p>
                            <ScreenshotButton
                              src={issue.before_screenshot}
                              alt={`Before screenshot for ${issue.title}`}
                              onClick={() => setActiveScreenshotUrl(issue.before_screenshot ?? null)}
                            />
                          </div>
                        )}
                        {issue.after_screenshot && (
                          <div>
                            <p className="text-xs text-muted-foreground mb-2 font-medium">After</p>
                            <ScreenshotButton
                              src={issue.after_screenshot}
                              alt={`After screenshot for ${issue.title}`}
                              onClick={() => setActiveScreenshotUrl(issue.after_screenshot ?? null)}
                            />
                          </div>
                        )}
                      </div>
                    </div>
                  ) : issue.element_screenshot ? (
                    <div className="mt-4">
                      <p className="text-xs font-medium text-muted-foreground mb-3 uppercase tracking-wide flex items-center gap-2">
                        <Layout className="w-3 h-3" />
                        Annotated Screenshot (Element Highlight)
                      </p>
                      <ScreenshotButton
                        src={issue.element_screenshot}
                        alt={`Highlight for ${issue.title}`}
                        onClick={() => setActiveScreenshotUrl(issue.element_screenshot ?? null)}
                        maxHeight="400px"
                      />
                    </div>
                  ) : issue.reference_screenshot ? (
                    <div className="mt-4">
                      <p className="text-xs font-medium text-muted-foreground mb-3 uppercase tracking-wide">
                        Reference Screenshot
                      </p>
                      <ScreenshotButton
                        src={issue.reference_screenshot}
                        alt={`Reference screenshot for ${issue.title}`}
                        onClick={() => setActiveScreenshotUrl(issue.reference_screenshot ?? null)}
                        maxHeight="400px"
                      />
                    </div>
                  ) : screenshots.length > 0 ? (
                    <div className="mt-4">
                      <p className="text-xs font-medium text-muted-foreground mb-3 uppercase tracking-wide">
                        Reference Screenshot
                      </p>
                      <div className="relative group rounded-lg overflow-hidden border border-border bg-secondary/20">
                        <button
                          type="button"
                          onClick={() => setActiveScreenshotUrl(fallbackScreenshot)}
                          className="w-full aspect-video relative"
                          title="Click to view full size"
                        >
                          <img
                            src={fallbackScreenshot ?? ""}
                            alt={`Screenshot for ${issue.title}`}
                            className="w-full h-full object-contain bg-secondary/50"
                          />
                          <div className="absolute inset-0 bg-background/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                            <div className="inline-flex items-center gap-2 px-3 py-2 rounded-md bg-secondary text-secondary-foreground text-sm">
                              <ZoomIn className="w-4 h-4" />
                              View Full Size
                            </div>
                          </div>
                        </button>
                      </div>
                    </div>
                  ) : (
                    <p className="text-xs text-muted-foreground mt-4 italic">
                      No screenshots were captured for this test run.
                    </p>
                  )}
                </div>
              </div>
            </motion.div>
          </motion.div>
        )
      })}
    </div>
  )
}
