export interface TestHistory {
  id: string
  appName: string
  versionName: string
  version: number
  status: "success" | "failed" | "running"
  testType: "general" | "functional" | "regression" | "performance" | "accessibility" | "broken_links" | "authentication"
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
  selector?: string
  element_screenshot?: string
  before_screenshot?: string
  after_screenshot?: string
}
