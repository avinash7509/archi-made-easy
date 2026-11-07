# Provider-specific architecture checks

Sources: AWS Well-Architected https://docs.aws.amazon.com/wellarchitected/latest/framework/welcome.html ; Azure https://learn.microsoft.com/azure/well-architected/ ; Google https://docs.cloud.google.com/architecture/framework . Unified six-pillar reporting is this library's taxonomy; Azure's core framework has five pillars.

## AWS

Validate WAFv2 resource association and scope, managed rules, staged enforcement, rate rules appropriate to endpoint behavior, and DDoS strategy. CloudFront OAC is origin-type-specific; do not apply S3 OAC semantics to arbitrary ALBs. CloudFront managed prefix lists restrict source networks but do not identify your distribution: validate distribution-specific origin protection. Source: https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/restrict-access-to-load-balancer.html .

Distinguish subnets, AZs, regions and accounts. Evaluate NAT versus gateway/interface endpoint economics with actual traffic; not every endpoint is cheaper. Model IAM role permissions and credential lifetime, not simply the existence of a role.

## Azure

Front Door Premium private-origin support depends on origin type and region. Application Gateway WAF_v2 is a different regional pattern. Validate policy association, supported managed ruleset, prevention mode suitability, origin restrictions, managed identity permissions and private DNS. Sources: https://learn.microsoft.com/azure/frontdoor/private-link and https://learn.microsoft.com/azure/frontdoor/origin-security .

## Google Cloud

Cloud Armor applies to supported load-balancer/backend combinations; validate policy type and attachment. Adaptive Protection, bot controls and parsing require applicable features and service tiers. IAP is identity-aware access, not interchangeable with network isolation. PSC and VPC Service Controls have distinct semantics. Use https://docs.cloud.google.com/armor/docs and the pinned checklist catalog.

## Kubernetes

Replicas alone do not prove HA: inspect topology spread, anti-affinity, disruption budgets, control-plane placement, persistent volumes and external dependencies. A Kubernetes Service of type LoadBalancer is not automatically a verified public endpoint; controller annotations, ingress policy and provider configuration determine exposure. Check workload identity, pod permissions, secrets, network policies and ingress TLS independently.
