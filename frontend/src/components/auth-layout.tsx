import { Link } from 'react-router-dom'

import './auth-layout.css'

/** Login and signup share this shell — Obsidian & Lime, matching the landing. */
export function AuthLayout({
  title,
  subtitle,
  children,
  footer,
}: {
  title: string
  subtitle: string
  children: React.ReactNode
  footer: React.ReactNode
}) {
  return (
    <div className="auth">
      <div className="auth__noise" aria-hidden />
      <div className="auth__glow auth__glow--a" aria-hidden />
      <div className="auth__glow auth__glow--b" aria-hidden />

      <div className="auth__shell">
        <div className="auth__brand">
          <Link to="/" className="auth__logo">
            <span className="auth__mark">C</span>
            <span className="auth__word">Contextor</span>
          </Link>
          <p className="auth__tagline">
            One record of what&apos;s true. Everyone reads it in their own terms.
          </p>
        </div>

        <div className="auth__card">
          <h1 className="auth__title">{title}</h1>
          <p className="auth__subtitle">{subtitle}</p>
          {children}
        </div>

        <p className="auth__footer">{footer}</p>
      </div>
    </div>
  )
}
