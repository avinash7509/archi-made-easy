# CLI reference

Run commands from the checkout after `npm ci` and `npm run build`.

```sh
node dist/cli.js validate examples/hybrid.json
node dist/cli.js simulate examples/hybrid.json --type node --target db
node dist/cli.js simulate examples/hybrid.json --type traffic --rps 5000
node dist/cli.js simulate examples/hybrid.json --type availability
node dist/cli.js inspect examples/hybrid.json --id gateway
node dist/cli.js discover /path/to/repository --out artifacts/inventory
node dist/cli.js render examples/hybrid.json --out artifacts/demo --no-raster
node dist/cli.js import artifacts/demo/as-is/architecture.drawio --out artifacts/edited
node dist/cli.js diff artifacts/demo/source.casg.json artifacts/edited/candidate.casg.json
node dist/cli.js benchmark benchmarks/manifest.json --out artifacts/benchmark
```

Commands emit JSON. `validate` exits 1 for known critical findings and 2 for invalid inputs. `render` delivers otherwise renderable models with findings; malformed graphs must be corrected first.

`discover` inventories supported static declarations and JS/TS imports. It does not prove runtime connectivity or deployment. The host agent interprets documents/images and resolves ambiguous source evidence.

After actual visual inspection, use `review <output-folder> --status passed|failed --reviewer <identity> --note <observations>`. Never mark a visual pass based only on schema checks or a browser exit code.
