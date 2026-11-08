import {spawnSync} from 'node:child_process';
import {copyFile,mkdir} from 'node:fs/promises';
const out=`artifacts/compact-public-${Date.now()}`;
const result=spawnSync(process.platform==='win32'?'python':'python3',['-I','-S','skills/archi-made-easy/scripts/render_workbench.py','skills/archi-made-easy/references/mcp-enterprise.casg.json','--out',out],{encoding:'utf8'});
if(result.status!==0)throw new Error(result.stderr);
await mkdir('docs/downloads',{recursive:true});
await copyFile(`${out}/archi-workbench.html`,'docs/compact-mcp.html');
await copyFile(`${out}/architecture.drawio`,'docs/downloads/mcp-compact.drawio');
console.log(JSON.stringify({page:'docs/compact-mcp.html',example:'illustrative proposed MCP target',checks:'Restricted renderer; not deployment certification'}));
