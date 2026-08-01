/** The product's own tokens, so the video and the app can't drift apart.
 * Values are the sRGB equivalents of the oklch() in frontend/src/index.css. */
export const theme = {
  bg: '#ffffff',
  fg: '#242424',
  muted: '#8a8a8a',
  line: '#e8e8e8',
  card: '#ffffff',

  // NL is the interpreted reading, so it carries the accent. IR is the record
  // and stays graphite — the same distinction the app makes.
  brand: '#5b53d6',
  brandSoft: '#eeedfb',
  ir: '#242424',

  attention: '#b5751f',
  attentionSoft: '#fbf3e8',
  alarm: '#d13b3b',
  alarmSoft: '#fbeded',

  font: "'Geist Variable', -apple-system, BlinkMacSystemFont, sans-serif",
} as const

export const FPS = 30
export const seconds = (n: number) => Math.round(n * FPS)
