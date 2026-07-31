import { useState } from 'react'

import { OperationsEditor } from '@/components/project/operations-editor'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import type { ChangeRequest, IREntry, Member, Operation } from '@/types/ir'

function RequestRow({
  request,
  author,
  entriesById,
  canAct,
  canEdit,
  busy,
  onApprove,
  onReject,
  onEdit,
}: {
  request: ChangeRequest
  author?: Member
  entriesById: Map<string, IREntry>
  canAct: boolean
  canEdit: boolean
  busy: boolean
  onApprove: () => void
  onReject: () => void
  onEdit: (operations: Operation[]) => void
}) {
  const [edited, setEdited] = useState(request.operations)
  const dirty = JSON.stringify(edited) !== JSON.stringify(request.operations)

  return (
    <div className="flex flex-col gap-3 border-b py-4 last:border-b-0">
      <p className="text-muted-foreground text-xs">
        <span className="font-medium">{author?.username ?? 'someone'}</span>{' '}
        proposed — “{request.source_text}”
      </p>

      <OperationsEditor
        operations={edited}
        entriesById={entriesById}
        onChange={setEdited}
      />

      {canAct ? (
        <div className="flex gap-2">
          {dirty && canEdit ? (
            <Button size="sm" onClick={() => onEdit(edited)} disabled={busy}>
              Save edits
            </Button>
          ) : (
            <Button size="sm" onClick={onApprove} disabled={busy}>
              Approve
            </Button>
          )}
          <Button size="sm" variant="outline" onClick={onReject} disabled={busy}>
            Reject
          </Button>
        </div>
      ) : (
        <div className="flex gap-2">
          {dirty && canEdit && (
            <Button size="sm" onClick={() => onEdit(edited)} disabled={busy}>
              Save edits
            </Button>
          )}
          <span className="text-muted-foreground self-center text-xs">
            Waiting on an admin.
          </span>
        </div>
      )}
    </div>
  )
}

/** Gate 2: everyone can see what's pending; only admins can apply it. */
export function PendingRequests({
  requests,
  members,
  entriesById,
  currentUserId,
  isAdmin,
  busy,
  onApprove,
  onReject,
  onEdit,
}: {
  requests: ChangeRequest[]
  members: Member[]
  entriesById: Map<string, IREntry>
  currentUserId: string
  isAdmin: boolean
  busy: boolean
  onApprove: (requestId: string) => void
  onReject: (requestId: string) => void
  onEdit: (requestId: string, operations: Operation[]) => void
}) {
  if (requests.length === 0) return null

  const byId = new Map(members.map((member) => [member.id, member]))

  return (
    <Card>
      <CardHeader>
        <CardTitle>
          Pending {requests.length === 1 ? 'change' : 'changes'} ({requests.length})
        </CardTitle>
        <CardDescription>
          {isAdmin
            ? 'Only you and other admins can apply these to the project.'
            : 'An admin has to approve these before they become facts.'}
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col">
        {requests.map((request) => (
          <RequestRow
            key={request.id}
            request={request}
            author={byId.get(request.author)}
            entriesById={entriesById}
            canAct={isAdmin}
            canEdit={isAdmin || request.author === currentUserId}
            busy={busy}
            onApprove={() => onApprove(request.id)}
            onReject={() => onReject(request.id)}
            onEdit={(operations) => onEdit(request.id, operations)}
          />
        ))}
      </CardContent>
    </Card>
  )
}
