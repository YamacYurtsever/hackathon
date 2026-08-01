import { useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRightIcon } from 'lucide-react'

import { readUiTheme, writeUiTheme, type UiTheme } from '@/lib/ui-theme'

import './landing.css'

const NAV_LINKS = [
  { href: '#features', label: 'Features' },
  { href: '#method', label: 'Method' },
  { href: '#start', label: 'Start' },
]

const STEPS = [
  {
    num: '01',
    title: 'Capture once',
    body: 'Say something, ask a question, or drop a document. One input — no classifying your own thought first.',
  },
  {
    num: '02',
    title: 'Gate the record',
    body: 'Review what we understood, submit for review, then an admin merges. Nothing writes itself into the IR.',
  },
  {
    num: '03',
    title: 'Read through your lens',
    body: 'NL is re-projected for you. IR is the neutral evidence — flip between them and see where every claim came from.',
  },
]

function IconGithub() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
      <path d="M12 2C6.477 2 2 6.477 2 12c0 4.42 2.865 8.17 6.839 9.49.5.092.682-.217.682-.482 0-.237-.008-.866-.013-1.7-2.782.603-3.369-1.34-3.369-1.34-.454-1.156-1.11-1.463-1.11-1.463-.908-.62.069-.608.069-.608 1.003.07 1.531 1.03 1.531 1.03.892 1.529 2.341 1.087 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.11-4.555-4.943 0-1.091.39-1.984 1.029-2.683-.103-.253-.446-1.27.098-2.647 0 0 .84-.269 2.75 1.025A9.578 9.578 0 0112 6.836c.85.004 1.705.114 2.504.336 1.909-1.294 2.747-1.025 2.747-1.025.546 1.377.202 2.394.1 2.647.64.699 1.028 1.592 1.028 2.683 0 3.842-2.339 4.687-4.566 4.935.359.309.678.919.678 1.852 0 1.336-.012 2.415-.012 2.743 0 .267.18.578.688.48C19.138 20.167 22 16.418 22 12c0-5.523-4.477-10-10-10z" />
    </svg>
  )
}

function IconX() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
      <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
    </svg>
  )
}

function IconLinkedIn() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
      <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
    </svg>
  )
}

export function LandingPage() {
  const [theme, setTheme] = useState<UiTheme>(() => readUiTheme())

  function toggleTheme() {
    const next: UiTheme = theme === 'obsidian' ? 'classic' : 'obsidian'
    writeUiTheme(next)
    setTheme(next)
  }

  return (
    <div className={`landing landing--${theme}`}>
      <div className="landing__noise" aria-hidden />

      <div className="landing__shell">
        <div className="landing__glow landing__glow--tl" aria-hidden />
        <div className="landing__glow landing__glow--br" aria-hidden />

        <nav className="landing-nav">
          <a href="#" className="landing-nav__logo">
            <span className="landing-nav__mark">C</span>
            <span className="landing-nav__word">Contextor</span>
          </a>

          <ul className="landing-nav__pill">
            {NAV_LINKS.map((link) => (
              <li key={link.href}>
                <a href={link.href}>{link.label}</a>
              </li>
            ))}
          </ul>

          <div className="landing-nav__right">
            <button
              type="button"
              className="landing-nav__theme"
              onClick={toggleTheme}
            >
              {theme === 'obsidian' ? 'Classic design' : 'New design'}
            </button>
            <Link to="/login" className="landing-nav__auth">
              Login / Signup
            </Link>
          </div>
        </nav>

        <section className="landing-hero">
          <div>
            <div className="landing-hero__label">
              <span className="landing-status__dot" />
              AI · Context re-projection
            </div>
            <h1 className="landing-hero__title">
              One record.
              <br />
              <em>Every</em> context.
            </h1>
            <p className="landing-hero__lede">
              An n-way translator between professional worlds — not languages. Your team
              shares one ground truth; each person reads it in their own terms.
            </p>
            <div className="landing-hero__ctas">
              <Link to="/signup" className="landing-btn landing-btn--neon">
                Start Free Trial
                <ArrowRightIcon size={16} />
              </Link>
              <a href="#features" className="landing-btn landing-btn--ghost">
                See how it works
              </a>
            </div>
          </div>

          <div className="landing-mock">
            <div className="landing-mock__shell">
              <div className="landing-mock__bar" aria-hidden>
                <span />
                <span />
                <span />
              </div>
              <div className="landing-mock__panel">
                <div className="landing-mock__panel-label">NL · Lawyer lens</div>
                <h3>Sampling change flagged</h3>
                <p>
                  Front-end moved to 2 kHz. That likely needs a 510(k) supplement —
                  combined with validation re-run, filing slips ~2 weeks.
                </p>
                <div className="landing-mock__lines" aria-hidden>
                  <i />
                  <i />
                  <i />
                </div>
              </div>
            </div>

            <div className="landing-float landing-float--a">
              <div className="landing-float__tag">IR entry</div>
              <div className="landing-float__value">
                sampling <span>1 → 2 kHz</span>
              </div>
            </div>

            <div className="landing-float landing-float--b">
              <div className="landing-float__tag">Conflict</div>
              <div className="landing-float__value">
                2 facts <span>can&apos;t both hold</span>
              </div>
            </div>

            <div className="landing-cursor">AI cursor</div>
          </div>
        </section>

        <section id="features" className="landing-section">
          <p className="landing-eyebrow">Capabilities</p>
          <h2 className="landing-heading">Built as a bento of hard edges</h2>

          <div className="landing-bento">
            <article className="landing-card landing-card--wide">
              <div className="landing-card__mono">01 · Ground truth</div>
              <h3>Neutral Intermediate Representation</h3>
              <p>
                Every fact lives in one shared record — structured, cited, and identical
                for every member. Re-projection filters what matters to you; IR holds
                the receipts.
              </p>
              <div className="landing-bars" aria-hidden>
                <span />
                <span />
                <span />
                <span />
                <span />
                <span />
              </div>
            </article>

            <article className="landing-card landing-card--tall">
              <div className="landing-card__mono">02 · Tokens</div>
              <h3>Lens palette</h3>
              <p>Context profiles shape vocabulary, not roles baked into the system.</p>
              <div className="landing-swatches">
                <div className="landing-swatch">
                  <i style={{ background: '#ccff00' }} />
                  <span>Engineer</span>
                </div>
                <div className="landing-swatch">
                  <i style={{ background: '#10b981' }} />
                  <span>Biologist</span>
                </div>
                <div className="landing-swatch">
                  <i style={{ background: '#ebebeb' }} />
                  <span>Counsel</span>
                </div>
                <div className="landing-swatch">
                  <i style={{ background: 'rgba(255,255,255,0.2)' }} />
                  <span>Ops</span>
                </div>
              </div>
            </article>

            <article className="landing-card">
              <div className="landing-card__mono">03 · Documents</div>
              <h3>Drop to read</h3>
              <p>Specs and transcripts enter where a message enters — then gate 1.</p>
            </article>

            <article className="landing-card landing-card--accent">
              <div className="landing-card__mono">04 · Alignment</div>
              <h3>Conflicts stay visible</h3>
              <p>
                Contradictions are a red state — not silently resolved by whoever wrote
                last. Settle them, or the record keeps saying both.
              </p>
            </article>
          </div>
        </section>

        <section id="method" className="landing-method">
          <div>
            <p className="landing-method__eyebrow">Methodology</p>
            <h2>Propose. Submit. Merge. Read.</h2>
            <ol className="landing-steps">
              {STEPS.map((step) => (
                <li key={step.num}>
                  <span className="landing-steps__num">{step.num}</span>
                  <div>
                    <h3>{step.title}</h3>
                    <p>{step.body}</p>
                  </div>
                </li>
              ))}
            </ol>
          </div>

          <div className="landing-method__visual">
            <div className="landing-portrait">
              <img
                src="https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=800&h=800&fit=crop&q=80"
                alt=""
              />
            </div>
            <div className="landing-quote">
              <p>
                “Same sampling change. Three different readings — and every claim cited
                back to the IR.”
              </p>
              <span>Priya Raman · Firmware</span>
            </div>
          </div>
        </section>

        <footer id="start" className="landing-footer">
          <div className="landing-footer__watermark" aria-hidden>
            SUPER
          </div>

          <div className="landing-footer__cta">
            <h2>Ready to share one record?</h2>
            <Link to="/signup" className="landing-btn landing-btn--footer">
              Start Free Trial
            </Link>
          </div>

          <div className="landing-footer__grid">
            <div className="landing-footer__col">
              <h4>Product</h4>
              <ul>
                <li>
                  <a href="#features">Features</a>
                </li>
                <li>
                  <a href="#method">Method</a>
                </li>
                <li>
                  <Link to="/signup">Free trial</Link>
                </li>
              </ul>
            </div>

            <div className="landing-footer__col">
              <h4>Connect</h4>
              <div className="landing-footer__socials">
                <a href="https://github.com" aria-label="GitHub" target="_blank" rel="noreferrer">
                  <IconGithub />
                </a>
                <a href="https://x.com" aria-label="X" target="_blank" rel="noreferrer">
                  <IconX />
                </a>
                <a
                  href="https://linkedin.com"
                  aria-label="LinkedIn"
                  target="_blank"
                  rel="noreferrer"
                >
                  <IconLinkedIn />
                </a>
              </div>
            </div>

            <div className="landing-footer__col">
              <h4>Legal</h4>
              <p className="landing-footer__copy">
                © {new Date().getFullYear()} Contextor
                <br />
                Obsidian &amp; Lime · All rights reserved
              </p>
              <ul style={{ marginTop: '0.75rem' }}>
                <li>
                  <Link to="/login">Sign in</Link>
                </li>
                <li>
                  <a href="mailto:hello@contextor.app">Contact</a>
                </li>
              </ul>
            </div>
          </div>
        </footer>
      </div>
    </div>
  )
}
