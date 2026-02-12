"use client"

import { useState, useEffect } from "react"
import { motion } from "framer-motion"
import { Users, Shield, ToggleLeft, ToggleRight, Loader2, AlertCircle, CheckCircle } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { toast } from "sonner"
import TopNav from "@/components/dashboard/top-nav"
import { adminApi, type User } from "@/lib/api"

export default function AdminDashboard() {
  const [users, setUsers] = useState<User[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [updatingUserId, setUpdatingUserId] = useState<number | null>(null)


  useEffect(() => {
    loadUsers()
  }, [])

  const loadUsers = async () => {
    try {
      setIsLoading(true)
      setError(null)
      const response = await adminApi.listUsers()
      setUsers(response.users)
    } catch (err: any) {
      setError(err.message || "Failed to load users")
    } finally {
      setIsLoading(false)
    }
  }

  const handleToggleStatus = async (userId: number, currentStatus: string) => {
    try {
      setUpdatingUserId(userId)
      setError(null)
      setSuccess(null)
      
      const newStatus = currentStatus === 'active' ? 'disabled' : 'active'
      const user = users.find(u => u.id === userId)
      const response = await adminApi.toggleUserStatus(userId, newStatus)
      
      // Update local state
      setUsers(users.map(user => 
        user.id === userId ? { ...user, status: newStatus } : user
      ))
      
      // Show toast notification
      toast.success(
        newStatus === 'active' ? "User Enabled" : "User Disabled",
        { description: `${user?.email || 'User'} has been ${newStatus === 'active' ? 'enabled' : 'disabled'} successfully.` }
      )
      
      setSuccess(response.message)
      setTimeout(() => setSuccess(null), 3000)
    } catch (err: any) {
      const user = users.find(u => u.id === userId)
      toast.error(
        "Error",
        { description: err.message || `Failed to update status for ${user?.email || 'user'}` }
      )
      setError(err.message || "Failed to update user status")
    } finally {
      setUpdatingUserId(null)
    }
  }

  const activeUsers = users.filter(u => u.status === 'active').length
  const disabledUsers = users.filter(u => u.status === 'disabled').length
  const adminUsers = users.filter(u => u.role === 'admin').length

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <TopNav />

      <main className="flex-1 overflow-auto p-6 lg:p-8">
        <div className="max-w-7xl mx-auto">
          {/* Header */}
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-8"
          >
            <div className="flex items-center gap-3 mb-2">
              <Shield className="w-8 h-8 text-orange-500" />
              <h1 className="text-3xl font-bold text-foreground">Admin Dashboard</h1>
            </div>
            <p className="text-muted-foreground">Manage user accounts and system settings</p>
          </motion.div>

          {/* Alerts */}
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="mb-6"
            >
              <Alert variant="destructive" className="bg-red-500/10 border-red-500/30">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription className="text-red-400">{error}</AlertDescription>
              </Alert>
            </motion.div>
          )}

          {success && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="mb-6"
            >
              <Alert className="bg-green-500/10 border-green-500/30">
                <CheckCircle className="h-4 w-4 text-green-400" />
                <AlertDescription className="text-green-400">{success}</AlertDescription>
              </Alert>
            </motion.div>
          )}

          {/* Stats Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
            >
              <Card className="border-border bg-card border-orange-500/10">
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-medium text-muted-foreground">Total Users</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold text-foreground">{users.length}</div>
                </CardContent>
              </Card>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
            >
              <Card className="border-border bg-card border-orange-500/10">
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-medium text-muted-foreground">Active Users</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold text-green-400">{activeUsers}</div>
                </CardContent>
              </Card>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
            >
              <Card className="border-border bg-card border-orange-500/10">
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-medium text-muted-foreground">Disabled Users</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold text-red-400">{disabledUsers}</div>
                </CardContent>
              </Card>
            </motion.div>
          </div>

          {/* Users Table */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
          >
            <Card className="border-border bg-card border-orange-500/10">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="flex items-center gap-2 text-orange-400">
                      <Users className="w-5 h-5" />
                      User Management
                    </CardTitle>
                    <CardDescription>View and manage all user accounts</CardDescription>
                  </div>
                  <Button
                    onClick={loadUsers}
                    variant="outline"
                    className="border-orange-500/50 text-orange-500 hover:bg-orange-500/10"
                  >
                    Refresh
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                {isLoading ? (
                  <div className="flex items-center justify-center py-12">
                    <Loader2 className="w-8 h-8 animate-spin text-orange-500" />
                  </div>
                ) : users.length === 0 ? (
                  <div className="text-center py-12 text-muted-foreground">
                    No users found
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead>
                        <tr className="border-b border-border">
                          <th className="text-left py-3 px-4 text-sm font-semibold text-muted-foreground">Email</th>
                          <th className="text-left py-3 px-4 text-sm font-semibold text-muted-foreground">Name</th>
                          <th className="text-left py-3 px-4 text-sm font-semibold text-muted-foreground">Role</th>
                          <th className="text-left py-3 px-4 text-sm font-semibold text-muted-foreground">Status</th>
                          <th className="text-left py-3 px-4 text-sm font-semibold text-muted-foreground">Joined</th>
                          <th className="text-left py-3 px-4 text-sm font-semibold text-muted-foreground">Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {users.map((user) => (
                          <tr
                            key={user.id}
                            className="border-b border-border/50 hover:bg-muted/30 transition-colors"
                          >
                            <td className="py-3 px-4 text-sm text-foreground">{user.email}</td>
                            <td className="py-3 px-4 text-sm text-foreground">
                              {user.first_name && user.last_name
                                ? `${user.first_name} ${user.last_name}`
                                : 'N/A'}
                            </td>
                            <td className="py-3 px-4">
                              <span
                                className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                                  user.role === 'admin'
                                    ? 'bg-orange-500/20 text-orange-400 border border-orange-500/30'
                                    : 'bg-muted text-muted-foreground'
                                }`}
                              >
                                {user.role}
                              </span>
                            </td>
                            <td className="py-3 px-4">
                              <span
                                className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                                  user.status === 'active'
                                    ? 'bg-green-500/20 text-green-400 border border-green-500/30'
                                    : 'bg-red-500/20 text-red-400 border border-red-500/30'
                                }`}
                              >
                                {user.status}
                              </span>
                            </td>
                            <td className="py-3 px-4 text-sm text-muted-foreground">
                              {new Date(user.date_joined).toLocaleDateString()}
                            </td>
                            <td className="py-3 px-4">
                              <Button
                                onClick={() => handleToggleStatus(user.id, user.status)}
                                disabled={updatingUserId === user.id}
                                variant="ghost"
                                size="sm"
                                className="text-orange-500 hover:text-orange-400 hover:bg-orange-500/10"
                              >
                                {updatingUserId === user.id ? (
                                  <Loader2 className="w-4 h-4 animate-spin" />
                                ) : user.status === 'active' ? (
                                  <ToggleRight className="w-4 h-4" />
                                ) : (
                                  <ToggleLeft className="w-4 h-4" />
                                )}
                                <span className="ml-2">
                                  {user.status === 'active' ? 'Disable' : 'Enable'}
                                </span>
                              </Button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </CardContent>
            </Card>
          </motion.div>
        </div>
      </main>
    </div>
  )
}

