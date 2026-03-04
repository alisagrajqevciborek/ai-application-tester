"use client"

import { useEffect, useState, useMemo } from "react"
import { useRouter } from "next/navigation"
import { motion } from "framer-motion"
import { Package, Sparkles, Plus, BarChart3, Play, ChevronDown, Search, Filter, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import TopNav from "@/components/dashboard/top-nav"
import { useAuth } from "@/contexts/AuthContext"
import { useData } from "@/contexts/DataContext"
import { testRunsApi, type TestRunStats } from "@/lib/api"
import { Loader2 } from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { cn } from "@/lib/utils"
import dynamic from "next/dynamic"
import { useDebounce } from "@/lib/hooks/useDebounce"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"

const StatisticsModal = dynamic(() => import("@/components/charts/statistics-modal"), {
  ssr: false,
})

export default function DashboardPage() {
  const { isAuthenticated, isLoading, user } = useAuth()
  const { applications, testHistory, stats, isLoading: isLoadingData } = useData()
  const router = useRouter()
  const [statsModalOpen, setStatsModalOpen] = useState(false)
  const [liveStats, setLiveStats] = useState<TestRunStats | null>(null)

  // Poll stats every 3 s while the modal is open so numbers update immediately
  useEffect(() => {
    if (!statsModalOpen) return

    let cancelled = false

    const fetchStats = () => {
      testRunsApi.stats()
        .then((data) => { if (!cancelled) setLiveStats(data) })
        .catch(() => {})
    }

    // Clear stale data then fetch immediately
    setLiveStats(null)
    fetchStats()

    const interval = setInterval(fetchStats, 3000)

    return () => {
      cancelled = true
      clearInterval(interval)
    }
  }, [statsModalOpen])

  const [searchQuery, setSearchQuery] = useState("")
  const [statusFilter, setStatusFilter] = useState<"all" | "success" | "failed" | "running">("all")
  const [testTypeFilter, setTestTypeFilter] = useState<"all" | "general" | "functional" | "regression" | "performance" | "accessibility" | "broken_links" | "authentication">("all")
  const [showFilters, setShowFilters] = useState(false)

  // Debounce search query to avoid filtering on every keystroke
  const debouncedSearch = useDebounce(searchQuery, 300)

  useEffect(() => {
    if (!isLoading) {
      if (!isAuthenticated) {
        router.push('/login')
      } else if (user?.role === 'admin') {
        router.push('/admin')
      }
    }
  }, [isAuthenticated, isLoading, user, router])

  // Group tests by app name
  const appsWithVersions = useMemo(() => {
    const groups: Record<string, typeof testHistory> = {}
    testHistory.forEach((test) => {
      const appName = test.appName
      if (!groups[appName]) {
        groups[appName] = []
      }
      groups[appName].push(test)
    })
    return groups
  }, [testHistory])

  const appNames = Object.keys(appsWithVersions).sort()

  // Check if filters are debounced search query and filters
  const filteredAppNames = useMemo(() => {
    let filtered = appNames

    // Apply search filter with debounced value
    if (debouncedSearch.trim()) {
      filtered = filtered.filter((appName) =>
        appName.toLowerCase().includes(debouncedSearch.toLowerCase())
      )
    }

    // Apply status and test type filters
    if (statusFilter !== "all" || testTypeFilter !== "all") {
      filtered = filtered.filter((appName) => {
        const appTests = appsWithVersions[appName]
        // Check if any test in this app matches the filters
        return appTests.some((test) => {
          const matchesStatus = statusFilter === "all" || test.status === statusFilter
          const matchesType = testTypeFilter === "all" || test.testType === testTypeFilter
          return matchesStatus && matchesType
        })
      })
    }

    return filtered
  }, [appNames, debouncedSearch, statusFilter, testTypeFilter, appsWithVersions])

  const hasActiveFilters = searchQuery.trim() !== "" || statusFilter !== "all" || testTypeFilter !== "all"

  const clearFilters = () => {
    setSearchQuery("")
    setStatusFilter("all")
    setTestTypeFilter("all")
  }

  if (isLoading || !isAuthenticated || user?.role === 'admin') {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <TopNav />
      
      <main className="flex-1 overflow-auto p-6 lg:p-8">
        <div className="max-w-7xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.2 }}
            className="space-y-8"
          >
            {/* Header */}
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-3xl font-bold text-foreground mb-2">Dashboard</h1>
                <p className="text-muted-foreground">
                  Manage your applications and test runs
                </p>
              </div>

              <Button
                onClick={() => setStatsModalOpen(true)}
                className="flex items-center gap-2"
              >
                <BarChart3 className="h-5 w-5" />
                <span>View Statistics</span>
              </Button>
            </div>

            {/* Quick Actions */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Card 
                className="border-orange-500/20 hover:border-orange-500/40 transition-all cursor-pointer group"
                onClick={() => router.push('/dashboard/new-test')}
              >
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-orange-500 group-hover:text-orange-400 transition-colors">
                    <Plus className="h-5 w-5" />
                    Create New Test
                  </CardTitle>
                  <CardDescription>
                    Configure and run automated tests for your applications
                  </CardDescription>
                </CardHeader>
              </Card>

              <Card 
                className="border-orange-500/20 hover:border-orange-500/40 transition-all cursor-pointer group"
                onClick={() => router.push('/dashboard/ai-generator')}
              >
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-orange-500 group-hover:text-orange-400 transition-colors">
                    <Sparkles className="h-5 w-5" />
                    AI Test Generator
                  </CardTitle>
                  <CardDescription>
                    Describe what you want to test and let AI generate test cases
                  </CardDescription>
                </CardHeader>
              </Card>
            </div>

            {/* Applications List */}
            <div>
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-2xl font-semibold text-foreground">Your Applications</h2>
                
                {appNames.length > 0 && (
                  <div className="flex items-center gap-3">
                    <div className="relative w-64">
                      <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                      <Input
                        placeholder="Search apps..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="pl-9 h-10 bg-background border-border"
                      />
                    </div>
                    <Button
                      variant="outline"
                      size="icon"
                      onClick={() => setShowFilters(!showFilters)}
                      className={cn(
                        "h-10 w-10",
                        showFilters && "bg-orange-500/10 border-orange-500/50"
                      )}
                    >
                      <Filter className="h-4 w-4" />
                    </Button>
                  </div>
                )}
              </div>

              {/* Filters */}
              {appNames.length > 0 && showFilters && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  className="mb-4 p-4 border border-border rounded-lg bg-card/50 space-y-3"
                >
                  {/* Status Filter */}
                  <div>
                    <label className="text-sm font-medium text-foreground mb-2 block">Status</label>
                    <div className="flex flex-wrap gap-2">
                      <button
                        onClick={() => setStatusFilter("all")}
                        className={cn(
                          "px-3 py-1.5 text-sm rounded-md transition-colors",
                          statusFilter === "all"
                            ? "bg-orange-600 text-white"
                            : "bg-muted text-muted-foreground hover:bg-orange-600/10 hover:text-orange-600"
                        )}
                      >
                        All Status
                      </button>
                      <button
                        onClick={() => setStatusFilter("success")}
                        className={cn(
                          "px-3 py-1.5 text-sm rounded-md transition-colors",
                          statusFilter === "success"
                            ? "bg-orange-600 text-white"
                            : "bg-muted text-muted-foreground hover:bg-orange-600/10 hover:text-orange-600"
                        )}
                      >
                        Passed
                      </button>
                      <button
                        onClick={() => setStatusFilter("failed")}
                        className={cn(
                          "px-3 py-1.5 text-sm rounded-md transition-colors",
                          statusFilter === "failed"
                            ? "bg-orange-600 text-white"
                            : "bg-muted text-muted-foreground hover:bg-orange-600/10 hover:text-orange-600"
                        )}
                      >
                        Failed
                      </button>
                      <button
                        onClick={() => setStatusFilter("running")}
                        className={cn(
                          "px-3 py-1.5 text-sm rounded-md transition-colors",
                          statusFilter === "running"
                            ? "bg-orange-600 text-white"
                            : "bg-muted text-muted-foreground hover:bg-orange-600/10 hover:text-orange-600"
                        )}
                      >
                        Running
                      </button>
                    </div>
                  </div>

                  {/* Test Type Filter */}
                  <div>
                    <label className="text-sm font-medium text-foreground mb-2 block">Test Type</label>
                    <div className="flex flex-wrap gap-2">
                      <button
                        onClick={() => setTestTypeFilter("all")}
                        className={cn(
                          "px-3 py-1.5 text-sm rounded-md transition-colors",
                          testTypeFilter === "all"
                            ? "bg-orange-600 text-white"
                            : "bg-muted text-muted-foreground hover:bg-orange-600/10 hover:text-orange-600"
                        )}
                      >
                        All Types
                      </button>
                      <button
                        onClick={() => setTestTypeFilter("general")}
                        className={cn(
                          "px-3 py-1.5 text-sm rounded-md transition-colors",
                          testTypeFilter === "general"
                            ? "bg-orange-600 text-white"
                            : "bg-muted text-muted-foreground hover:bg-orange-600/10 hover:text-orange-600"
                        )}
                      >
                        General
                      </button>
                      <button
                        onClick={() => setTestTypeFilter("functional")}
                        className={cn(
                          "px-3 py-1.5 text-sm rounded-md transition-colors",
                          testTypeFilter === "functional"
                            ? "bg-orange-600 text-white"
                            : "bg-muted text-muted-foreground hover:bg-orange-600/10 hover:text-orange-600"
                        )}
                      >
                        Functional
                      </button>
                      <button
                        onClick={() => setTestTypeFilter("regression")}
                        className={cn(
                          "px-3 py-1.5 text-sm rounded-md transition-colors",
                          testTypeFilter === "regression"
                            ? "bg-orange-600 text-white"
                            : "bg-muted text-muted-foreground hover:bg-orange-600/10 hover:text-orange-600"
                        )}
                      >
                        Regression
                      </button>
                      <button
                        onClick={() => setTestTypeFilter("performance")}
                        className={cn(
                          "px-3 py-1.5 text-sm rounded-md transition-colors",
                          testTypeFilter === "performance"
                            ? "bg-orange-600 text-white"
                            : "bg-muted text-muted-foreground hover:bg-orange-600/10 hover:text-orange-600"
                        )}
                      >
                        Performance
                      </button>
                      <button
                        onClick={() => setTestTypeFilter("accessibility")}
                        className={cn(
                          "px-3 py-1.5 text-sm rounded-md transition-colors",
                          testTypeFilter === "accessibility"
                            ? "bg-orange-600 text-white"
                            : "bg-muted text-muted-foreground hover:bg-orange-600/10 hover:text-orange-600"
                        )}
                      >
                        Accessibility
                      </button>
                      <button
                        onClick={() => setTestTypeFilter("broken_links")}
                        className={cn(
                          "px-3 py-1.5 text-sm rounded-md transition-colors",
                          testTypeFilter === "broken_links"
                            ? "bg-orange-600 text-white"
                            : "bg-muted text-muted-foreground hover:bg-orange-600/10 hover:text-orange-600"
                        )}
                      >
                        Broken Links
                      </button>
                      <button
                        onClick={() => setTestTypeFilter("authentication")}
                        className={cn(
                          "px-3 py-1.5 text-sm rounded-md transition-colors",
                          testTypeFilter === "authentication"
                            ? "bg-orange-600 text-white"
                            : "bg-muted text-muted-foreground hover:bg-orange-600/10 hover:text-orange-600"
                        )}
                      >
                        Authentication
                      </button>
                    </div>
                  </div>

                  {/* Clear Filters */}
                  {hasActiveFilters && (
                    <div className="pt-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={clearFilters}
                        className="text-muted-foreground hover:text-orange-600 hover:bg-orange-600/10"
                      >
                        <X className="h-3 w-3 mr-1" />
                        Clear all filters
                      </Button>
                    </div>
                  )}
                </motion.div>
              )}

              {/* Results count */}
              {appNames.length > 0 && hasActiveFilters && (
                <div className="mb-4 text-sm text-muted-foreground">
                  {filteredAppNames.length} app{filteredAppNames.length !== 1 ? 's' : ''} found
                </div>
              )}
              
              {isLoadingData ? (
                <div className="flex items-center justify-center min-h-[200px]">
                  <Loader2 className="w-8 h-8 animate-spin text-primary" />
                </div>
              ) : appNames.length === 0 ? (
                <Card className="border-dashed">
                  <CardContent className="flex flex-col items-center justify-center py-12">
                    <Package className="h-12 w-12 text-muted-foreground mb-4" />
                    <p className="text-muted-foreground mb-4">No applications yet</p>
                    <Button onClick={() => router.push('/dashboard/new-test')}>
                      Create Your First Test
                    </Button>
                  </CardContent>
                </Card>
              ) : filteredAppNames.length === 0 ? (
                <Card className="border-dashed">
                  <CardContent className="flex flex-col items-center justify-center py-12">
                    <Filter className="h-12 w-12 text-muted-foreground mb-4" />
                    <p className="text-muted-foreground mb-2">No applications match your filters</p>
                    <p className="text-sm text-muted-foreground mb-4">Try adjusting your search or filters</p>
                    {hasActiveFilters && (
                      <Button variant="outline" onClick={clearFilters}>
                        Clear Filters
                      </Button>
                    )}
                  </CardContent>
                </Card>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {filteredAppNames.map((appName) => {
                    const versions = appsWithVersions[appName]
                    const versionCount = versions.length
                    const latestVersion = versions.sort((a, b) => b.version - a.version)[0]
                    const app = applications.find(a => a.name === appName)

                    return (
                      <Card 
                        key={appName}
                        className="border-border hover:border-orange-500/40 transition-all cursor-pointer group"
                        onClick={() => router.push(`/dashboard/apps/${encodeURIComponent(appName)}`)}
                      >
                        <CardHeader>
                          <div className="flex items-start justify-between">
                            <div className="flex items-center gap-2 flex-1">
                              <Package className="h-5 w-5 text-orange-600 flex-shrink-0" />
                              <CardTitle className="text-lg truncate">{appName}</CardTitle>
                            </div>
                          </div>
                          <CardDescription className="line-clamp-1">
                            {app?.url || 'No URL'}
                          </CardDescription>
                        </CardHeader>
                        <CardContent>
                          <div className="flex items-center justify-between text-sm">
                            <span className="text-muted-foreground">
                              {versionCount} version{versionCount !== 1 ? 's' : ''}
                            </span>
                            {latestVersion && (
                              <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                                latestVersion.status === 'success' 
                                  ? 'bg-green-500/20 text-green-400 border border-green-500/30'
                                  : latestVersion.status === 'failed'
                                  ? 'bg-red-500/20 text-red-400 border border-red-500/30'
                                  : 'bg-orange-500/20 text-orange-400 border border-orange-500/30'
                              }`}>
                                {latestVersion.status}
                              </span>
                            )}
                          </div>
                        </CardContent>
                      </Card>
                    )
                  })}
                </div>
              )}
            </div>
          </motion.div>
        </div>
      </main>

      {/* Statistics Modal */}
      <StatisticsModal
        open={statsModalOpen}
        onOpenChange={setStatsModalOpen}
        stats={liveStats ?? stats}
      />
    </div>
  )
}
