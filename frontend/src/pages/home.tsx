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
          <Link to="/projects/new" className={buttonVariants({ variant: 'brand' })}>
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
            <Link key={project.id} to={`/projects/${project.id}`} className="group">
              <Card className="ring-border/70 group-hover:ring-brand/40 relative overflow-hidden shadow-sm transition-all group-hover:-translate-y-0.5 group-hover:shadow-[0_1px_2px_rgb(0_0_0/0.04),0_12px_28px_-14px_rgb(0_0_0/0.18)]">
                {/* An accent edge that arrives on hover, so the row feels
                    reachable without shouting when it isn't. */}
                <span className="bg-brand absolute inset-y-0 left-0 w-0.5 origin-top scale-y-0 transition-transform duration-200 group-hover:scale-y-100 motion-reduce:transition-none" />
                <CardHeader>
                  <CardTitle className="group-hover:text-brand transition-colors">
                    {project.name}
                  </CardTitle>
                  <p className="text-muted-foreground flex items-center gap-2 text-sm">
                    <span className="tabular-nums">
                      {project.users.length}{' '}
                      {project.users.length === 1 ? 'member' : 'members'}
                    </span>
                    <span className="bg-muted-foreground/40 size-1 rounded-full" />
                    <span className="tabular-nums">
                      {project.ir.length}{' '}
                      {project.ir.length === 1 ? 'entry' : 'entries'}
                    </span>
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
