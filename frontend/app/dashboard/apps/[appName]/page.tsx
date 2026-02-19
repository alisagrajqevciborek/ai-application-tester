"use client"

import { useEffect, useState, useMemo } from "react"
import { useRouter, useParams } from "next/navigation"
import { motion } from "framer-motion"
import { ArrowLeft, Package, Play, ChevronDown, BarChart3, Home } from "lucide-react"
import { Button } from "@/components/ui/button"
import TopNav from "@/components/dashboard/top-nav"
import VersionCard from "@/components/reports/version-card"
import { useAuth } from "@/contexts/AuthContext"
import { useData } from "@/contexts/DataContext"
import { testRunsApi } from "@/lib/api"
import { Loader2 } from "lucide-react"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { useToast } from "@/components/ui/use-toast"
import dynamic from "next/dynamic"

const StatisticsModal = dynamic(() => import("@/components/charts/statistics-modal"), {
  ssr: false,
})

export default function AppVersionsPage() {
  const { isAuthenticated, isLoading, user } = useAuth()
  const { testHistory, stats, isLoading: isLoadingData, forceRefresh } = useData()
  const router = useRouter()
  const params = useParams()
  const appName = decodeURIComponent(params.appName as string)
  const [statsModalOpen, setStatsModalOpen] = useState(false)
  const { toast } = useToast()

  useEffect(() => {
    if (!isLoading) {
      if (!isAuthenticated) {
        router.push('/login')
      } else if (user?.role === 'admin') {
        router.push('/admin')
      }
    }
  }, [isAuthenticated, isLoading, user, router])

  // Filter versions for this app and sort by version number (newest first)
  const versions = useMemo(() => {
    return testHistory
      .filter((test) => test.appName === appName)
      .sort((a, b) => b.version - a.version)
  }, [testHistory, appName])

  if (isLoading || !isAuthenticated || user?.role === 'admin') {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    )
  }

  const handleSelectTest = (test: typeof testHistory[0]) => {
    router.push(`/dashboard/reports/${test.id}`)
  }

  const handleDeleteTest = async (testId: string) => {
    const isLastVersion = versions.length === 1
    
    // Show loading toast
    toast({
      title: "Deleting test run...",
      description: "Please wait while we delete the test run.",
    })
    
    try {
      await testRunsApi.delete(parseInt(testId))
      
      // Force refresh to update the list
      await forceRefresh()
      
      toast({
        title: "Test run deleted",
        description: "The test run has been successfully deleted.",
      })
      
      // If this was the last version, the app is now empty — go to the dashboard
      if (isLastVersion) {
        router.push('/dashboard')
      }
    } catch (err) {
      console.error("Failed to delete test run:", err)
      toast({
        title: "Failed to delete test run",
        description: err instanceof Error ? err.message : "An error occurred while deleting the test run.",
        variant: "destructive",
      })
    }
  }

  const handleRunTest = (appName: string, testType: string) => {
    router.push(`/dashboard/new-test?app=${encodeURIComponent(appName)}&testType=${testType}`)
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
            className="space-y-6"
          >
            {/* Header */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  onClick={() => router.push('/dashboard')}
                  className="flex items-center gap-2 text-muted-foreground hover:text-foreground"
                >
                  <ArrowLeft className="h-4 w-4" />
                  <span>Back</span>
                </Button>
                <Button
                  variant="outline"
                  size="icon"
                  onClick={() => router.push('/dashboard')}
                  className="text-muted-foreground hover:text-foreground"
                  title="Go to Dashboard"
                >
                  <Home className="h-4 w-4" />
                </Button>
              </div>

              <Button
                onClick={() => setStatsModalOpen(true)}
                className="flex items-center gap-2"
              >
                <BarChart3 className="h-5 w-5" />
                <span>View Statistics</span>
              </Button>
            </div>

            {/* App Header */}
            <div className="flex items-center justify-between pb-2 border-b border-border">
              <div className="flex items-center gap-2">
                <Package className="h-5 w-5 text-orange-600" />
                <h1 className="text-2xl font-semibold text-foreground">{appName}</h1>
                <span className="text-sm text-muted-foreground">
                  ({versions.length} version{versions.length !== 1 ? 's' : ''})
                </span>
              </div>

              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button className="bg-primary text-primary-foreground hover:bg-primary/90">
                    <Play className="w-4 h-4 mr-2" />
                    Run New Test
                    <ChevronDown className="w-4 h-4 ml-2 opacity-50" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="bg-popover border-border">
                  <DropdownMenuItem onClick={() => handleRunTest(appName, "general")}>
                    General (Full Suite)
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => handleRunTest(appName, "functional")}>
                    Functional Testing
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => handleRunTest(appName, "regression")}>
                    Regression Testing
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => handleRunTest(appName, "performance")}>
                    Performance Testing
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => handleRunTest(appName, "accessibility")}>
                    Accessibility Testing
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => handleRunTest(appName, "broken_links")}>
                    Broken Link Check
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => handleRunTest(appName, "authentication")}>
                    Authentication Flow
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>

            {/* Version Cards Grid */}
            {isLoadingData ? (
              <div className="flex items-center justify-center min-h-[400px]">
                <Loader2 className="w-8 h-8 animate-spin text-primary" />
              </div>
            ) : versions.length === 0 ? (
              <div className="text-center py-12">
                <p className="text-muted-foreground">No test versions found for {appName}</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                {versions.map((test) => (
                  <VersionCard
                    key={test.id}
                    test={test}
                    onSelect={handleSelectTest}
                    onDelete={handleDeleteTest}
                    onRunTest={handleRunTest}
                    isSelected={false}
                  />
                ))}
              </div>
            )}
          </motion.div>
        </div>
      </main>

      {/* Statistics Modal */}
      <StatisticsModal
        open={statsModalOpen}
        onOpenChange={setStatsModalOpen}
        stats={stats}
      />
    </div>
  )
}
