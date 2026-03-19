"use client"

import { LogOut, User, Settings } from "lucide-react"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { useAuth } from "@/contexts/AuthContext"
import { useRouter } from "next/navigation"

export default function TopNav() {
  const { user, logout } = useAuth()
  const router = useRouter()

  const getInitials = () => {
    if (!user) return "U"
    const first = user.first_name?.[0] || ""
    const last = user.last_name?.[0] || ""
    return (first + last).toUpperCase() || user.email[0].toUpperCase()
  }

  const handleLogout = async () => {
    await logout()
    router.push('/login')
  }

  const handleProfileClick = () => {
    router.push('/profile')
  }

  return (
    <header className="h-16 border-b border-border/50 bg-card/50 backdrop-blur-sm sticky top-0 z-50">
      <div className="flex items-center justify-between h-full px-4 lg:px-6">
        <div className="ml-5 lg:ml-8 flex items-center gap-4 group cursor-pointer transition-all hover:opacity-90 h-full">
          <span className="brand-wordmark text-[1.45rem] text-foreground/95">
            TestFlow
          </span>
        </div>

        {/* User Profile */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="relative h-10 w-10 rounded-full hover:bg-orange-600/10">
              <Avatar className="h-10 w-10 border-2 border-border">
                <AvatarFallback className="bg-primary/20 text-primary font-semibold">{getInitials()}</AvatarFallback>
              </Avatar>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent className="w-56 bg-popover border-border" align="end">
            <DropdownMenuLabel className="text-foreground">
              <div className="flex flex-col space-y-1">
                <p className="text-sm font-medium">
                  {user?.first_name && user?.last_name
                    ? `${user.first_name} ${user.last_name}`
                    : user?.email || "User"}
                </p>
                <p className="text-xs text-muted-foreground">{user?.email || ""}</p>
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator className="bg-border" />
            <DropdownMenuItem onClick={handleProfileClick} className="cursor-pointer">
              <User className="mr-2 h-4 w-4" />
              <span>Profile & Settings</span>
            </DropdownMenuItem>
            <DropdownMenuSeparator className="bg-border" />
            <DropdownMenuItem onClick={handleLogout} className="text-destructive focus:text-destructive cursor-pointer">
              <LogOut className="mr-2 h-4 w-4" />
              <span>Log out</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  )
}
