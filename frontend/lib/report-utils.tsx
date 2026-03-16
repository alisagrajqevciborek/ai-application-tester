import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import type { Components, ExtraProps } from "react-markdown"
import {
  AlertTriangle,
  AlertCircle,
  Info,
} from "lucide-react"

// ---------------------------------------------------------------------------
// Parsed report types
// ---------------------------------------------------------------------------

export type ParsedSubsection = { title: string; content: string; idx: number }
export type ParsedSection = {
  title: string | null
  content?: string
  hasSubsections: boolean
  intro?: { title: string | null; content: string; idx: number } | null
  subsections?: ParsedSubsection[]
  idx: number
}

export interface ParsedDetailedReport {
  cleanReport: string
  parsedSections: ParsedSection[]
  hasOnlyPlain: boolean
  intro: ParsedSection | null
  sectionsWithHeadings: ParsedSection[]
  defaultExpanded: string[]
}

// ---------------------------------------------------------------------------
// Console log helpers
// ---------------------------------------------------------------------------

export interface ConsoleLog {
  type: string
  text: string
  location?: string
}

export function parseConsoleLogs(logs: ConsoleLog[] | undefined): {
  errors: number
  warnings: number
} {
  if (!logs) return { errors: 0, warnings: 0 }
  return {
    errors: logs.filter((l) => l.type === "error").length,
    warnings: logs.filter((l) => l.type === "warning").length,
  }
}

// ---------------------------------------------------------------------------
// Severity config
// ---------------------------------------------------------------------------

export const severityConfig = {
  critical: {
    icon: AlertTriangle,
    color: "text-red-400",
    bg: "bg-red-500/10",
    border: "border-red-500/30",
    label: "Critical",
  },
  major: {
    icon: AlertCircle,
    color: "text-amber-400",
    bg: "bg-amber-500/10",
    border: "border-amber-500/30",
    label: "Major",
  },
  minor: {
    icon: Info,
    color: "text-blue-400",
    bg: "bg-blue-500/10",
    border: "border-blue-500/30",
    label: "Minor",
  },
} as const

// ---------------------------------------------------------------------------
// Markdown utilities
// ---------------------------------------------------------------------------

export function hasMarkdownTable(content: string): boolean {
  return /\|.+\|/.test(content) && /\|\s*[-:]{3,}/.test(content)
}

export function buildFallbackRows(content: string): Array<{ label: string; value: string }> {
  return content
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => Boolean(line) && !line.startsWith("### ") && !line.startsWith("## "))
    .map((line, index) => {
      const normalized = line.replace(/^[-*]\s+/, "").replace(/^\d+\.\s+/, "")
      const boldMatch = normalized.match(/^\*\*(.+?)\*\*\s*:\s*(.+)$/)
      if (boldMatch) {
        return { label: boldMatch[1].trim(), value: boldMatch[2].trim() }
      }
      const keyValueMatch = normalized.match(/^([^:]{2,80}):\s+(.+)$/)
      if (keyValueMatch) {
        return { label: keyValueMatch[1].trim(), value: keyValueMatch[2].trim() }
      }
      return { label: `Item ${index + 1}`, value: normalized }
    })
}

// ---------------------------------------------------------------------------
// Markdown component overrides (react-markdown v10, properly typed)
// ---------------------------------------------------------------------------

type ElementProps<T extends keyof JSX.IntrinsicElements> = JSX.IntrinsicElements[T] & ExtraProps

export const markdownComponents: Components = {
  h2: ({ node: _n, ...props }: ElementProps<"h2">) => (
    <h2 className="text-base font-semibold mt-5 mb-3 text-foreground" {...props} />
  ),
  h3: ({ node: _n, ...props }: ElementProps<"h3">) => (
    <h3 className="text-sm font-semibold mt-4 mb-2 text-foreground" {...props} />
  ),
  h4: ({ node: _n, ...props }: ElementProps<"h4">) => (
    <h4 className="text-sm font-medium mt-3 mb-2 text-foreground" {...props} />
  ),
  p: ({ node: _n, ...props }: ElementProps<"p">) => (
    <p className="text-sm text-muted-foreground leading-relaxed mb-3" {...props} />
  ),
  ul: ({ node: _n, ...props }: ElementProps<"ul">) => (
    <ul className="space-y-2 mb-3 ml-5 list-disc" {...props} />
  ),
  ol: ({ node: _n, ...props }: ElementProps<"ol">) => (
    <ol className="space-y-2 mb-3 ml-5 list-decimal" {...props} />
  ),
  li: ({ node: _n, ...props }: ElementProps<"li">) => (
    <li className="text-sm text-muted-foreground leading-relaxed" {...props} />
  ),
  // pre wraps code blocks — strip default browser styling
  pre: ({ node: _n, ...props }: ElementProps<"pre">) => (
    <pre className="my-2 p-0 bg-transparent border-0 overflow-x-auto whitespace-pre-wrap" {...props} />
  ),
  // code: className present = code block, absent = inline code
  code: ({ node: _n, className, children, ...props }: ElementProps<"code">) =>
    className ? (
      <code className="text-sm font-normal text-muted-foreground" {...props}>
        {children}
      </code>
    ) : (
      <code className="text-sm font-medium text-foreground" {...props}>
        {children}
      </code>
    ),
  hr: () => <hr className="border-t border-border/30 my-6" />,
  strong: ({ node: _n, ...props }: ElementProps<"strong">) => (
    <strong className="font-semibold" {...props} />
  ),
  table: ({ node: _n, ...props }: ElementProps<"table">) => (
    <details open className="my-3 rounded-xl border border-border/50 bg-muted/10 overflow-hidden">
      <summary className="cursor-pointer px-4 py-2.5 text-xs font-semibold tracking-wide text-foreground/80 border-b border-border/40 hover:bg-orange-600/10 transition-colors">
        Table
      </summary>
      <div className="overflow-x-auto">
        <table className="w-full text-sm" {...props} />
      </div>
    </details>
  ),
  thead: ({ node: _n, ...props }: ElementProps<"thead">) => (
    <thead className="bg-muted/30 border-b border-border/50" {...props} />
  ),
  tr: ({ node: _n, ...props }: ElementProps<"tr">) => (
    <tr className="border-b border-border/40 last:border-b-0 align-top" {...props} />
  ),
  th: ({ node: _n, ...props }: ElementProps<"th">) => (
    <th className="text-left px-4 py-3 font-semibold text-foreground" {...props} />
  ),
  td: ({ node: _n, ...props }: ElementProps<"td">) => (
    <td
      className="px-4 py-3 text-sm text-muted-foreground leading-relaxed align-top whitespace-normal break-words [&_p]:mb-1 [&_p:last-child]:mb-0 [&_ul]:my-1 [&_ol]:my-1 [&_li]:my-0.5 [&_code]:whitespace-nowrap"
      {...props}
    />
  ),
}

// ---------------------------------------------------------------------------
// NumberedSubsectionTable — renders a plain-text subsection as a table
// ---------------------------------------------------------------------------

export function NumberedSubsectionTable({ content }: { content: string }) {
  const rows = buildFallbackRows(content)
  if (rows.length === 0) return null

  return (
    <details open className="rounded-xl border border-border/50 overflow-hidden bg-muted/10">
      <summary className="cursor-pointer px-4 py-2.5 text-xs font-semibold tracking-wide text-foreground/80 border-b border-border/40 hover:bg-orange-600/10 transition-colors">
        Table
      </summary>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-muted/30 border-b border-border/50">
            <tr>
              <th className="text-left px-4 py-3 font-semibold text-foreground w-[32%]">Category</th>
              <th className="text-left px-4 py-3 font-semibold text-foreground">Details</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, idx) => (
              <tr key={`${row.label}-${idx}`} className="border-b border-border/40 last:border-b-0 align-top">
                <td className="px-4 py-3 font-medium text-foreground">{row.label}</td>
                <td className="px-4 py-3 text-muted-foreground leading-relaxed">{row.value}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  )
}

// ---------------------------------------------------------------------------
// parseDetailedReport — parses AI Markdown into a structured accordion tree
// ---------------------------------------------------------------------------

export function parseDetailedReport(rawReport: string): ParsedDetailedReport {
  const cleanReport = rawReport.split(/={10,}\s*AUTOMATED TEST FINDINGS \(REFERENCE\)/)[0].trim()
  const mainSections = cleanReport.split(/(?=^## )/m)

  const parseSubsections = (content: string) => {
    const subsections = content.split(/(?=^### )/m)
    if (subsections.length <= 1) {
      return { hasSubsections: false, content }
    }

    const parsed = subsections
      .map((sub, idx) => {
        const trimmed = sub.trim()
        if (!trimmed) return null
        if (trimmed.startsWith("### ")) {
          const firstLineEnd = trimmed.indexOf("\n")
          const title = firstLineEnd > 0 ? trimmed.substring(4, firstLineEnd).trim() : trimmed.substring(4).trim()
          const subContent = firstLineEnd > 0 ? trimmed.substring(firstLineEnd + 1).trim() : ""
          return { title, content: subContent, idx }
        }
        return { title: null, content: trimmed, idx }
      })
      .filter(Boolean) as Array<{ title: string | null; content: string; idx: number }>

    return {
      hasSubsections: true,
      intro: parsed[0]?.title ? null : parsed[0],
      subsections: parsed.filter((s) => Boolean(s.title)) as ParsedSubsection[],
    }
  }

  const parsedSections = mainSections
    .map((section, idx) => {
      const trimmed = section.trim()
      if (!trimmed) return null

      if (trimmed.startsWith("## ")) {
        const firstLineEnd = trimmed.indexOf("\n")
        const title = firstLineEnd > 0 ? trimmed.substring(3, firstLineEnd).trim() : trimmed.substring(3).trim()
        const content = firstLineEnd > 0 ? trimmed.substring(firstLineEnd + 1).trim() : ""
        const subsectionData = parseSubsections(content)
        return { title, ...subsectionData, idx } as ParsedSection
      }

      return { title: null, content: trimmed, hasSubsections: false, idx } as ParsedSection
    })
    .filter(Boolean) as ParsedSection[]

  const hasOnlyPlain = parsedSections.length > 0 && parsedSections.every((s) => !s.title)
  const intro = parsedSections[0]?.title ? null : parsedSections[0] ?? null

  const excludedSections = ["screenshot analysis", "conclusion", "conclusions"]
  const sectionsWithHeadings = parsedSections.filter(
    (s) => s.title && !excludedSections.includes(s.title.toLowerCase().replace(/^\d+\.\s*/, "").trim()),
  )
  const defaultExpanded = sectionsWithHeadings.length > 0 ? ["section-0"] : []

  return { cleanReport, parsedSections, hasOnlyPlain, intro, sectionsWithHeadings, defaultExpanded }
}

// ---------------------------------------------------------------------------
// Inline markdown renderer (convenience wrapper)
// ---------------------------------------------------------------------------

export function ReportMarkdown({ children }: { children: string }) {
  return (
    <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
      {children}
    </ReactMarkdown>
  )
}
