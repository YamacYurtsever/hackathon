import type { Candidate, Unresolved } from './types'

export const CERTAINTY_VALUES = ['stated', 'predicted', 'estimated', 'reported'] as const

/** Envelope fields the model must never author. Stripped, not rejected. */
const RESERVED_KEYS = ['id', 'author', 'created_at']

/**
 * Whitespace, case and punctuation-style differences are not hallucinations —
 * models routinely straighten curly quotes or re-wrap lines. Everything else is.
 */
export function normalizeForQuoteMatch(text: string): string {
  return text
    .toLowerCase()
    .replace(/[‘’‛]/g, "'")
    .replace(/[“”]/g, '"')
    .replace(/[‐-―]/g, '-')
    .replace(/\s+/g, ' ')
    .trim()
}

/** The mechanical form of the grounding guardrail: a quote must really be in the source. */
export function isVerbatim(quote: string, sourceText: string): boolean {
  const needle = normalizeForQuoteMatch(quote)
  if (!needle) return false
  return normalizeForQuoteMatch(sourceText).includes(needle)
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === 'string' && value.trim().length > 0
}

/**
 * Validates one candidate against the soft content convention. Returns the
 * problems found; an empty array means the candidate is usable.
 */
export function validateCandidate(
  content: Record<string, unknown>,
  sourceText: string,
): string[] {
  const problems: string[] = []

  if (Object.keys(content).length === 0) {
    return ['content is empty']
  }

  if (!isNonEmptyString(content.statement)) {
    problems.push('missing "statement"')
  }
  if (!isNonEmptyString(content.subject)) {
    problems.push('missing "subject"')
  }

  const certainty = content.certainty
  if (!isNonEmptyString(certainty)) {
    problems.push('missing "certainty"')
  } else if (!(CERTAINTY_VALUES as readonly string[]).includes(certainty)) {
    problems.push(`"certainty" is "${certainty}", expected one of ${CERTAINTY_VALUES.join(', ')}`)
  }

  const quote = content.source_quote
  if (!isNonEmptyString(quote)) {
    problems.push('missing "source_quote" — an ungrounded fact cannot be shown')
  } else if (!isVerbatim(quote, sourceText)) {
    problems.push(`"source_quote" is not verbatim in the input: ${JSON.stringify(quote)}`)
  }

  return problems
}

/** Drops envelope fields the model should not have authored. */
export function stripReservedKeys(content: Record<string, unknown>): Record<string, unknown> {
  const cleaned = { ...content }
  for (const key of RESERVED_KEYS) delete cleaned[key]
  return cleaned
}

interface ParsedResponse {
  candidates: Candidate[]
  unresolved: Unresolved[]
}

/** Coerces a raw model response into candidates, tolerating minor shape drift. */
export function parseModelResponse(data: unknown): ParsedResponse {
  if (typeof data !== 'object' || data === null) {
    throw new Error('Model response was not a JSON object.')
  }

  const record = data as Record<string, unknown>
  const rawEntries = Array.isArray(record.entries) ? record.entries : []
  const rawUnresolved = Array.isArray(record.unresolved) ? record.unresolved : []

  const candidates: Candidate[] = []
  for (const entry of rawEntries) {
    if (typeof entry !== 'object' || entry === null) continue
    const asRecord = entry as Record<string, unknown>
    // Accept both {content: {...}} and a bare content object.
    const content =
      typeof asRecord.content === 'object' && asRecord.content !== null
        ? (asRecord.content as Record<string, unknown>)
        : asRecord
    candidates.push({ content: stripReservedKeys(content) })
  }

  const unresolved: Unresolved[] = []
  for (const item of rawUnresolved) {
    if (typeof item !== 'object' || item === null) continue
    const asRecord = item as Record<string, unknown>
    if (isNonEmptyString(asRecord.issue)) {
      unresolved.push({
        quote: isNonEmptyString(asRecord.quote) ? asRecord.quote : '',
        issue: asRecord.issue,
      })
    }
  }

  return { candidates, unresolved }
}
