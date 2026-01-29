"use client"

import type React from "react"
import { useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { Eye, EyeOff, Mail, Lock, User, Zap, Loader2, AlertCircle, ArrowLeft, CheckCircle } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { useAuth } from "@/contexts/AuthContext"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { authApi, saveTokens, saveUser } from "@/lib/api"

interface RegisterPageProps {
  onBack: () => void
  onRegisterComplete: () => void
}

type Step = "register" | "verify"

export default function RegisterPage({ onBack, onRegisterComplete }: RegisterPageProps) {
  const [step, setStep] = useState<Step>("register")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [passwordConfirm, setPasswordConfirm] = useState("")
  const [firstName, setFirstName] = useState("")
  const [lastName, setLastName] = useState("")
  const [verificationCode, setVerificationCode] = useState("")
  const [showPassword, setShowPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  const { refreshUser } = useAuth()

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setSuccess(null)

    if (password !== passwordConfirm) {
      setError("Passwords do not match")
      return
    }

    if (password.length < 8) {
      setError("Password must be at least 8 characters long")
      return
    }

    setIsLoading(true)

    try {
      const response = await authApi.register(email, password, passwordConfirm, firstName, lastName)
      setSuccess(response.message)
      setStep("verify")
    } catch (err: any) {
      setError(err.message || "Registration failed. Please try again.")
    } finally {
      setIsLoading(false)
    }
  }

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setSuccess(null)

    if (verificationCode.length !== 6) {
      setError("Please enter a 6-digit verification code")
      return
    }

    setIsLoading(true)

    try {
      const response = await authApi.verifyEmail(email, verificationCode)
      // Save tokens and user
      saveTokens(response.access, response.refresh)
      saveUser(response.user)
      // Update auth context
      await refreshUser()
      onRegisterComplete()
    } catch (err: any) {
      setError(err.message || "Invalid verification code. Please try again.")
    } finally {
      setIsLoading(false)
    }
  }

  const handleResendCode = async () => {
    setError(null)
    setIsLoading(true)

    try {
      const response = await authApi.resendCode(email)
      setSuccess(response.message)
    } catch (err: any) {
      setError(err.message || "Failed to resend code. Please try again.")
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#0a1628]">
      <motion.div
        initial={{ opacity: 0, y: 20, scale: 0.95 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.5, ease: "easeOut" }}
        className="relative z-10 w-full max-w-md mx-4"
      >
        <div className="rounded-2xl p-8 shadow-2xl bg-[#0f1e36] border border-white/10">
          {/* Logo and Title */}
          <div className="text-center mb-8">
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="mb-2"
            >
              <span className="font-bold text-4xl tracking-tight text-foreground">TestFlow</span>
            </motion.div>
            <p className="text-muted-foreground mt-2">
              {step === "register" ? "Create your account" : "Verify your email"}
            </p>
          </div>

          <AnimatePresence mode="wait">
            {step === "register" ? (
              <motion.form
                key="register"
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
                onSubmit={handleRegister}
                className="space-y-6"
              >
                {error && (
                  <Alert variant="destructive" className="bg-red-500/10 border-red-500/30">
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription className="text-red-400">{error}</AlertDescription>
                  </Alert>
                )}

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="firstName" className="text-foreground/80">
                      First Name
                    </Label>
                    <div className="relative">
                      <User className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
                      <Input
                        id="firstName"
                        type="text"
                        placeholder="John"
                        value={firstName}
                        onChange={(e) => setFirstName(e.target.value)}
                        className="pl-10 bg-[#162442] border-white/10 focus:border-primary h-12 rounded-xl"
                        required
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="lastName" className="text-foreground/80">
                      Last Name
                    </Label>
                    <div className="relative">
                      <User className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
                      <Input
                        id="lastName"
                        type="text"
                        placeholder="Doe"
                        value={lastName}
                        onChange={(e) => setLastName(e.target.value)}
                        className="pl-10 bg-[#162442] border-white/10 focus:border-primary h-12 rounded-xl"
                        required
                      />
                    </div>
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="email" className="text-foreground/80">
                    Email
                  </Label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
                    <Input
                      id="email"
                      type="email"
                      placeholder="you@company.com"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      className="pl-10 bg-[#162442] border-white/10 focus:border-primary h-12 rounded-xl"
                      required
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="password" className="text-foreground/80">
                    Password
                  </Label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
                    <Input
                      id="password"
                      type={showPassword ? "text" : "password"}
                      placeholder="••••••••"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      className="pl-10 pr-10 bg-[#162442] border-white/10 focus:border-primary h-12 rounded-xl"
                      required
                      minLength={8}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                    >
                      {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                    </button>
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="passwordConfirm" className="text-foreground/80">
                    Confirm Password
                  </Label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
                    <Input
                      id="passwordConfirm"
                      type={showPassword ? "text" : "password"}
                      placeholder="••••••••"
                      value={passwordConfirm}
                      onChange={(e) => setPasswordConfirm(e.target.value)}
                      className="pl-10 bg-[#162442] border-white/10 focus:border-primary h-12 rounded-xl"
                      required
                      minLength={8}
                    />
                  </div>
                </div>

                <Button
                  type="submit"
                  className="w-full h-12 rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 font-semibold text-base transition-all duration-200"
                  disabled={isLoading}
                >
                  {isLoading ? (
                    <span className="flex items-center gap-2">
                      <Loader2 className="w-5 h-5 animate-spin" />
                      Creating account...
                    </span>
                  ) : (
                    "Create Account"
                  )}
                </Button>

                <p className="text-center text-muted-foreground text-sm">
                  Already have an account?{" "}
                  <button type="button" onClick={onBack} className="text-primary hover:underline font-medium">
                    Sign in
                  </button>
                </p>
              </motion.form>
            ) : (
              <motion.form
                key="verify"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                onSubmit={handleVerify}
                className="space-y-6"
              >
                {error && (
                  <Alert variant="destructive" className="bg-red-500/10 border-red-500/30">
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription className="text-red-400">{error}</AlertDescription>
                  </Alert>
                )}

                {success && (
                  <Alert className="bg-green-500/10 border-green-500/30">
                    <CheckCircle className="h-4 w-4 text-green-400" />
                    <AlertDescription className="text-green-400">{success}</AlertDescription>
                  </Alert>
                )}

                <div className="text-center mb-6">
                  <p className="text-foreground mb-2">We've sent a verification code to</p>
                  <p className="text-primary font-semibold">{email}</p>
                  <p className="text-muted-foreground text-sm mt-2">Please enter the 6-digit code below</p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="code" className="text-foreground/80">
                    Verification Code
                  </Label>
                  <Input
                    id="code"
                    type="text"
                    placeholder="000000"
                    value={verificationCode}
                    onChange={(e) => setVerificationCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                    className="bg-[#162442] border-white/10 focus:border-primary h-14 rounded-xl text-center text-2xl font-mono tracking-widest"
                    required
                    maxLength={6}
                  />
                </div>

                <Button
                  type="submit"
                  className="w-full h-12 rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 font-semibold text-base transition-all duration-200"
                  disabled={isLoading || verificationCode.length !== 6}
                >
                  {isLoading ? (
                    <span className="flex items-center gap-2">
                      <Loader2 className="w-5 h-5 animate-spin" />
                      Verifying...
                    </span>
                  ) : (
                    "Verify Email"
                  )}
                </Button>

                <div className="text-center space-y-2">
                  <button
                    type="button"
                    onClick={handleResendCode}
                    disabled={isLoading}
                    className="text-sm text-muted-foreground hover:text-primary transition-colors"
                  >
                    Didn't receive the code? Resend
                  </button>
                  <p className="text-sm text-muted-foreground">
                    Wrong email?{" "}
                    <button type="button" onClick={() => setStep("register")} className="text-primary hover:underline">
                      Go back
                    </button>
                  </p>
                </div>
              </motion.form>
            )}
          </AnimatePresence>
        </div>
      </motion.div>
    </div>
  )
}

