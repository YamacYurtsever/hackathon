import { useState } from 'react'

import { Card, CardContent } from '@/components/ui/card'
import type { IREntry, Member } from '@/types/ir'

function timeOf(iso: string): string {
  return new Date(iso).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
  })
}

function statementOf(entry: IREntry): string {
  const statement = entry.content.statement
  return typeof statement === 'string' ? statement : JSON.stringify(entry.content)
}

function EntryRow({ entry, author }: { entry: IREntry; author?: Member }) {
  const [showRaw, setShowRaw] = useState(false)
  const subject = entry.content.subject

  return (
    <div className="flex flex-col gap-1 border-b py-3 last:border-b-0">
      <div className="text-muted-foreground flex items-baseline gap-2 text-xs">
        <span>{timeOf(entry.created_at)}</span>
        <span className="font-medium">{author?.username ?? 'unknown'}</span>
        {typeof subject === 'string' && (
          <span className="bg-secondary text-secondary-foreground rounded px-1.5 py-0.5">
            {subject}
          </span>
        )}
      </div>

      <p className="text-sm">{statementOf(entry)}</p>

      <button
        type="button"
        onClick={() => setShowRaw(!showRaw)}
        className="text-muted-foreground hover:text-foreground w-fit text-xs underline"
      >
        {showRaw ? 'hide' : 'raw IR'}
      </button>

      {showRaw && (
        <pre className="bg-muted overflow-x-auto rounded p-2 text-xs">
          {JSON.stringify(entry.content, null, 2)}
        </pre>
      )}
    </div>
  )
}

export function Feed({
  entries,
  members,
}: {
  entries: IREntry[]
  members: Member[]
}) {
  const byId = new Map(members.map((member) => [member.id, member]))

  if (entries.length === 0) {
    return (
      <Card>
        <CardContent className="text-muted-foreground py-8 text-center text-sm">
          Nothing recorded yet. Say something below — a statement becomes a fact
          once an admin approves it, a question just gets answered.
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardContent className="flex flex-col">
        {entries.map((entry) => (
          <EntryRow key={entry.id} entry={entry} author={byId.get(entry.author)} />
        ))}
      </CardContent>
    </Card>
  )
}
