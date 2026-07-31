# NL → IR extraction lab

A working prototype of the extraction half of the core pipeline: a natural
language message in, atomic IR entry `content` objects out.

**Status: deliberately not wired to anything.** Nothing imports these files.
They are parked here so the prompt and validation work isn't lost, and so
whoever picks up Milestone 5 has a tested starting point rather than a blank
page.

## What's here

| File | Role |
| --- | --- |
| `prompt.ts` | Extraction system prompt, the content convention, and the repair prompt |
| `validate.ts` | Grounding checks — pure functions, no network, no React |
| `extract.ts` | Orchestration: call → validate → one repair retry → assemble entries |
| `fixtures.ts` | Four MedGuard profiles and five test messages with expectations |
| `types.ts` | Shared types |
| `../mistral.ts` | Thin Mistral chat client |
| `../../components/ExtractionLab.tsx` | Dev UI for eyeballing output |

## To wire it up you need two things

Neither is done, on purpose:

1. **A Mistral proxy.** `mistral.ts` posts to `/api/mistral/v1/chat/completions`,
   which nothing currently serves. It previously came from a `server.proxy`
   entry in `vite.config.ts` that attached `MISTRAL_API_KEY` server-side so the
   key never entered the browser bundle. That entry is gone.
2. **A route.** `ExtractionLab.tsx` default-exports a page component that isn't
   referenced by `App.tsx`.

## Read this before wiring it into the frontend

Milestone 5 puts extraction in the **backend** (`POST /api/projects/:id/messages`),
which is the right call — client-side extraction means a message's IR could be
forged by whoever posts it.

So the likely path is not "wire this into the app" but "port `prompt.ts` and
`validate.ts` to Python and delete the rest." The two files worth porting are
pure logic with no React and no frontend dependencies, specifically so that
port is easy.

## Design notes worth keeping

**The content convention is soft.** The IR schema leaves `content` free-form.
`CONTENT_CONVENTION` in `prompt.ts` asks for four keys every time — `statement`,
`subject`, `source_quote`, `certainty` — and explicitly invites extra keys per
fact. Change the shape there; it's the single place it's decided.

**Verbatim quoting is the grounding guardrail, mechanized.** Every entry carries
a `source_quote` that must appear character-for-character in the input
(normalizing only whitespace, case and curly quotes). A fabricated quote fails
validation, gets one repair attempt, then is dropped rather than displayed.

**Extraction records facts only, never consequences.** Rule 5 of the prompt
forbids inferring implications for other disciplines. Cross-context propagation
is computed at re-projection time, so baking consequences into stored entries
would both duplicate that work and create update anomalies.

## Tested state

All five fixtures passed against live `mistral-large-latest`: zero rejections,
zero repair retries, correct atomicity, and no consequence leakage on the
canonical demo message.

One known gap: the verbatim check only guards `source_quote`. Other keys are
unchecked, and the model was observed inventing a year — `"14 March"` in the
input became `"date": "2024-03-14"` in the output. Any port should add a rule
against adding precision the input didn't contain, plus a check for years absent
from the source text.
