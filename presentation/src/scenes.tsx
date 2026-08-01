import React from 'react'
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion'

import { theme } from './theme'
import {
  Backdrop,
  Badge,
  Card,
  EntryRow,
  Eyebrow,
  Heading,
  Mark,
  Prose,
  Rise,
  Sub,
  Toggle,
} from './ui'

const column: React.CSSProperties = { display: 'flex', flexDirection: 'column', gap: 34 }

/** 1 — the name, and the claim in one line. */
export const Title: React.FC = () => {
  const frame = useCurrentFrame()
  const { fps } = useVideoConfig()
  const sheen = interpolate(frame, [10, 90], [-40, 140], { extrapolateRight: 'clamp' })
  const mark = spring({ frame, fps, config: { damping: 200 } })

  return (
    <Backdrop>
      <div style={{ ...column, alignItems: 'center', textAlign: 'center', gap: 40 }}>
        <div style={{ transform: `scale(${mark})` }}>
          <Mark size={30} gap={12} />
        </div>
        <h1
          style={{
            fontSize: 168,
            fontWeight: 600,
            letterSpacing: -6,
            margin: 0,
            // The same travelling accent the login page uses.
            backgroundImage: `linear-gradient(100deg, ${theme.fg} ${sheen - 40}%, ${theme.brand} ${sheen}%, ${theme.fg} ${sheen + 40}%)`,
            WebkitBackgroundClip: 'text',
            backgroundClip: 'text',
            color: 'transparent',
          }}
        >
          Contextor
        </h1>
        <Rise delay={18}>
          <Sub>One record of what&rsquo;s true. Everyone reads it in their own terms.</Sub>
        </Rise>
      </div>
    </Backdrop>
  )
}

/** 2 — the problem, stated as the thing everyone has already lived. */
export const Problem: React.FC = () => {
  const people = [
    { who: 'Engineer', needs: 'Did anything change under my firmware?' },
    { who: 'Clinical scientist', needs: 'Do I have to re-run the study?' },
    { who: 'Regulatory counsel', needs: 'Does this move the filing?' },
    { who: 'Ops lead', needs: 'Does this move a date or a cost?' },
  ]

  return (
    <Backdrop>
      <div style={column}>
        <Rise>
          <Eyebrow>The problem</Eyebrow>
        </Rise>
        <Rise delay={6}>
          <Heading>
            One fact. Four people who need
            <br />
            four different things from it.
          </Heading>
        </Rise>
        <Rise delay={14}>
          <Card style={{ padding: '26px 34px', maxWidth: 900 }}>
            <div style={{ fontSize: 30, fontWeight: 500 }}>
              &ldquo;Bumped sampling to 2 kHz, added a debounce filter.&rdquo;
            </div>
          </Card>
        </Rise>
        <div style={{ display: 'flex', gap: 20, marginTop: 6 }}>
          {people.map((person, index) => (
            <Rise key={person.who} delay={22 + index * 5}>
              <Card style={{ width: 380, height: 190 }}>
                <div style={{ color: theme.brand, fontSize: 23, fontWeight: 600 }}>
                  {person.who}
                </div>
                <div style={{ fontSize: 26, marginTop: 14, lineHeight: 1.45 }}>{person.needs}</div>
              </Card>
            </Rise>
          ))}
        </div>
        <Rise delay={46}>
          <Sub>
            Today someone translates by hand, or nobody does and it surfaces three weeks late.
          </Sub>
        </Rise>
      </div>
    </Backdrop>
  )
}

/** 3 — the pipeline, which is the whole idea in three boxes. */
export const Pipeline: React.FC = () => {
  const frame = useCurrentFrame()
  const line = (delay: number) =>
    interpolate(frame, [delay, delay + 18], [0, 1], {
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
    })

  const box = (label: string, body: string, colour: string, soft: string) => (
    <Card accent={`${colour}55`} style={{ width: 440, background: soft }}>
      <div style={{ color: colour, fontSize: 24, fontWeight: 600, letterSpacing: 1 }}>{label}</div>
      <div style={{ fontSize: 27, marginTop: 12, lineHeight: 1.45 }}>{body}</div>
    </Card>
  )

  return (
    <Backdrop>
      <div style={column}>
        <Rise>
          <Eyebrow>How it works</Eyebrow>
        </Rise>
        <Rise delay={6}>
          <Heading>Not translation. Re-projection.</Heading>
        </Rise>

        <div style={{ display: 'flex', alignItems: 'center', gap: 26, marginTop: 20 }}>
          <Rise delay={16}>
            {box('WHAT SOMEONE SAID', 'In their own words, with their own assumptions.', theme.brand, '#fff')}
          </Rise>
          <div style={{ width: 70, height: 3, background: theme.line, position: 'relative' }}>
            <div
              style={{
                position: 'absolute',
                inset: 0,
                background: theme.brand,
                transformOrigin: 'left',
                transform: `scaleX(${line(26)})`,
              }}
            />
          </div>
          <Rise delay={30}>
            {box('THE RECORD', 'Neutral facts. One per fact. The same for everyone.', theme.ir, '#f7f7f8')}
          </Rise>
          <div style={{ width: 70, height: 3, background: theme.line, position: 'relative' }}>
            <div
              style={{
                position: 'absolute',
                inset: 0,
                background: theme.brand,
                transformOrigin: 'left',
                transform: `scaleX(${line(44)})`,
              }}
            />
          </div>
          <Rise delay={48}>
            {box('WHAT IT MEANS FOR YOU', 'Read through your own context, and filtered.', theme.brand, '#fff')}
          </Rise>
        </div>

        <Rise delay={62}>
          <Sub>
            The output can say things the input never did &mdash; and every claim traces back to a
            fact that does.
          </Sub>
        </Rise>
      </div>
    </Backdrop>
  )
}

/** 4 — the payload: one record, two readers, side by side. */
export const TwoReaders: React.FC = () => (
  <Backdrop>
    <div style={column}>
      <Rise>
        <Eyebrow>The same nine facts</Eyebrow>
      </Rise>
      <Rise delay={5}>
        <Heading size={64}>Read by two people who need opposite things.</Heading>
      </Rise>

      <div style={{ display: 'flex', gap: 30, marginTop: 10 }}>
        <Rise delay={16}>
          <Card style={{ width: 640, height: 330 }}>
            <div style={{ color: theme.brand, fontSize: 23, fontWeight: 600, marginBottom: 18 }}>
              ENGINEER
            </div>
            <Prose
              parts={[
                'The 1 kHz sampling rate and second-order anti-aliasing filter are now fixed; any further tweaks to rates or topologies will need a formal delta filing.',
                1,
                ' Detection firmware is the sole gatekeeper for false positives.',
                2,
              ]}
              size={26}
            />
          </Card>
        </Rise>
        <Rise delay={26}>
          <Card style={{ width: 640, height: 330 }}>
            <div style={{ color: theme.brand, fontSize: 23, fontWeight: 600, marginBottom: 18 }}>
              REGULATORY COUNSEL
            </div>
            <Prose
              parts={[
                'The debounce filter is a Class II modification under 21 CFR 807.81(a)(3). You will need a new 510(k) unless you can demonstrate substantial equivalence to the pre-filter predicate.',
                1,
                2,
              ]}
              size={26}
            />
          </Card>
        </Rise>
      </div>

      <Rise delay={40}>
        <Sub>
          Neither of them wrote that. Neither of them had to read the other&rsquo;s.
        </Sub>
      </Rise>
    </div>
  </Backdrop>
)

/** 5 — the toggle: prose, then the receipts for it. */
export const Evidence: React.FC = () => {
  const frame = useCurrentFrame()
  const flipped = frame > 70

  return (
    <Backdrop>
      <div style={{ ...column, alignItems: 'center' }}>
        <Rise>
          <Eyebrow>Cite, don&rsquo;t recite</Eyebrow>
        </Rise>
        <Rise delay={5}>
          <Heading size={62}>Flip it, and there are the receipts.</Heading>
        </Rise>

        <Rise delay={12}>
          <Toggle active={flipped ? 'IR' : 'NL'} />
        </Rise>

        <Rise delay={18}>
          <Card style={{ width: 1180, minHeight: 330 }}>
            {flipped ? (
              <div>
                <EntryRow cite={1} author="engineer" text="The biopotential front-end samples at 1 kHz." />
                <EntryRow cite={2} author="engineer" text="The front-end uses a second-order anti-aliasing filter." />
                <EntryRow cite={3} author="engineer" text="The device is being filed as a 510(k) with the Reveal LINQ II as predicate." />
                <EntryRow cite={4} author="biologist" text="A false-positive characterisation study is running against Holter recordings." />
              </div>
            ) : (
              <Prose
                parts={[
                  'The 1 kHz sampling rate and second-order anti-aliasing filter are now fixed for the 510(k) submission.',
                  1,
                  2,
                  3,
                  ' The false-positive rate is the single metric the clinical evidence package hinges on.',
                  4,
                ]}
                size={30}
              />
            )}
          </Card>
        </Rise>

        <Rise delay={26}>
          <Sub>
            Every claim resolves to real entries &mdash; checked server-side, not asked for in a
            prompt.
          </Sub>
        </Rise>
      </div>
    </Backdrop>
  )
}

/** 6 — nothing reaches the record without a person saying so. */
export const Gates: React.FC = () => {
  const steps = [
    { label: 'PROPOSED', body: 'What we understood. Nothing stored.', tone: theme.muted },
    { label: 'SUBMITTED', body: 'The author kept it. Still not a fact.', tone: theme.attention },
    { label: 'MERGED', body: 'An admin applied it. Now it is the record.', tone: theme.brand },
  ]

  return (
    <Backdrop>
      <div style={column}>
        <Rise>
          <Eyebrow>Trust</Eyebrow>
        </Rise>
        <Rise delay={5}>
          <Heading>A model reads. People decide.</Heading>
        </Rise>

        <div style={{ display: 'flex', gap: 24, marginTop: 16 }}>
          {steps.map((step, index) => (
            <Rise key={step.label} delay={14 + index * 10}>
              <Card style={{ width: 500, height: 210 }} accent={`${step.tone}44`}>
                <div style={{ color: step.tone, fontSize: 24, fontWeight: 600, letterSpacing: 2 }}>
                  {step.label}
                </div>
                <div style={{ fontSize: 28, marginTop: 16, lineHeight: 1.4 }}>{step.body}</div>
              </Card>
            </Rise>
          ))}
        </div>

        <Rise delay={48}>
          <Sub>
            Merging is the only way the record changes, so it is the only place that needs a gate.
          </Sub>
        </Rise>
      </div>
    </Backdrop>
  )
}

/** 7 — what the record can do once it exists. */
export const Beyond: React.FC = () => (
  <Backdrop>
    <div style={column}>
      <Rise>
        <Eyebrow>Because the record is structured</Eyebrow>
      </Rise>
      <Rise delay={5}>
        <Heading size={64}>It can notice things nobody asked it to.</Heading>
      </Rise>

      <div style={{ display: 'flex', gap: 28, marginTop: 14 }}>
        <Rise delay={16}>
          <Card style={{ width: 760 }} accent={`${theme.alarm}44`}>
            <div style={{ marginBottom: 20 }}>
              <Badge label="1 conflict" tone="alarm" />
            </div>
            <div style={{ color: theme.alarm, fontSize: 24, marginBottom: 18 }}>
              Enrolment cannot both target 240 patients and be committed to complete 300 before
              database lock.
            </div>
            <EntryRow author="biologist" text="The enrolment target is 240 patients." />
            <div style={{ height: 1, background: theme.line }} />
            <EntryRow author="business" text="Enrolment is committed to complete 300 patients." />
          </Card>
        </Rise>

        <Rise delay={28}>
          <Card style={{ width: 560, height: 380 }}>
            <div style={{ marginBottom: 22 }}>
              <Badge label="28 facts read" tone="brand" />
            </div>
            <div style={{ fontSize: 29, lineHeight: 1.45 }}>
              Drop in a spec and it enters the same way a sentence does &mdash; read, proposed,
              reviewed, merged.
            </div>
            <div style={{ fontSize: 24, color: theme.muted, marginTop: 22, lineHeight: 1.45 }}>
              Facts already on record come back as revisions, not duplicates.
            </div>
          </Card>
        </Rise>
      </div>
    </div>
  </Backdrop>
)

/** 8 — close on the name. */
export const Close: React.FC = () => {
  const frame = useCurrentFrame()
  const { fps } = useVideoConfig()
  const grow = spring({ frame, fps, config: { damping: 200 } })

  return (
    <AbsoluteFill
      style={{
        backgroundColor: theme.bg,
        backgroundImage: `radial-gradient(ellipse 60% 40% at 50% 50%, ${theme.brand}26, transparent)`,
        fontFamily: theme.font,
        color: theme.fg,
        alignItems: 'center',
        justifyContent: 'center',
        gap: 40,
      }}
    >
      <div style={{ transform: `scale(${grow})` }}>
        <Mark size={26} gap={11} />
      </div>
      <Rise delay={8}>
        <div style={{ fontSize: 128, fontWeight: 600, letterSpacing: -5 }}>Contextor</div>
      </Rise>
      <Rise delay={16}>
        <div style={{ fontSize: 34, color: theme.muted }}>
          Everyone reads the same record. Nobody reads the same thing.
        </div>
      </Rise>
    </AbsoluteFill>
  )
}
