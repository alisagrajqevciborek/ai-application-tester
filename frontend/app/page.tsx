"use client"

import { useState } from "react"
import { AnimatePresence, motion } from "framer-motion"
import LoginPage from "@/components/login-page"
import Dashboard from "@/components/dashboard"

export default function Home() {
  const [isAuthenticated, setIsAuthenticated] = useState(false)

  return (
    <div className="min-h-screen bg-background">
      <AnimatePresence mode="wait">
        {!isAuthenticated ? (
          <motion.div
            key="login"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0, x: -50 }}
            transition={{ duration: 0.3 }}
          >
            <LoginPage onLogin={() => setIsAuthenticated(true)} />
          </motion.div>
        ) : (
          <motion.div
            key="dashboard"
            initial={{ opacity: 0, x: 50 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3 }}
          >
            <Dashboard onLogout={() => setIsAuthenticated(false)} />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
