import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { AppLayout } from '@/components/app-layout'
import { Button } from '@/components/ui/button'
import { Card, CardHeader, CardTitle } from '@/components/ui/card'
import { api } from '@/lib/api'
import type { Project } from '@/types/ir'

export function JoinProjectPage() {
  const navigate = useNavigate()
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [joiningId, setJoiningId] = useState('')

  useEffect(() => {
    api
      .listAvailableProjects()
      .then(setProjects)
      .catch((err) =>
        setError(err instanceof Error ? err.message : 'Could not load projects'),
      )
      .finally(() => setLoading(false))
  }, [])

  async function handleJoin(id: string) {
    setError('')
    setJoiningId(id)
    try {
      await api.joinProject(id)
      navigate(`/projects/${id}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not join project')
      setJoiningId('')
    }
  }

  return (
    <AppLayout>
      <div className="flex flex-col gap-6">
        <h1 className="text-2xl font-semibold">Join a project</h1>

        {loading && <p className="text-muted-foreground">Loading…</p>}
        {error && <p className="text-destructive">{error}</p>}

        {!loading && !error && projects.length === 0 && (
          <p className="text-muted-foreground">
            There are no other projects to join.
          </p>
        )}

        <div className="flex flex-col gap-3">
          {projects.map((project) => (
            <Card key={project.id}>
              <CardHeader className="flex flex-row items-center justify-between gap-4">
                <div>
                  <CardTitle>{project.name}</CardTitle>
                  <p className="text-muted-foreground text-sm">
                    {project.users.length}{' '}
                    {project.users.length === 1 ? 'member' : 'members'}
                  </p>
                </div>
                <Button
                  onClick={() => handleJoin(project.id)}
                  disabled={joiningId === project.id}
                >
                  {joiningId === project.id ? 'Joining…' : 'Join'}
                </Button>
              </CardHeader>
            </Card>
          ))}
        </div>
      </div>
    </AppLayout>
  )
}
