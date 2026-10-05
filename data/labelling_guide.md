# Requirement Quality Labelling Guide

**Scheme: `grade_0_5_v1`** — integer 0-5 grade anchors per criterion. This
supersedes the earlier binary (0/1 violation) convention; the two must never
be mixed in one dataset file.

## Purpose

The golden dataset represents the human ground-truth evaluation of each
software requirement.

Each requirement is evaluated independently according to five software
requirement quality criteria:

1. Atomicity
2. Testability
3. Feasibility
4. Clarity
5. Completeness

The resulting human evaluation acts as the reference against which LLM1 and
the second assessor are both measured.

---

# Scoring Convention

Each criterion receives an integer grade from 0 to 5. Higher means better
quality. These anchors apply to all five criteria; each criterion section
below gives its own worked examples at each anchor.

| Grade | Meaning |
|---|---|
| 5 | Fully satisfies the criterion within the stated scope |
| 4 | Minor defect, limited impact |
| 3 | Partially satisfies it; a material defect remains |
| 2 | Major defect substantially undermines the criterion |
| 1 | Very little of the criterion is satisfied |
| 0 | Fundamentally fails the criterion |

The overall score is calculated as:

```
overall_score = (atomicity + testability + feasibility + clarity + completeness) / 5
```

This is computed by the harness, never by a model, and kept unrounded until
comparison. Each criterion is graded independently — a requirement may score
well on some criteria and poorly on others.

---

# 1. Atomicity

## Definition

A requirement is atomic when it expresses one main behavior, obligation, or
capability that can be implemented and accepted as a single unit.

**Boundary (preserve):** conditions, triggers, output fields, or acceptance
constraints that belong to the same behavior do not by themselves lower
atomicity. Non-atomicity means genuinely independent obligations — things
that could reasonably be implemented, prioritized, or accepted separately.

## Grade anchors

- **5** — One main behavior, however many conditions/fields/constraints
  attach to it.

  > For each successful payment, the service shall store a receipt
  > containing the transaction ID and amount.

  One behavior: storing a payment receipt. Atomicity = 5.

- **3** — The requirement is mostly one behavior, but a secondary obligation
  is loosely bundled in a way that complicates independent acceptance
  without being fully separable (material defect, not yet two requirements).

- **0** — Two or more independent behaviors that could be implemented,
  changed, or accepted separately.

  > The login API shall reject incorrect passwords with HTTP 401, and the
  > reports API shall export monthly sales totals as CSV.

  Two unrelated behaviors. Atomicity = 0.

---

# 2. Testability

## Definition

A requirement is testable when compliance can be objectively verified
through testing, inspection, measurement, or analysis — a tester can
determine pass or fail.

**Boundary (preserve):** an objectively verifiable requirement does not need
a specified test procedure to be testable. A requirement that is impossible
to satisfy can still be objectively disproved — infeasibility is not the
same defect as untestability.

## Grade anchors

- **5** — Objectively verifiable expected behavior.

  > The upload API shall reject files larger than 10,485,760 bytes with
  > HTTP 413.

  A test can upload an oversized file and check the status code.
  Testability = 5.

- **3** — A verifiable core behavior with one secondary condition left
  subjective enough to need interpretation before testing, but not so vague
  that the whole requirement is unverifiable.

- **0** — Depends on subjective, undefined, or ambiguous conditions that
  prevent any objective pass/fail decision (e.g. "quickly," "easy to use,"
  "pleasant," "appropriate," "user-friendly," with no measurable
  definition).

  > The dashboard shall load quickly after the user signs in.

  "Quickly" has no measurable threshold. Testability = 0.

---

# 3. Feasibility

## Definition

A requirement is feasible when its stated behavior can realistically and
technically be implemented under reasonable software-system constraints.

**Boundary (preserve):** difficulty, expense, or missing detail alone do not
lower feasibility. Only a clear technical impossibility or unrealistic
guarantee does.

## Grade anchors

- **5** — No clear technical impossibility or unrealistic guarantee.

  > For each successful payment, the service shall store its transaction ID.

  Technically achievable. Feasibility = 5.

- **3** — Achievable but relies on an implicit assumption or edge case that,
  if taken literally, strains realism without being outright impossible.

- **0** — Demands something technically impossible, logically contradictory,
  or unrealistic under its own stated constraints.

  > The service shall reconstruct every possible 1 MiB file solely from its
  > 256-bit hash without access to any other information.

  Cannot be guaranteed for every possible file — the hash space is smaller
  than the file space. Feasibility = 0.

---

# 4. Clarity

## Definition

A requirement is clear when its wording has one understandable
interpretation — actor, action, references, conditions, and expected
behavior are not materially ambiguous.

**Boundary (preserve):** standard technical terminology (e.g. HTTP status
codes) does not need to be redefined to be clear.

## Grade anchors

- **5** — One reasonable interpretation.

  > The profile page shall display the signed-in user's stored display name.

  Actor and expected information are clear. Clarity = 5.

- **3** — The primary actor/action is clear but one reference or term
  ("their," "last month," "relevant," "ordered by price" with no direction)
  admits more than one reasonable reading without derailing the rest.

- **0** — Wording can reasonably be read multiple ways, or contains
  ambiguous references.

  > When an administrator sends a message to an account owner, the
  > dashboard shall display their name.

  "Their name" could mean the administrator or the account owner.
  Clarity = 0.

---

# 5. Completeness

## Definition

A requirement is complete when it contains the information needed to
understand and verify the behavior within its own stated scope — it does not
need to describe the entire system, only what its own obligation requires.

**Boundary (preserve):** completeness is judged only within the
requirement's stated scope. Do not penalize it for omitting detail that
belongs to a different requirement or an implementation decision.

## Grade anchors

- **5** — All essential information for the stated behavior is present.

  > The audit service shall retain each login event for 30 days after the
  > event timestamp.

  Retention period is given. Completeness = 5.

- **3** — The core behavior is specified but one essential parameter
  (threshold, format, retention period, acceptance target) is missing while
  the rest of the obligation is otherwise understandable.

- **0** — Essential information is missing — timing thresholds, maximum
  values, output formats, retention periods, acceptance targets.

  > The audit service shall retain each login event for a specified
  > retention period.

  The actual retention period is missing. Completeness = 0.

---

# Independent Evaluation of Criteria

The five criteria must be evaluated independently; a requirement may score
differently across them.

> The dashboard shall load quickly after the user signs in.

Possible evaluation:

- Atomicity = 5
- Testability = 0
- Feasibility = 5
- Clarity = 2
- Completeness = 1

```
overall_score = (5 + 0 + 5 + 2 + 1) / 5 = 2.6
```

---

# Golden Dataset Format (scheme `grade_0_5_v1`)

```json
{
  "id": "REQ-001",
  "requirement": "Requirement text",
  "scheme": "grade_0_5_v1",
  "criteria": {
    "atomicity": 5,
    "testability": 5,
    "feasibility": 5,
    "clarity": 5,
    "completeness": 5
  },
  "gold_score": 5.0,
  "split": "dev"
}
```

A row without a `scheme` field (or with any other `scheme` value) carries no
usable gold grades under this convention and must not be read as one — see
`harness/schemas.py:validate_gold_criteria` and the runner's dataset loader.
