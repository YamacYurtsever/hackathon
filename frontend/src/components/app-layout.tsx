import { Link, useNavigate } from 'react-router-dom'

import { Button, buttonVariants } from '@/components/ui/button'
import { api } from '@/lib/api'
import { useAuth } from '@/lib/auth-context'

/** `fill` locks the page to the viewport so a child can pin something to the
 * bottom and scroll its own middle — the project view needs it, list pages
 * are happier scrolling normally. */
export function AppLayout({
  children,
  fill = false,
}: {
  children: React.ReactNode
  fill?: boolean
}) {
  const { profile, setProfile } = useAuth()
  const navigate = useNavigate()

  async function handleLogout() {
    await api.logout()
    setProfile(null)
    navigate('/login')
  }

  return (
    <div className={fill ? 'flex h-svh flex-col' : 'min-h-svh'}>
      <header className="shrink-0 border-b">
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
      <main
        className={`mx-auto w-full max-w-3xl p-4 ${fill ? 'min-h-0 flex-1' : ''}`}
      >
        {children}
      </main>
    </div>
  )
}
