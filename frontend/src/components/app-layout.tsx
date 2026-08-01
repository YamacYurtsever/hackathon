import { Link, useNavigate } from 'react-router-dom'

import { api } from '@/lib/api'
import { useAuth } from '@/lib/auth-context'
import type { UiTheme } from '@/lib/ui-theme'

import './app-layout.css'

/** `fill` locks the page to the viewport so a child can pin something to the
 * bottom and scroll its own middle — the project view needs it, list pages
 * are happier scrolling normally.
 *
 * Classic and Obsidian share one layout (fonts, sizes, button placement);
 * only the colour tokens change. Pass `onToggleTheme` to show the switcher. */
export function AppLayout({
  children,
  fill = false,
  theme = 'classic',
  onToggleTheme,
}: {
  children: React.ReactNode
  fill?: boolean
  theme?: UiTheme
  onToggleTheme?: () => void
}) {
  const { profile, setProfile } = useAuth()
  const navigate = useNavigate()

  async function handleLogout() {
    await api.logout()
    setProfile(null)
    navigate('/login')
  }

  return (
    <div
      className={`app-shell app-shell--${theme}${fill ? ' app-shell--fill' : ''}`}
    >
      <div className="app-shell__noise" aria-hidden />
      <div className="app-shell__frame">
        <div className="app-shell__glow app-shell__glow--tl" aria-hidden />
        <div className="app-shell__glow app-shell__glow--br" aria-hidden />

        <header className="app-shell__nav">
          <Link to="/home" className="app-shell__logo">
            <span className="app-shell__mark">C</span>
            <span className="app-shell__word">Contextor</span>
          </Link>
          <div className="app-shell__actions">
            {onToggleTheme && (
              <button
                type="button"
                className="app-shell__btn app-shell__btn--ghost"
                onClick={onToggleTheme}
              >
                {theme === 'obsidian' ? 'Classic design' : 'New design'}
              </button>
            )}
            <Link to="/profile" className="app-shell__btn app-shell__btn--ghost">
              {profile?.username}
            </Link>
            <button
              type="button"
              className="app-shell__btn app-shell__btn--ghost"
              onClick={handleLogout}
            >
              Log out
            </button>
          </div>
        </header>

        <main
          className={`app-shell__main${theme === 'obsidian' ? ' dark' : ''}${
            fill ? ' app-shell__main--fill' : ''
          }`}
        >
          {children}
        </main>
      </div>
    </div>
  )
}
