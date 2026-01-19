const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api'

// Types
export interface User {
  id: number
  email: string
  first_name: string
  last_name: string
  date_joined: string
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

  const data = await response.json()

  if (!response.ok) {
    throw new Error(data.error || data.message || 'An error occurred')
  }

  return data
}

// Auth API
export const authApi = {
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
    return apiRequest<Application>(`/applications/${id}`)
  },

  async create(name: string, url: string): Promise<Application> {
    return apiRequest<Application>('/applications/', {
      method: 'POST',
      body: JSON.stringify({ name, url }),
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
}

