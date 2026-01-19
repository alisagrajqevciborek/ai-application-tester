"use client"

import { LogOut } from "lucide-react"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
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

export default function TopNav() {
  const { user, logout } = useAuth()
  
  const getInitials = () => {
    if (!user) return "U"
    const first = user.first_name?.[0] || ""
    const last = user.last_name?.[0] || ""
    return (first + last).toUpperCase() || user.email[0].toUpperCase()
  }

  const handleLogout = async () => {
    await logout()
  }

  return (
    <header className="h-16 border-b border-border/50 bg-card/50 backdrop-blur-sm sticky top-0 z-50">
      <div className="flex items-center justify-between h-full px-4 lg:px-6">
        <span className="font-bold text-lg text-foreground">TestFlow AI</span>

        {/* User Profile */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="relative h-10 w-10 rounded-full hover:bg-orange-600/10">
              <Avatar className="h-10 w-10 border-2 border-border">
                <AvatarImage src="/professional-avatar.png" alt="User" />
                <AvatarFallback className="bg-secondary text-secondary-foreground">{getInitials()}</AvatarFallback>
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
