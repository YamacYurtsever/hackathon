import { Card, CardContent } from '@/components/ui/card'
import type { Segment } from '@/types/ir'

export function SummaryPanel({
  segments,
  loading,
  numbers,
  onCitationClick,
}: {
  segments: Segment[]
  loading: boolean
  numbers: Map<string, number>
  onCitationClick: (entryId: string) => void
}) {
  if (loading) {
    return (
      <Card className="min-h-0 flex-1">
        <CardContent className="text-muted-foreground py-8 text-center text-sm">
          Reading the project for you…
        </CardContent>
      </Card>
    )
  }

  if (segments.length === 0) {
    return (
      <Card className="min-h-0 flex-1">
        <CardContent className="text-muted-foreground py-8 text-center text-sm">
          Nothing here concerns you yet.
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="min-h-0 flex-1 overflow-hidden">
      {/* Long summaries scroll here rather than pushing the composer off-screen. */}
      <CardContent className="h-full overflow-y-auto py-6">
        {/* One flowing block, not one row per segment — the seams between
            segments shouldn't be visible to the reader. */}
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
      </CardContent>
    </Card>
  )
}
