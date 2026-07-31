import { Link, useNavigate } from 'react-router-dom'

import { Button, buttonVariants } from '@/components/ui/button'
import { api } from '@/lib/api'
import { useAuth } from '@/lib/auth-context'

export function AppLayout({ children }: { children: React.ReactNode }) {
  const { profile, setProfile } = useAuth()
  const navigate = useNavigate()

  async function handleLogout() {
    await api.logout()
    setProfile(null)
    navigate('/login')
  }

  return (
    <div className="min-h-svh">
      <header className="border-b">
        <div className="mx-auto flex max-w-3xl items-center justify-between gap-4 p-4">
          <Link to="/" className="font-semibold">
            Context Translator
          </Link>
          <nav className="flex items-center gap-2">
            <Link to="/profile" className={buttonVariants({ variant: 'ghost' })}>
              {profile?.username}
            </Link>
            <Button variant="outline" onClick={handleLogout}>
              Log out
            </Button>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-3xl p-4">{children}</main>
    </div>
  )
}
