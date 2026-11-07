# Draw.io editing

Native export embeds the baseline model and SHA-256. Import supports uncompressed and compressed diagrams, native mxCell vertices/edges, labels, containment and waypoint arrays. Use `--page` to select a page. It does not merge conflicting edits across multiple pages automatically.

Preserve original XML in the output folder. Unsupported UserObject/custom stencil semantics must remain explicitly unprocessed. Do not infer a control became deployed because a human drew an icon. Re-run schema and architecture checks on changed topology.

When current source differs from the embedded baseline, emit separate candidates and a conflict report. Never overwrite the source XML or current model automatically. Inspect deletions carefully when importing a scoped view.
