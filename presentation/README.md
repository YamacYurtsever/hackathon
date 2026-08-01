# The Contextor presentation

An eight-beat animated deck, written in React and rendered to video with
[Remotion](https://remotion.dev). It reuses the product's own tokens — the
accent, the graphite, Geist, the NL/IR toggle, the badge chips — so the video
and the app can't drift apart, and the copy quotes real output rather than
invented marketing lines.

```bash
nvm use 22.21.0

npm install
npm run dev     # Remotion Studio: scrub, edit, hot-reload
npm run build   # renders out/contextor.mp4 (1920×1080, 30fps, ~60s)
npm run still   # a single frame as a PNG, for slides or a thumbnail
```

## The beats

| # | Scene | Says |
|---|-------|------|
| 1 | Title | What it's called, and the claim in one line |
| 2 | Problem | One fact, four people who need different things from it |
| 3 | Pipeline | Re-projection, not translation |
| 4 | Two readers | The same nine facts, read by an engineer and by counsel |
| 5 | Evidence | The toggle: prose, then the entries it was built from |
| 6 | Gates | A model reads, people decide |
| 7 | Beyond | Conflicts and document import, which the record makes possible |
| 8 | Close | The name |

Timings live in `src/Presentation.tsx` — one `hold` in seconds per beat, so
re-cutting to fit a slot is editing one number per scene. `src/theme.ts` holds
the colours; `src/ui.tsx` the shared pieces; `src/scenes.tsx` the beats.

## Notes

- **TypeScript is pinned to 5.x.** Remotion's bundler calls the classic
  `typescript.readConfigFile` API, which TS 7 doesn't expose the same way — on
  7.x the render fails before it starts.
- Remotion is free for individuals and small companies but a company above a
  certain size needs a licence. Worth checking before this goes anywhere
  commercial: <https://remotion.dev/license>
