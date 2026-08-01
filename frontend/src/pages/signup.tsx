import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { AuthLayout } from '@/components/auth-layout'
import { api } from '@/lib/api'
import { useAuth } from '@/lib/auth-context'

export function SignupPage() {
  const { setProfile } = useAuth()
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      setProfile(await api.signup(username, password))
      // Straight to the profile page — describing yourself happens there,
      // not at signup.
      navigate('/profile')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Signup failed')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AuthLayout
      title="Create your account"
      subtitle="Then describe how you read things — that's what shapes your view."
      footer={
        <>
          Already have an account? <Link to="/login">Log in</Link>
        </>
      }
    >
      <form onSubmit={handleSubmit} className="auth__form">
        <div className="auth__field">
          <label htmlFor="username" className="auth__label">
            Username
          </label>
          <input
            id="username"
            className="auth__input"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            required
          />
        </div>
        <div className="auth__field">
          <label htmlFor="password" className="auth__label">
            Password
          </label>
          <input
            id="password"
            type="password"
            className="auth__input"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="new-password"
            required
          />
        </div>
        {error && <p className="auth__error">{error}</p>}
        <button type="submit" className="auth__submit" disabled={submitting}>
          {submitting ? 'Creating account…' : 'Create account'}
        </button>
      </form>
    </AuthLayout>
  )
}
