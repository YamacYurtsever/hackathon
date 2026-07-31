import type { IREntry } from '@/types/ir'

/**
 * What the model is asked to emit per fact. Deliberately NOT a full IREntry:
 * `id`, `author` and `created_at` are assigned by us (and by the server later),
 * never by the model.
 */
export interface Candidate {
  content: Record<string, unknown>
}

/** Something the input gestured at but did not pin down. Surfaced, never invented. */
export interface Unresolved {
  quote: string
  issue: string
}

export interface RejectedCandidate {
  content: Record<string, unknown>
  problems: string[]
}

export interface ExtractionDiagnostics {
  attempts: number
  latencyMs: number
  promptTokens: number | null
  completionTokens: number | null
  model: string
  /** Raw assistant text of the final attempt, for eyeballing in the lab. */
  raw: string
}

export interface ExtractionResult {
  entries: IREntry[]
  unresolved: Unresolved[]
  /** Candidates that failed validation twice and were dropped rather than shown. */
  rejected: RejectedCandidate[]
  diagnostics: ExtractionDiagnostics
}
