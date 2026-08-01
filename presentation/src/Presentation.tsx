import React from 'react'
import { Series } from 'remotion'
import '@fontsource-variable/geist'

import { seconds } from './theme'
import { Beyond, Close, Evidence, Gates, Pipeline, Problem, Title, TwoReaders } from './scenes'

/** Eight beats, in the order you'd actually argue it: what it is, why it's
 * needed, how it works, what it produces, why you can trust it, what that
 * unlocks. Timings are generous enough to read every card aloud. */
const beats = [
  { component: Title, hold: 4.5 },
  { component: Problem, hold: 8.5 },
  { component: Pipeline, hold: 8.5 },
  { component: TwoReaders, hold: 9 },
  { component: Evidence, hold: 8.5 },
  { component: Gates, hold: 7.5 },
  { component: Beyond, hold: 8 },
  { component: Close, hold: 5 },
]

export const TOTAL_FRAMES = beats.reduce((total, beat) => total + seconds(beat.hold), 0)

export const Presentation: React.FC = () => (
  <Series>
    {beats.map((beat, index) => (
      <Series.Sequence key={index} durationInFrames={seconds(beat.hold)}>
        <beat.component />
      </Series.Sequence>
    ))}
  </Series>
)
