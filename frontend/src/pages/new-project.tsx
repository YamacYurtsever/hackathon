import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { AppLayout } from '@/components/app-layout'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { api } from '@/lib/api'

export function NewProjectPage() {
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      const project = await api.createProject(name)
      navigate(`/projects/${project.id}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not create project')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AppLayout>
      <Card>
        <CardHeader>
          <CardTitle>New project</CardTitle>
          <CardDescription>
            You'll be its first admin — only admins can approve changes to the
            project's facts.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div className="flex flex-col gap-2">
              <Label htmlFor="name">Project name</Label>
              <Input
                id="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </div>
            {error && <p className="text-destructive text-sm">{error}</p>}
            <div className="flex gap-2">
              <Button type="submit" variant="brand" disabled={submitting}>
                {submitting ? 'Creating…' : 'Create project'}
              </Button>
              <Button
                type="button"
                variant="ghost"
                onClick={() => navigate('/home')}
              >
                Cancel
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </AppLayout>
  )
}
