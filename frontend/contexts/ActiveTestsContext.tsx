"use client"

import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from "react"
import { testRunsApi, type TestRun } from "@/lib/api"
import { useAuth } from "@/contexts/AuthContext"

interface ActiveTestsContextType {
  /** Test runs that are currently pending or running */
  activeTests: TestRun[]
  /** Whether the initial fetch is still in progress */
  isLoading: boolean
}

const ActiveTestsContext = createContext<ActiveTestsContextType | undefined>(undefined)

const POLL_INTERVAL_MS = 3000

export function ActiveTestsProvider({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth()
  const [activeTests, setActiveTests] = useState<TestRun[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const pollRef = useRef<NodeJS.Timeout | null>(null)
  const isMountedRef = useRef(true)

  const fetchActiveTests = useCallback(async () => {
    if (!isAuthenticated) {
      setActiveTests([])
      setIsLoading(false)
      return
    }
    try {
      const allRuns = await testRunsApi.list()
      if (!isMountedRef.current) return
      const running = allRuns.filter(
        (tr) => tr.status === "running" || tr.status === "pending"
      )
      setActiveTests(running)
    } catch {
      // Silently ignore – widget is non-critical
    } finally {
      if (isMountedRef.current) setIsLoading(false)
    }
  }, [isAuthenticated])

  // Initial fetch + polling
  useEffect(() => {
    isMountedRef.current = true

    if (!isAuthenticated) {
      setActiveTests([])
      setIsLoading(false)
      return
    }

    // Fetch immediately
    fetchActiveTests()

    // Start polling
    pollRef.current = setInterval(fetchActiveTests, POLL_INTERVAL_MS)

    return () => {
      isMountedRef.current = false
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [isAuthenticated, fetchActiveTests])

  return (
    <ActiveTestsContext.Provider value={{ activeTests, isLoading }}>
      {children}
    </ActiveTestsContext.Provider>
  )
}

export function useActiveTests() {
  const context = useContext(ActiveTestsContext)
  if (context === undefined) {
    throw new Error("useActiveTests must be used within an ActiveTestsProvider")
  }
  return context
}

