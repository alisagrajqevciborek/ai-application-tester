// Base URL for the backend API.
// In production, this is provided via NEXT_PUBLIC_API_URL (e.g. your Render URL).
// For local development, it falls back to localhost:8000.
const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api'

// Types
export interface User {
  id: number
  email: string
  first_name: string
  last_name: string
  date_joined: string
  status: 'active' | 'disabled'
  role: 'user' | 'admin'
}

export interface Application {
  id: number
  name: string
  url: string
  owner: number
  owner_email: string
  test_username?: string
  test_password?: string
  login_url?: string
  created_at: string
  updated_at: string
}

export interface TestRunStepResult {
  id: number
  step_key: string
  step_label: string
  status: 'pending' | 'running' | 'success' | 'failed'
  pass_rate: number
  fail_rate: number
  error_message: string
  started_at: string | null
  completed_at: string | null
  details_json: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface TestRun {
  id: number
  application: number
  application_name: string
  application_url: string
  test_type: 'general' | 'functional' | 'regression' | 'performance' | 'accessibility' | 'broken_links' | 'authentication'
  status: 'pending' | 'running' | 'success' | 'failed'
  pass_rate: number
  fail_rate: number
  check_broken_links: boolean
  check_auth: boolean
  started_at: string
  completed_at: string | null
  version: number
  version_name: string
  step_results?: TestRunStepResult[]
}

export interface Report {
  id: number
  test_run_id: number
  application_name: string
  application_url: string
  test_type: string
  status: string
  pass_rate: number
  fail_rate: number
  started_at: string
  completed_at: string | null
  summary: string
  detailed_report: string
  issues_json: Array<{
    severity: 'critical' | 'major' | 'minor'
    title: string
    description: string
    location: string
    selector?: string
    element_screenshot?: string
    before_screenshot?: string
    after_screenshot?: string
  }>
  console_logs_json?: Array<{
    type: string
    text: string
    location?: string
  }>
  screenshots: string[]
  artifacts?: Array<{
    id: number
    kind: string
    url: string
    step_name?: string
    created_at?: string
  }>
  created_at: string
}

export interface TestRunStats {
  total: number
  success: number
  failed: number
  running: number
  pending: number
  average_pass_rate: number
  average_fail_rate: number
}

export interface LoginResponse {
  user: User
  access: string
  refresh: string
}

export interface ApiError {
  error?: string
  message?: string
  [key: string]: any
}

function getDefaultStatusMessage(status: number): string {
  if (status === 400) return 'Invalid request. Please check your input and try again.'
  if (status === 401) return 'Session expired. Please log in again.'
  if (status === 403) return 'You do not have permission to perform this action.'
  if (status === 404) return 'Requested resource was not found.'
  if (status >= 500) return 'Server error. Please try again later.'
  return 'An error occurred'
}

function buildErrorMessageFromData(data: unknown, status: number): string {
  if (!data) {
    return getDefaultStatusMessage(status)
  }

  if (typeof data === 'string') {
    const trimmed = data.trim()
    return trimmed || getDefaultStatusMessage(status)
  }

  if (Array.isArray(data)) {
    const items = data.map((item) => String(item)).filter(Boolean)
    return items.length > 0 ? items.join('\n') : getDefaultStatusMessage(status)
  }

  if (typeof data === 'object') {
    const record = data as Record<string, unknown>

    const directMessage = [record.error, record.message, record.detail]
      .find((value) => typeof value === 'string' && value.trim().length > 0)

    if (typeof directMessage === 'string' && directMessage.trim()) {
      return directMessage.trim()
    }

    const entries = Object.entries(record)
      .filter(([, value]) => value !== null && value !== undefined)
      .map(([key, value]) => {
        if (Array.isArray(value)) {
          return `${key}: ${value.map((item) => String(item)).join(', ')}`
        }
        if (typeof value === 'object') {
          return `${key}: ${JSON.stringify(value)}`
        }
        return `${key}: ${String(value)}`
      })

    if (entries.length > 0) {
      return entries.join('\n')
    }
  }

  return getDefaultStatusMessage(status)
}

// Helper function to get auth token from localStorage
function getAuthToken(): string | null {
  if (typeof window === 'undefined') return null
  return localStorage.getItem('access_token')
}

// Helper function to get refresh token from localStorage
function getRefreshToken(): string | null {
  if (typeof window === 'undefined') return null
  return localStorage.getItem('refresh_token')
}

// ---------------------------------------------------------------------------
// Token auto-refresh queue
// Multiple concurrent requests hitting 401 at the same time will all queue
// up behind a single refresh attempt, then retry with the new token.
// ---------------------------------------------------------------------------
let isRefreshingToken = false
let tokenRefreshSubscribers: Array<(token: string | null) => void> = []

function addRefreshSubscriber(cb: (token: string | null) => void) {
  tokenRefreshSubscribers.push(cb)
}

function notifyRefreshSubscribers(token: string | null) {
  tokenRefreshSubscribers.forEach(cb => cb(token))
  tokenRefreshSubscribers = []
}

async function doTokenRefresh(): Promise<string | null> {
  const refresh = getRefreshToken()
  if (!refresh) { clearTokens(); return null }

  try {
    const res = await fetch(`${API_BASE_URL}/auth/refresh/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh }),
    })
    if (!res.ok) { clearTokens(); return null }
    const data = await res.json()
    saveTokens(data.access, refresh)
    return data.access as string
  } catch {
    clearTokens()
    return null
  }
}

async function ensureTokenRefreshed(): Promise<string | null> {
  if (!isRefreshingToken) {
    isRefreshingToken = true
    const newToken = await doTokenRefresh()
    isRefreshingToken = false
    notifyRefreshSubscribers(newToken)
    return newToken
  }
  // Another request is already refreshing — wait for it to finish
  return new Promise<string | null>(resolve => addRefreshSubscriber(resolve))
}

function isAuthEndpoint(endpoint: string): boolean {
  return (
    endpoint.includes('/auth/login') ||
    endpoint.includes('/auth/refresh') ||
    endpoint.includes('/auth/register') ||
    endpoint.includes('/auth/logout')
  )
}

// Helper function to save tokens
export function saveTokens(access: string, refresh: string): void {
  if (typeof window === 'undefined') return
  localStorage.setItem('access_token', access)
  localStorage.setItem('refresh_token', refresh)
}

// Helper function to clear tokens
export function clearTokens(): void {
  if (typeof window === 'undefined') return
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  localStorage.removeItem('user')
}

// Helper function to save user
export function saveUser(user: User): void {
  if (typeof window === 'undefined') return
  localStorage.setItem('user', JSON.stringify(user))
}

// Helper function to get user
export function getUser(): User | null {
  if (typeof window === 'undefined') return null
  const userStr = localStorage.getItem('user')
  if (!userStr) return null
  try {
    return JSON.parse(userStr)
  } catch {
    return null
  }
}

// Extended options for API requests
interface ApiRequestOptions extends RequestInit {
  timeout?: number // Custom timeout in milliseconds
}

// Generic API request function
// _isRetry is an internal flag — prevents infinite refresh loops on a single call
async function apiRequest<T>(
  endpoint: string,
  options: ApiRequestOptions = {},
  _isRetry = false
): Promise<T> {
  const token = getAuthToken()

  // Validate endpoint doesn't contain unsubstituted route parameters
  if (endpoint.includes(':') && !endpoint.startsWith(':')) {
    console.error('Invalid endpoint with unsubstituted parameter:', endpoint)
    throw new Error(`Invalid API endpoint: ${endpoint}. Route parameters must be substituted.`)
  }

  const url = `${API_BASE_URL}${endpoint}`

  const { timeout = 15000, ...fetchOptions } = options

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(fetchOptions.headers as Record<string, string> || {}),
  }

  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), timeout)

  try {
    const response = await fetch(url, {
      ...fetchOptions,
      headers,
      signal: controller.signal,
    })

    clearTimeout(timeoutId)

    // --- Token auto-refresh on 401 ---
    if (response.status === 401 && !_isRetry && !isAuthEndpoint(endpoint)) {
      const newToken = await ensureTokenRefreshed()
      if (newToken) {
        // Retry the original request once with the fresh token
        return apiRequest<T>(endpoint, options, true)
      }
      // Refresh failed — notify the app so it can redirect to login
      if (typeof window !== 'undefined') {
        window.dispatchEvent(new Event('auth:logout'))
      }
      throw new Error('Session expired. Please log in again.')
    }

    // Handle 204 No Content
    if (response.status === 204) {
      return {} as T
    }

    // Check if response is JSON
    const contentType = response.headers.get('content-type')
    const isJson = Boolean(contentType && (contentType.includes('application/json') || contentType.includes('+json')))

    if (!isJson) {
      const textBody = await response.text().catch(() => '')

      if (!response.ok) {
        throw new Error(textBody.trim() || getDefaultStatusMessage(response.status))
      }

      throw new Error(
        response.status === 404
          ? 'API endpoint not found. Please check if the backend server is running.'
          : response.status >= 500
            ? 'Server error. Please try again later.'
            : `Unexpected response format. Status: ${response.status}`
      )
    }

    let data
    try {
      data = await response.json()
    } catch {
      if (!response.ok) {
        throw new Error(getDefaultStatusMessage(response.status))
      }
      throw new Error('Failed to parse response as JSON. The server may be returning an error page.')
    }

    if (!response.ok) {
      throw new Error(buildErrorMessageFromData(data, response.status))
    }

    return data
  } catch (error) {
    clearTimeout(timeoutId)
    if (error instanceof Error && error.name === 'AbortError') {
      throw new Error('Request timeout. The operation is taking longer than expected. Please wait and try again.')
    }
    throw error
  }
}

// ---------------------------------------------------------------------------
// Pagination helper — fetches ALL pages for list endpoints that paginate
// Optimized to fetch pages in parallel for better performance
// ---------------------------------------------------------------------------
async function fetchAllPages<T>(endpoint: string): Promise<T[]> {
  // Fetch first page to get total count
  const firstResponse = await apiRequest<{
    results: T[]
    next: string | null
    count: number
  } | T[]>(endpoint)

  if (Array.isArray(firstResponse)) {
    // Non-paginated response — return as-is
    return firstResponse
  }

  const all: T[] = [...firstResponse.results]
  
  // If there's no next page, return what we have
  if (!firstResponse.next) {
    return all
  }

  // Calculate how many pages we need to fetch
  const pageSize = firstResponse.results.length
  const totalPages = Math.ceil(firstResponse.count / pageSize)
  
  // Fetch remaining pages in parallel (limit to 5 concurrent requests)
  const pagePromises: Promise<T[]>[] = []
  for (let page = 2; page <= totalPages; page++) {
    const pageEndpoint = `${endpoint}${endpoint.includes('?') ? '&' : '?'}page=${page}`
    pagePromises.push(
      apiRequest<{ results: T[] }>(pageEndpoint).then(response => response.results)
    )
  }

  // Wait for all pages (in batches of 5 to avoid overwhelming the server)
  const batchSize = 5
  for (let i = 0; i < pagePromises.length; i += batchSize) {
    const batch = pagePromises.slice(i, i + batchSize)
    const results = await Promise.all(batch)
    results.forEach(pageResults => all.push(...pageResults))
  }

  return all
}

// Auth API
export const authApi = {
  async register(email: string, password: string, passwordConfirm: string, firstName: string, lastName: string): Promise<{ message: string; email: string }> {
    return apiRequest<{ message: string; email: string }>('/auth/register/', {
      method: 'POST',
      body: JSON.stringify({
        email,
        password,
        password_confirm: passwordConfirm,
        first_name: firstName,
        last_name: lastName
      }),
    })
  },

  async verifyEmail(email: string, code: string): Promise<LoginResponse> {
    const response = await apiRequest<LoginResponse>('/auth/verify-email/', {
      method: 'POST',
      body: JSON.stringify({ email, code }),
    })
    return response
  },

  async resendCode(email: string): Promise<{ message: string }> {
    return apiRequest<{ message: string }>('/auth/resend-code/', {
      method: 'POST',
      body: JSON.stringify({ email }),
    })
  },

  async login(email: string, password: string): Promise<LoginResponse> {
    const response = await apiRequest<LoginResponse>('/auth/login/', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    })
    return response
  },

  async logout(): Promise<void> {
    const refresh = getRefreshToken()
    if (refresh) {
      try {
        await apiRequest('/auth/logout/', {
          method: 'POST',
          body: JSON.stringify({ refresh }),
        })
      } catch (error) {
        // Continue with logout even if API call fails
        console.error('Logout error:', error)
      }
    }
    clearTokens()
  },

  async getMe(): Promise<User> {
    return apiRequest<User>('/auth/me/')
  },

  async updateProfile(firstName: string, lastName: string, email: string): Promise<{ message: string; user: User }> {
    return apiRequest<{ message: string; user: User }>('/auth/me/', {
      method: 'PUT',
      body: JSON.stringify({
        first_name: firstName,
        last_name: lastName,
        email: email,
      }),
    })
  },

  async changePassword(oldPassword: string, newPassword: string, newPasswordConfirm: string): Promise<{ message: string }> {
    return apiRequest<{ message: string }>('/auth/change-password/', {
      method: 'POST',
      body: JSON.stringify({
        old_password: oldPassword,
        new_password: newPassword,
        new_password_confirm: newPasswordConfirm,
      }),
    })
  },

  async refreshToken(refresh: string): Promise<{ access: string }> {
    return apiRequest<{ access: string }>('/auth/refresh/', {
      method: 'POST',
      body: JSON.stringify({ refresh }),
    })
  },
}

// Admin API
export const adminApi = {
  async listUsers(): Promise<{ users: User[]; count: number }> {
    return apiRequest<{ users: User[]; count: number }>('/admin/users')
  },

  async toggleUserStatus(userId: number, status: 'active' | 'disabled'): Promise<{ message: string; user: User }> {
    return apiRequest<{ message: string; user: User }>(`/admin/users/${userId}/toggle-status`, {
      method: 'PUT',
      body: JSON.stringify({ status }),
    })
  },
}

// Applications API
export const applicationsApi = {
  async list(): Promise<Application[]> {
    return fetchAllPages<Application>('/applications/')
  },

  async get(id: number): Promise<Application> {
    if (!id || isNaN(id)) {
      throw new Error('Invalid application ID')
    }
    return apiRequest<Application>(`/applications/${id}`)
  },

  async create(name: string, url: string, authData?: { test_username?: string; test_password?: string; login_url?: string }): Promise<Application> {
    // Validate inputs
    if (!name || !name.trim()) {
      throw new Error('Application name is required')
    }
    if (!url || !url.trim()) {
      throw new Error('Application URL is required')
    }

    // Ensure URL has protocol
    let normalizedUrl = url.trim()
    if (!normalizedUrl.startsWith('http://') && !normalizedUrl.startsWith('https://')) {
      normalizedUrl = `https://${normalizedUrl}`
    }

    return apiRequest<Application>('/applications/', {
      method: 'POST',
      body: JSON.stringify({
        name: name.trim(),
        url: normalizedUrl,
        ...authData
      }),
    })
  },

  async update(id: number, name: string, url: string): Promise<Application> {
    return apiRequest<Application>(`/applications/${id}`, {
      method: 'PUT',
      body: JSON.stringify({ name, url }),
    })
  },

  async delete(id: number): Promise<void> {
    return apiRequest<void>(`/applications/${id}`, {
      method: 'DELETE',
    })
  },
}

// Test Runs API
export const testRunsApi = {
  async list(options?: { includeSteps?: boolean; pageSize?: number }): Promise<TestRun[]> {
    const includeSteps = options?.includeSteps ?? true
    const pageSize = options?.pageSize ?? 100
    const query = `?include_steps=${includeSteps ? 'true' : 'false'}&page_size=${pageSize}`
    return fetchAllPages<TestRun>(`/applications/test-runs/${query}`)
  },

  async listActive(): Promise<TestRun[]> {
    return apiRequest<TestRun[]>('/applications/test-runs/active/')
  },

  async get(id: number): Promise<TestRun> {
    return apiRequest<TestRun>(`/applications/test-runs/${id}/`)
  },

  async getStatus(id: number): Promise<{
    id: number
    status: 'pending' | 'running' | 'success' | 'failed'
    started_at: string
    completed_at: string | null
    pass_rate: number
    fail_rate: number
    steps: Array<{
      step_key: string
      step_label: string
      status: 'pending' | 'running' | 'success' | 'failed'
    }>
  }> {
    return apiRequest(`/applications/test-runs/${id}/status/`)
  },

  async create(applicationId: number, testType: string, options?: { check_broken_links?: boolean; check_auth?: boolean }): Promise<TestRun> {
    return apiRequest<TestRun>('/applications/test-runs/', {
      method: 'POST',
      body: JSON.stringify({
        application: applicationId,
        test_type: testType,
        ...options
      }),
    })
  },

  async delete(id: number): Promise<void> {
    return apiRequest<void>(`/applications/test-runs/${id}/`, {
      method: 'DELETE',
    })
  },

  async stats(): Promise<TestRunStats> {
    return apiRequest<TestRunStats>('/applications/test-runs/stats/')
  },
}

// Reports API
export const reportsApi = {
  async get(testRunId: number): Promise<Report> {
    return apiRequest<Report>(`/reports/${testRunId}/`)
  },

  async exportToJira(testRunId: number): Promise<{
    message: string
    error_ticket?: { key: string; url: string }
    warning_ticket?: { key: string; url: string }
    errors_exported?: number
    warnings_exported?: number
    error?: string
  }> {
    return apiRequest<{
      message: string
      error_ticket?: { key: string; url: string }
      warning_ticket?: { key: string; url: string }
      errors_exported?: number
      warnings_exported?: number
      error?: string
    }>(`/reports/${testRunId}/jira-export/`, {
      method: 'POST',
    })
  },
}

// Generated Test Case Types
export interface TestCaseStep {
  order: number
  action: string
  selector: string | null
  value: string | null
  description: string
  expected_result: string
}

export interface GeneratedTestCase {
  id?: number
  application?: number
  application_name?: string
  application_url?: string
  name: string
  description: string
  test_type: string
  steps: TestCaseStep[]
  expected_results: string
  tags: string[]
  estimated_duration: string
  is_ai_generated?: boolean
  fallback?: boolean
  // Optional script generation fields (when requested)
  script_framework?: 'playwright' | 'selenium' | 'cypress'
  script_code?: string
  created_at?: string
  updated_at?: string
}

// Test Case Generator API
export const testCaseApi = {
  async generate(
    prompt: string,
    applicationId: number,
    testType: string = 'functional',
    scriptFramework?: 'playwright' | 'selenium' | 'cypress'
  ): Promise<GeneratedTestCase> {
    return apiRequest<GeneratedTestCase>('/applications/test-cases/generate/', {
      method: 'POST',
      body: JSON.stringify({
        prompt,
        application_id: applicationId,
        test_type: testType,
        ...(scriptFramework ? { script_framework: scriptFramework } : {}),
      }),
    })
  },

  async refine(testCase: GeneratedTestCase, refinementPrompt: string): Promise<GeneratedTestCase> {
    return apiRequest<GeneratedTestCase>('/applications/test-cases/refine/', {
      method: 'POST',
      body: JSON.stringify({
        test_case: testCase,
        refinement_prompt: refinementPrompt,
      }),
    })
  },

  async save(applicationId: number, testCase: GeneratedTestCase): Promise<GeneratedTestCase> {
    return apiRequest<GeneratedTestCase>('/applications/test-cases/save/', {
      method: 'POST',
      body: JSON.stringify({
        application_id: applicationId,
        test_case: testCase,
      }),
    })
  },

  async list(applicationId: number): Promise<GeneratedTestCase[]> {
    return apiRequest<GeneratedTestCase[]>(`/applications/${applicationId}/test-cases/`)
  },

  async delete(testCaseId: number): Promise<void> {
    return apiRequest<void>(`/applications/test-cases/${testCaseId}/`, {
      method: 'DELETE',
    })
  },

  async run(testCaseId: number): Promise<TestRun> {
    return apiRequest<TestRun>(`/applications/test-cases/${testCaseId}/run/`, {
      method: 'POST',
    })
  },
}
