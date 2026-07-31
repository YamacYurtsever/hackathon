// Thin Mistral chat client. Talks to the /api/mistral proxy defined in
// vite.config.ts, which attaches the API key server-side.

const BASE_URL = '/api/mistral'

export const MISTRAL_MODELS = [
  'mistral-large-latest',
  'mistral-medium-latest',
  'mistral-small-latest',
] as const

export type MistralModel = (typeof MISTRAL_MODELS)[number]

export interface Usage {
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
}

export interface ChatJSONResult {
  /** Parsed JSON object returned by the model. */
  data: unknown
  /** Raw assistant text, kept so the lab can show exactly what came back. */
  raw: string
  usage: Usage | null
  latencyMs: number
}

export class MistralError extends Error {
  status?: number
  body?: string

  constructor(message: string, status?: number, body?: string) {
    super(message)
    this.name = 'MistralError'
    this.status = status
    this.body = body
  }
}

export interface ChatJSONOptions {
  system: string
  user: string
  model?: MistralModel
  /** Low by default: extraction should be reproducible, not creative. */
  temperature?: number
  signal?: AbortSignal
}

export async function chatJSON({
  system,
  user,
  model = 'mistral-large-latest',
  temperature = 0.1,
  signal,
}: ChatJSONOptions): Promise<ChatJSONResult> {
  const startedAt = performance.now()

  let response: Response
  try {
    response = await fetch(`${BASE_URL}/v1/chat/completions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      signal,
      body: JSON.stringify({
        model,
        temperature,
        response_format: { type: 'json_object' },
        messages: [
          { role: 'system', content: system },
          { role: 'user', content: user },
        ],
      }),
    })
  } catch (cause) {
    if (cause instanceof DOMException && cause.name === 'AbortError') throw cause
    throw new MistralError(
      'Could not reach the Mistral proxy. Is the Vite dev server running?',
    )
  }

  const latencyMs = Math.round(performance.now() - startedAt)

  if (!response.ok) {
    const body = await response.text()
    const hint =
      response.status === 401
        ? ' Set MISTRAL_API_KEY in frontend/.env.local and restart the dev server.'
        : ''
    throw new MistralError(
      `Mistral returned ${response.status}.${hint}`,
      response.status,
      body,
    )
  }

  const payload = (await response.json()) as {
    choices?: { message?: { content?: string } }[]
    usage?: Usage
  }

  const raw = payload.choices?.[0]?.message?.content
  if (!raw) throw new MistralError('Mistral returned no message content.')

  let data: unknown
  try {
    data = JSON.parse(raw)
  } catch {
    throw new MistralError(`Model did not return valid JSON: ${raw.slice(0, 200)}`)
  }

  return { data, raw, usage: payload.usage ?? null, latencyMs }
}
