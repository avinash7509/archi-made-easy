# Evaluation protocol

Fixture tests validate deterministic behavior, not agent skill effectiveness. Retain 30 prompts: six reference-inspired diagrams, twelve enterprise/cloud categories and twelve traps with valid counterexamples. Keep gold answers outside agent-visible input.

For each of three model configurations run each prompt three times in clean output folders. Record agent/model version, package commit/hash, tool availability, timestamps, first draft, final candidate, repair count and transcript. Never silently drop failed runs.

Compare pinned diagram-design and Archify packages under equivalent prompts and budgets. Blind reviewers assess final visuals; report ties and uncertainty. Architecture-rule detection is assessed separately from diagram-only tools. Targets: 95% applicable quality success and 70% visual preference; they are goals until measured.

Do not call synthetic fixtures a completed 270-run benchmark or claim cross-platform testing from a single Windows run. The repository CI matrix supplies independent OS execution when run on a configured CI host.
