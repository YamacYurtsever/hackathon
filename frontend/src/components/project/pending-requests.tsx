import { useState } from 'react'

import { OperationCard } from '@/components/project/operation-card'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import type { ChangeRequest, IREntry, Member, Operation } from '@/types/ir'

function RequestRow({
  request,
  target,
  canAct,
  canEdit,
  busy,
  onMerge,
  onReject,
  onEdit,
}: {
  request: ChangeRequest
  target?: IREntry
  canAct: boolean
  canEdit: boolean
  busy: boolean
  onMerge: () => void
  onReject: () => void
  onEdit: (operation: Operation) => void
}) {
  const [edited, setEdited] = useState(request.operation)
  const dirty = JSON.stringify(edited) !== JSON.stringify(request.operation)

  return (
    <OperationCard
      operation={edited}
      target={target}
      onChange={canEdit ? setEdited : undefined}
      actions={
        <>
          {dirty && canEdit && (
            <Button size="xs" variant="brand" onClick={() => onEdit(edited)} disabled={busy}>
              Save edits
            </Button>
          )}
          {canAct ? (
            <>
              {!dirty && (
                <Button size="xs" variant="brand" onClick={onMerge} disabled={busy}>
                  Merge
                </Button>
              )}
              <Button size="xs" variant="outline" onClick={onReject} disabled={busy}>
                Reject
              </Button>
            </>
          ) : (
            <span className="text-muted-foreground text-xs">Waiting on an admin.</span>
          )}
        </>
      }
    />
  )
}

/** Gate 2, behind a header button: submitted changes waiting to be merged.
 * Everyone can see the queue; only admins can merge, and each request carries
 * one change so merging one doesn't commit you to the rest. */
export function PendingRequests({
  requests,
  members,
  entriesById,
  currentUserId,
  isAdmin,
  busy,
  onMerge,
  onMergeAll,
  onReject,
  onEdit,
}: {
  requests: ChangeRequest[]
  members: Member[]
  entriesById: Map<string, IREntry>
  currentUserId: string
  isAdmin: boolean
  busy: boolean
  onMerge: (requestId: string) => void
  onMergeAll: () => void
  onReject: (requestId: string) => void
  onEdit: (requestId: string, operation: Operation) => void
}) {
  if (requests.length === 0) return null

  const byId = new Map(members.map((member) => [member.id, member]))

  // One message can propose a dozen changes, and repeating its text above each
  // of them buried the changes themselves. The message is said once; what it
  // produced sits under it.
  const groups: { author: string; source: string; items: ChangeRequest[] }[] = []
  for (const request of requests) {
    const last = groups.at(-1)
    if (last && last.author === request.author && last.source === request.source_text) {
      last.items.push(request)
    } else {
      groups.push({
        author: request.author,
        source: request.source_text,
        items: [request],
      })
    }
  }

  const mine = requests.filter((request) => request.author === currentUserId).length

  return (
    <Dialog>
      <DialogTrigger
        render={
          <Button variant="attention">
            <span className="bg-attention size-1.5 rounded-full" />
            {requests.length} pending
          </Button>
        }
      />
      <DialogContent className="max-h-[85svh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>
            {requests.length} {requests.length === 1 ? 'change' : 'changes'} waiting
          </DialogTitle>
          <DialogDescription>
            {isAdmin
              ? 'Nothing here is in the project yet. Merging is the only thing that puts it there.'
              : mine === requests.length
                ? "Yours are in the queue — an admin has to merge them before they're facts."
                : "An admin has to merge these before they're facts."}
          </DialogDescription>
        </DialogHeader>

        {/* Bootstrapping a project means approving a batch, not adjudicating
            one fact at a time — the per-request controls stay for when you do
            want to go through them individually. */}
        {isAdmin && requests.length > 1 && (
          <div className="flex justify-end">
            <Button size="sm" variant="brand" onClick={onMergeAll} disabled={busy}>
              Merge all {requests.length}
            </Button>
          </div>
        )}

        <div className="flex flex-col gap-5">
          {groups.map((group) => (
            <div key={`${group.author}:${group.source}`} className="flex flex-col gap-2">
              <div className="flex items-baseline gap-2">
                <span className="text-foreground shrink-0 text-sm font-medium">
                  {byId.get(group.author)?.username ?? 'someone'}
                  {group.author === currentUserId && (
                    <span className="text-muted-foreground font-normal"> (you)</span>
                  )}
                </span>
                <span className="text-muted-foreground min-w-0 flex-1 truncate text-xs italic">
                  {group.source}
                </span>
                <span className="text-muted-foreground shrink-0 text-xs tabular-nums">
                  {group.items.length}
                </span>
              </div>

              {/* An accent rail ties the proposals back to the message above. */}
              <div className="border-brand/25 flex flex-col gap-2 border-l-2 pl-3">
                {group.items.map((request) => (
                  <RequestRow
                    key={request.id}
                    request={request}
                    target={
                      request.operation.target_id
                        ? entriesById.get(request.operation.target_id)
                        : undefined
                    }
                    canAct={isAdmin}
                    canEdit={isAdmin || request.author === currentUserId}
                    busy={busy}
                    onMerge={() => onMerge(request.id)}
                    onReject={() => onReject(request.id)}
                    onEdit={(operation) => onEdit(request.id, operation)}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  )
}
