"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { AnimatePresence, motion } from "framer-motion"
import LoginPage from "@/components/auth/login-page"
import RegisterPage from "@/components/auth/register-page"
// Dynamic imports for heavy dashboard components
import dynamic from 'next/dynamic'
import { Loader2 } from "lucide-react"
import { useAuth } from "@/contexts/AuthContext"

const Dashboard = dynamic(() => import("@/components/dashboard/dashboard"), {
  loading: () => <div className="flex items-center justify-center h-screen"><Loader2 className="w-8 h-8 animate-spin text-primary" /></div>
})

const AdminDashboard = dynamic(() => import("@/components/admin/admin-dashboard"), {
  loading: () => <div className="flex items-center justify-center h-screen"><Loader2 className="w-8 h-8 animate-spin text-primary" /></div>
})

type AuthView = "login" | "register"

export default function Home() {
  const { isAuthenticated, isLoading, refreshUser, user } = useAuth()
  const [authView, setAuthView] = useState<AuthView>("login")
  const router = useRouter()

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    )
  }

  const handleRegisterComplete = async () => {
    await refreshUser()
  }

  return (
    <div className="min-h-screen bg-background">
      <AnimatePresence mode="wait">
        {!isAuthenticated ? (
          authView === "login" ? (
            <motion.div
              key="login"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0, x: -50 }}
              transition={{ duration: 0.3 }}
            >
              <LoginPage onLogin={() => {}} onShowRegister={() => setAuthView("register")} />
            </motion.div>
          ) : (
            <motion.div
              key="register"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0, x: 50 }}
              transition={{ duration: 0.3 }}
            >
              <RegisterPage 
                onBack={() => setAuthView("login")} 
                onRegisterComplete={handleRegisterComplete}
              />
            </motion.div>
          )
        ) : (
          <motion.div
            key="dashboard"
            initial={{ opacity: 0, x: 50 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3 }}
          >
            {user?.role === 'admin' ? <AdminDashboard /> : <Dashboard />}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
