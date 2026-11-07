# Contributing

Help architects make better decisions with evidence they can inspect.

## High-value contributions

1. **Architecture traps and valid counterexamples:** a minimal model showing a missed failure or incorrect warning.
2. **Provider rules:** authoritative source, applicability conditions, unknown-evidence behavior, and a counterexample.
3. **Readable diagrams:** reproducible model, before/after captures, and unchanged semantic relationships.
4. **Reusable examples:** synthetic or anonymized systems with clear assumptions.

For large changes, open an issue or discussion first. Small fixes can go directly to a pull request.

```sh
npm ci
npx playwright install chromium
npm test
npm run benchmark:fixtures
```

Change runtime source in `src/`, skill guidance in `skills/archi-made-easy/`, and models in `examples/` or `benchmarks/cases/`. Do not commit credentials, customer data, generated private artifacts, or cached vendor icons.

Keep observed evidence distinct from proposals. Unknowns must not become passes. Preserve meaning during layout repairs. Add a regression test for behavior changes and actual visual inspection for rendering changes. Describe the checks run and remaining limitations in your PR.

Keep discussions constructive and focused on reproducible behavior. Contributions use Apache-2.0; vendor assets retain their own terms.
