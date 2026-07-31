import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { extractIR } from '@/lib/extraction/extract'
import { FIXTURES, PROFILES, profileById, type Fixture } from '@/lib/extraction/fixtures'
import type { ExtractionResult } from '@/lib/extraction/types'
import { isVerbatim } from '@/lib/extraction/validate'
import { MISTRAL_MODELS, type MistralModel } from '@/lib/mistral'
import type { IREntry } from '@/types/ir'

const CERTAINTY_STYLES: Record<string, string> = {
  stated: 'bg-primary/10 text-primary',
  predicted: 'bg-chart-4/20 text-foreground',
  estimated: 'bg-chart-3/20 text-foreground',
  reported: 'bg-muted text-muted-foreground',
}

function str(value: unknown): string {
  return typeof value === 'string' ? value : ''
}

/** Keys rendered in their own row; everything else goes to the extra-fields block. */
const CONVENTION_KEYS = new Set(['statement', 'subject', 'source_quote', 'certainty'])

function EntryCard({ entry, sourceText }: { entry: IREntry; sourceText: string }) {
  const [showRaw, setShowRaw] = useState(false)
  const content = entry.content
  const certainty = str(content.certainty)
  const quote = str(content.source_quote)
  const verbatim = isVerbatim(quote, sourceText)
  const extras = Object.entries(content).filter(([key]) => !CONVENTION_KEYS.has(key))

  return (
    <div className="rounded-lg border border-border bg-card p-3">
      <div className="mb-2 flex items-start justify-between gap-3">
        <p className="text-sm leading-snug">{str(content.statement)}</p>
        <span
          className={`shrink-0 rounded px-1.5 py-0.5 text-[11px] font-medium ${
            CERTAINTY_STYLES[certainty] ?? 'bg-muted text-muted-foreground'
          }`}
        >
          {certainty || '—'}
        </span>
      </div>

      <p className="mb-2 text-xs text-muted-foreground">
        subject: <span className="text-foreground">{str(content.subject)}</span>
      </p>

      <blockquote
        className={`border-l-2 pl-2 text-xs italic ${
          verbatim ? 'border-primary/40 text-muted-foreground' : 'border-destructive text-destructive'
        }`}
      >
        “{quote}”
        <span className="ml-1.5 not-italic">{verbatim ? '✓ verbatim' : '✗ not in source'}</span>
      </blockquote>

      {extras.length > 0 && (
        <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-2 gap-y-0.5 text-xs">
          {extras.map(([key, value]) => (
            <div key={key} className="contents">
              <dt className="text-muted-foreground">{key}</dt>
              <dd className="font-mono text-[11px]">{JSON.stringify(value)}</dd>
            </div>
          ))}
        </dl>
      )}

      <button
        type="button"
        onClick={() => setShowRaw((open) => !open)}
        className="mt-2 text-[11px] text-muted-foreground underline underline-offset-2 hover:text-foreground"
      >
        {showRaw ? 'hide' : 'show'} raw IR entry
      </button>
      {showRaw && (
        <pre className="mt-1.5 overflow-x-auto rounded bg-muted p-2 text-[11px] leading-relaxed">
          {JSON.stringify(entry, null, 2)}
        </pre>
      )}
    </div>
  )
}

function ResultPanel({ result, sourceText }: { result: ExtractionResult; sourceText: string }) {
  const { entries, unresolved, rejected, diagnostics } = result

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-x-4 gap-y-1 rounded-lg bg-muted px-3 py-2 text-xs text-muted-foreground">
        <span>{entries.length} entries</span>
        <span>{unresolved.length} unresolved</span>
        <span className={rejected.length > 0 ? 'text-destructive' : undefined}>
          {rejected.length} rejected
        </span>
        <span>{diagnostics.attempts} attempt(s)</span>
        <span>{diagnostics.latencyMs} ms</span>
        {diagnostics.completionTokens !== null && (
          <span>
            {diagnostics.promptTokens}↑ / {diagnostics.completionTokens}↓ tok
          </span>
        )}
        <span>{diagnostics.model}</span>
      </div>

      <section className="space-y-2">
        {entries.map((entry) => (
          <EntryCard key={entry.id} entry={entry} sourceText={sourceText} />
        ))}
      </section>

      {unresolved.length > 0 && (
        <section>
          <h3 className="mb-1.5 text-xs font-semibold tracking-wide text-muted-foreground uppercase">
            Unresolved — asked, not invented
          </h3>
          <ul className="space-y-1.5">
            {unresolved.map((item, index) => (
              <li key={index} className="rounded-lg border border-dashed border-border p-2 text-xs">
                <span className="italic text-muted-foreground">“{item.quote}”</span>
                <p className="mt-0.5">{item.issue}</p>
              </li>
            ))}
          </ul>
        </section>
      )}

      {rejected.length > 0 && (
        <section>
          <h3 className="mb-1.5 text-xs font-semibold tracking-wide text-destructive uppercase">
            Rejected — failed grounding, dropped
          </h3>
          <ul className="space-y-1.5">
            {rejected.map((item, index) => (
              <li key={index} className="rounded-lg border border-destructive/40 p-2 text-xs">
                <p className="mb-1">{str(item.content.statement) || '(no statement)'}</p>
                <ul className="list-inside list-disc text-destructive">
                  {item.problems.map((problem) => (
                    <li key={problem}>{problem}</li>
                  ))}
                </ul>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  )
}

interface BatchRow {
  fixture: Fixture
  entries: number
  unresolved: number
  rejected: number
  missing: string[]
  error?: string
}

function checkExpectations(fixture: Fixture, result: ExtractionResult): BatchRow {
  const haystack = result.entries
    .map((entry) => str(entry.content.statement).toLowerCase())
    .join(' | ')

  return {
    fixture,
    entries: result.entries.length,
    unresolved: result.unresolved.length,
    rejected: result.rejected.length,
    missing: fixture.expect.mentions.filter((term) => !haystack.includes(term.toLowerCase())),
  }
}

export default function ExtractionLab() {
  const [text, setText] = useState(FIXTURES[0].text)
  const [authorId, setAuthorId] = useState(FIXTURES[0].authorId)
  const [model, setModel] = useState<MistralModel>('mistral-large-latest')
  const [result, setResult] = useState<ExtractionResult | null>(null)
  const [sourceText, setSourceText] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [batch, setBatch] = useState<BatchRow[] | null>(null)

  async function runOne() {
    setBusy(true)
    setError(null)
    setBatch(null)
    try {
      const extracted = await extractIR({
        text,
        author: authorId,
        profile: profileById(authorId),
        model,
      })
      setSourceText(text.trim())
      setResult(extracted)
    } catch (cause) {
      setResult(null)
      setError(cause instanceof Error ? cause.message : String(cause))
    } finally {
      setBusy(false)
    }
  }

  async function runAll() {
    setBusy(true)
    setError(null)
    setResult(null)
    const rows: BatchRow[] = []
    for (const fixture of FIXTURES) {
      try {
        const extracted = await extractIR({
          text: fixture.text,
          author: fixture.authorId,
          profile: profileById(fixture.authorId),
          model,
        })
        rows.push(checkExpectations(fixture, extracted))
      } catch (cause) {
        rows.push({
          fixture,
          entries: 0,
          unresolved: 0,
          rejected: 0,
          missing: [],
          error: cause instanceof Error ? cause.message : String(cause),
        })
      }
      setBatch([...rows])
    }
    setBusy(false)
  }

  function loadFixture(fixture: Fixture) {
    setText(fixture.text)
    setAuthorId(fixture.authorId)
    setResult(null)
    setBatch(null)
    setError(null)
  }

  return (
    <div className="mx-auto max-w-6xl p-6">
      <header className="mb-5">
        <h1 className="text-xl font-semibold">NL → IR extraction lab</h1>
        <p className="text-sm text-muted-foreground">
          Facts only. Consequences for other people are computed later, at re-projection time.
        </p>
      </header>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="space-y-3">
          <div className="flex flex-wrap gap-1.5">
            {FIXTURES.map((fixture) => (
              <Button
                key={fixture.id}
                size="xs"
                variant={text === fixture.text ? 'secondary' : 'outline'}
                onClick={() => loadFixture(fixture)}
              >
                {fixture.label}
              </Button>
            ))}
          </div>

          <textarea
            value={text}
            onChange={(event) => setText(event.target.value)}
            rows={5}
            className="w-full resize-y rounded-lg border border-border bg-background p-3 text-sm outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
            placeholder="Post a message the way you would actually write it…"
          />

          <div className="flex flex-wrap items-center gap-2">
            <select
              value={authorId}
              onChange={(event) => setAuthorId(event.target.value)}
              className="h-8 rounded-lg border border-border bg-background px-2 text-sm"
            >
              {PROFILES.map((profile) => (
                <option key={profile.id} value={profile.id}>
                  {str(profile.content.name)}
                </option>
              ))}
            </select>

            <select
              value={model}
              onChange={(event) => setModel(event.target.value as MistralModel)}
              className="h-8 rounded-lg border border-border bg-background px-2 text-sm"
            >
              {MISTRAL_MODELS.map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
            </select>

            <Button onClick={runOne} disabled={busy || !text.trim()}>
              {busy ? 'Extracting…' : 'Extract'}
            </Button>
            <Button variant="outline" onClick={runAll} disabled={busy}>
              Run all fixtures
            </Button>
          </div>

          <details className="rounded-lg border border-border p-2 text-xs">
            <summary className="cursor-pointer text-muted-foreground">
              Author profile sent as disambiguation context
            </summary>
            <pre className="mt-2 overflow-x-auto text-[11px] leading-relaxed">
              {JSON.stringify(profileById(authorId)?.content ?? {}, null, 2)}
            </pre>
          </details>
        </div>

        <div>
          {error && (
            <div className="rounded-lg border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive">
              {error}
            </div>
          )}

          {result && <ResultPanel result={result} sourceText={sourceText} />}

          {batch && (
            <table className="w-full text-left text-xs">
              <thead className="text-muted-foreground">
                <tr>
                  <th className="pb-1 font-medium">Fixture</th>
                  <th className="pb-1 font-medium">Entries</th>
                  <th className="pb-1 font-medium">Unres.</th>
                  <th className="pb-1 font-medium">Rej.</th>
                  <th className="pb-1 font-medium">Notes</th>
                </tr>
              </thead>
              <tbody>
                {batch.map((row) => {
                  const short = row.entries < row.fixture.expect.minEntries
                  return (
                    <tr key={row.fixture.id} className="border-t border-border align-top">
                      <td className="py-1.5 pr-2">{row.fixture.label}</td>
                      <td className={`py-1.5 pr-2 ${short ? 'text-destructive' : ''}`}>
                        {row.entries}/{row.fixture.expect.minEntries}
                      </td>
                      <td className="py-1.5 pr-2">{row.unresolved}</td>
                      <td className={`py-1.5 pr-2 ${row.rejected > 0 ? 'text-destructive' : ''}`}>
                        {row.rejected}
                      </td>
                      <td className="py-1.5 text-muted-foreground">
                        {row.error ?? (row.missing.length > 0 ? `missing: ${row.missing.join(', ')}` : 'ok')}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}

          {!error && !result && !batch && (
            <p className="text-sm text-muted-foreground">
              Pick a fixture or write a message, then extract.
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
