# Requirement Quality Labelling Guide

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

The resulting human evaluation acts as the reference answer against which
the AI-based evaluation system will later be compared.

---

# Scoring Convention

Each criterion receives a binary score:

- `1` = the requirement satisfies the criterion
- `0` = the requirement does not satisfy the criterion

The final quality score is calculated as:

gold_score =
atomicity +
testability +
feasibility +
clarity +
completeness

The final score therefore ranges from:

- `0/5` = satisfies none of the quality criteria
- `1/5` = satisfies one criterion
- `2/5` = satisfies two criteria
- `3/5` = satisfies three criteria
- `4/5` = satisfies four criteria
- `5/5` = satisfies all five criteria

Each criterion must be evaluated independently.

A requirement may fail several criteria simultaneously.

---

# 1. Atomicity

## Definition

A requirement is atomic when it expresses one main behavior, obligation,
or capability that can be implemented and accepted as a single unit.

## Score 1

Give `atomicity = 1` when the requirement describes one main behavior.

Conditions, triggers, output fields, or acceptance constraints related to
the same behavior do not make the requirement non-atomic.

### Example

> For each successful payment, the service shall store a receipt containing
> the transaction ID and amount.

This describes one main behavior: storing a payment receipt.

Atomicity = 1

## Score 0

Give `atomicity = 0` when the requirement combines independent behaviors
that could reasonably be implemented, changed, prioritized, or accepted
separately.

### Example

> The login API shall reject incorrect passwords with HTTP 401, and the
> reports API shall export monthly sales totals as CSV.

This describes two unrelated behaviors.

Atomicity = 0

---

# 2. Testability

## Definition

A requirement is testable when compliance can be objectively verified
through testing, inspection, measurement, or analysis.

A tester should be able to determine whether the requirement passes or
fails.

## Score 1

Give `testability = 1` when the requirement provides an objectively
verifiable expected behavior.

### Example

> The upload API shall reject files larger than 10,485,760 bytes with
> HTTP 413.

A test can upload a file larger than the specified size and verify the
returned status code.

Testability = 1

## Score 0

Give `testability = 0` when the requirement depends on subjective,
undefined, or ambiguous conditions that prevent an objective acceptance
decision.

Examples include terms such as:

- quickly
- easy to use
- pleasant
- appropriate
- user-friendly

unless those terms are given measurable definitions.

### Example

> The dashboard shall load quickly after the user signs in.

"Quickly" has no measurable threshold.

Testability = 0

---

# 3. Feasibility

## Definition

A requirement is feasible when its stated behavior can realistically and
technically be implemented under reasonable software-system constraints.

## Score 1

Give `feasibility = 1` when there is no clear technical impossibility or
unrealistic guarantee in the requirement.

A requirement should not receive a feasibility score of 0 simply because
it is difficult, expensive, or missing some details.

### Example

> For each successful payment, the service shall store its transaction ID.

This behavior is technically achievable.

Feasibility = 1

## Score 0

Give `feasibility = 0` when the requirement demands something technically
impossible, logically contradictory, or unrealistic under its stated
constraints.

### Example

> The service shall reconstruct every possible 1 MiB file solely from its
> 256-bit hash without access to any other information.

This cannot be guaranteed for every possible file because different files
can map to the same finite hash space.

Feasibility = 0

---

# 4. Clarity

## Definition

A requirement is clear when its wording has one understandable
interpretation.

The actor, action, references, conditions, and expected behavior should
not be materially ambiguous.

## Score 1

Give `clarity = 1` when the requirement has one reasonable interpretation.

Standard technical terminology such as HTTP status codes does not need to
be redefined.

### Example

> The profile page shall display the signed-in user's stored display name.

The actor and expected information are clearly identified.

Clarity = 1

## Score 0

Give `clarity = 0` when wording can reasonably be interpreted in multiple
ways or contains ambiguous references.

### Example

> When an administrator sends a message to an account owner, the dashboard
> shall display their name.

"Their name" could refer to either the administrator or the account owner.

Clarity = 0

Other examples of potentially unclear wording include:

- last month
- appropriate
- their
- ordered by price without specifying direction
- relevant information

when the intended meaning cannot be determined from the requirement.

---

# 5. Completeness

## Definition

A requirement is complete when it contains enough information to
understand and verify the behavior within the scope of that requirement.

The requirement does not need to describe the entire system.

It only needs to contain the information necessary for its stated
behavior.

## Score 1

Give `completeness = 1` when all essential information required to
understand and accept the stated behavior is provided.

### Example

> The audit service shall retain each login event for 30 days after the
> event timestamp.

The required retention period is provided.

Completeness = 1

## Score 0

Give `completeness = 0` when essential information is missing.

Examples include:

- missing timing thresholds
- unspecified maximum values
- unspecified output formats
- missing retention periods
- undefined acceptance targets

### Example

> The audit service shall retain each login event for a specified retention
> period.

The actual retention period is missing.

Completeness = 0

---

# Independent Evaluation of Criteria

The five criteria must be evaluated independently.

A problem may affect more than one criterion.

For example:

> The dashboard shall load quickly after the user signs in.

Possible evaluation:

- Atomicity = 1
- Testability = 0
- Feasibility = 1
- Clarity = 0
- Completeness = 0

Gold score:

1 + 0 + 1 + 0 + 0 = 2

Therefore:

gold_score = 2

---

# Golden Dataset Format

Each item in `golden_set.jsonl` follows this structure:

```json
{
  "id": "REQ-001",
  "requirement": "Requirement text",
  "criteria": {
    "atomicity": 1,
    "testability": 1,
    "feasibility": 1,
    "clarity": 1,
    "completeness": 1
  },
  "gold_score": 5,
  "split": "dev"
}
```
