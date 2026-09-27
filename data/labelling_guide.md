# Requirement Quality Labelling Guide

## Label convention

For each criterion:
- `true` = the requirement violates the criterion.
- `false` = the requirement satisfies the criterion.

The five criteria are:
1. Atomicity (`atomic`)
2. Testability (`testable`)
3. Feasibility (`feasible`)
4. Clarity (`clarity`)
5. Completeness (`complete`)

Label the original requirement as written. Use ordinary software terminology, but do not invent project context, thresholds, or business rules. Judge the stated obligation within its scope; a single requirement need not specify the entire system. These pilot labels are provisional suggestions requiring independent human review, not evidence of agreement between labellers. For the final set, two people should label each item independently, record disagreements before reconciliation, and report agreement as counts and percentages.

## 1. Atomicity

**Definition:** One requirement expresses one main behaviour, obligation, or capability that can be accepted as a unit.

**Violation = true:** It combines independent obligations that could be accepted, changed, or prioritised separately, such as authentication behaviour and report generation.

**Satisfied = false:** It describes one behaviour with its trigger, conditions, output fields, or acceptance constraints. Several fields in a receipt do not create separate requirements. Encoding and reconstructing a file may jointly define one lossless-storage capability. The word “and” alone does not establish a violation.

**Good example:** “For each successful payment, the service shall store a receipt containing the transaction ID and amount.” `atomic: false`

**Bad example:** “The login API shall reject incorrect passwords with HTTP 401, and the reports API shall export monthly sales totals as CSV.” `atomic: true`

## 2. Testability

**Definition:** Compliance can be decided objectively through a test, inspection, measurement, or analysis with a determinate acceptance result.

**Violation = true:** Subjective standards lack an acceptance rule, essential parameters are unspecified, or ambiguous wording produces different acceptance outcomes. Words such as “quickly” and “pleasant” need an operational definition. Mark this criterion independently of the source of the uncertainty.

**Satisfied = false:** A reviewer can determine compliance with the stated obligation. A status code or specified stored fields can be inspected without a numerical performance target. An impossible claim can still be objectively disproved by mathematical analysis; infeasibility alone does not imply non-testability.

**Good example:** “The upload API shall reject files larger than 10,485,760 bytes with HTTP 413.” `testable: false`

**Bad example:** “The dashboard shall load quickly after sign-in.” `testable: true`

## 3. Feasibility

**Definition:** The stated obligation is technically and realistically achievable under plausible software-system constraints.

**Violation = true:** It demands an impossible capability, contradicts its own constraints, or requires an absolute guarantee that cannot reasonably be achieved. For example, losslessly compressing every possible fixed-length input into a strictly smaller space is impossible by counting distinct inputs and outputs.

**Satisfied = false:** No concrete impossibility or unrealistic guarantee is evident. Difficulty, expense, missing deployment details, and vague wording alone are insufficient reasons to mark infeasibility. Interpret “instantly” as an undefined timing target unless the text explicitly demands zero elapsed time.

**Good example:** “For each successful payment, the service shall store its transaction ID.” `feasible: false`

**Bad example:** “The service shall reconstruct every possible 1 MiB file solely from its 256-bit hash, without any other information about the file.” `feasible: true`

## 4. Clarity

**Definition:** The wording conveys one understandable meaning for the actor, action, references, and conditions it actually states.

**Violation = true:** Undefined pronouns, subjective descriptions, or ambiguous qualifiers permit materially different interpretations. “Their name” with two possible people, “last month” without a calendar-versus-rolling definition, and ordering by price without a direction are examples.

**Satisfied = false:** The stated wording has one reasonable meaning. A plainly identified missing parameter is a completeness problem, not automatically a clarity problem; distinguish an absent value from competing meanings. Standard technical terms such as HTTP 401 do not require redefinition.

**Good example:** “The profile page shall display the signed-in user’s stored display name.” `clarity: false`

**Bad example:** “When an administrator messages an account owner, the dashboard shall display their name.” `clarity: true`

## 5. Completeness

**Definition:** The requirement supplies the information necessary to understand and accept its stated behaviour within its own scope.

**Violation = true:** A necessary trigger, actor, outcome, parameter, constraint, or condition is absent. Examples include an unspecified retention period, export format, or maximum name length. A subjective quality target without an acceptance definition also lacks essential information.

**Satisfied = false:** The obligation contains enough information for its stated scope. Do not demand unrelated error cases, implementation choices, or whole-system specifications. Do not automatically mark completeness when an existing pronoun or qualifier is ambiguous: use clarity, plus testability if acceptance depends on resolving it. Add completeness when essential information is separately absent.

**Good example:** “The audit service shall retain each login event for 30 days after the event timestamp.” `complete: false`

**Bad example:** “The audit service shall retain each login event for a specified retention period.” `complete: true`

## Multiple simultaneous violations

Evaluate all five criteria independently; one requirement may violate several. “The dashboard shall load quickly” is unclear, lacks an objective acceptance rule, and omits a defined timing target, so `clarity`, `testable`, and `complete` are all `true`. Do not force single-label items or assume that every requirement is defective. The examples under each criterion illustrate that criterion only, not a complete label vector.

For the initial dev pilot, REQ-001–004 are good examples, REQ-005–008 primarily illustrate clarity, REQ-009–011 testability, REQ-012–014 completeness, REQ-015–016 atomicity, REQ-017–018 feasibility, and REQ-019–020 multiple problems. These are diversity groups, not mutually exclusive labels. All 20 items are development data; reserve separate, unseen test items for final reporting.

## Critique Scoring Rubric

Human evaluators and, later, the LLM judge will use this 1–5 rubric to evaluate the **output of the critique system**, not the original requirement itself.

- **Job 1:** Humans label the original requirement using binary criterion violations.
- **Job 2:** Humans and later the LLM judge score the critique system’s response using the 1–5 rubric.

### Score 5
All real issues are correctly identified, no false issues are introduced, the explanations are accurate, and the rewrite fully fixes the problems.

### Score 4
Issues are correctly identified and explanations are solid, but the rewrite contains a minor gap.

### Score 3
The main issue is identified, but a secondary issue is missed, the explanation is vague, or the rewrite only partially fixes the requirement.

### Score 2
A real issue is missed, an incorrect issue is introduced, or the rewrite does not meaningfully improve the requirement.

### Score 1
The critique is mostly incorrect or unhelpful, or the rewrite worsens the requirement.

For consistent use of overlapping descriptions, a missed secondary issue alone fits score 3 when the main issue is correctly addressed; missing the main issue fits score 2. Use score 1 when the response is mostly incorrect, unhelpful, or makes the requirement worse. For a good original requirement, identifying no issues and preserving its meaning can earn score 5; inventing a defect cannot.
