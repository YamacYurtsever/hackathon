import { Card, CardContent } from '@/components/ui/card'
import type { Segment } from '@/types/ir'

/** Segments concatenated into one flowing block, not one row per segment — the
 * seams shouldn't be visible to the reader. Shared by the summary and by an
 * answer, which are the same thing pointed at different questions. */
function Prose({
  segments,
  numbers,
  onCitationClick,
}: {
  segments: Segment[]
  numbers: Map<string, number>
  onCitationClick: (entryId: string) => void
}) {
  return (
    <p className="text-sm leading-7">
      {segments.map((segment, index) => (
        <span key={index}>
          {segment.text}
          {segment.source_entry_ids.map((entryId) => (
            <button
              key={entryId}
              type="button"
              onClick={() => onCitationClick(entryId)}
              title="Show the entry this came from"
              className="text-muted-foreground hover:text-foreground ml-0.5 align-super text-[0.65rem] hover:underline"
            >
              [{numbers.get(entryId)}]
            </button>
          ))}{' '}
        </span>
      ))}
    </p>
  )
}

export function SummaryPanel({
  segments,
  loading,
  numbers,
  answer,
  onCitationClick,
}: {
  segments: Segment[]
  loading: boolean
  numbers: Map<string, number>
  /** A reply to what you just asked. Transient — it isn't a fact, so it never
   * enters the feed or the IR — but it belongs in this panel rather than a
   * second box below it. It stands until the next message; the summary is what
   * the panel shows when you haven't asked anything, not a place to go back to. */
  answer?: { question: string; segments: Segment[]; pending?: boolean } | null
  onCitationClick: (entryId: string) => void
}) {
  if (answer) {
    return (
      <Card className="min-h-0 flex-1 overflow-hidden py-0">
        <CardContent className="flex h-full flex-col gap-4 overflow-y-auto p-6">
          <p className="text-muted-foreground text-sm">“{answer.question}”</p>
          {answer.pending ? (
            <p className="text-muted-foreground animate-pulse text-sm">
              Thinking…
            </p>
          ) : (
            <Prose
              segments={answer.segments}
              numbers={numbers}
              onCitationClick={onCitationClick}
            />
          )}
        </CardContent>
      </Card>
    )
  }

  if (loading) {
    return (
      <Card className="min-h-0 flex-1 py-0">
        <CardContent className="text-muted-foreground p-6 text-center text-sm">
          Reading the project for you…
        </CardContent>
      </Card>
    )
  }

  if (segments.length === 0) {
    return (
      <Card className="min-h-0 flex-1 py-0">
        <CardContent className="text-muted-foreground p-6 text-center text-sm">
          Nothing here concerns you yet.
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="min-h-0 flex-1 overflow-hidden py-0">
      {/* Long summaries scroll here rather than pushing the composer off-screen. */}
      <CardContent className="h-full overflow-y-auto p-6">
        <Prose
          segments={segments}
          numbers={numbers}
          onCitationClick={onCitationClick}
        />
      </CardContent>
    </Card>
  )
}
