# Share Archi-Made-Easy

Drafts for the maintainer to adapt and post. Nothing here has been sent to social platforms or other communities. Respect each community's self-promotion rules and disclose that you maintain the project.

## A short introduction

I’m building Archi-Made-Easy, an open-source architecture skill and local CLI.

It keeps an as-is model intact, proposes a separate target, checks declared risks, and lets you click a component to explore its failure impact. Outputs include editable draw.io and standalone HTML.

It’s early: the checks are model-based, and simulations aren’t production tests. I’d especially value small, anonymized examples where it misses a risk or flags a valid design.

Demo: https://avinash7509.github.io/archi-made-easy/
Source: https://github.com/avinash7509/archi-made-easy

## A technical community opener

**What dependency did your architecture diagram hide?**

I maintain Archi-Made-Easy, a local architecture-review tool built around a versioned semantic graph. One use case is spotting when two apparently independent paths share a dependency. Another is preserving the observed architecture while proposing changes in a separate model.

The public demo lets you simulate a database failure and download an editable diagram. I’m looking for reproducible architecture traps and false positives—not claims that every design should use the same cloud patterns.

https://github.com/avinash7509/archi-made-easy

## Demo walkthrough

1. Open the live example. Explain that it is synthetic data.
2. Enable **Failure simulation** and select **Order database**.
3. Show the affected dependencies and inspector evidence.
4. Switch to **target** and explain that its controls are proposals.
5. Download the native draw.io file.
6. Invite one concrete counterexample or rendering bug.

## Useful signals to track

Compare GitHub traffic, clones, relevant issues, reproducible examples, and returning contributors after each change. Stars are a discovery signal, not proof of technical quality. Do not buy engagement, invent testimonials, or claim benchmark results that have not been run.
