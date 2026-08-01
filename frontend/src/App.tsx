import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'

import { AuthProvider } from '@/components/auth-provider'
import { useAuth } from '@/lib/auth-context'
import { HomePage } from '@/pages/home'
import { InvitePage } from '@/pages/invite'
import { LandingPage } from '@/pages/landing'
import { LoginPage } from '@/pages/login'
import { NewProjectPage } from '@/pages/new-project'
import { ProfilePage } from '@/pages/profile'
import { ProjectPage } from '@/pages/project'
import { SignupPage } from '@/pages/signup'

function RequireAuth({ children }: { children: React.ReactNode }) {
  const { profile, loading } = useAuth()
  if (loading) return null
  return profile ? children : <Navigate to="/login" replace />
}

function RedirectIfAuthed({ children }: { children: React.ReactNode }) {
  const { profile, loading } = useAuth()
  if (loading) return null
  return profile ? <Navigate to="/home" replace /> : children
}

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route
            path="/login"
            element={
              <RedirectIfAuthed>
                <LoginPage />
              </RedirectIfAuthed>
            }
          />
          <Route
            path="/signup"
            element={
              <RedirectIfAuthed>
                <SignupPage />
              </RedirectIfAuthed>
            }
          />
          <Route
            path="/home"
            element={
              <RequireAuth>
                <HomePage />
              </RequireAuth>
            }
          />
          <Route
            path="/profile"
            element={
              <RequireAuth>
                <ProfilePage />
              </RequireAuth>
            }
          />
          <Route
            path="/projects/new"
            element={
              <RequireAuth>
                <NewProjectPage />
              </RequireAuth>
            }
          />
          <Route
            path="/invite/:projectId"
            element={
              <RequireAuth>
                <InvitePage />
              </RequireAuth>
            }
          />
          <Route
            path="/projects/:projectId"
            element={
              <RequireAuth>
                <ProjectPage />
              </RequireAuth>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}

export default App
