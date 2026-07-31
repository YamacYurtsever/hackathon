import { useState } from 'react'

import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { api } from '@/lib/api'
import { useAuth } from '@/lib/auth-context'

export function ProfilePage() {
  const { profile, setProfile } = useAuth()
  const [description, setDescription] = useState(
    typeof profile?.content.description === 'string'
      ? profile.content.description
      : '',
  )
  const [status, setStatus] = useState('')
  const [saving, setSaving] = useState(false)

  if (profile === null) return null

  async function handleSave(event: React.FormEvent) {
    event.preventDefault()
    setStatus('')
    setSaving(true)
    try {
      // Keep any other content keys the profile already has (seeded
      // profiles carry role/expertise/history_summary).
      setProfile(
        await api.updateOwnProfile({ ...profile!.content, description }),
      )
      setStatus('Saved')
    } catch (err) {
      setStatus(err instanceof Error ? err.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  async function handleLogout() {
    await api.logout()
    setProfile(null)
    window.location.assign('/login')
  }

  return (
    <div className="mx-auto flex min-h-svh max-w-2xl flex-col gap-6 p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">{profile.username}</h1>
        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={() => window.location.assign('/')}
          >
            Back to projects
          </Button>
          <Button variant="outline" onClick={handleLogout}>
            Log out
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Your context</CardTitle>
          <CardDescription>
            Describe your role, expertise, and background. This shapes how the
            project's facts get re-projected for you — and you can change it any
            time.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSave} className="flex flex-col gap-4">
            <div className="flex flex-col gap-2">
              <Label htmlFor="description">About you</Label>
              <Textarea
                id="description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={6}
                placeholder="e.g. Regulatory lawyer. I handle FDA 510(k) submissions and need to know when engineering changes affect our filings."
              />
            </div>
            <div className="flex items-center gap-3">
              <Button type="submit" disabled={saving}>
                {saving ? 'Saving…' : 'Save'}
              </Button>
              {status && (
                <span className="text-muted-foreground text-sm">{status}</span>
              )}
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
