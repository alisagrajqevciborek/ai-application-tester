"use client"

import { ExternalLink, Video } from "lucide-react"
import { useMemo } from "react"
import { motion } from "framer-motion"
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion"
import type { Report } from "@/lib/api"

interface ReportVideoArtifactsProps {
  artifacts: Report["artifacts"]
}

export function ReportVideoArtifacts({ artifacts }: ReportVideoArtifactsProps) {
  const videoArtifacts = useMemo(() => {
    const list = artifacts ?? []
    const uniqueByUrl = new Map<string, NonNullable<Report["artifacts"]>[number]>()
    for (const artifact of list) {
      if (artifact.kind !== "playwright_video" || !artifact.url) continue
      if (!uniqueByUrl.has(artifact.url)) uniqueByUrl.set(artifact.url, artifact)
    }
    return Array.from(uniqueByUrl.values())
  }, [artifacts])

  if (videoArtifacts.length === 0) return null

  const [primary, ...extras] = videoArtifacts

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.18 }}
      className="glass rounded-2xl p-6 mb-8"
    >
      <h3 className="text-lg font-semibold text-foreground mb-4 flex items-center gap-2">
        <Video className="w-5 h-5 text-primary" />
        Test Recording
      </h3>
      <p className="text-sm text-muted-foreground mb-4">
        Screen recording captured during test execution. The main video below shows the full run; additional recordings
        are available when needed.
      </p>

      <div className="space-y-4">
        {/* Primary video */}
        <div className="rounded-xl overflow-hidden border border-border bg-black/20">
          <video
            src={primary.url}
            controls
            className="w-full aspect-video object-contain"
            preload="metadata"
            playsInline
          >
            Your browser does not support the video tag.
          </video>
          <div className="flex items-center justify-between gap-2 px-4 py-2 border-t border-border">
            <span className="text-xs font-medium text-foreground">
              Main recording{primary.step_name ? ` – ${primary.step_name}` : ""}
            </span>
            <a
              href={primary.url}
              target="_blank"
              rel="noreferrer"
              className="text-xs text-primary hover:underline flex items-center gap-1"
            >
              <ExternalLink className="w-3 h-3" />
              Open in new tab
            </a>
          </div>
        </div>

        {/* Extra recordings, collapsed by default */}
        {extras.length > 0 && (
          <Accordion type="single" collapsible className="w-full">
            <AccordionItem value="extra-recordings" className="border border-border/60 rounded-xl px-3">
              <AccordionTrigger className="text-sm font-medium text-foreground py-2">
                More recordings ({extras.length})
              </AccordionTrigger>
              <AccordionContent className="space-y-3 pb-3">
                {extras.map((artifact) => (
                  <div
                    key={`${artifact.id}-${artifact.url}`}
                    className="rounded-lg overflow-hidden border border-border bg-black/20"
                  >
                    <video
                      src={artifact.url}
                      controls
                      className="w-full aspect-video object-contain"
                      preload="metadata"
                      playsInline
                    >
                      Your browser does not support the video tag.
                    </video>
                    <div className="flex items-center justify-between gap-2 px-4 py-2 border-t border-border">
                      <span className="text-xs text-muted-foreground truncate">
                        {artifact.step_name || "Additional recording"}
                      </span>
                      <a
                        href={artifact.url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-xs text-primary hover:underline flex items-center gap-1"
                      >
                        <ExternalLink className="w-3 h-3" />
                        Open in new tab
                      </a>
                    </div>
                  </div>
                ))}
              </AccordionContent>
            </AccordionItem>
          </Accordion>
        )}
      </div>
    </motion.div>
  )
}
