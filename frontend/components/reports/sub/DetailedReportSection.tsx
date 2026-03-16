"use client"

import { useState, useMemo } from "react"
import { motion } from "framer-motion"
import { FileText, Lightbulb, Loader2 } from "lucide-react"
import { ReportMarkdown, NumberedSubsectionTable, hasMarkdownTable, parseDetailedReport } from "@/lib/report-utils"
import type { Report } from "@/lib/api"

interface DetailedReportSectionProps {
  report: Report | null
  isGeneratingReport: boolean
}

const ChevronIcon = ({ size = 20 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 20 20" fill="none">
    <path
      d="M5 7.5L10 12.5L15 7.5"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
)

export function DetailedReportSection({ report, isGeneratingReport }: DetailedReportSectionProps) {
  const [isExpanded, setIsExpanded] = useState(true)
  const [expandedSections, setExpandedSections] = useState<string[]>(["section-0"])
  const [expandedSubsections, setExpandedSubsections] = useState<string[]>([])

  const parsedReport = useMemo(() => {
    if (!report?.detailed_report || report.detailed_report.length <= 100) return null
    return parseDetailedReport(report.detailed_report)
  }, [report?.detailed_report])

  const toggleSection = (key: string) =>
    setExpandedSections((prev) =>
      prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key],
    )

  const toggleSubsection = (key: string) =>
    setExpandedSubsections((prev) =>
      prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key],
    )

  return (
    <div className="mb-8">
      <button
        onClick={() => setIsExpanded((prev) => !prev)}
        className="w-full mb-4 p-4 flex items-center justify-between text-left rounded-xl border border-border/50 glass hover:bg-orange-600/10 transition-colors"
      >
        <h3 className="text-lg font-semibold text-foreground">Detailed Report</h3>
        <motion.div animate={{ rotate: isExpanded ? 180 : 0 }} className="text-muted-foreground">
          <ChevronIcon />
        </motion.div>
      </button>

      <motion.div
        initial={false}
        animate={{ height: isExpanded ? "auto" : 0, opacity: isExpanded ? 1 : 0 }}
        className="overflow-hidden"
      >
        {isGeneratingReport ? (
          <div className="rounded-xl border border-primary/30 bg-primary/10 p-4 flex items-center gap-4 mb-8">
            <Loader2 className="h-6 w-6 shrink-0 animate-spin text-primary" />
            <p className="font-medium text-foreground">Generating your report</p>
          </div>
        ) : parsedReport ? (
          <div className="mb-8">
            {parsedReport.hasOnlyPlain ? (
              <div className="p-6 bg-gradient-to-br from-muted/30 to-muted/50 rounded-xl border border-border/50 shadow-lg">
                <div className="max-w-none text-sm text-muted-foreground leading-relaxed">
                  <ReportMarkdown>{parsedReport.cleanReport}</ReportMarkdown>
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                {parsedReport.intro?.content && (
                  <div className="p-6 bg-gradient-to-br from-muted/30 to-muted/50 rounded-xl border border-border/50 shadow-lg mb-4">
                    <div className="max-w-none text-sm text-muted-foreground leading-relaxed">
                      <ReportMarkdown>{parsedReport.intro.content}</ReportMarkdown>
                    </div>
                  </div>
                )}

                <div className="space-y-4">
                  {parsedReport.sectionsWithHeadings.map((section, idx) => {
                    const sectionKey = `section-${idx}`
                    const isSectionExpanded = expandedSections.includes(sectionKey)

                    return (
                      <motion.div
                        key={sectionKey}
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.2 + idx * 0.05 }}
                        className="glass rounded-xl overflow-hidden border border-border/50"
                      >
                        <button
                          onClick={() => toggleSection(sectionKey)}
                          className="w-full p-4 flex items-start gap-4 text-left hover:bg-orange-600/10 transition-colors"
                        >
                          <div className="p-2 rounded-lg bg-primary/10">
                            <FileText className="w-5 h-5 text-primary" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <h4 className="font-medium text-foreground">{section.title}</h4>
                          </div>
                          <motion.div
                            animate={{ rotate: isSectionExpanded ? 180 : 0 }}
                            className="text-muted-foreground"
                          >
                            <ChevronIcon />
                          </motion.div>
                        </button>

                        <motion.div
                          initial={false}
                          animate={{ height: isSectionExpanded ? "auto" : 0, opacity: isSectionExpanded ? 1 : 0 }}
                          className="overflow-hidden"
                        >
                          <div className="px-4 pb-4 pt-0 border-t border-border/50">
                            {section.hasSubsections ? (
                              <div className="space-y-3 pt-4">
                                {section.intro?.content && (
                                  <div className="max-w-none text-sm text-muted-foreground leading-relaxed mb-2">
                                    <ReportMarkdown>{section.intro.content}</ReportMarkdown>
                                  </div>
                                )}

                                {section.subsections?.map((subsection, subIdx) => {
                                  const subsectionKey = `subsection-${idx}-${subIdx}`
                                  const isSubExpanded = expandedSubsections.includes(subsectionKey)
                                  const isNumbered = /^\d+\./.test(subsection.title)
                                  const renderAsTable = isNumbered && !hasMarkdownTable(subsection.content)

                                  return (
                                    <div
                                      key={subsectionKey}
                                      className="rounded-lg overflow-hidden border border-border/40 bg-muted/10"
                                    >
                                      <button
                                        onClick={() => toggleSubsection(subsectionKey)}
                                        className="w-full px-4 py-3 flex items-start gap-3 text-left hover:bg-orange-600/10 transition-colors"
                                      >
                                        <div className="p-1.5 rounded-md bg-primary/10 mt-0.5">
                                          <Lightbulb className="w-3.5 h-3.5 text-primary" />
                                        </div>
                                        <div className="flex-1 min-w-0">
                                          <span className="font-semibold text-foreground">{subsection.title}</span>
                                        </div>
                                        <motion.div
                                          animate={{ rotate: isSubExpanded ? 180 : 0 }}
                                          className="text-muted-foreground"
                                        >
                                          <ChevronIcon size={18} />
                                        </motion.div>
                                      </button>

                                      <motion.div
                                        initial={false}
                                        animate={{
                                          height: isSubExpanded ? "auto" : 0,
                                          opacity: isSubExpanded ? 1 : 0,
                                        }}
                                        className="overflow-hidden"
                                      >
                                        <div className="px-4 pb-4 pt-0 border-t border-border/40">
                                          <div className="pt-4">
                                            {renderAsTable ? (
                                              <NumberedSubsectionTable content={subsection.content} />
                                            ) : (
                                              <div className="max-w-none text-sm text-muted-foreground leading-relaxed">
                                                <ReportMarkdown>{subsection.content}</ReportMarkdown>
                                              </div>
                                            )}
                                          </div>
                                        </div>
                                      </motion.div>
                                    </div>
                                  )
                                })}
                              </div>
                            ) : (
                              <div className="max-w-none text-sm text-muted-foreground leading-relaxed pt-4">
                                <ReportMarkdown>{section.content ?? ""}</ReportMarkdown>
                              </div>
                            )}
                          </div>
                        </motion.div>
                      </motion.div>
                    )
                  })}
                </div>
              </div>
            )}
          </div>
        ) : null}
      </motion.div>
    </div>
  )
}
