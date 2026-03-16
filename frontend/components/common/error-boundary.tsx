"use client"

import { Component, type ErrorInfo, type ReactNode } from "react"
import { Button } from "@/components/ui/button"
import { AlertTriangle } from "lucide-react"

interface ErrorBoundaryProps {
  children: ReactNode
  /** Optional fallback to render instead of the default error UI */
  fallback?: ReactNode
}

interface ErrorBoundaryState {
  hasError: boolean
  error: Error | null
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // Log to the console in development; wire up to an error tracking service here if needed
    if (process.env.NODE_ENV !== "production") {
      console.error("[ErrorBoundary] Uncaught error:", error, info.componentStack)
    }
  }

  reset = () => this.setState({ hasError: false, error: null })

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback

      return (
        <div className="flex flex-col items-center justify-center min-h-[200px] p-8 rounded-2xl border border-destructive/30 bg-destructive/5 text-center gap-4">
          <div className="p-3 rounded-full bg-destructive/10">
            <AlertTriangle className="w-6 h-6 text-destructive" />
          </div>
          <div>
            <h3 className="font-semibold text-foreground mb-1">Something went wrong</h3>
            <p className="text-sm text-muted-foreground max-w-sm">
              {this.state.error?.message ?? "An unexpected error occurred while rendering this section."}
            </p>
          </div>
          <Button variant="outline" size="sm" onClick={this.reset}>
            Try again
          </Button>
        </div>
      )
    }

    return this.props.children
  }
}
