# Restricted execution hosts

Discover actual tools and executable availability; do not infer restrictions from the product name. A pasted diagnosis of Copilot is not execution evidence. Record errors when commands fail.

1. Prefer bundled Node with `--no-raster`; this already generates HTML without npm or browser downloads.
2. If Node cannot execute, use `python <skill-directory>/scripts/render_workbench.py model.json --out new-output`. Standard Python generates HTML, SVG, editable draw.io and CASG offline. PNG is opportunistic when Pillow and DejaVuSans are already installed. Never install dependencies just to obtain the core workbench.
3. For brownfield, pass `--target target.json`. The host agent authors the proposed target, respecting requirements. The fallback does not run the six-pillar policy engine, full JSON Schema validator, ELK, automatic repairs, availability calculations or full draw.io round-trip metadata.
4. Fallback geometry uses compact columns, focused views, dedicated routing gutters, scope labels and crossing gaps. Views over eight nodes are partitioned, with connector detail pages for cross-view edges. It is not ELK's nested layout. Simulation follows the entire model's required/optional/fallback/quorum dependencies and buffered async callers, without recovery timing or capacity validation. Do not describe it as full engine parity. See `compact-start.md` for the standalone compact-package workflow.
5. Open the output HTML in an ordinary browser if the chat UI cannot preview it. Use the host's file-publishing tool to expose generated files. If HTML attachments are prohibited, disclose that specific limitation and provide a ZIP of the outputs when supported. Never claim a file was attached without an actual attachment/link.

No-execution hosts can use instructions for reasoning but cannot gain execution permissions by uploading a skill. No renderer guarantees universal Copilot compatibility or perfect visual quality. Preserve all renderable outputs and report individual missing formats.
