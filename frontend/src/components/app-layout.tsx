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
      <header className="bg-background/70 sticky top-0 z-30 shrink-0 border-b backdrop-blur-md">
        <div className="mx-auto flex max-w-3xl items-center justify-between gap-4 p-4">
          <Link to="/" className="group flex items-center gap-2 font-semibold">
            {/* The two readings, side by side, as a mark. */}
            <span className="flex items-center gap-0.5">
              <span className="bg-brand size-2.5 rounded-full transition-transform group-hover:scale-110" />
              <span className="bg-foreground/25 size-2.5 rounded-full transition-transform group-hover:scale-110" />
            </span>
            Contextor
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
