# Compact master workbench

Upload the entire compact ZIP: SKILL.md, agents/, references/ and scripts/. Python 3.9+ generates the complete architecture without Node or downloads.

```sh
python scripts/render_workbench.py references/mcp-enterprise.casg.json --out output
```

Open output/archi-workbench.html. The default master includes every component, dependency and parent-defined boundary. Lenses dim unrelated elements without removing nodes. The sequence list focuses relationships. Use wheel zoom, background drag, search, Fit View, Reset Filter and Minimap.

Use CASG components with kind=boundary and parent IDs for cloud, region, network, subnet or trust containers. These names denote scope semantics; containment alone is not a security control. Cards show a name and role; inspect controls, evidence and assumptions in the drawer.

Failure mode evaluates required, optional, fallback, quorum and buffered dependencies in the browser. Red is the selected source, amber indicates impact, green indicates unaffected nodes, and dashed blue shows surviving fallback/quorum connections. Capacity and failover timing are not validated.

Deliver architecture-master.svg, archi-workbench.html, architecture.drawio, casg-model.json and architecture-artifacts.zip. PNG requires installed CairoSVG, Resvg or Chromium; inspect receipt.json. No WAF, full JSON Schema or availability engine runs in this restricted renderer. Dense graphs and label placement still require visual review. Role colors are not compliance scores.
