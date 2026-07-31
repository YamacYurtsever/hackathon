import { useEffect, useRef } from 'react'

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
  const ref = useRef<HTMLDivElement>(null)

  // Arriving here from a citation click should land you on the right row.
  useEffect(() => {
    if (highlighted) ref.current?.scrollIntoView({ block: 'center' })
  }, [highlighted])

  return (
    <div
      ref={ref}
      className={`flex flex-col gap-1 border-b py-3 transition-colors first:pt-0 last:border-b-0 last:pb-0 ${
        highlighted ? 'bg-secondary rounded' : ''
      }`}
    >
      <div className="text-muted-foreground flex items-baseline gap-2 text-xs">
        {citation !== undefined && <span className="font-medium">[{citation}]</span>}
        <span>{timeOf(entry.created_at)}</span>
        <span className="font-medium">{author?.username ?? 'unknown'}</span>
      </div>

      <p className="text-sm">{statementOf(entry)}</p>
    </div>
  )
}

export function Feed({
  entries,
  members,
  citations,
  highlightId,
}: {
  entries: IREntry[]
  members: Member[]
  /** Entry id → citation number, for whatever the NL panel is showing. */
  citations?: Map<string, number>
  highlightId?: string
}) {
  const byId = new Map(members.map((member) => [member.id, member]))

  // IR is the evidence for what you just read — the entries the summary or the
  // answer actually drew on, in the order they were cited so [1] comes first
  // and following a marker lands where you expect. With nothing cited yet
  // there's no reading to be evidence for, so the whole record shows, in time
  // order as a plain timeline.
  const cited = citations && citations.size > 0
  const visible = cited
    ? entries
        .filter((entry) => citations.has(entry.id))
        .sort((a, b) => citations.get(a.id)! - citations.get(b.id)!)
    : entries

  if (entries.length === 0) {
    return (
      <Card className="min-h-0 flex-1 py-0">
        <CardContent className="text-muted-foreground p-6 text-center text-sm">
          Nothing recorded yet. Say something below — a statement becomes a fact
          once an admin approves it, a question just gets answered.
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="min-h-0 flex-1 overflow-hidden py-0">
      <CardContent className="flex h-full flex-col overflow-y-auto p-6">
        {visible.map((entry) => (
          <EntryRow
            key={entry.id}
            entry={entry}
            author={byId.get(entry.author)}
            citation={citations?.get(entry.id)}
            highlighted={entry.id === highlightId}
          />
        ))}
      </CardContent>
    </Card>
  )
}
