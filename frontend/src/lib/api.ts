import type { Profile } from '@/types/ir'

// Same host as the frontend (localhost) so the session cookie is same-site.
const BASE_URL = 'http://localhost:5001/api'

class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    // Session cookie rides along on every call.
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })

  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new ApiError(response.status, body.error ?? 'Something went wrong')
  }

  return response.status === 204 ? (undefined as T) : response.json()
}

export const api = {
  signup: (username: string, password: string) =>
    request<Profile>('/signup', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    }),

  login: (username: string, password: string) =>
    request<Profile>('/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    }),

  logout: () => request<void>('/logout', { method: 'POST' }),

  me: () => request<Profile>('/me'),

  getProfile: (id: string) => request<Profile>(`/profiles/${id}`),

  updateOwnProfile: (content: Record<string, unknown>) =>
    request<Profile>('/profiles/me', {
      method: 'PUT',
      body: JSON.stringify({ content }),
    }),
}
