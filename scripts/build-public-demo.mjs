import {readFile,writeFile,mkdir,copyFile} from 'node:fs/promises';
import {resolve} from 'node:path';
// Public example uses generic cards: never redistribute locally acquired vendor icons.
process.env.ARCHI_MADE_EASY_ASSETS=resolve('artifacts/public-demo-no-vendor-assets');
const {deliver}=await import('../dist/export.js');
const source=JSON.parse(await readFile('examples/hybrid.json','utf8'));
const out='artifacts/public-demo';
await deliver(source,out,{raster:false});
let page=await readFile(`${out}/index.html`,'utf8');
page=page.replace('<title>', '<meta name="description" content="Explore architecture risks, simulate a database failure, and compare as-is and proposed target diagrams. Open-source, local-first architecture tooling."><meta property="og:title" content="Archi-Made-Easy — See what breaks"><meta property="og:description" content="An interactive architecture review: inspect risks, simulate failures, export editable diagrams."><meta property="og:image" content="https://avinash7509.github.io/archi-made-easy/assets/social-preview.png"><meta property="og:url" content="https://avinash7509.github.io/archi-made-easy/"><meta name="twitter:card" content="summary_large_image"><title>');
page=page.replace('<header>','<nav style="padding:12px 24px;background:#142b24;color:white;font:14px Arial;display:flex;gap:18px;flex-wrap:wrap"><strong>Interactive sample · synthetic architecture</strong><span>Try: enable Failure simulation, then click Order database.</span><a style="color:#bbf7d0" href="https://github.com/avinash7509/archi-made-easy">Get the source ↗</a><a style="color:#bbf7d0" href="https://github.com/avinash7509/archi-made-easy/releases/download/v0.1.4/archi-made-easy-0.1.4-full.zip">Download full skill ZIP</a><a style="color:#bbf7d0" href="downloads/architecture.drawio" download>Download editable draw.io</a></nav><header>');
await mkdir('docs/downloads',{recursive:true});
await writeFile('docs/index.html',page);
await writeFile('docs/.nojekyll','');
await copyFile(`${out}/as-is/architecture.drawio`,'docs/downloads/architecture.drawio');
await copyFile('examples/hybrid.json','docs/downloads/example.casg.json');
console.log(JSON.stringify({page:'docs/index.html',example:'synthetic hybrid architecture',vendorIconsBundled:false}));
