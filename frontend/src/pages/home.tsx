import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { AppLayout } from '@/components/app-layout'
import { buttonVariants } from '@/components/ui/button'
import { Card, CardHeader, CardTitle } from '@/components/ui/card'
import { api } from '@/lib/api'
import type { Project } from '@/types/ir'

export function HomePage() {
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

  return (
    <AppLayout>
      <div className="flex flex-col gap-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-semibold">Your projects</h1>
          <Link to="/projects/new" className={buttonVariants()}>
            New project
          </Link>
        </div>

        {loading && <p className="text-muted-foreground">Loading…</p>}
        {error && <p className="text-destructive">{error}</p>}

        {!loading && !error && projects.length === 0 && (
          <p className="text-muted-foreground">
            You haven't joined any projects yet. Create one, or ask an admin for
            an invite link.
          </p>
        )}

        <div className="flex flex-col gap-3">
          {projects.map((project) => (
            <Link key={project.id} to={`/projects/${project.id}`}>
              <Card className="hover:bg-accent transition-colors">
                <CardHeader>
                  <CardTitle>{project.name}</CardTitle>
                  <p className="text-muted-foreground text-sm">
                    {project.users.length}{' '}
                    {project.users.length === 1 ? 'member' : 'members'} ·{' '}
                    {project.ir.length}{' '}
                    {project.ir.length === 1 ? 'entry' : 'entries'}
                  </p>
                </CardHeader>
              </Card>
            </Link>
          ))}
        </div>
      </div>
    </AppLayout>
  )
}
