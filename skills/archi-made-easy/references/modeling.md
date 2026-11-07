# Modeling evidence faithfully

Read the package CASG schema before authoring. A relationship points from the dependent/caller to its dependency/callee; use `optional` for nonessential telemetry or analytics. `fallback` edges in the same group require one surviving destination. `quorum` edges require a shared group and threshold. Async does not automatically mean optional or durable.

Containment (`parent`) and dependency edges are different. Region, AZ, VPC/VNet, subnet, administrative scope and trust zone must have truthful labels; a boundary is not necessarily a network segment. Managed service placement depends on the product and deployment mode.

All scalar control values are evidence claims. Missing controls are unknown, not false. For observed nodes attach `observed` evidence with `repo:relative/path:line` or a deployment inventory reference. For proposed nodes attach `proposed` evidence. Do not mark an illustrative brief as observed repository evidence.

Discovery supports declarations from Terraform/Bicep, structured CloudFormation/ARM/Kubernetes, and JS/TS imports. It does not evaluate dynamic expressions, Terraform modules, deployment overlays or arbitrary framework routing. Resolve these with source inspection, retain unknowns, and never execute untrusted project code to extract a diagram.

Documents and images require the host agent's reading/vision capability. Transcribe uncertain labels as assumptions. Existing images are evidence of intended structure, not proof of current deployed configuration.
