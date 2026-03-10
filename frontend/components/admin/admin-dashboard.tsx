"use client"

import { useState, useEffect } from "react"
import { motion } from "framer-motion"
import { Users, Shield, ToggleLeft, ToggleRight, Loader2, AlertCircle, CheckCircle, Activity } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { toast } from "sonner"
import TopNav from "@/components/dashboard/top-nav"
import { adminApi, type User, type UserActivity } from "@/lib/api"

export default function AdminDashboard() {
  const [users, setUsers] = useState<User[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [updatingUserId, setUpdatingUserId] = useState<number | null>(null)
  const [selectedUser, setSelectedUser] = useState<User | null>(null)
  const [userActivity, setUserActivity] = useState<UserActivity | null>(null)
  const [isActivityLoading, setIsActivityLoading] = useState(false)
  const [activityError, setActivityError] = useState<string | null>(null)
  const [activityOpen, setActivityOpen] = useState(false)


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

  const handleViewActivity = async (user: User) => {
    setSelectedUser(user)
    setUserActivity(null)
    setActivityError(null)
    setIsActivityLoading(true)
    setActivityOpen(true)
    try {
      const activity = await adminApi.getUserActivity(user.id)
      setUserActivity(activity)
    } catch (err: any) {
      setActivityError(err.message || "Failed to load user activity")
      toast.error("Error loading activity", {
        description: err.message || "Could not load this user's activity.",
      })
    } finally {
      setIsActivityLoading(false)
    }
  }

  const activeUsers = users.filter(u => u.status === 'active').length
  const disabledUsers = users.filter(u => u.status === 'disabled').length
  const adminUsers = users.filter(u => u.role === 'admin').length

  // Derived activity data for popup (last 7 days, versions per app)
  const now = new Date()
  const oneWeekAgo = new Date(now)
  oneWeekAgo.setDate(now.getDate() - 7)

  const recentTestRuns = userActivity
    ? userActivity.test_runs
        .filter(run => new Date(run.started_at) >= oneWeekAgo)
        .sort((a, b) => new Date(b.started_at).getTime() - new Date(a.started_at).getTime())
    : []

  const lastActivityDate = userActivity
    ? recentTestRuns[0]?.started_at ||
      userActivity.test_runs[0]?.started_at ||
      userActivity.applications[0]?.created_at ||
      null
    : null

  const versionsByApp: Record<number, string[]> = {}
  if (userActivity) {
    userActivity.applications.forEach(app => {
      const versions = userActivity.test_runs
        .filter(run => run.application === app.id)
        .map(run => run.version_name)
      versionsByApp[app.id] = Array.from(new Set(versions)).sort()
    })
  }

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
                              <div className="flex flex-col sm:flex-row gap-2">
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
                                <Button
                                  onClick={() => handleViewActivity(user)}
                                  variant="outline"
                                  size="sm"
                                  className="border-orange-500/40 text-orange-500 hover:bg-orange-500/10"
                                >
                                  <Activity className="w-4 h-4 mr-2" />
                                  View Activity
                                </Button>
                              </div>
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

          {/* User Activity Popup */}
          <Dialog
            open={activityOpen && Boolean(selectedUser)}
            onOpenChange={(open) => {
              setActivityOpen(open)
              if (!open) {
                setSelectedUser(null)
                setUserActivity(null)
                setActivityError(null)
              }
            }}
          >
            <DialogContent className="w-[96vw] sm:w-[95vw] sm:max-w-6xl max-h-[90vh] overflow-y-auto rounded-2xl bg-background/95 p-0 shadow-2xl backdrop-blur-xl">
              <div className="w-full">
                <DialogHeader className="px-6 pt-6 pb-4 border-b border-border/60">
                  <DialogTitle className="flex items-center gap-2 text-orange-400 text-lg sm:text-xl">
                    <Activity className="w-5 h-5" />
                    {selectedUser ? `User Activity – ${selectedUser.email}` : "User Activity"}
                  </DialogTitle>
                </DialogHeader>

                <div className="px-6 pb-6">
                  {isActivityLoading ? (
                    <div className="flex items-center justify-center py-8">
                      <Loader2 className="w-6 h-6 animate-spin text-orange-500" />
                    </div>
                  ) : activityError ? (
                    <Alert variant="destructive" className="bg-red-500/10 border-red-500/30 mb-4">
                      <AlertCircle className="h-4 w-4" />
                      <AlertDescription className="text-red-400">
                        {activityError}
                      </AlertDescription>
                    </Alert>
                  ) : userActivity ? (
                    <div className="space-y-6">
                      {/* Summary stats */}
                      <div className="mt-4 rounded-2xl border border-orange-500/40 bg-gradient-to-br from-orange-500/10 via-card/40 to-background p-4">
                        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                          <div>
                            <p className="text-[11px] font-medium tracking-widest text-muted-foreground uppercase mb-1">
                              Applications
                            </p>
                            <p className="text-2xl font-semibold text-foreground">
                              {userActivity.applications.length}
                            </p>
                          </div>
                          <div>
                            <p className="text-[11px] font-medium tracking-widest text-muted-foreground uppercase mb-1">
                              Test Runs (last 7 days)
                            </p>
                            <p className="text-2xl font-semibold text-foreground">
                              {recentTestRuns.length}
                            </p>
                          </div>
                          <div>
                            <p className="text-[11px] font-medium tracking-widest text-muted-foreground uppercase mb-1">
                              Last Activity
                            </p>
                            <p className="text-sm text-muted-foreground">
                              {lastActivityDate
                                ? new Date(lastActivityDate).toLocaleString()
                                : "No activity yet"}
                            </p>
                          </div>
                        </div>
                      </div>

                      <div className="space-y-6">
                        {/* Recent test runs (top) */}
                        <div>
                          <p className="text-[11px] font-medium tracking-widest text-orange-300/80 uppercase mb-1">
                            Recent Test Runs
                          </p>
                          <h3 className="text-sm font-semibold mb-3 text-foreground">
                            Last 7 days
                          </h3>
                          {recentTestRuns.length === 0 ? (
                            <p className="text-sm text-muted-foreground">
                              No tests have been run in the last week.
                            </p>
                          ) : (
                            <div className="space-y-2 max-h-64 overflow-auto pr-2">
                              {recentTestRuns.slice(0, 20).map(run => (
                                <div
                                  key={run.id}
                                  className="border border-border/60 rounded-lg p-3 text-sm"
                                >
                                  <div className="flex items-center justify-between mb-1">
                                    <p className="font-medium text-foreground truncate">
                                      {run.application_name} – {run.test_type} ({run.version_name})
                                    </p>
                                    <span
                                      className={`ml-2 inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium ${
                                        run.status === 'success'
                                          ? 'bg-green-500/15 text-green-400'
                                          : run.status === 'failed'
                                            ? 'bg-red-500/15 text-red-400'
                                            : 'bg-yellow-500/10 text-yellow-400'
                                      }`}
                                    >
                                      {run.status}
                                    </span>
                                  </div>
                                  <p className="text-xs text-muted-foreground">
                                    Started: {new Date(run.started_at).toLocaleString()}
                                  </p>
                                  <p className="text-xs text-muted-foreground mt-0.5">
                                    Pass rate: {run.pass_rate}% &middot; Fail rate: {run.fail_rate}%
                                  </p>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>

                        <div className="h-px bg-gradient-to-r from-transparent via-orange-500/40 to-transparent" />

                        {/* Applications with versions (bottom) */}
                        <div>
                          <p className="text-[11px] font-medium tracking-widest text-orange-300/80 uppercase mb-1">
                            Applications
                          </p>
                          <h3 className="text-sm font-semibold mb-3 text-foreground">
                            Applications &amp; Versions
                          </h3>
                          {userActivity.applications.length === 0 ? (
                            <p className="text-sm text-muted-foreground">
                              No applications created yet.
                            </p>
                          ) : (
                            <div className="space-y-2 max-h-64 overflow-auto pr-2">
                              {userActivity.applications.map(app => {
                                const versions = versionsByApp[app.id] || []
                                return (
                                  <div
                                    key={app.id}
                                    className="border border-border/60 rounded-lg p-3 text-sm bg-card/30"
                                  >
                                    <p className="font-medium text-foreground">
                                      {app.name}
                                    </p>
                                    <p className="text-xs text-muted-foreground truncate">
                                      {app.url}
                                    </p>
                                    <p className="text-xs text-muted-foreground mt-1">
                                      Created: {new Date(app.created_at).toLocaleString()}
                                    </p>
                                    {versions.length > 0 && (
                                      <div className="mt-2">
                                        <p className="text-[11px] font-medium text-muted-foreground mb-1">
                                          Versions:
                                        </p>
                                        <div className="flex flex-wrap gap-1">
                                          {versions.map(v => (
                                            <span
                                              key={v}
                                              className="inline-flex items-center rounded-full border border-border/60 px-2 py-0.5 text-[11px] text-muted-foreground"
                                            >
                                              {v}
                                            </span>
                                          ))}
                                        </div>
                                      </div>
                                    )}
                                  </div>
                                )
                              })}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground">
                      Select a user to view their activity.
                    </p>
                  )}
                </div>
              </div>
            </DialogContent>
          </Dialog>
        </div>
      </main>
    </div>
  )
}

