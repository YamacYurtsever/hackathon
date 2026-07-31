import { Link } from 'react-router-dom'

/** The way in. Login and signup differ by a few words, so they share
 * everything else — and the name sits above the card rather than inside it,
 * because it's the product speaking, not a field label. */
export function AuthLayout({
  title,
  subtitle,
  children,
  footer,
}: {
  title: string
  subtitle: string
  children: React.ReactNode
  footer: React.ReactNode
}) {
  return (
    <div className="relative flex min-h-svh flex-col items-center justify-center overflow-hidden p-6">
      {/* Ambient light rather than a flat page: two accent pools, well out of
          the way of the text they sit behind. */}
      <div aria-hidden className="pointer-events-none absolute inset-0 -z-10">
        <div className="bg-brand/20 absolute -top-40 left-1/2 size-[36rem] -translate-x-1/2 rounded-full blur-[120px]" />
        <div className="bg-attention/10 absolute -bottom-52 left-[15%] size-[30rem] rounded-full blur-[130px]" />
      </div>

      <div className="flex w-full max-w-sm flex-col items-center gap-8">
        <div className="flex flex-col items-center gap-4">
          {/* The two readings, side by side — the same mark as the header. */}
          <span className="relative flex items-center gap-1">
            <span className="bg-brand absolute -inset-3 rounded-full opacity-20 blur-xl" />
            <span className="bg-brand relative size-3.5 rounded-full" />
            <span className="bg-foreground/25 relative size-3.5 rounded-full" />
          </span>

          <Link
            to="/"
            className="wordmark font-heading text-4xl font-semibold tracking-tight"
          >
            Contextor
          </Link>

          <p className="text-muted-foreground max-w-[22rem] text-center text-sm leading-6 text-balance">
            One record of what's true. Everyone reads it in their own terms.
          </p>
        </div>

        <div className="bg-card ring-border/70 w-full rounded-2xl p-6 shadow-[0_1px_2px_rgb(0_0_0/0.04),0_24px_48px_-24px_rgb(0_0_0/0.25)] ring-1">
          <h1 className="font-heading mb-1 text-base font-medium">{title}</h1>
          <p className="text-muted-foreground mb-5 text-sm">{subtitle}</p>
          {children}
        </div>

        <p className="text-muted-foreground text-sm">{footer}</p>
      </div>
    </div>
  )
}
