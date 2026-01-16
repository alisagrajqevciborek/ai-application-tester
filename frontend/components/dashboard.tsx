"use client"

import { useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import TopNav from "@/components/top-nav"
import Sidebar from "@/components/sidebar"
import NewTestForm from "@/components/new-test-form"
import ReportView from "@/components/report-view"
import type { TestHistory } from "@/lib/types"

interface DashboardProps {
  onLogout: () => void
}

const mockHistory: TestHistory[] = [
  {
    id: "1",
    appName: "E-commerce App",
    status: "success",
    testType: "functional",
    date: "2024-01-15",
    passRate: 94,
    failRate: 6,
  },
  {
    id: "2",
    appName: "Dashboard Pro",
    status: "failed",
    testType: "regression",
    date: "2024-01-14",
    passRate: 67,
    failRate: 33,
  },
  {
    id: "3",
    appName: "Mobile API",
    status: "running",
    testType: "performance",
    date: "2024-01-14",
    passRate: 0,
    failRate: 0,
  },
  {
    id: "4",
    appName: "Auth Service",
    status: "success",
    testType: "functional",
    date: "2024-01-13",
    passRate: 100,
    failRate: 0,
  },
  {
    id: "5",
    appName: "Payment Gateway",
    status: "success",
    testType: "regression",
    date: "2024-01-12",
    passRate: 89,
    failRate: 11,
  },
  {
    id: "6",
    appName: "Analytics App",
    status: "failed",
    testType: "accessibility",
    date: "2024-01-11",
    passRate: 45,
    failRate: 55,
  },
  {
    id: "7",
    appName: "User Portal",
    status: "success",
    testType: "performance",
    date: "2024-01-10",
    passRate: 91,
    failRate: 9,
  },
  {
    id: "8",
    appName: "Admin Panel",
    status: "failed",
    testType: "accessibility",
    date: "2024-01-09",
    passRate: 72,
    failRate: 28,
  },
]

export default function Dashboard({ onLogout }: DashboardProps) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [selectedTest, setSelectedTest] = useState<TestHistory | null>(null)
  const [history, setHistory] = useState<TestHistory[]>(mockHistory)

  const handleNewTestComplete = (newTest: TestHistory) => {
    setHistory([newTest, ...history])
    setSelectedTest(newTest)
  }

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <TopNav onLogout={onLogout} />

      <div className="flex flex-1 overflow-hidden">
        <Sidebar
          collapsed={sidebarCollapsed}
          onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
          history={history}
          selectedId={selectedTest?.id || null}
          onSelectTest={setSelectedTest}
        />

        <main className="flex-1 overflow-auto p-6 lg:p-8">
          <AnimatePresence mode="wait">
            {selectedTest ? (
              <motion.div
                key="report"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.2 }}
              >
                <ReportView test={selectedTest} onBack={() => setSelectedTest(null)} />
              </motion.div>
            ) : (
              <motion.div
                key="new-test"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.2 }}
              >
                <NewTestForm onTestComplete={handleNewTestComplete} />
              </motion.div>
            )}
          </AnimatePresence>
        </main>
      </div>
    </div>
  )
}
