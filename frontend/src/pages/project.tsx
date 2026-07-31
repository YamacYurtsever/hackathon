import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'

import { AppLayout } from '@/components/app-layout'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { api } from '@/lib/api'
import { useAuth } from '@/lib/auth-context'
import type { Member, Project } from '@/types/ir'

// Later milestones fill this same view with the IR feed and re-projected
// claims — for now it's the project's identity and member management.
export function ProjectPage() {
  const { projectId } = useParams()
  const navigate = useNavigate()
  const { profile } = useAuth()

  const [project, setProject] = useState<Project | null>(null)
  const [members, setMembers] = useState<Member[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [busyId, setBusyId] = useState('')
  const [copied, setCopied] = useState(false)
  // Bumped to re-fetch after a change (e.g. promoting someone).
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    if (!projectId) return
    let cancelled = false

    Promise.all([api.getProject(projectId), api.listMembers(projectId)])
      .then(([loadedProject, loadedMembers]) => {
        if (cancelled) return
        setProject(loadedProject)
        setMembers(loadedMembers)
      })
      .catch((err) => {
        if (cancelled) return
        setError(err instanceof Error ? err.message : 'Could not load project')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [projectId, reloadKey])

  const viewerIsAdmin = members.some(
    (member) => member.id === profile?.id && member.is_admin,
  )

  async function handlePromote(userId: string) {
    if (!projectId) return
    setError('')
    setBusyId(userId)
    try {
      await api.promoteMember(projectId, userId)
      setReloadKey((key) => key + 1)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not promote member')
    } finally {
      setBusyId('')
    }
  }

  async function handleCopyInvite() {
    const link = `${window.location.origin}/invite/${projectId}`
    try {
      await navigator.clipboard.writeText(link)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // Clipboard can be blocked (permissions, insecure context) — show the
      // link so it can still be copied by hand.
      setError(`Copy this invite link: ${link}`)
    }
  }

  async function handleExit() {
    if (!projectId) return
    setError('')
    try {
      await api.exitProject(projectId)
      navigate('/')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not leave project')
    }
  }

  if (loading) {
    return (
      <AppLayout>
        <p className="text-muted-foreground">Loading…</p>
      </AppLayout>
    )
  }

  if (project === null) {
    return (
      <AppLayout>
        <p className="text-destructive">{error || 'Project not found'}</p>
      </AppLayout>
    )
  }

  return (
    <AppLayout>
      <div className="flex flex-col gap-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold">{project.name}</h1>
            <p className="text-muted-foreground text-sm">
              {project.ir.length}{' '}
              {project.ir.length === 1 ? 'entry' : 'entries'}
            </p>
          </div>
          <div className="flex gap-2">
            {viewerIsAdmin && (
              <Button variant="outline" onClick={handleCopyInvite}>
                {copied ? 'Link copied' : 'Copy invite link'}
              </Button>
            )}
            <Button variant="outline" onClick={handleExit}>
              Leave project
            </Button>
          </div>
        </div>

        {error && <p className="text-destructive text-sm">{error}</p>}

        <Card>
          <CardHeader>
            <CardTitle>Members</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-2">
            {members.map((member) => (
              <div
                key={member.id}
                className="flex items-center justify-between gap-4 border-b py-2 last:border-b-0"
              >
                <div className="flex items-center gap-2">
                  <span>{member.username}</span>
                  {member.id === profile?.id && (
                    <span className="text-muted-foreground text-xs">(you)</span>
                  )}
                  {member.is_admin && (
                    <span className="bg-secondary text-secondary-foreground rounded px-1.5 py-0.5 text-xs">
                      admin
                    </span>
                  )}
                </div>
                {viewerIsAdmin && !member.is_admin && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handlePromote(member.id)}
                    disabled={busyId === member.id}
                  >
                    {busyId === member.id ? 'Promoting…' : 'Make admin'}
                  </Button>
                )}
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </AppLayout>
  )
}
