# Interpret assessment and simulation

Pillar score uses known checks only. Coverage is reported independently. `unknown` must never count as a pass. A target control proposed by remediation is a design requirement, not proof of implementation. Explain critical findings and unresolved applicability.

Availability uses exact enumeration of at most 18 independent failure domains. It counts shared components once, supports explicit perfectly correlated domains, and assumes instantaneous failover. Vendor SLAs are contractual terms and only scenario proxies for availability. Do not silently use them as empirical probabilities.

RTO/RPO are end-to-end recovery objectives. A dependency comparison flags an inconsistency for review; a complete recovery plan must include detection, orchestration, restoration, replay and validation. Read-only/degraded capabilities can have different objectives.

Traffic scenarios default to 100/1000/5000 RPS. Queue backlog requires service rate, buffer, retry multiplier and scaling delay. Missing inputs remain explicit. P99 is calculated by seeded sampling of component distributions, not summing individual P99 values; dependence and queueing assumptions remain limitations.

Do not invent official cross-AZ latency baselines. Catalog facts require conditions, date, source and freshness; quota defaults do not reveal account overrides. Monetary TCO requires region, currency, date, volume, contract/discount assumptions and resource configuration.
