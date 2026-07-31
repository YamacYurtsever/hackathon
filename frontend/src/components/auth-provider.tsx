import { useEffect, useState } from 'react'

import { api } from '@/lib/api'
import { AuthContext } from '@/lib/auth-context'
import type { Profile } from '@/types/ir'

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [profile, setProfile] = useState<Profile | null>(null)
  const [loading, setLoading] = useState(true)

  // Restore the session on load — the cookie outlives a page refresh.
  useEffect(() => {
    api
      .me()
      .then(setProfile)
      .catch(() => setProfile(null))
      .finally(() => setLoading(false))
  }, [])

  return (
    <AuthContext value={{ profile, loading, setProfile }}>
      {children}
    </AuthContext>
  )
}
