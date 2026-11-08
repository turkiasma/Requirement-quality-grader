# Software requirement grading guide

Version: requirement_quality_v2. Scheme: grade_0_5_v2.

Grade the original requirement, not the assessor's writing. Each criterion is
an integer 0–5; higher is better. The overall score is the unrounded mean of
all five grades. Assess criteria independently; a defect may affect several
criteria only with a separate justification for each. Quote or identify the
specific obligation, ambiguity, missing parameter, or implausible guarantee.
Do not infer unstated system context. Explicit references to defined contracts
or standards are acceptable; references explicitly pending definition are not.

Common anchors: 5 fully satisfied; 4 minor issue; 3 meaningful but bounded
defect; 2 significant defect; 1 very poor satisfaction; 0 fundamental failure.
Choose the closest criterion-specific anchor, not an arithmetic defect count.
If two anchors fit, record the uncertainty and explain the selected grade.

## Atomicity

Measures whether there is one independently deliverable obligation. Does not
count words, conjunctions, response fields, conditions, or acceptance checks.

| Grade | Anchor |
|---|---|
| 5 | One obligation, including its trigger, conditions, fields and constraints. |
| 4 | One obligation with a minor ancillary action that could be separated. |
| 3 | Two closely coupled but separately deliverable obligations in one workflow. |
| 2 | Several separately deliverable obligations in one feature or workflow. |
| 1 | A bundle spanning distinct features, with only a loose shared purpose. |
| 0 | Explicitly unrelated obligations combined with no common workflow. |

Positive: “On a duplicate SKU, POST /stock shall return 409 with the SKU.”
Negative: “The stock API shall reject duplicates and the calendar shall print holidays.”
Borderline: saving an order and emailing its confirmation are related but can
ship separately (3). Returning several fields in one response is 5. Logging
as a minor side effect may be 4; an independently specified audit subsystem
is another obligation. Explain separability rather than counting 'and'.

## Testability

Measures objective verification through testing, inspection, measurement, or
analysis. Does not require a full test procedure, implementation plan or proof
that a requirement is feasible. An impossible mathematical claim can be
objectively falsified and therefore testable.

| Grade | Anchor |
|---|---|
| 5 | Objective acceptance or rejection can be determined for the stated scope. |
| 4 | Core pass/fail is objective; a minor boundary or measurement detail is unclear. |
| 3 | Meaningful behaviour can be tested, but one important acceptance detail is missing. |
| 2 | Only a small part can be checked; major acceptance conditions are unspecified. |
| 1 | An observable intent exists but almost no usable acceptance rule is given. |
| 0 | Entire acceptance depends on subjective praise or an undefined quality term. |

Positive: “The search API shall return at most 25 results per page.”
Negative: “The interface shall feel wonderful.”
Borderline: a measurable latency with no workload can be 3; 'quickly' alone
is 0, not 3. Undefined sort direction can be 4 when size and ordering by a
specified key remain checkable. A fixed protocol error code needs no test script.

## Feasibility

Measures technical achievability under explicit constraints and guarantees.
Does not penalize cost, unfamiliarity, difficulty, lack of design detail, or
ordinary ambitious targets without evidence. Assume conventional resources
unless the requirement constrains them. Give 5 when no concrete feasibility
problem is supported; this is not a certification that implementation will succeed.

| Grade | Anchor |
|---|---|
| 5 | Achievable with ordinary engineering; no supported feasibility defect. |
| 4 | A small, explicitly constrained engineering margin is questionable. |
| 3 | A demanding stated resource or operating constraint creates substantial risk. |
| 2 | Specified constraints are severely unrealistic although not logically impossible. |
| 1 | An operational absolute promises control over events outside the system. |
| 0 | Contradiction or physical, mathematical or information-theoretic impossibility. |

Positive: “A worker shall retry a failed delivery three times.”
Negative: “The service shall recover any original document from a one-bit checksum alone.”
Borderline: low latency is not inherently infeasible; assess the explicit data
volume, hardware and workload. 'Never fail even when every replica is destroyed'
is a fundamental contradiction (0). 'Every email arrives despite recipient
server outages' is an unsupported operational guarantee (1). Do not invent
bandwidth limits or hardware budgets to lower a score.

## Clarity

Measures whether a reasonable engineer can identify one intended meaning.
Does not measure absent but clearly identified parameters or restate completeness.
Standard technical terms need no glossary unless used inconsistently.

| Grade | Anchor |
|---|---|
| 5 | One reasonably unambiguous interpretation of the stated obligation. |
| 4 | Minor local wording uncertainty with little effect on expected behaviour. |
| 3 | One material ambiguity, while the main actor/action remains understandable. |
| 2 | Several material ambiguities or an ambiguous central object/condition. |
| 1 | Most of the intended behaviour requires guessing. |
| 0 | No coherent interpretation, or directly incompatible meanings with no resolution. |

Positive: “The supervisor's name shall appear beside the supervisor's approval.”
Negative: “The flag shall be both enabled and not enabled for the same request.”
Borderline: 'their name' with two plausible people is 3 if the display action
is otherwise clear; it is not automatically 0. A clearly named limit marked
TBD is a completeness/testability defect, not necessarily unclear wording.

## Completeness

Measures sufficient information to implement and verify the obligation within
its stated scope. Does not require an entire product specification, unrelated
features, every exception, or optional architecture choices.

| Grade | Anchor |
|---|---|
| 5 | Necessary actor/trigger/action/outcome and parameters for the stated scope exist. |
| 4 | Minor boundary detail missing; the core obligation is implementable. |
| 3 | One essential parameter or outcome is absent, but the main contract is defined. |
| 2 | Several essential details are absent; only part of the contract is defined. |
| 1 | A broad intent remains, with most essential contract details absent. |
| 0 | No actionable obligation or outcome can be identified. |

Positive: “For an expired token, GET /records shall return HTTP 401.”
Negative: “The application shall do what is needed.”
Borderline: a retention period explicitly TBD is 3 when the event and retention
action are defined; not 0. An undefined trigger, recipient and payload together
may be 1. A requirement specifying only one error path may be fully complete
for that path; do not demand all successful paths too.

## Annotation and evaluation protocol

References begin as AI-prepared `proposed` annotations. A human reviewer reads
the requirement and all five rationales, corrects grades and explanations, then
explicitly marks it `verified` with their name and review timestamp. Retain the
initial proposal and import history. No item is automatically human verified.
This project follows the user's reported instructor clarification permitting
one manually verified reference set; it does not claim inter-annotator agreement.

LLM1 receives concise definitions only. The judge receives this guide and LLM1's
assessment, never reference grades or review records. Both outputs grade the
same original requirement. Python derives averages and retained flags. Model
agreement with proposed labels is provisional, not human-reference reliability.
Test examples must not enter prompts, guide examples or prompt-tuning runs.
