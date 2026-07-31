import type { Profile } from '@/types/ir'

/**
 * Seeded MedGuard profiles. Content is free-form by design — these are just an
 * example of what someone might write about themselves. Nothing in the pipeline
 * reads a fixed "role" key.
 */
export const PROFILES: Profile[] = [
  {
    id: 'u_priya',
    username: 'priya',
    content: {
      name: 'Priya Raman',
      describes_self_as:
        'Embedded firmware engineer. Ten years in signal acquisition, mostly biopotential front-ends.',
      expertise: ['DSP', 'ADC design', 'firmware', 'filter design'],
      on_this_project:
        'Owns the sensor front-end and detection firmware. Joined at kickoff.',
      assume_i_know:
        'Sampling theory, filter topologies, the device signal chain end to end.',
      dont_explain: 'Anything about DSP or embedded systems.',
    },
  },
  {
    id: 'u_marcus',
    username: 'marcus',
    content: {
      name: 'Marcus Oyelaran',
      describes_self_as:
        'Clinical scientist. I design and run the validation studies that produce our performance claims.',
      expertise: ['study design', 'cardiac physiology', 'biostatistics'],
      on_this_project:
        'Owns the false-positive characterisation study and the clinical evidence package.',
      assume_i_know: 'Study protocols, arrhythmia physiology, what invalidates a result.',
      dont_explain: 'Statistics or clinical trial methodology.',
      weak_on: 'Firmware and DSP — explain signal chain changes in terms of what they do, not how.',
    },
  },
  {
    id: 'u_ellen',
    username: 'ellen',
    content: {
      name: 'Ellen Whitcombe',
      describes_self_as:
        'Regulatory counsel, medical devices. Fifteen years of 510(k) and PMA submissions.',
      expertise: ['FDA device regulation', '21 CFR', 'submission strategy'],
      on_this_project: 'Owns the 510(k) submission. Joined three months in.',
      assume_i_know: 'The regulatory framework and what triggers a new submission.',
      weak_on: 'Engineering detail — tell me what changed and whether it is significant, not how it works.',
    },
  },
  {
    id: 'u_dan',
    username: 'dan',
    content: {
      name: 'Dan Foster',
      describes_self_as: 'Ops lead. I own the launch plan, budget and vendor commitments.',
      expertise: ['program management', 'budgeting', 'vendor management'],
      on_this_project: 'Owns the hospital pilot launch date and the burn rate.',
      cares_about: 'Anything that moves a date or a cost. Everything else is noise.',
      weak_on: 'Both the engineering and the science — I need consequences, not mechanisms.',
    },
  },
]

export interface Fixture {
  id: string
  label: string
  authorId: string
  text: string
  /** Soft expectations — eyeball aids for the lab, not hard assertions. */
  expect: {
    minEntries: number
    /** Lowercased substrings that should appear somewhere in the statements. */
    mentions: string[]
    /** True when the message deliberately leaves something unspecified. */
    unresolved: boolean
    note?: string
  }
}

export const FIXTURES: Fixture[] = [
  {
    id: 'canonical',
    label: 'Canonical demo message',
    authorId: 'u_priya',
    text: 'Bumped sampling rate to 2kHz, added debounce filter, should cut false positives.',
    expect: {
      minEntries: 3,
      mentions: ['sampling rate', 'debounce', 'false positive'],
      unresolved: true,
      note: 'The scenario from CLAUDE.md. Must NOT extract validation/510(k)/timeline consequences.',
    },
  },
  {
    id: 'consequence-bait',
    label: 'Consequence bait',
    authorId: 'u_marcus',
    text: "Ran the FP study on the old build last week, got 4.2%. Obviously that number is dead now that the firmware changed, and legal will want to know.",
    expect: {
      minEntries: 2,
      mentions: ['4.2', 'study'],
      unresolved: true,
      note: 'The author states a consequence themselves — that IS extractable as their claim. But the extractor must not add filing consequences of its own.',
    },
  },
  {
    id: 'vague',
    label: 'Vague, nothing to pin down',
    authorId: 'u_dan',
    text: 'Talked to the vendor, they think the enclosure might slip a bit but nothing serious.',
    expect: {
      minEntries: 1,
      mentions: ['enclosure'],
      unresolved: true,
      note: 'No dates, no magnitude. Almost everything should land in unresolved.',
    },
  },
  {
    id: 'dense',
    label: 'Dense multi-fact',
    authorId: 'u_ellen',
    text: 'Submission went out 14 March. Predicate is the CardioTrack CT-200. FDA has 90 days to respond, so we should hear by mid-June at the latest.',
    expect: {
      minEntries: 3,
      mentions: ['submission', 'predicate', '90'],
      unresolved: false,
      note: 'Tests atomicity: four distinct facts in two sentences.',
    },
  },
  {
    id: 'quote-trap',
    label: 'Quote trap (jargon + numbers)',
    authorId: 'u_priya',
    text: 'Moved the AFE gain from 6x to 12x and re-tuned the 0.5–40Hz bandpass. Noise floor looks better on the bench.',
    expect: {
      minEntries: 3,
      mentions: ['gain', 'bandpass', 'noise'],
      unresolved: true,
      note: 'Models like to normalise "0.5–40Hz" or "6x" when quoting. Verbatim check should catch it.',
    },
  },
]

export function profileById(id: string): Profile | null {
  return PROFILES.find((profile) => profile.id === id) ?? null
}
