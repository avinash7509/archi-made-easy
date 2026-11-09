import {spawnSync} from 'node:child_process';
import {copyFile,mkdir} from 'node:fs/promises';
for(const [fixture,page,name] of [['mcp-enterprise','compact-mcp','mcp'],['azure-enterprise','compact-azure','azure']]){
 const out=`artifacts/compact-${name}-${Date.now()}`;
 const result=spawnSync(process.platform==='win32'?'python':'python3',['-I','-S','skills/archi-made-easy/scripts/render_workbench.py',`skills/archi-made-easy/references/${fixture}.casg.json`,'--out',out],{encoding:'utf8'});
 if(result.status!==0)throw new Error(result.stderr);
 await mkdir('docs/downloads',{recursive:true});
 await copyFile(`${out}/archi-workbench.html`,`docs/${page}.html`);
 await copyFile(`${out}/architecture.drawio`,`docs/downloads/${name}-compact.drawio`);
 await copyFile(`${out}/architecture-master.svg`,`docs/downloads/${name}-compact.svg`);
 console.log(JSON.stringify({page:`docs/${page}.html`,example:'illustrative proposed target',checks:'Restricted renderer; not deployment certification'}));
}
