# Compact skill package

This package deliberately contains only root SKILL.md plus agents/, references/, and scripts/. Upload the whole compact ZIP; do not remove the schema or example from references/.

The host needs Python 3.9+ execution and access to the extracted files. No Node, npm, browser download, or Python library installation is required for HTML/SVG/draw.io/CASG.

First-run prompt:

> Read SKILL.md. Use scripts/render_workbench.py. Build a proposed CASG with meaningful component kinds, explicit proposed controls and evidence, and focused views of at most eight nodes. Separate MCP from downstream REST, identity and telemetry. Use references/mcp-enterprise.casg.json as a format example, not an assertion about my system. Generate the interactive workbench and editable draw.io, then provide actual download links to both and the CASG/SVG. State missing checks and formats.

Offline self-test:

```sh
python scripts/render_workbench.py references/mcp-enterprise.casg.json --out output
```

Open output/archi-workbench.html. Its view selector includes protocol, REST, identity/security, monitoring and trust-scope views. Draw.io contains corresponding pages. Failure inspection uses the entire model, including hidden dependencies. Large views are partitioned; connector detail pages retain cross-view relationships.

This is the restricted Python renderer, not the Node policy engine. It does not run WAF assessments, full schema validation, availability calculations, nested trust-zone rendering, or full semantic draw.io round trips. Scope labels and the original CASG preserve boundaries. PNG requires preinstalled Pillow/font; SVG/HTML remain available without it. Hosted-agent compatibility still depends on actual execution and attachment tools.
