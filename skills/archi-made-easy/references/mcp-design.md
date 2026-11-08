# MCP design and compact-package example

Use `mcp-enterprise.casg.json` as a modeling example, not as evidence about the user's deployment. Run it with `python scripts/render_workbench.py references/mcp-enterprise.casg.json --out output` from the compact skill directory.

- Identify the host/agent, client SDK role, gateway policy role and tool server. A client SDK is not automatically a standalone infrastructure service.
- Distinguish MCP transport to the tool server from downstream REST calls made by tool adapters. Use explicit relationship labels containing MCP or REST. Don't label all agent calls MCP by assumption.
- Azure API Management can front existing MCP servers or expose tools from REST APIs. A separate box named MCP Gateway may therefore be a role implemented by APIM, not an additional product. If showing both, state the reason and deployment assumption.
- Propose applicable authentication, audience validation, tool authorization, secret access, audit redaction and timeout/idempotency controls. Do not blindly forward inbound tokens downstream. Distinguish control/configuration edges from per-request runtime dependencies.
- Verify the supported Microsoft 365 Copilot extension/integration mechanism for the intended deployment. The example's connection is a logical assumption, not a certified connector.
- Define protocol, enterprise integration, identity/security and operations views. Keep semantic scope labels; the compact renderer does not implement nested trust-zone geometry.

Provider references retrieved 2026-11-08:
- https://learn.microsoft.com/en-us/azure/api-management/mcp-server-overview
- https://learn.microsoft.com/en-us/azure/api-management/secure-mcp-servers
- https://learn.microsoft.com/en-us/azure/api-management/expose-existing-mcp-server

Risk review must still consider prompt injection, excessive tool permissions, token audience confusion, secrets in logs, direct backend bypass, unavailable APIs, and retrying non-idempotent writes. The Python fallback does not certify these controls or run the Node WAF engine. Availability, capacity, deployment editions and recovery targets remain open until supplied.
