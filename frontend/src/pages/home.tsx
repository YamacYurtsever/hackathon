import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { api } from '@/lib/api'
import { useAuth } from '@/lib/auth-context'
import {
  readHomeTheme,
  writeHomeTheme,
  type HomeTheme,
} from '@/lib/home-theme'
import type { Project } from '@/types/ir'

import './home.css'

export function HomePage() {
  const { profile, setProfile } = useAuth()
  const navigate = useNavigate()
  const [theme, setTheme] = useState<HomeTheme>(() => readHomeTheme())
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    api
      .listProjects()
      .then(setProjects)
      .catch((err) =>
        setError(err instanceof Error ? err.message : 'Could not load projects'),
      )
      .finally(() => setLoading(false))
  }, [])

  function toggleTheme() {
    const next: HomeTheme = theme === 'obsidian' ? 'classic' : 'obsidian'
    writeHomeTheme(next)
    setTheme(next)
  }

  async function handleLogout() {
    await api.logout()
    setProfile(null)
    navigate('/login')
  }

  return (
    <div className={`home home--${theme}`}>
      <div className="home__noise" aria-hidden />
      <div className="home__shell">
        <div className="home__glow home__glow--tl" aria-hidden />
        <div className="home__glow home__glow--br" aria-hidden />

        <header className="home__nav">
          <Link to="/home" className="home__logo">
            <span className="home__mark">C</span>
            <span className="home__word">Contextor</span>
          </Link>

          <div className="home__actions">
            <button
              type="button"
              className="home__btn home__btn--ghost"
              onClick={toggleTheme}
            >
              {theme === 'obsidian' ? 'Classic design' : 'New design'}
            </button>
            <Link to="/profile" className="home__btn home__btn--ghost">
              {profile?.username}
            </Link>
            <button
              type="button"
              className="home__btn home__btn--ghost"
              onClick={handleLogout}
            >
              Log out
            </button>
          </div>
        </header>

        <main className="home__main">
          <div className="home__header">
            <div>
              <p className="home__eyebrow">Workspace</p>
              <h1 className="home__title">Your projects</h1>
            </div>
            <Link to="/projects/new" className="home__btn home__btn--neon">
              New project
            </Link>
          </div>

          {loading && <p className="home__muted">Loading…</p>}
          {error && <p className="home__error">{error}</p>}

          {!loading && !error && projects.length === 0 && (
            <div className="home__empty">
              <p>
                You haven&apos;t joined any projects yet. Create one, or ask an
                admin for an invite link.
              </p>
              <Link to="/projects/new" className="home__btn home__btn--neon">
                New project
              </Link>
            </div>
          )}

          <div className="home__list">
            {projects.map((project) => (
              <Link
                key={project.id}
                to={`/projects/${project.id}`}
                className="home__card"
              >
                <h2 className="home__card-name">{project.name}</h2>
              </Link>
            ))}
          </div>
        </main>
      </div>
    </div>
  )
}
