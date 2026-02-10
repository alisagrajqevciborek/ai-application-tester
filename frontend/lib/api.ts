// Always use localhost in the browser (browser can't resolve Docker service names)
// Server-side can use the env variable for internal Docker network calls
const API_BASE_URL = typeof window !== 'undefined' 
  ? 'http://localhost:8000/api'  // Browser/client-side
  : (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api')  // Server-side/SSR

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
async function apiRequest<T>(
  endpoint: string,
  options: ApiRequestOptions = {}
): Promise<T> {
  const token = getAuthToken()

  // Validate endpoint doesn't contain unsubstituted route parameters
  if (endpoint.includes(':') && !endpoint.startsWith(':')) {
    console.error('Invalid endpoint with unsubstituted parameter:', endpoint)
    throw new Error(`Invalid API endpoint: ${endpoint}. Route parameters must be substituted.`)
  }

  const url = `${API_BASE_URL}${endpoint}`

  const { timeout = 60000, ...fetchOptions } = options // Default 60 second timeout (increased from 30s)

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(fetchOptions.headers as Record<string, string> || {}),
  }

  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  // Add timeout to prevent hanging requests
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), timeout)

  try {
    const response = await fetch(url, {
      ...fetchOptions,
      headers,
      signal: controller.signal,
    })

    clearTimeout(timeoutId)

    // Handle 204 No Content
    if (response.status === 204) {
      return {} as T
    }

    // Check if response is JSON
    const contentType = response.headers.get('content-type')
    if (!contentType || !contentType.includes('application/json')) {
      // If not JSON, it's likely an HTML error page
      const text = await response.text()
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
    } catch (error) {
      throw new Error('Failed to parse response as JSON. The server may be returning an error page.')
    }

    if (!response.ok) {
      // Handle validation errors
      if (data.email || data.password || data.code) {
        const errorMessages = Object.entries(data)
          .map(([key, value]) => {
            if (Array.isArray(value)) {
              return `${key}: ${value.join(', ')}`
            }
            return `${key}: ${value}`
          })
          .join('\n')
        throw new Error(errorMessages)
      }
      throw new Error(data.error || data.message || data.detail || 'An error occurred')
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
    const response = await apiRequest<{
      results?: Application[]
      count?: number
      next?: string | null
      previous?: string | null
    }>('/applications/')

    // Handle paginated response
    if (response.results) {
      return response.results
    }
    // Handle non-paginated response
    return response as unknown as Application[]
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
  async list(): Promise<TestRun[]> {
    const response = await apiRequest<{
      results?: TestRun[]
      count?: number
      next?: string | null
      previous?: string | null
    }>('/applications/test-runs/')

    // Handle paginated response
    if (response.results) {
      return response.results
    }
    // Handle non-paginated response
    return response as unknown as TestRun[]
  },

  async get(id: number): Promise<TestRun> {
    return apiRequest<TestRun>(`/applications/test-runs/${id}/`)
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
  created_at?: string
  updated_at?: string
}

// Test Case Generator API
export const testCaseApi = {
  async generate(prompt: string, applicationId: number, testType: string = 'functional'): Promise<GeneratedTestCase> {
    return apiRequest<GeneratedTestCase>('/applications/test-cases/generate', {
      method: 'POST',
      body: JSON.stringify({
        prompt,
        application_id: applicationId,
        test_type: testType,
      }),
    })
  },

  async refine(testCase: GeneratedTestCase, refinementPrompt: string): Promise<GeneratedTestCase> {
    return apiRequest<GeneratedTestCase>('/applications/test-cases/refine', {
      method: 'POST',
      body: JSON.stringify({
        test_case: testCase,
        refinement_prompt: refinementPrompt,
      }),
    })
  },

  async save(applicationId: number, testCase: GeneratedTestCase): Promise<GeneratedTestCase> {
    return apiRequest<GeneratedTestCase>('/applications/test-cases/save', {
      method: 'POST',
      body: JSON.stringify({
        application_id: applicationId,
        test_case: testCase,
      }),
    })
  },

  async list(applicationId: number): Promise<GeneratedTestCase[]> {
    return apiRequest<GeneratedTestCase[]>(`/applications/${applicationId}/test-cases`)
  },

  async delete(testCaseId: number): Promise<void> {
    return apiRequest<void>(`/applications/test-cases/${testCaseId}`, {
      method: 'DELETE',
    })
  },

  async run(testCaseId: number): Promise<TestRun> {
    return apiRequest<TestRun>(`/applications/test-cases/${testCaseId}/run`, {
      method: 'POST',
    })
  },
}
