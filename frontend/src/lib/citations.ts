import type { Segment } from '@/types/ir'

/** Numbers the cited entries in order of first appearance, so markers read like
 * real citations — [1] is the same entry everywhere it shows up. */
export function citationNumbers(segments: Segment[]): Map<string, number> {
  const numbers = new Map<string, number>()
  for (const segment of segments) {
    for (const entryId of segment.source_entry_ids) {
      if (!numbers.has(entryId)) numbers.set(entryId, numbers.size + 1)
    }
  }
  return numbers
}
