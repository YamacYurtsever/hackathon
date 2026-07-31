import { createContext, use } from 'react'

import type { Profile } from '@/types/ir'

export interface AuthValue {
  profile: Profile | null
  loading: boolean
  setProfile: (profile: Profile | null) => void
}

export const AuthContext = createContext<AuthValue | null>(null)

export function useAuth(): AuthValue {
  const value = use(AuthContext)
  if (value === null) {
    throw new Error('useAuth must be used inside <AuthProvider>')
  }
  return value
}
