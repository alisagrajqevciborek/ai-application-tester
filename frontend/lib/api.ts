const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api'

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
  created_at: string
  updated_at: string
}

export interface TestRun {
  id: number
  application: number
  application_name: string
  application_url: string
  test_type: 'functional' | 'regression' | 'performance' | 'accessibility'
  status: 'pending' | 'running' | 'success' | 'failed'
  pass_rate: number
  fail_rate: number
  started_at: string
  completed_at: string | null
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
  }>
  created_at: string
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

// Generic API request function
async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getAuthToken()
  
  // Validate endpoint doesn't contain unsubstituted route parameters
  if (endpoint.includes(':') && !endpoint.startsWith(':')) {
    console.error('Invalid endpoint with unsubstituted parameter:', endpoint)
    throw new Error(`Invalid API endpoint: ${endpoint}. Route parameters must be substituted.`)
  }
  
  const url = `${API_BASE_URL}${endpoint}`

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...options.headers,
  }

  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const response = await fetch(url, {
    ...options,
    headers,
  })

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
}

// Auth API
export const authApi = {
  async register(email: string, password: string, passwordConfirm: string, firstName: string, lastName: string): Promise<{ message: string; email: string }> {
    return apiRequest<{ message: string; email: string }>('/auth/register', {
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
    const response = await apiRequest<LoginResponse>('/auth/verify-email', {
      method: 'POST',
      body: JSON.stringify({ email, code }),
    })
    return response
  },

  async resendCode(email: string): Promise<{ message: string }> {
    return apiRequest<{ message: string }>('/auth/resend-code', {
      method: 'POST',
      body: JSON.stringify({ email }),
    })
  },

  async login(email: string, password: string): Promise<LoginResponse> {
    const response = await apiRequest<LoginResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    })
    return response
  },

  async logout(): Promise<void> {
    const refresh = getRefreshToken()
    if (refresh) {
      try {
        await apiRequest('/auth/logout', {
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
    return apiRequest<User>('/auth/me')
  },

  async updateProfile(firstName: string, lastName: string, email: string): Promise<{ message: string; user: User }> {
    return apiRequest<{ message: string; user: User }>('/auth/me', {
      method: 'PUT',
      body: JSON.stringify({
        first_name: firstName,
        last_name: lastName,
        email: email,
      }),
    })
  },

  async changePassword(oldPassword: string, newPassword: string, newPasswordConfirm: string): Promise<{ message: string }> {
    return apiRequest<{ message: string }>('/auth/change-password', {
      method: 'POST',
      body: JSON.stringify({
        old_password: oldPassword,
        new_password: newPassword,
        new_password_confirm: newPasswordConfirm,
      }),
    })
  },

  async refreshToken(refresh: string): Promise<{ access: string }> {
    return apiRequest<{ access: string }>('/auth/refresh', {
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

  async create(name: string, url: string): Promise<Application> {
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
      body: JSON.stringify({ name: name.trim(), url: normalizedUrl }),
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
    return apiRequest<TestRun>(`/applications/test-runs/${id}`)
  },

  async create(applicationId: number, testType: string): Promise<TestRun> {
    return apiRequest<TestRun>('/applications/test-runs/', {
      method: 'POST',
      body: JSON.stringify({ 
        application: applicationId,
        test_type: testType 
      }),
    })
  },

  async delete(id: number): Promise<void> {
    return apiRequest<void>(`/applications/test-runs/${id}`, {
      method: 'DELETE',
    })
  },
}

// Reports API
export const reportsApi = {
  async get(testRunId: number): Promise<Report> {
    return apiRequest<Report>(`/reports/${testRunId}/`)
  },
}

