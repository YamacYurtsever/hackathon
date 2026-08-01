import React from 'react'
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion'

import { theme } from './theme'

/** Everything enters the same way: a short rise with a spring, staggered by
 * index. Consistent motion is most of what makes a deck feel deliberate. */
export const Rise: React.FC<{
  children: React.ReactNode
  delay?: number
  distance?: number
  style?: React.CSSProperties
}> = ({ children, delay = 0, distance = 24, style }) => {
  const frame = useCurrentFrame()
  const { fps } = useVideoConfig()
  const progress = spring({
    frame: frame - delay,
    fps,
    config: { damping: 200, mass: 0.6 },
  })

  return (
    <div
      style={{
        opacity: progress,
        transform: `translateY(${(1 - progress) * distance}px)`,
        ...style,
      }}
    >
      {children}
    </div>
  )
}

/** The page the app sits on: a faint accent pool at the top, nothing else. */
export const Backdrop: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <AbsoluteFill
    style={{
      backgroundColor: theme.bg,
      backgroundImage: `radial-gradient(ellipse 70% 45% at 50% -8%, ${theme.brand}1f, transparent)`,
      fontFamily: theme.font,
      color: theme.fg,
      padding: 110,
      justifyContent: 'center',
    }}
  >
    {children}
  </AbsoluteFill>
)

/** The two readings, side by side. The product's mark, and its whole argument. */
export const Mark: React.FC<{ size?: number; gap?: number }> = ({ size = 22, gap = 8 }) => (
  <div style={{ display: 'flex', gap, alignItems: 'center' }}>
    <div style={{ width: size, height: size, borderRadius: 999, background: theme.brand }} />
    <div style={{ width: size, height: size, borderRadius: 999, background: '#00000029' }} />
  </div>
)

export const Eyebrow: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div
    style={{
      fontSize: 24,
      letterSpacing: 3,
      textTransform: 'uppercase',
      color: theme.brand,
      fontWeight: 600,
    }}
  >
    {children}
  </div>
)

export const Heading: React.FC<{ children: React.ReactNode; size?: number }> = ({
  children,
  size = 74,
}) => (
  <h1
    style={{
      fontSize: size,
      lineHeight: 1.08,
      letterSpacing: -2,
      fontWeight: 600,
      margin: 0,
      maxWidth: 1400,
    }}
  >
    {children}
  </h1>
)

export const Sub: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <p style={{ fontSize: 32, lineHeight: 1.5, color: theme.muted, margin: 0, maxWidth: 1150 }}>
    {children}
  </p>
)

export const Card: React.FC<{
  children: React.ReactNode
  accent?: string
  style?: React.CSSProperties
}> = ({ children, accent, style }) => (
  <div
    style={{
      background: theme.card,
      border: `1px solid ${accent ?? theme.line}`,
      borderRadius: 20,
      padding: 32,
      boxShadow: '0 1px 2px rgba(0,0,0,0.04), 0 24px 48px -28px rgba(0,0,0,0.25)',
      ...style,
    }}
  >
    {children}
  </div>
)

/** A header chip, exactly as the app renders one. */
export const Badge: React.FC<{ label: string; tone: 'brand' | 'attention' | 'alarm' }> = ({
  label,
  tone,
}) => {
  const colour = { brand: theme.brand, attention: theme.attention, alarm: theme.alarm }[tone]
  const soft = { brand: theme.brandSoft, attention: theme.attentionSoft, alarm: theme.alarmSoft }[
    tone
  ]
  return (
    <div
      style={{
        display: 'inline-flex',
        alignSelf: 'flex-start',
        width: 'fit-content',
        alignItems: 'center',
        gap: 10,
        background: soft,
        color: colour,
        border: `1px solid ${colour}44`,
        borderRadius: 999,
        padding: '10px 20px',
        fontSize: 24,
        fontWeight: 500,
      }}
    >
      <div style={{ width: 9, height: 9, borderRadius: 999, background: colour }} />
      {label}
    </div>
  )
}

/** The NL | IR toggle, with the pill parked on whichever side is active. */
export const Toggle: React.FC<{ active: 'NL' | 'IR' }> = ({ active }) => {
  const frame = useCurrentFrame()
  const { fps } = useVideoConfig()
  const slide = spring({ frame, fps, config: { damping: 200 } })
  const onIr = active === 'IR'

  return (
    <div
      style={{
        position: 'relative',
        display: 'flex',
        background: '#f4f4f5',
        borderRadius: 999,
        padding: 6,
        width: 260,
      }}
    >
      <div
        style={{
          position: 'absolute',
          top: 6,
          bottom: 6,
          left: 6,
          width: 124,
          borderRadius: 999,
          background: onIr ? theme.ir : theme.brand,
          transform: `translateX(${onIr ? slide * 124 : 0}px)`,
        }}
      />
      {(['NL', 'IR'] as const).map((label) => (
        <div
          key={label}
          style={{
            position: 'relative',
            width: 124,
            textAlign: 'center',
            padding: '10px 0',
            fontSize: 26,
            fontWeight: 500,
            color: label === active ? '#fff' : theme.muted,
          }}
        >
          {label}
        </div>
      ))}
    </div>
  )
}

/** One IR row: time, author, the neutral fact. */
export const EntryRow: React.FC<{ author: string; text: string; cite?: number }> = ({
  author,
  text,
  cite,
}) => (
  <div style={{ display: 'flex', gap: 18, alignItems: 'baseline', padding: '14px 0' }}>
    {cite !== undefined && (
      <span
        style={{
          background: theme.brandSoft,
          color: theme.brand,
          borderRadius: 8,
          padding: '4px 12px',
          fontSize: 20,
          fontWeight: 600,
        }}
      >
        {cite}
      </span>
    )}
    <span style={{ fontSize: 22, color: theme.muted, minWidth: 130 }}>{author}</span>
    <span style={{ fontSize: 26 }}>{text}</span>
  </div>
)

/** Prose with the citation markers the product shows. */
export const Prose: React.FC<{ parts: (string | number)[]; size?: number }> = ({
  parts,
  size = 27,
}) => (
  <p style={{ fontSize: size, lineHeight: 1.65, margin: 0 }}>
    {parts.map((part, index) =>
      typeof part === 'number' ? (
        <sup key={index} style={{ color: theme.brand, fontSize: size * 0.55, fontWeight: 600 }}>
          {' '}
          [{part}]
        </sup>
      ) : (
        <React.Fragment key={index}>{part}</React.Fragment>
      ),
    )}
  </p>
)

export const fadeOut = (frame: number, at: number) =>
  interpolate(frame, [at, at + 12], [1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' })
