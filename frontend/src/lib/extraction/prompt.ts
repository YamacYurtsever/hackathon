import type { IREntry, Profile } from '@/types/ir'
import type { RejectedCandidate } from './types'

/**
 * The IR schema leaves `content` free-form on purpose. This is a *soft*
 * convention, not a template: four keys we ask for every time so downstream
 * re-projection has something to rely on, plus explicit permission to add
 * whatever else the fact needs. Loosen or tighten it here — it is the single
 * place the shape of extracted content is decided.
 */
export const CONTENT_CONVENTION = `Every content object SHOULD carry these four keys:
  "statement"    - one neutral sentence stating the fact. No discipline jargon,
                   no hedging, no audience-specific framing.
  "subject"      - short canonical name of the thing the fact is about
                   (e.g. "ECG sensor sampling rate"). Reuse an existing subject
                   string verbatim when the fact concerns something already known.
  "source_quote" - a VERBATIM span copied from the input text. Must appear in the
                   input character-for-character. This is what the UI shows when a
                   user clicks a citation, so it must be real.
  "certainty"    - one of: "stated" (asserted as fact by the author),
                   "predicted" (expected but not yet observed),
                   "estimated" (approximate figure), or
                   "reported" (relayed from someone/something else).

Beyond those four, add any keys the fact genuinely needs. Suggestions, not rules:
  - quantities as objects with units: {"value": 2000, "unit": "Hz"}
  - changes as "previous" and "current"
  - dates as ISO strings
Do not pad content with keys that carry no information.`

const RULES = `You extract atomic facts from a team message into a project's neutral
Intermediate Representation (IR).

RULES

1. ATOMIC. One entry per fact. A message stating three things produces three
   entries. Never bundle unrelated facts into one entry.

2. NEUTRAL, NOT SIMPLIFIED. Strip framing that belongs to the author's
   discipline, but keep every bit of technical precision. "2 kHz" stays "2 kHz";
   it does not become "a higher rate". You are removing perspective, not detail.

3. GROUND EVERYTHING. Every entry needs a source_quote that appears verbatim in
   the input. If you cannot quote it, you may not claim it.

4. NEVER INVENT. If the message implies something without specifying it — a
   value, a date, a mechanism — do NOT fill it in. Put it in "unresolved" with
   the quote that raised the question. An unresolved item is a success, not a
   failure.

5. SAY WHAT WAS SAID, NOT WHAT IT MEANS. Do not extract consequences,
   downstream impacts, or implications for other disciplines. A prediction the
   author made is a fact about their prediction (certainty "predicted"); a
   consequence you worked out yourself is not extractable. Something else
   computes those later.

6. NO ENVELOPE FIELDS. Never emit "id", "author" or "created_at" — those are
   assigned outside the model.

OUTPUT
Return a single JSON object:
{
  "entries": [ { "content": { ... } } ],
  "unresolved": [ { "quote": "...", "issue": "..." } ]
}
Both keys are required; use [] when empty.`

const EXAMPLE = `EXAMPLE

Input: "Bumped sampling rate to 2kHz, added debounce filter, should cut false positives."

Output:
{
  "entries": [
    {
      "content": {
        "statement": "The ECG sensor sampling rate was raised from its previous setting to 2 kHz.",
        "subject": "ECG sensor sampling rate",
        "source_quote": "Bumped sampling rate to 2kHz",
        "certainty": "stated",
        "current": { "value": 2000, "unit": "Hz" },
        "change_type": "increase"
      }
    },
    {
      "content": {
        "statement": "A debounce filter was added to the detection signal chain.",
        "subject": "detection signal chain",
        "source_quote": "added debounce filter",
        "certainty": "stated",
        "change_type": "addition"
      }
    },
    {
      "content": {
        "statement": "The author expects these changes to reduce the false positive rate.",
        "subject": "false positive rate",
        "source_quote": "should cut false positives",
        "certainty": "predicted",
        "expected_direction": "decrease"
      }
    }
  ],
  "unresolved": [
    {
      "quote": "added debounce filter",
      "issue": "No time constant, window length, or position in the signal chain was given."
    },
    {
      "quote": "should cut false positives",
      "issue": "No magnitude given and no measurement taken; recorded as a prediction, not as a new false positive rate."
    }
  ]
}

Note the third entry: the author's prediction is recorded as a prediction. Note
also what is absent — nothing about validation studies, filings or schedules.
Those are consequences, and consequences are not extracted.`

export const EXTRACTION_SYSTEM_PROMPT = `${RULES}\n\n${CONTENT_CONVENTION}\n\n${EXAMPLE}`

function describeProfile(profile?: Profile | null): string {
  if (!profile) return ''
  return `AUTHOR CONTEXT
The message was written by this person. Use it only to resolve shorthand and
jargon — it must NOT colour the extracted facts, which stay neutral.
${JSON.stringify(profile.content, null, 2)}

`
}

function describeExisting(entries: readonly IREntry[]): string {
  if (entries.length === 0) return ''
  const subjects = [
    ...new Set(
      entries
        .map((entry) => entry.content.subject)
        .filter((subject): subject is string => typeof subject === 'string'),
    ),
  ]
  if (subjects.length === 0) return ''
  return `KNOWN SUBJECTS
Reuse these strings verbatim when a new fact is about the same thing:
${subjects.map((subject) => `  - ${subject}`).join('\n')}

`
}

export function buildExtractionPrompt(
  text: string,
  profile?: Profile | null,
  existing: readonly IREntry[] = [],
): string {
  return `${describeProfile(profile)}${describeExisting(existing)}MESSAGE TO EXTRACT
"""
${text}
"""`
}

/** Second-chance prompt: hand the model its own failures and ask for a fix. */
export function buildRepairPrompt(
  original: string,
  rejected: readonly RejectedCandidate[],
): string {
  const listed = rejected
    .map(
      (item, index) =>
        `${index + 1}. ${JSON.stringify(item.content)}\n   problems: ${item.problems.join('; ')}`,
    )
    .join('\n')

  return `${original}

YOUR PREVIOUS ATTEMPT HAD REJECTED ENTRIES
${listed}

Re-extract the message from scratch. The most common failure is a source_quote
that is not a character-for-character span of the input — copy and paste it,
never paraphrase or reconstruct it. Drop any fact you cannot quote.`
}
