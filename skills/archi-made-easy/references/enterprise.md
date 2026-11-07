# Enterprise integration lenses

SAP: identify actual deployment model, system/client boundaries, supported API/IDoc/RFC interfaces, transactional ownership, business posting semantics, transport and recovery dependencies. Do not assume arbitrary retry is safe for financial postings.

MuleSoft: distinguish control plane, runtime plane, deployment model, API policy enforcement, connectivity, durable delivery and transaction boundaries. An API gateway does not automatically supply a WAF or distributed transaction.

Databricks: distinguish account/workspace administration, compute plane, data storage, catalog authorization, ingestion paths and serving endpoints. Validate workspace network mode, storage identity, lineage and data residency against current deployment documentation.

ServiceNow: distinguish SaaS APIs, MID Server connectivity and on-prem integrations; reason about asynchronous jobs, rate limits, retries and idempotency. Do not place the SaaS tenant inside a customer subnet.

Hybrid: show DNS, identity, route advertisements, transit, redundant connectivity, certificate and firewall ownership. Shared identity and network dependencies can invalidate apparent multi-cloud independence.

These are authoring lenses, not complete vendor configuration validators. Pin authoritative documentation for each concrete architecture and disclose unsupported checks.
