# Prompts for your next architecture review

Use these with an agent that can read the skill and run the CLI. Replace bracketed context with your requirements.

## Brownfield: explain what actually exists

> Use Archi-Made-Easy on [repository]. Trace the request path from ingress to stateful dependencies. Attach file evidence to observed components. Deliver an as-is view with risks, a proposed target, and a semantic diff. Preserve behavior and distinguish inferred connectivity from observed facts.

## Resilience: find the hidden shared dependency

> Review [model] for resilience. The design claims two independent paths. Check whether they share identity, networking, storage, region, or control-plane dependencies. Simulate a database failure and an AZ outage. State what the model cannot prove.

## MVP: keep the architecture proportionate

> Design [application] for a small team at [traffic and budget]. Compare a modular application with an event-driven option. Prefer the simplest option meeting the requirements. Do not add multi-region, a service mesh, or microservices merely because they sound production-ready. Produce a target model, editable diagram, and grounded ADR.

## Security: follow the path around the WAF

> Inspect all public HTTP entry points in [model]. Check WAF applicability, policy attachment, authentication requirements, and direct-origin bypass. Separate unknown configuration from known failures. Produce an edge-security view and a proposed remediation diff.

## Migration: preserve the truth while improving the design

> Document [legacy system] and propose a migration toward [goal]. Preserve residency, integration compatibility, and business transaction semantics. Show as-is and target side-by-side. Explain migration risks rather than presenting the target as already deployed.

## Diagram handoff: edit without losing meaning

> Import this edited draw.io page against its baseline model. Show changed components, dependencies, and containment. Re-run assessment. Preserve unsupported objects in the original file and report conflicts rather than overwriting either version.

Share synthetic or anonymized models with the command, expected behavior, and final diagram. A screenshot alone cannot reproduce a semantic failure. Describe scenario calculations as modeled results, not production measurements.
