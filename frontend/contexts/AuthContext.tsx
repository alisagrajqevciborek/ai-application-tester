"use client"

import React, { createContext, useContext, useState, useEffect, useCallback } from "react"
import { useRouter } from "next/navigation"
import { authApi, saveTokens, saveUser, clearTokens, getUser, type User } from "@/lib/api"

interface AuthContextType {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
  refreshUser: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const router = useRouter()

  // Load user from localStorage on mount
  useEffect(() => {
    const storedUser = getUser()
    if (storedUser) {
      // Optimistically set user and stop loading immediately
      setUser(storedUser)
      setIsLoading(false)

      // Verify token is still valid in the background (non-blocking)
      authApi
        .getMe()
        .then((currentUser) => {
          setUser(currentUser)
          saveUser(currentUser)
        })
        .catch(() => {
          // Token invalid, clear everything
          clearTokens()
          setUser(null)
        })
    } else {
      setIsLoading(false)
    }
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    try {
      const response = await authApi.login(email, password)
      saveTokens(response.access, response.refresh)
      saveUser(response.user)
      setUser(response.user)
      
      // Redirect to appropriate dashboard after login
      if (response.user.role === 'admin') {
        router.push('/admin')
      } else {
        router.push('/dashboard')
      }
    } catch (error) {
      throw error
    }
  }, [router])

  const logout = useCallback(async () => {
    try {
      await authApi.logout()
    } catch (error) {
      console.error("Logout error:", error)
    } finally {
      clearTokens()
      setUser(null)
      router.push('/login')
    }
  }, [router])

  const refreshUser = useCallback(async () => {
    try {
      const currentUser = await authApi.getMe()
      setUser(currentUser)
      saveUser(currentUser)
    } catch (error) {
      console.error("Failed to refresh user:", error)
      clearTokens()
      setUser(null)
    }
  }, [])

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        login,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider")
  }
  return context
}

