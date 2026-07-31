import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'

import { AppLayout } from '@/components/app-layout'
import { AnswerCard } from '@/components/project/answer-card'
import { ChangesetPreview } from '@/components/project/changeset-preview'
import { Composer } from '@/components/project/composer'
import { Feed } from '@/components/project/feed'
import { PendingRequests } from '@/components/project/pending-requests'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { api } from '@/lib/api'
import { useAuth } from '@/lib/auth-context'
import type {
  ChangeRequest,
  IREntry,
  InputResult,
  Member,
  Operation,
  Project,
} from '@/types/ir'

export function ProjectPage() {
  const { projectId } = useParams()
  const navigate = useNavigate()
  const { profile } = useAuth()

  const [project, setProject] = useState<Project | null>(null)
  const [members, setMembers] = useState<Member[]>([])
  const [entries, setEntries] = useState<IREntry[]>([])
  const [requests, setRequests] = useState<ChangeRequest[]>([])
  const [pending, setPending] = useState<InputResult | null>(null)

  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [copied, setCopied] = useState(false)
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    if (!projectId) return
    let cancelled = false

    Promise.all([
      api.getProject(projectId),
      api.listMembers(projectId),
      api.getChanges(projectId),
      api.listRequests(projectId),
    ])
      .then(([loadedProject, loadedMembers, loadedEntries, loadedRequests]) => {
        if (cancelled) return
        setProject(loadedProject)
        setMembers(loadedMembers)
        setEntries(loadedEntries)
        setRequests(loadedRequests)
      })
      .catch((err) => {
        if (!cancelled)
          setError(err instanceof Error ? err.message : 'Could not load project')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [projectId, reloadKey])

  const viewerIsAdmin = Boolean(
    profile && project?.admins.includes(profile.id),
  )
  const entriesById = new Map(entries.map((entry) => [entry.id, entry]))

  const refresh = () => setReloadKey((key) => key + 1)

  async function run<T>(work: () => Promise<T>): Promise<T | undefined> {
    setError('')
    setBusy(true)
    try {
      return await work()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong')
    } finally {
      setBusy(false)
    }
  }

  async function handleSend(text: string, kind?: 'changeset' | 'answer') {
    if (!projectId) return
    const result = await run(() => api.sendInput(projectId, text, kind))
    if (result) setPending(result)
  }

  async function handleConfirm(operations: Operation[]) {
    if (!projectId || pending?.kind !== 'changeset') return
    const done = await run(() =>
      api.confirmChangeset(projectId, pending.text, operations),
    )
    if (done) {
      setPending(null)
      refresh()
    }
  }

  async function handleCopyInvite() {
    const link = `${window.location.origin}/invite/${projectId}`
    try {
      await navigator.clipboard.writeText(link)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      setError(`Copy this invite link: ${link}`)
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
              {entries.length} {entries.length === 1 ? 'entry' : 'entries'} ·{' '}
              {members.length} {members.length === 1 ? 'member' : 'members'}
            </p>
          </div>
          <div className="flex gap-2">
            {viewerIsAdmin && (
              <Button variant="outline" onClick={handleCopyInvite}>
                {copied ? 'Link copied' : 'Copy invite link'}
              </Button>
            )}
            <Button
              variant="outline"
              onClick={() =>
                projectId &&
                run(() => api.exitProject(projectId)).then(() => navigate('/'))
              }
            >
              Leave
            </Button>
          </div>
        </div>

        {error && <p className="text-destructive text-sm">{error}</p>}

        <PendingRequests
          requests={requests}
          members={members}
          entriesById={entriesById}
          currentUserId={profile?.id ?? ''}
          isAdmin={viewerIsAdmin}
          busy={busy}
          onApprove={(id) =>
            projectId &&
            run(() => api.approveRequest(projectId, id)).then(refresh)
          }
          onReject={(id) =>
            projectId && run(() => api.rejectRequest(projectId, id)).then(refresh)
          }
          onEdit={(id, operations) =>
            projectId &&
            run(() => api.editRequest(projectId, id, operations)).then(refresh)
          }
        />

        <Feed entries={entries} members={members} />

        {pending?.kind === 'changeset' && (
          <ChangesetPreview
            operations={pending.operations}
            unresolved={pending.unresolved}
            entriesById={entriesById}
            busy={busy}
            onConfirm={handleConfirm}
            onDiscard={() => setPending(null)}
          />
        )}

        {pending?.kind === 'answer' && (
          <AnswerCard
            question={pending.text}
            segments={pending.segments}
            busy={busy}
            onDismiss={() => setPending(null)}
            onTreatAsStatement={() => handleSend(pending.text, 'changeset')}
          />
        )}

        <Composer busy={busy} onSend={handleSend} />

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
                <div className="flex items-center gap-2 text-sm">
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
                    disabled={busy}
                    onClick={() =>
                      projectId &&
                      run(() => api.promoteMember(projectId, member.id)).then(refresh)
                    }
                  >
                    Make admin
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
