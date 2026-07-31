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
  author,
  target,
  canAct,
  canEdit,
  busy,
  onMerge,
  onReject,
  onEdit,
}: {
  request: ChangeRequest
  author?: Member
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
    <div className="flex flex-col gap-2 py-3">
      <p className="text-muted-foreground text-xs">
        <span className="font-medium">{author?.username ?? 'someone'}</span>{' '}
        proposed — “{request.source_text}”
      </p>

      <OperationCard
        operation={edited}
        target={target}
        onChange={canEdit ? setEdited : undefined}
        actions={
          <>
            {dirty && canEdit && (
              <Button size="xs" onClick={() => onEdit(edited)} disabled={busy}>
                Save edits
              </Button>
            )}
            {canAct ? (
              <>
                {!dirty && (
                  <Button size="xs" onClick={onMerge} disabled={busy}>
                    Merge
                  </Button>
                )}
                <Button size="xs" variant="outline" onClick={onReject} disabled={busy}>
                  Reject
                </Button>
              </>
            ) : (
              <span className="text-muted-foreground text-xs">
                Waiting on an admin.
              </span>
            )}
          </>
        }
      />
    </div>
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
  onReject: (requestId: string) => void
  onEdit: (requestId: string, operation: Operation) => void
}) {
  if (requests.length === 0) return null

  const byId = new Map(members.map((member) => [member.id, member]))

  return (
    <Dialog>
      <DialogTrigger
        render={<Button>{requests.length} pending</Button>}
      />
      <DialogContent className="max-h-[85svh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>
            Pending {requests.length === 1 ? 'change' : 'changes'}
          </DialogTitle>
          <DialogDescription>
            {isAdmin
              ? 'Only you and other admins can merge these into the project.'
              : 'An admin has to merge these before they become facts.'}
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col">
          {requests.map((request) => (
            <RequestRow
              key={request.id}
              request={request}
              author={byId.get(request.author)}
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
      </DialogContent>
    </Dialog>
  )
}
