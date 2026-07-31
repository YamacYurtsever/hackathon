import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'

import { AppLayout } from '@/components/app-layout'
import { api } from '@/lib/api'
import type { Project } from '@/types/ir'

// Placeholder shell — milestone 4 adds the member list and admin controls,
// and later milestones add the IR feed and re-projected claims.
export function ProjectPage() {
  const { projectId } = useParams()
  const [project, setProject] = useState<Project | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!projectId) return
    api
      .getProject(projectId)
      .then(setProject)
      .catch((err) =>
        setError(err instanceof Error ? err.message : 'Could not load project'),
      )
  }, [projectId])

  return (
    <AppLayout>
      {error && <p className="text-destructive">{error}</p>}
      {project && (
        <div className="flex flex-col gap-2">
          <h1 className="text-2xl font-semibold">{project.name}</h1>
          <p className="text-muted-foreground">
            {project.users.length}{' '}
            {project.users.length === 1 ? 'member' : 'members'}
          </p>
        </div>
      )}
    </AppLayout>
  )
}
