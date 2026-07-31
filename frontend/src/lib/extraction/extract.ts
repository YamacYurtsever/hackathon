import { chatJSON, type MistralModel } from '@/lib/mistral'
import type { IREntry, Profile } from '@/types/ir'
import {
  EXTRACTION_SYSTEM_PROMPT,
  buildExtractionPrompt,
  buildRepairPrompt,
} from './prompt'
import type { ExtractionResult, RejectedCandidate, Unresolved } from './types'
import { parseModelResponse, validateCandidate } from './validate'

export interface ExtractOptions {
  text: string
  /** User id recorded as the entry author. */
  author: string
  /** Author's profile — used only to resolve shorthand, never to colour facts. */
  profile?: Profile | null
  /** Entries already in the project, so subjects get reused instead of duplicated. */
  existing?: readonly IREntry[]
  model?: MistralModel
  signal?: AbortSignal
}

/**
 * NL → IR. Runs extraction, validates every candidate against the grounding
 * rules, and gives the model exactly one chance to repair its failures before
 * dropping them.
 *
 * Invalid entries are never returned as if they were good: they land in
 * `rejected` so the lab can show what was thrown away and why.
 */
export async function extractIR({
  text,
  author,
  profile,
  existing = [],
  model = 'mistral-large-latest',
  signal,
}: ExtractOptions): Promise<ExtractionResult> {
  const source = text.trim()
  if (!source) throw new Error('Nothing to extract — the message is empty.')

  const basePrompt = buildExtractionPrompt(source, profile, existing)

  let attempts = 0
  let latencyMs = 0
  let promptTokens = 0
  let completionTokens = 0
  let raw = ''

  let accepted: Record<string, unknown>[] = []
  let rejected: RejectedCandidate[] = []
  let unresolved: Unresolved[] = []

  for (let attempt = 0; attempt < 2; attempt += 1) {
    const prompt = attempt === 0 ? basePrompt : buildRepairPrompt(basePrompt, rejected)

    const result = await chatJSON({
      system: EXTRACTION_SYSTEM_PROMPT,
      user: prompt,
      model,
      signal,
    })

    attempts += 1
    latencyMs += result.latencyMs
    promptTokens += result.usage?.prompt_tokens ?? 0
    completionTokens += result.usage?.completion_tokens ?? 0
    raw = result.raw

    const parsed = parseModelResponse(result.data)

    accepted = []
    rejected = []
    for (const candidate of parsed.candidates) {
      const problems = validateCandidate(candidate.content, source)
      if (problems.length === 0) accepted.push(candidate.content)
      else rejected.push({ content: candidate.content, problems })
    }
    unresolved = parsed.unresolved

    if (rejected.length === 0) break
  }

  const createdAt = new Date().toISOString()
  const entries: IREntry[] = accepted.map((content) => ({
    id: crypto.randomUUID(),
    content,
    author,
    created_at: createdAt,
  }))

  return {
    entries,
    unresolved,
    rejected,
    diagnostics: {
      attempts,
      latencyMs,
      promptTokens: promptTokens || null,
      completionTokens: completionTokens || null,
      model,
      raw,
    },
  }
}
