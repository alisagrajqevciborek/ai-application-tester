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

// Start with 5 second polling, increase to 15 seconds when no active tests
const POLL_INTERVAL_ACTIVE = 5000
const POLL_INTERVAL_IDLE = 15000

export function ActiveTestsProvider({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth()
  const [activeTests, setActiveTests] = useState<TestRun[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const pollRef = useRef<NodeJS.Timeout | null>(null)
  const isMountedRef = useRef(true)
  const pollIntervalRef = useRef(POLL_INTERVAL_ACTIVE)

  const fetchActiveTests = useCallback(async () => {
    if (!isAuthenticated) {
      setActiveTests([])
      setIsLoading(false)
      return
    }
    try {
      // Use optimized endpoint that only returns active tests
      const running = await testRunsApi.listActive()
      if (!isMountedRef.current) return
      
      setActiveTests(running)
      
      // Adjust polling interval based on whether there are active tests
      if (running.length > 0) {
        pollIntervalRef.current = POLL_INTERVAL_ACTIVE
      } else {
        // Slow down polling when there are no active tests
        pollIntervalRef.current = POLL_INTERVAL_IDLE
      }
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

    // Start polling with dynamic interval
    const startPolling = () => {
      if (pollRef.current) clearInterval(pollRef.current)
      pollRef.current = setInterval(() => {
        fetchActiveTests()
        // Restart polling with potentially new interval
        startPolling()
      }, pollIntervalRef.current)
    }
    startPolling()

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

