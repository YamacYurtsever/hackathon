import { useEffect, useRef, useState } from 'react'

import { Button } from '@/components/ui/button'
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

function EntryRow({
  entry,
  author,
  citation,
  highlighted,
}: {
  entry: IREntry
  author?: Member
  citation?: number
  highlighted: boolean
}) {
  const [showRaw, setShowRaw] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  const subject = entry.content.subject

  // Arriving here from a citation click should land you on the right row.
  useEffect(() => {
    if (highlighted) ref.current?.scrollIntoView({ block: 'center' })
  }, [highlighted])

  return (
    <div
      ref={ref}
      className={`flex flex-col gap-1 border-b px-2 py-3 transition-colors last:border-b-0 ${
        highlighted ? 'bg-secondary rounded' : ''
      }`}
    >
      <div className="text-muted-foreground flex items-baseline gap-2 text-xs">
        {citation !== undefined && <span className="font-medium">[{citation}]</span>}
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
  citations,
  highlightId,
  showAll,
  onShowAllChange,
}: {
  entries: IREntry[]
  members: Member[]
  /** Entry id → citation number, when the summary cited it. */
  citations?: Map<string, number>
  highlightId?: string
  showAll: boolean
  onShowAllChange: (showAll: boolean) => void
}) {
  const byId = new Map(members.map((member) => [member.id, member]))

  // The IR side defaults to the evidence behind the summary — the receipts for
  // what you just read — with everything else a click away.
  const cited = citations && citations.size > 0
  const visible = showAll || !cited
    ? entries
    : entries.filter((entry) => citations.has(entry.id))
  const hidden = entries.length - visible.length

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
        {visible.map((entry) => (
          <EntryRow
            key={entry.id}
            entry={entry}
            author={byId.get(entry.author)}
            citation={citations?.get(entry.id)}
            highlighted={entry.id === highlightId}
          />
        ))}

        {cited && (hidden > 0 || showAll) && (
          <Button
            variant="ghost"
            size="sm"
            className="mt-2 self-start"
            onClick={() => onShowAllChange(!showAll)}
          >
            {showAll
              ? 'Show only what the summary cited'
              : `Show everything (${hidden} more)`}
          </Button>
        )}
      </CardContent>
    </Card>
  )
}
