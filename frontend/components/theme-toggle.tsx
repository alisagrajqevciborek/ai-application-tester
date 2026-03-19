'use client'

import * as React from 'react'
import { Moon, Sun } from 'lucide-react'
import { useTheme } from 'next-themes'

import { Button } from '@/components/ui/button'

export default function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme()
  const [mounted, setMounted] = React.useState(false)
  const isLightMode = resolvedTheme === 'light'

  React.useEffect(() => {
    setMounted(true)
  }, [])

  const toggleTheme = React.useCallback(() => {
    setTheme(isLightMode ? 'dark' : 'light')
  }, [isLightMode, setTheme])

  if (!mounted) {
    return (
      <Button
        type="button"
        variant="outline"
        size="icon"
        className="fixed right-4 bottom-4 z-50 rounded-full shadow-lg"
        aria-label="Toggle theme"
        title="Toggle theme"
      >
        <Sun className="size-4" />
      </Button>
    )
  }

  return (
    <Button
      type="button"
      variant="outline"
      size="icon"
      onClick={toggleTheme}
      className="fixed right-4 bottom-4 z-50 rounded-full shadow-lg"
      aria-label={isLightMode ? 'Switch to dark mode' : 'Switch to light mode'}
      title={isLightMode ? 'Switch to dark mode' : 'Switch to light mode'}
    >
      {isLightMode ? <Moon className="size-4" /> : <Sun className="size-4" />}
    </Button>
  )
}
