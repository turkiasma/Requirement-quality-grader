# Active pipeline design (v5)

Requirement → LLM1 (short definitions) → judge (requirement + complete LLM1
assessment + detailed guide) → Python scoring → persisted results and summary.

Both models grade original requirement quality on five 0–5 dimensions. References
are used only for Python comparison and never included in model requests. The
judge's retained flags are derived from numerical equality, not its self-report.

Historical binary/pass-fail and rewrite designs are superseded; their history
remains available in Git and prompts v1–v4. See README for active commands,
reference review, schemas, cost controls and evaluation limitations.
