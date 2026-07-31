# MedGuard Implantable Cardiac Monitor — System Requirements Specification

**Document:** MG-SRS-0001
**Revision:** C
**Status:** Released for design review
**Classification:** Internal — Confidential

---

## Revision History

| Rev | Date | Author | Summary |
| --- | --- | --- | --- |
| A | 04 Jan | P. Raman | Initial release |
| B | 22 Jan | P. Raman | Front-end section expanded |
| C | 19 Feb | Systems Engineering | Predicate change, pilot re-plan, budget reforecast |

## Table of Contents

1. Scope and Intended Use
2. Signal Acquisition Front-End
3. Detection Subsystem
4. Regulatory Strategy
5. Clinical Evidence
6. Programme Constraints
7. Non-Functional Requirements
Appendix A — Consolidated Parameter Table

---

## 1. Scope and Intended Use

MedGuard is an implantable cardiac monitor intended for the detection and
recording of arrhythmia events. Rev C extends the intended use beyond
outpatient review: the device is now specified for **continuous inpatient
telemetry during the first 72 hours post-implant**, with outpatient review
thereafter. This dual-mode indication was agreed at the 11 February design
review and supersedes the outpatient-only scope carried in Revisions A and B.

**REQ-001.** The device shall detect and record arrhythmia events for both
inpatient telemetry and outpatient review.

**REQ-002.** The device shall be implantable subcutaneously in the left
pectoral region, with a total implanted volume not exceeding 1.2 cc.

---

## 2. Signal Acquisition Front-End

### 2.1 Sampling

**REQ-010.** The biopotential front-end shall sample each channel at
**2 kHz**. The 1 kHz rate specified in Revision A was found insufficient to
resolve the QRS morphology features the detection algorithm depends on; the
increase was approved by the design review board on 11 February.

**REQ-011.** The ADC shall provide no less than 16 bits of resolution across
an input range of ±5 mV.

### 2.2 Filtering

**REQ-012.** The front-end shall implement a **fourth-order** anti-aliasing
filter ahead of the ADC. Bench characterisation showed the second-order
topology carried in earlier revisions to leave inadequate stopband rejection at
the new sampling rate.

**REQ-013.** A digital debounce filter shall be applied to the detection
signal chain to suppress transient artefacts arising from patient motion and
lead micro-dislodgement.

**REQ-014.** A 50/60 Hz notch filter shall be selectable in firmware, defaulted
by region at manufacture.

---

## 3. Detection Subsystem

**REQ-020.** Arrhythmia detection shall run in a **hybrid configuration**:
first-pass detection executes on-device, and every flagged event is uploaded
for cloud-based adjudication before it is presented to a clinician. Rev C
changes this from the wholly on-device detection specified previously; the
change is a consequence of the adjudication model's memory footprint, which
exceeds what the implant can host.

**REQ-021.** On-device first-pass detection shall complete within 400 ms of
event onset.

**REQ-022.** Where connectivity is unavailable, the device shall buffer flagged
events locally for no less than 30 days and adjudicate them on reconnection.

**REQ-023.** Detection sensitivity shall be no less than 97.5% against the
reference annotation set.

---

## 4. Regulatory Strategy

**REQ-030.** The device shall be submitted to FDA under a 510(k) premarket
notification, with the **Abbott Confirm Rx ICM** as the predicate device. The
Reveal LINQ II named in Revisions A and B has been withdrawn as predicate:
regulatory counsel advised on 06 February that the Confirm Rx is the closer
technological match now that adjudication is partly off-device.

**REQ-031.** The submission shall include a cybersecurity risk management file
per the FDA premarket cybersecurity guidance, covering the cloud adjudication
path introduced in REQ-020.

**REQ-032.** The device shall be labelled MR Conditional at 1.5 T and 3 T.

---

## 5. Clinical Evidence

**REQ-040.** Detection performance shall be characterised in a **prospective
in-clinic cohort of no fewer than 240 subjects** across three sites. Rev C
retires the retrospective study against annotated Holter recordings that
Revisions A and B specified; the prospective design was required by the change
of predicate and the addition of the inpatient indication.

**REQ-041.** The **primary endpoint of the clinical evidence package shall be
detection sensitivity**, with false-positive rate recorded as a secondary
endpoint. Earlier revisions treated the false-positive rate as the primary
measure; the reordering follows the predicate change, since the Confirm Rx
labelling claims are stated in sensitivity terms.

**REQ-042.** All adjudicated events shall be reviewable by two independent
electrophysiologists, with disagreements resolved by a third.

---

## 6. Programme Constraints

**REQ-050.** The hospital pilot shall commence on **28 April**. The 14 March
date committed in Revision A is no longer achievable: the prospective study in
REQ-040 cannot enrol and complete inside the original window.

**REQ-051.** The programme budget through end of year is **$2.9M**. The
reforecast covers the prospective study, the cloud adjudication infrastructure,
and six additional weeks of contract engineering.

**REQ-052.** Vendor commitments for the enclosure tooling shall not be
released until the design review closes.

---

## 7. Non-Functional Requirements

**REQ-060.** Implanted battery life shall be no less than 3 years under a duty
cycle of 40 flagged events per day.

**REQ-061.** The enclosure shall be grade 5 titanium, hermetically sealed to a
leak rate below 1×10⁻⁸ atm·cc/s.

**REQ-062.** Telemetry shall use Bluetooth Low Energy 5.2, with all patient
data encrypted at rest and in transit using AES-256.

**REQ-063.** The device shall comply with IEC 60601-1 and IEC 60601-1-2.

**REQ-064.** Firmware shall be field-updatable over the telemetry link, with
rollback to the previously installed image on a failed update.

---

## Appendix A — Consolidated Parameter Table

| Parameter | Rev C value | Requirement |
| --- | --- | --- |
| Sampling rate | 2 kHz per channel | REQ-010 |
| ADC resolution | 16 bits | REQ-011 |
| Anti-aliasing filter | Fourth-order | REQ-012 |
| Detection latency | ≤ 400 ms | REQ-021 |
| Local buffer | ≥ 30 days | REQ-022 |
| Sensitivity | ≥ 97.5% | REQ-023 |
| Predicate device | Abbott Confirm Rx ICM | REQ-030 |
| Study population | 240 subjects, prospective | REQ-040 |
| Pilot start | 28 April | REQ-050 |
| Budget to year end | $2.9M | REQ-051 |
| Battery life | ≥ 3 years | REQ-060 |

*MG-SRS-0001 Rev C — Internal — Confidential — Page 7 of 7*
