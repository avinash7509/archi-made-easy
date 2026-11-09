# Production topology synthesis

For scalable, enterprise, resilient or production design requests containing a global edge and a regional stack, propose two regional deployments by default. Compare warm standby with active/active; select warm standby unless write semantics, capacity and budget justify active/active. Explicit residency, cost, single-region, compatibility or monolith requirements override this default. Record the inference as proposed evidence and enumerate migration, secondary capacity, routing, database promotion and replication costs. Never clone observed brownfield facts as if a second deployment already exists.

Decompose generic web compute plus API Management into logical frontend and API roles unless a monolith is required. These may share a deployment unit; do not imply separate billing or scaling without saying so. Route web paths directly from ingress and API paths through API management when the intended security model supports it.

In application views, private endpoints, integration subnets, NSGs, routes and NAT are attachments or boundaries, not application boxes. Preserve them as nodes for packet/network views and preserve observed source facts even when a presentation hides detail. Use `deployment.posture` for a concise second line, `networkAccess`, `auth`, `sku`, `scaling`, and `scope` for structured inspection. Use a regional deployment boundary for PaaS services. Key Vault and SQL are managed services reached through private endpoints; enclosing them in a VNet boundary would falsely claim injection. Private DNS, endpoint approval and public access restrictions are separate proposed controls.

Global identity belongs above regions. Regional secrets/data stay under their regional parent near consumers. Telemetry is an operations sink. Collector buses are presentation only: retain every underlying edge, evidence and dependency; aggregate only compatible same-kind, same-protocol, same-auth flows to one sink. A junction means deliberate fan-in, not a new deployed collector service.

Author labels expressing intent and protocol, <=24 display characters: `/* HTTPS`, `/api/* HTTPS`, `HTTPS / primary`, `HTTPS / failover`, `HTTPS + token`, `SQL / TLS`, `Async geo-replication`, `OIDC / PKCE`, `JWT keys`, `MI / HTTPS`, `TLS certificate`, `Traces / metrics`. Full labels remain in CASG. Do not infer managed identity, SQL wire protocol or asynchronous replication solely from product names. Bare HTTPS produces a presentation warning when no intent is supplied.

Failover alternatives use dependency `fallback` with a shared group on the caller; replication is a separate relationship, not a serving dependency. Region outage propagates through containment. Mark secondary capacity, promotion and recovery inputs as assumptions. `deployment.recovery` can declare detectionSeconds, routingSeconds, promotionSeconds, warmupSeconds, replicationLagSeconds and a required explanatory basis. The inspector sums the four serial recovery stages only when all are declared; replication lag is an illustrative RPO input, not a guarantee. Existing rtoSeconds/rpoSeconds are objectives, never measured timings. Model stateful promotion and test operational procedures before making readiness claims.

IaC skeletons belong in `deployment.bicep` / `terraform` with resourceType and apiVersion. They are reviewable authored examples, not a deployment action. Include supported properties only; do not copy SKU/publicNetworkAccess onto arbitrary services. Unknown mappings remain unknown. Modern Front Door Standard/Premium is `Microsoft.Cdn/profiles`, not classic `Microsoft.Network/frontDoors`; routes, endpoints, origin groups and policies require additional resources.

Sources checked 2026-11-09:
- https://learn.microsoft.com/en-us/azure/key-vault/general/private-link-service
- https://learn.microsoft.com/en-us/azure/private-link/private-endpoint-overview
- https://learn.microsoft.com/en-us/azure/templates/microsoft.cdn/2023-05-01/profiles

The compact runtime performs structural failure propagation and presentation checks. It does not certify WAF compliance, validate IaC against a live provider, or prove production recovery.

For a web-to-API token/request backchannel that would stretch the primary ingress layout, `controls.layoutBackchannel: true` excludes that edge from placement ranking only. The route, dependency, inspection and simulation remain intact. Never set it merely to conceal a cyclic dependency.
