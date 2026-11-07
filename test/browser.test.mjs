import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile,mkdtemp} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {pathToFileURL} from 'node:url';
import {chromium} from 'playwright';
import {deliver} from '../dist/export.js';
test('offline workbench exports vectors, preserves source and supports failure inspection',async()=>{
 const m={schemaVersion:1,id:'browser',title:'Browser <safety> test',mode:'as-is',components:[{id:'api',label:'API <script>alert(1)</script>',kind:'api',public:true,controls:{edgeWaf:false}},{id:'db',label:'Database',kind:'database',stateful:true}],relationships:[{id:'read',from:'api',to:'db',kind:'sync'}],evidence:[],views:[{id:'deployment',label:'Deployment',type:'deployment'}]};
 const out=await mkdtemp(join(tmpdir(),'archi-made-easy-'));const receipt=await deliver(m,out,{raster:false});assert.equal(receipt.sourceUnchanged,true);assert.equal(receipt.exports.visualReview,'not-performed');assert.match(await readFile(join(out,'as-is','architecture.drawio'),'utf8'),/mxCell/);
 const browser=await chromium.launch();try{const page=await browser.newPage({viewport:{width:1440,height:900}});const errors=[];page.on('pageerror',e=>errors.push(e.message));await page.route('http**',route=>route.abort());await page.goto(pathToFileURL(join(out,'index.html')).href);await page.locator('#drawing svg').waitFor();assert.equal(await page.locator('#view option').count(),2);await page.locator('#failure').check();await page.locator('#drawing [data-id="db"]').click();assert.equal(await page.locator('#drawing .failed').count(),2);assert.match(await page.locator('#detail').innerText(),/Database/);await page.locator('#view').selectOption('1');assert.match(await page.locator('#status').innerText(),/target/);await page.locator('#comparison').click();assert.equal(await page.locator('#compare section').count(),2);assert.deepEqual(errors,[]);}finally{await browser.close();}
});
