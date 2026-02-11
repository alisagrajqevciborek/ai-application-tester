"use client"

import { useEffect } from "react"
import { useRouter } from "next/navigation"
import { motion } from "framer-motion"
import { Home } from "lucide-react"
import { Button } from "@/components/ui/button"
import AdminDashboard from "@/components/admin/admin-dashboard"
import { useAuth } from "@/contexts/AuthContext"
import { Loader2 } from "lucide-react"

export default function AdminPage() {
  const { isAuthenticated, isLoading, user } = useAuth()
  const router = useRouter()

  useEffect(() => {
    if (!isLoading) {
      if (!isAuthenticated) {
        router.push('/login')
      } else if (user?.role !== 'admin') {
        // Redirect non-admins to user dashboard
        router.push('/dashboard')
      }
    }
  }, [isAuthenticated, isLoading, user, router])

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    )
  }

  if (!isAuthenticated || user?.role !== 'admin') {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.3 }}
      className="relative"
    >
      <div className="absolute top-4 right-8 z-10">
        <Button
          variant="outline"
          size="sm"
          onClick={() => router.push('/admin')}
          className="flex items-center gap-2 text-muted-foreground hover:text-foreground"
        >
          <Home className="h-4 w-4" />
          <span>Admin Home</span>
        </Button>
      </div>
      <AdminDashboard />
    </motion.div>
  )
}
