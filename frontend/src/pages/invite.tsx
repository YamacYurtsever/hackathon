import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'

import { AppLayout } from '@/components/app-layout'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { api } from '@/lib/api'

// Landing page for a shared invite link. Projects aren't browsable — you can
// only join one whose link you've been given.
export function InvitePage() {
  const { projectId } = useParams()
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [joining, setJoining] = useState(false)

  useEffect(() => {
    if (!projectId) return
    let cancelled = false

    api
      .previewInvite(projectId)
      .then((preview) => {
        if (!cancelled) setName(preview.name)
      })
      .catch((err) => {
        if (!cancelled)
          setError(err instanceof Error ? err.message : 'Invalid invite link')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [projectId])

  async function handleJoin() {
    if (!projectId) return
    setError('')
    setJoining(true)
    try {
      await api.joinProject(projectId)
      navigate(`/projects/${projectId}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not join project')
      setJoining(false)
    }
  }

  return (
    <AppLayout>
      {loading ? (
        <p className="text-muted-foreground">Loading…</p>
      ) : error ? (
        <p className="text-destructive">{error}</p>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle>Join {name}</CardTitle>
            <CardDescription>
              You've been invited to this project. You'll join as a member — an
              admin can promote you later.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex gap-2">
            <Button variant="brand" onClick={handleJoin} disabled={joining}>
              {joining ? 'Joining…' : `Join ${name}`}
            </Button>
            <Button variant="ghost" onClick={() => navigate('/home')}>
              Cancel
            </Button>
          </CardContent>
        </Card>
      )}
    </AppLayout>
  )
}
