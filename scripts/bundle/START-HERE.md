# Archi-Made-Easy — full skill package

This ZIP contains the skill instructions, specialist references, compiled runtime, pinned JavaScript dependencies, source code, schemas, provider catalogs, examples, fixture suite, and a prebuilt interactive demo.

## First: choose your environment

| Environment | What to do |
|---|---|
| Coding agent with filesystem and Node.js 22+ | Extract the ZIP into one directory; ask the agent to read its root `SKILL.md`. Run setup below. |
| Agent platform accepting skill ZIPs | Upload the whole ZIP. It has `SKILL.md` at the archive root. The platform must also support Node.js execution, package filesystem access, and returning generated files for full functionality. |
| Chat-only agent or restricted skill sandbox | The instructions can guide reasoning, but cannot add missing execution tools. Do not expect deterministic checks or file exports to work just because the upload succeeded. |
| No Node.js installed | Install Node.js 22+ from https://nodejs.org, then run setup. This archive does not bundle a platform-specific Node executable. |

Specific Copilot Studio/other hosted-agent upload and execution compatibility has not been certified. A successful upload is not proof the runtime can execute there.

## Start without cloning or npm install

From the extracted directory:

```sh
node setup.mjs
```

Setup checks the package hashes, verifies the CLI, and generates the example into `artifacts/demo/`. Open `artifacts/demo/index.html` for the interactive review. This path works offline with Node.js already installed. You can also open `docs/index.html` immediately for the prebuilt sample.

For PNG/PDF exports:

```sh
node setup.mjs --browser
```

This downloads the pinned, platform-specific Chromium build. Linux may additionally need Playwright system libraries installed by an administrator. Corporate download restrictions may prevent the browser installation; HTML/SVG/draw.io and analysis remain available.

## Ask your agent

```text
Read the SKILL.md at the root of this extracted Archi-Made-Easy package.
Review my system using the included runtime and references.
Preserve an evidence-backed as-is model and create a separate proposed target.
Simulate the loss of the main database. Respect our cost and residency constraints.
Deliver editable draw.io and interactive HTML. Identify assumptions and missing evidence.
```

The root launcher works from any working directory:

```sh
node /path/to/archi-made-easy/archi-made-easy.mjs --help
node archi-made-easy.mjs render runtime/examples/hybrid.json --out artifacts/my-review --no-raster
node archi-made-easy.mjs simulate runtime/examples/hybrid.json --type node --target db
```

## Optional provider icons

```sh
node archi-made-easy.mjs assets azure
node archi-made-easy.mjs assets aws
node archi-made-easy.mjs assets gcp
```

Vendor icon downloads require internet and remain under their own terms. They are not redistributed in this ZIP. Generic labeled cards work without them.

## What this package does not promise

This is the implemented v0.1 capability set, not the entire future roadmap. The host agent supplies architectural judgment. Unknown inputs remain unknown; proposed controls are not verified deployments; simulations are not live production tests. See `docs/implementation-status.md` and `ROADMAP.md`.

The archive does not include API keys, paid model access, Node.js executables, Chromium binaries, or private data. It does not install cloud resources or modify your system architecture. No agent can gain tools its host does not permit merely by reading a skill.

## Integrity and licensing

Compare the ZIP SHA-256 with the release's `SHA256SUMS.txt`. Setup checks the extracted manifest as an integrity check, not a publisher signature. Original code is Apache-2.0; dependency licenses are retained inside `runtime/node_modules`. See `LICENSE` and `NOTICE`.
