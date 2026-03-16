"use client"

import { X } from "lucide-react"
import { AnimatePresence, motion } from "framer-motion"
import { Button } from "@/components/ui/button"

interface ScreenshotLightboxProps {
  url: string | null
  onClose: () => void
}

export function ScreenshotLightbox({ url, onClose }: ScreenshotLightboxProps) {
  return (
    <AnimatePresence>
      {url && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-sm"
          onClick={onClose}
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            onClick={(e) => e.stopPropagation()}
            className="w-full max-w-5xl max-h-[85vh] rounded-2xl bg-card border border-border shadow-2xl flex flex-col overflow-hidden"
          >
            <div className="flex items-center justify-between p-4 border-b border-border">
              <div className="text-sm text-muted-foreground truncate">Screenshot</div>
              <div className="flex items-center gap-3">
                <a
                  href={url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-sm text-primary hover:underline"
                >
                  Open in new tab
                </a>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={onClose}
                  className="text-muted-foreground hover:text-orange-600 hover:bg-orange-600/10"
                >
                  <X className="w-5 h-5" />
                </Button>
              </div>
            </div>
            <div className="p-4 overflow-auto">
              <img
                src={url}
                alt="Screenshot"
                className="w-full h-auto rounded-lg border border-border"
              />
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
