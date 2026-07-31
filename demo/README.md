# Demo documents

Fixtures for demoing document import. Nothing here is real, and nothing here is
loaded automatically — drop a file onto the MedGuard project view to use it.

## `medguard-srs-rev-c.md`

A requirements spec written to disagree with what MedGuard already records. The
seeded project was founded from a paragraph (`backend/src/data/seed.py`); this
document is the "Rev C" that contradicts most of it, so importing it should
produce **updates to existing entries**, not a second set of facts alongside
them.

| MedGuard currently records | Rev C says |
| --- | --- |
| Samples at 1 kHz | 2 kHz (REQ-010) |
| Second-order anti-aliasing filter | Fourth-order (REQ-012) |
| Detection runs on-device | Hybrid — on-device first pass, cloud adjudication (REQ-020) |
| 510(k) predicate is the Reveal LINQ II | Predicate is the Abbott Confirm Rx ICM (REQ-030) |
| False-positive rate is the primary measure | Sensitivity is primary, false-positive rate secondary (REQ-041) |
| Characterisation study against annotated Holter recordings | Prospective in-clinic cohort, 240 subjects (REQ-040) |
| Pilot committed for 14 March | Pilot starts 28 April (REQ-050) |
| Budget $2.4M through end of year | $2.9M (REQ-051) |
| Flags events for outpatient review | Outpatient review *and* inpatient telemetry (REQ-001) |

It also carries facts the project has never heard of — battery life, enclosure
material, telemetry stack, MR conditional labelling, the 30-day buffer — which
should come through as plain creates.

**What each part of it is there to exercise:**

- **The conflicts above** — the reconciler pointing a restatement at the entry
  it revises, rather than letting the project hold both "1 kHz" and "2 kHz".
- **Appendix A** — every headline parameter restated as a table row, a long way
  from where it was first stated. One fact, two passages: the cross-chunk
  reconciliation either collapses those or you see each number twice.
- **The revision history table, the table of contents, and the page footer** —
  document furniture. None of it is a fact about the project, and none of it
  should appear in the review dialog.
- **Its length** — about 7 kB, so it chunks into several passages and the
  reading dialog runs long enough to be worth watching.

Reviewing it is gate 1 exactly as a typed message is: nothing is stored until
you submit, and an admin still has to merge what you send.
