# Archi-Made-Easy

Evidence-backed architecture modeling, contextual assessment, failure analysis and editable diagrams for agents. Display name **Archi-Made-Easy**; CLI/package **archi-made-easy**.

This is the first working **0.1.0 implementation**, not a completed claim of Principal Architect equivalence or superior visual quality. The host agent supplies architectural judgment; the local runtime provides repeatable mechanics. See [implementation status](docs/implementation-status.md) for explicit boundaries.

## Quick start

Requires Node.js 22 or newer. Tested locally on Windows with Node.js 24. CI is configured for Windows, Linux and macOS; those remote runs have not been executed here.

```sh
git clone https://github.com/avinash7509/archi-made-easy.git
cd archi-made-easy
npm ci
npm run build
npx playwright install chromium
node dist/cli.js assets azure
node dist/cli.js render examples/hybrid.json --out artifacts/demo
```

Open `artifacts/demo/index.html`. The bundle includes as-is and proposed target models, native editable draw.io, selectable-text SVG, 300-DPI-scaled PNG, PDF, assessment, simulations, ADR, diff and architecture dossier. `--no-raster` works without a browser. Offline rendering works after setup and optional icon acquisition.

Optional official icons:

```sh
node dist/cli.js assets aws
node dist/cli.js assets gcp
```

Icons are cached locally with checksums and terms, excluded from the published package. Unavailable vendor marks fall back to labeled generic cards. No vendor endorsement is implied.

## Agent skill

Use [SKILL.md](skills/archi-made-easy/SKILL.md) directly from this checkout, or install a self-contained skill package:

```sh
node scripts/install-skill.mjs
```

The installer creates `~/.codex/skills/archi-made-easy` with its own runtime. It refuses to overwrite an existing installation. Other agent hosts can use the same folder through their skill installation mechanism; no host-specific paid service is required.

## CLI

```sh
node dist/cli.js validate examples/hybrid.json
node dist/cli.js simulate examples/hybrid.json --type node --target db
node dist/cli.js simulate examples/hybrid.json --type traffic --rps 5000
node dist/cli.js simulate examples/hybrid.json --type availability
node dist/cli.js inspect examples/hybrid.json --id gateway
node dist/cli.js discover /path/to/repository --out artifacts/inventory
node dist/cli.js import artifacts/demo/as-is/architecture.drawio --out artifacts/edited
node dist/cli.js diff artifacts/demo/source.casg.json artifacts/edited/candidate.casg.json
node dist/cli.js benchmark benchmarks/manifest.json --out artifacts/benchmark
```

All commands emit JSON. `validate` exits 1 for known critical findings and 2 for invalid inputs. Findings do not prevent `render` from delivering an otherwise renderable candidate. Structural errors stop rendering because there is no well-defined graph to draw. No approval or waiver files are used.

`discover` is a bounded static inventory assistant, not a complete IaC interpreter. It inventories Terraform/Bicep declarations, structured CloudFormation/ARM/Kubernetes resources and JS/TS imports. An agent must resolve runtime relationships and ambiguous expressions. Documents/images are interpreted by the host agent, not by a bundled OCR/LLM service.

## Confidence and safety of interpretation

- The source model is preserved. Remediation modifies a separate proposed model, never infrastructure.
- Unknown evidence does not pass assessment. Coverage and score are separate.
- Proposed controls are design requirements, not proof of implementation or successful tests.
- Availability uses independent-domain assumptions and instant failover; it is not an SLA guarantee.
- Traffic and latency are disclosed scenarios, not live load tests.
- Browser export is not visual review. After actual inspection, record artifact-bound evidence with `review`.
- The default tradeoff matrix is illustrative; substantive design choices require the agent's requirement-specific comparison.

## Verification

```sh
npm test
node dist/cli.js benchmark benchmarks/manifest.json --out artifacts/benchmark
npm audit
npm pack --dry-run
```

The 30-case fixture suite is not the planned 270-run cross-model benchmark. Blind comparisons with diagram-design and Archify remain unperformed. No superiority claim is made.

Original code and guidance: Apache-2.0. See [NOTICE](NOTICE) for third-party references and icon terms.
