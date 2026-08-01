import type { UiTheme } from '@/lib/ui-theme'
import { cn } from '@/lib/utils'

/** Portaled dialogs leave `.app-shell`, so they need the theme class reapplied
 * or they always render in the light `:root` tokens. */
export function themedDialogClass(theme: UiTheme, className?: string) {
  return cn(
    theme === 'obsidian' ? 'app-shell--obsidian' : 'app-shell--classic',
    className,
  )
}
