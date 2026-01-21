export interface TestHistory {
  id: string
  appName: string
  versionName: string
  version: number
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
