# Actual artifact inspection

Inspect PNG exports and the default HTML viewport. Trace each critical path. Check line endpoints, containment, readable labels, clipping, ambiguous crossings, icon correctness, legend and the difference between observed and proposed state.

Do not equate browser success with visual quality. If the vision tool is unavailable, retain `not-performed`. At most three repair cycles: fix measured geometry without deleting relationships; if semantic changes are needed, update the target model and re-assess separately. Imported human geometry should remain stable unless the user requests reflow.

Verify typography at declared print size (SVG CSS 16px corresponds to 12pt). PNG dimensions use 300/96 scaling. A huge diagram fitted to a laptop may still be unreadable; provide curated detail views. Missing official icons must be identified as generic, never imitated and labeled official.

After review, `review <output-folder> --status passed|failed --reviewer <identity> --note <observations>` binds the result to the artifact hashes. A new render invalidates previous review evidence.
