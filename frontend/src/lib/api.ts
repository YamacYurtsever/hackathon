import type {
  ChangeRequest,
  IREntry,
  InputResult,
  Member,
  Operation,
  Profile,
  Project,
  Summary,
} from '@/types/ir'

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

  listProjects: () => request<Project[]>('/projects'),

  // Name-only preview for someone following an invite link — they can't see
  // members or IR content until they've joined.
  previewInvite: (id: string) =>
    request<{ id: string; name: string }>(`/projects/${id}/invite`),

  createProject: (name: string) =>
    request<Project>('/projects', {
      method: 'POST',
      body: JSON.stringify({ name }),
    }),

  getProject: (id: string) => request<Project>(`/projects/${id}`),

  joinProject: (id: string) =>
    request<Project>(`/projects/${id}/join`, { method: 'POST' }),

  listMembers: (id: string) => request<Member[]>(`/projects/${id}/members`),

  promoteMember: (id: string, userId: string) =>
    request<Project>(`/projects/${id}/promote`, {
      method: 'POST',
      body: JSON.stringify({ user_id: userId }),
    }),

  exitProject: (id: string) =>
    request<void>(`/projects/${id}/exit`, { method: 'POST' }),

  // One box: a message may propose changes, answer a question, or both.
  sendInput: (id: string, text: string) =>
    request<InputResult>(`/projects/${id}/input`, {
      method: 'POST',
      body: JSON.stringify({ text }),
    }),

  getView: (id: string) => request<Summary>(`/projects/${id}/view`),

  // encodeURIComponent matters: an unencoded "+00:00" offset arrives as a
  // space and the server sees a different timestamp.
  getChanges: (id: string, since?: string) =>
    request<IREntry[]>(
      `/projects/${id}/changes${since ? `?since=${encodeURIComponent(since)}` : ''}`,
    ),

  listRequests: (id: string) => request<ChangeRequest[]>(`/projects/${id}/requests`),

  // The author submitting for review — the first point anything is stored.
  // Submitting is not merging: each change becomes its own pending request.
  submitChanges: (id: string, text: string, operations: Operation[]) =>
    request<ChangeRequest[]>(`/projects/${id}/requests`, {
      method: 'POST',
      body: JSON.stringify({ text, operations }),
    }),

  editRequest: (id: string, requestId: string, operation: Operation) =>
    request<ChangeRequest>(`/projects/${id}/requests/${requestId}`, {
      method: 'PUT',
      body: JSON.stringify({ operation }),
    }),

  // The only call that changes the IR.
  mergeRequest: (id: string, requestId: string) =>
    request<{ merged: string }>(`/projects/${id}/requests/${requestId}/merge`, {
      method: 'POST',
    }),

  rejectRequest: (id: string, requestId: string) =>
    request<void>(`/projects/${id}/requests/${requestId}/reject`, { method: 'POST' }),
}
