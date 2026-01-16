export interface TestHistory {
  id: string
  appName: string
  status: "success" | "failed" | "running"
  testType: "functional" | "regression" | "performance" | "accessibility"
  date: string
  passRate: number
  failRate: number
}

export interface TestIssue {
  id: string
  title: string
  severity: "critical" | "major" | "minor"
  description: string
  screenshot: string
  location: string
}
