const STORAGE_KEY = 'ct:uiTheme'
const LEGACY_KEY = 'ct:homeTheme'

export type UiTheme = 'obsidian' | 'classic'

/** @deprecated Use UiTheme — kept so existing home imports keep typechecking. */
export type HomeTheme = UiTheme

export function readUiTheme(): UiTheme {
  const stored = localStorage.getItem(STORAGE_KEY) ?? localStorage.getItem(LEGACY_KEY)
  return stored === 'classic' ? 'classic' : 'obsidian'
}

export function writeUiTheme(theme: UiTheme) {
  localStorage.setItem(STORAGE_KEY, theme)
  localStorage.setItem(LEGACY_KEY, theme)
}

export const readHomeTheme = readUiTheme
export const writeHomeTheme = writeUiTheme
