"use client"

import React, { createContext, useContext, useState, useEffect, useRef, useCallback } from "react"
import { applicationsApi, testRunsApi, type Application, type TestRun, type TestRunStats } from "@/lib/api"
import { useAuth } from "@/contexts/AuthContext"
import type { TestHistory } from "@/lib/types"

const convertTestRunToHistory = (testRun: TestRun): TestHistory => ({
  id: testRun.id.toString(),
  appName: testRun.application_name,
  versionName: testRun.version_name,
  version: testRun.version,
  status: testRun.status === 'success' ? 'success' : testRun.status === 'failed' ? 'failed' : 'running',
  testType: testRun.test_type,
  date: new Date(testRun.started_at).toISOString().split("T")[0],
  passRate: testRun.pass_rate,
  failRate: testRun.fail_rate,
})

interface DataContextType {
  applications: Application[]
  testHistory: TestHistory[]
  stats: TestRunStats | null
  isLoading: boolean       // true only on the very first load (no data yet)
  isRefreshing: boolean    // true on background refreshes (data already visible)
  forceRefresh: () => Promise<void>
}

const DataContext = createContext<DataContextType | undefined>(undefined)

// Cache duration: 5 minutes - data older than this triggers a background refresh
const CACHE_DURATION = 300000

export function DataProvider({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading: authLoading } = useAuth()

  const [applications, setApplications] = useState<Application[]>([])
  const [testHistory, setTestHistory] = useState<TestHistory[]>([])
  const [stats, setStats] = useState<TestRunStats | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isRefreshing, setIsRefreshing] = useState(false)

  // Use refs so they never cause re-renders or stale closures
  const lastFetchRef = useRef<number>(0)
  const isFetchingRef = useRef(false)
  const hasDataRef = useRef(false)

  const clearData = useCallback(() => {
    setApplications([])
    setTestHistory([])
    setStats(null)
    setIsLoading(true)
    lastFetchRef.current = 0
    isFetchingRef.current = false
    hasDataRef.current = false
  }, [])

  const fetchAll = useCallback(async (force = false) => {
    // Never fetch if not authenticated
    if (!isAuthenticated) return

    // Prevent concurrent fetches
    if (isFetchingRef.current) return

    // Skip if cache is still fresh and not forced
    const isStale = Date.now() - lastFetchRef.current > CACHE_DURATION
    if (!force && !isStale && hasDataRef.current) return

    isFetchingRef.current = true

    // Only show full-page spinner on the very first load
    // For subsequent refreshes show nothing (or a subtle indicator)
    if (!hasDataRef.current) {
      setIsLoading(true)
    } else {
      setIsRefreshing(true)
    }

    try {
      const [apps, testRuns, statsData] = await Promise.all([
        applicationsApi.list().catch(() => [] as Application[]),
        testRunsApi.list().catch(() => [] as TestRun[]),
        testRunsApi.stats().catch(() => null),
      ])

      setApplications(apps || [])
      // Memoize conversion to avoid recalculating on every render
      const convertedHistory = (testRuns || []).map(convertTestRunToHistory)
      setTestHistory(convertedHistory)
      setStats(statsData)

      lastFetchRef.current = Date.now()
      hasDataRef.current = true
    } finally {
      setIsLoading(false)
      setIsRefreshing(false)
      isFetchingRef.current = false
    }
  }, [isAuthenticated]) // Re-create when auth state changes

  // Fetch once auth is confirmed; clear data when user logs out
  useEffect(() => {
    if (authLoading) return // Wait for auth check to complete first

    if (isAuthenticated) {
      fetchAll(true)
    } else {
      clearData()
    }
  }, [isAuthenticated, authLoading, fetchAll, clearData])

  // Listen for the auth:logout event dispatched by apiRequest when a token
  // refresh fails mid-session, so we clear stale data immediately.
  useEffect(() => {
    const handler = () => clearData()
    window.addEventListener('auth:logout', handler)
    return () => window.removeEventListener('auth:logout', handler)
  }, [clearData])

  // Stable forceRefresh for use after create/delete actions
  const forceRefresh = useCallback(async () => {
    await fetchAll(true)
  }, [fetchAll])

  return (
    <DataContext.Provider value={{ applications, testHistory, stats, isLoading, isRefreshing, forceRefresh }}>
      {children}
    </DataContext.Provider>
  )
}

export function useData() {
  const context = useContext(DataContext)
  if (context === undefined) {
    throw new Error("useData must be used within a DataProvider")
  }
  return context
}
