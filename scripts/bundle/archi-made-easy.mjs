#!/usr/bin/env node
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
const cli=fileURLToPath(new URL('./runtime/dist/cli.js',import.meta.url));
if(Number(process.versions.node.split('.')[0])<22){console.error('Archi-Made-Easy requires Node.js 22 or newer.');process.exit(2);}
const result=spawnSync(process.execPath,[cli,...process.argv.slice(2)],{stdio:'inherit'});
if(result.error){console.error(result.error.message);process.exit(2);}
process.exitCode=result.status??2;
