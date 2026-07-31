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
import type { IREntry, Operation, Unresolved } from '@/types/ir'

/** Gate 1: our reading of what you said, before anyone else sees it. */
export function ChangesetPreview({
  operations,
  unresolved,
  entriesById,
  busy,
  onConfirm,
  onDiscard,
}: {
  operations: Operation[]
  unresolved: Unresolved[]
  entriesById: Map<string, IREntry>
  busy: boolean
  onConfirm: (operations: Operation[]) => void
  onDiscard: () => void
}) {
  const [edited, setEdited] = useState(operations)

  return (
    <Card className="border-primary/40">
      <CardHeader>
        <CardTitle>Here's what we understood</CardTitle>
        <CardDescription>
          Nothing is recorded yet. Check it, fix it if we got it wrong, then send
          it for approval.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <OperationsEditor
          operations={edited}
          entriesById={entriesById}
          onChange={setEdited}
        />

        {unresolved.length > 0 && (
          <div className="text-muted-foreground flex flex-col gap-1 border-t pt-3 text-xs">
            <span className="font-medium">Left open on purpose:</span>
            {unresolved.map((item, index) => (
              <span key={index}>
                “{item.quote}” — {item.issue}
              </span>
            ))}
          </div>
        )}

        <div className="flex gap-2">
          <Button onClick={() => onConfirm(edited)} disabled={busy || !edited.length}>
            {busy ? 'Sending…' : 'Send for approval'}
          </Button>
          <Button variant="ghost" onClick={onDiscard} disabled={busy}>
            Discard
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
