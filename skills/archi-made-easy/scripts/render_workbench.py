#!/usr/bin/env python3
"""Offline restricted-host renderer. Python 3.9+ stdlib; optional Pillow for PNG.
Not a substitute for the Node policy, schema, or availability engines.
"""
import argparse
import html
import json
import re
import textwrap
import xml.etree.ElementTree as ET
from pathlib import Path


def validate(model):
    nodes = model.get('components', [])
    ids = [n['id'] for n in nodes]
    edges = model.get('relationships', [])
    if not nodes or len(set(ids)) != len(ids):
        raise ValueError('Components must have unique IDs and cannot be empty')
    if len({e['id'] for e in edges}) != len(edges) or set(ids) & {e['id'] for e in edges}:
        raise ValueError('Relationship IDs must be unique and distinct from component IDs')
    for edge in edges:
        if edge['from'] not in ids or edge['to'] not in ids:
            raise ValueError('Dangling relationship: ' + edge['id'])
    for view in model.get('views', []):
        if any(id not in ids for id in view.get('nodes', ids)):
            raise ValueError('Unknown component in view: ' + view['id'])
    for node in nodes:
        seen = {node['id']}
        parent = node.get('parent')
        while parent:
            if parent not in ids or parent in seen:
                raise ValueError('Invalid containment: ' + node['id'])
            seen.add(parent)
            parent = next(n for n in nodes if n['id'] == parent).get('parent')
    return model


def failure(model, initial):
    failed = set(initial)
    for _ in range(len(model['components']) + 1):
        before = set(failed)
        for n in model['components']:
            deps = [e for e in model['relationships'] if e['from'] == n['id'] and e['kind'] in ('sync', 'async') and e.get('dependency') != 'optional']
            broken = any(e['to'] in failed and not (e['kind'] == 'async' and n.get('controls', {}).get('buffered') is True) for e in deps if e.get('dependency', 'required') == 'required')
            groups = {}
            for e in deps:
                if e.get('dependency') in ('fallback', 'quorum'):
                    groups.setdefault(e.get('group', 'fallback'), []).append(e)
            for group in groups.values():
                threshold = group[0].get('quorum', 1) if group[0]['dependency'] == 'quorum' else 1
                broken |= sum(e['to'] not in failed for e in group) < threshold
            if broken or n.get('parent') in failed:
                failed.add(n['id'])
        if failed == before:
            break
    degraded = [n['id'] for n in model['components'] if n['id'] not in failed and any(e['from'] == n['id'] and e['to'] in failed for e in model['relationships'])]
    return {'failed': sorted(failed), 'degraded': degraded, 'confidence': 'structural-analysis', 'limitations': 'No capacity, recovery timing, or live resilience test.'}


def scene(model):
    nodes = model['components']
    boxes = []
    def place(parent, x, y):
        children = [n for n in nodes if n.get('parent') == parent]
        cursor_y = y
        max_x = x
        for start in range(0, len(children), 3):
            cursor_x, row_height = x, 0
            for n in children[start:start+3]:
                compound = any(c.get('parent') == n['id'] for c in nodes) or n['kind'] == 'boundary'
                box = {'id':n['id'],'x':cursor_x,'y':cursor_y,'width':300,'height':100,'lines':[textwrap.shorten(n['label'],width=30,placeholder='…'), textwrap.shorten(n.get('service') or n['kind'],width=32,placeholder='…')], 'boundary':compound, 'parent':parent, 'row':cursor_y}
                boxes.append(box)
                if compound:
                    width,height = place(n['id'],cursor_x+35,cursor_y+65)
                    box['width'],box['height'] = max(370,width+70),max(165,height+100)
                cursor_x += box['width']+100
                row_height = max(row_height,box['height'])
                max_x = max(max_x,cursor_x-100)
            cursor_y += row_height+100
        return max_x-x, max(0,cursor_y-y-100)
    width,height=place(None,70,200)
    byid={b['id']:b for b in boxes}
    # Visibility-grid routing avoids leaf interiors; shared lanes remain explicit.
    obstacles=[b for b in boxes if not b['boundary']]
    routes=[]
    import heapq
    for i,e in enumerate(model['relationships']):
        a,b=byid[e['from']],byid[e['to']]
        start=(a['x']+a['width'],a['y']+a['height']/2)
        end=(b['x'],b['y']+b['height']/2)
        xs=sorted(set([start[0],end[0]]+[v for n in boxes for v in (n['x']-20,n['x']+n['width']+20)]))
        ys=sorted(set([start[1],end[1]]+[v for n in boxes for v in (n['y']-20,n['y']+n['height']+20)]))
        def clear(p,q):
            for n in obstacles:
                if p[0]==q[0] and n['x']<p[0]<n['x']+n['width'] and max(p[1],q[1])>n['y'] and min(p[1],q[1])<n['y']+n['height']:return False
                if p[1]==q[1] and n['y']<p[1]<n['y']+n['height'] and max(p[0],q[0])>n['x'] and min(p[0],q[0])<n['x']+n['width']:return False
            return True
        initial=(xs.index(start[0]),ys.index(start[1]),-1)
        queue=[(0,initial)];cost={initial:0};prev={};last=None
        while queue:
            distance,state=heapq.heappop(queue)
            if distance!=cost[state]:continue
            ix,iy,direction=state;p0=(xs[ix],ys[iy])
            if p0==end:last=state;break
            for dx,dy,di in [(1,0,0),(-1,0,0),(0,1,1),(0,-1,1)]:
                nx,ny=ix+dx,iy+dy
                if not(0<=nx<len(xs) and 0<=ny<len(ys)):continue
                q=(xs[nx],ys[ny])
                if not clear(p0,q):continue
                nxt=(nx,ny,di);value=distance+abs(p0[0]-q[0])+abs(p0[1]-q[1])+(25 if direction not in (-1,di) else 0)
                if value<cost.get(nxt,float('inf')):cost[nxt]=value;prev[nxt]=state;heapq.heappush(queue,(value,nxt))
        points=[]
        if last is None:raise ValueError('Unable to route relationship '+e['id'])
        while True:
            points.append([xs[last[0]],ys[last[1]]])
            if last not in prev:break
            last=prev[last]
        points.reverse()
        label=e.get('protocol') or e.get('label') or e['kind']
        protocol=next((p for p in ['MCP','HTTPS','gRPC','AMQP','OIDC','OAuth','SQL','REST'] if p.lower() in label.lower()),e['kind'])
        color={'async':'#0f766e','control':'#b45309','telemetry':'#64748b'}.get(e['kind'],'#7c3aed' if protocol=='MCP' else '#0284c7')
        routes.append({'id':e['id'],'points':points,'number':i+1,'kind':e['kind'],'color':color,'protocol':protocol})
    occupied=[]
    for r in routes:
        candidates=[]
        for a,b in zip(r['points'],r['points'][1:]):
            for fraction in (.5,.25,.75):
                x=a[0]+(b[0]-a[0])*fraction-32;y=a[1]+(b[1]-a[1])*fraction-11
                candidates.append((x,y))
        def overlaps(a,b):return a[0]<b[0]+b[2] and a[0]+a[2]>b[0] and a[1]<b[1]+b[3] and a[1]+a[3]>b[1]
        for x,y in candidates:
            rectangle=(x,y,64,22)
            if any(overlaps(rectangle,(b['x'],b['y'],b['width'],b['height'])) for b in obstacles):continue
            if any(overlaps(rectangle,other) for other in occupied):continue
            r['labelX'],r['labelY']=x,y;occupied.append((x-4,y-4,72,30));break
        if 'labelX' not in r:
            r['labelX'],r['labelY']=r['points'][0][0]+8,r['points'][0][1]-11
            r['labelWarning']='Protocol label placement requires review'
    return {'boxes':boxes,'routes':routes,'width':max(1100,width+140),'height':height+280}


def view_models(model):
    return [('Full Master Architecture',model)]


def theme(node):
    kind=node.get('kind','').lower()
    if kind=='boundary':return ('Boundary / scope','#475569','#e2e8f0')
    if kind in ('actor','external'):return ('Actor / external','#0f766e','#ccfbf1')
    if kind in ('api','gateway','edge','loadbalancer'):return ('Edge / gateway','#1d4ed8','#dbeafe')
    if kind in ('queue','broker','stream','messaging'):return ('Messaging','#9d174d','#fce7f3')
    if kind in ('database','storage','cache'):return ('Database / storage','#166534','#dcfce7')
    if kind in ('identity','security','secret') or 'vault' in node.get('label','').lower():return ('Security / identity','#92400e','#fef3c7')
    if kind in ('monitor','observability','management') or 'monitor' in node.get('label','').lower():return ('Operations','#0e7490','#cffafe')
    return ('Compute / workload','#6d28d9','#ede9fe')


def svg(model, s):
    esc = html.escape
    nodes = {n['id']:n for n in model['components']}
    roles = list(dict.fromkeys(theme(nodes[b['id']]) for b in s['boxes']))
    markers = ''.join(f'<marker id="arrow-{i}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0 L10 5 L0 10Z" fill="{r["color"]}"/></marker>' for i,r in enumerate(s['routes']))
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{s["width"]}" height="{s["height"]}" viewBox="0 0 {s["width"]} {s["height"]}" style="font-family:Arial,sans-serif"><defs>{markers}</defs><rect width="100%" height="100%" fill="#f8fafc"/>', f'<text x="30" y="35" font-size="24" font-weight="700" fill="#0f172a">Archi-Made-Easy · {esc(model.get("mode", "unspecified"))}</text><text x="30" y="64" font-size="16" fill="#475569">Select a component to inspect controls, evidence and failure impact</text>']
    legend_cols = max(1, (s['width']-60)//172)
    for i,(role,accent,tint) in enumerate(roles):
        x = 30 + (i%legend_cols)*172
        ly = 82 + (i//legend_cols)*34
        parts.append(f'<rect x="{x}" y="{ly}" width="160" height="28" rx="14" fill="{tint}"/><circle cx="{x+14}" cy="{ly+14}" r="5" fill="{accent}"/><text x="{x+26}" y="{ly+19}" font-size="13" font-weight="700" fill="{accent}">{esc(role)}</text>')
    parts.append(f'<text x="30" y="{137+34*((len(roles)-1)//legend_cols)}" font-size="14" fill="#475569">Flows: purple MCP · blue REST · amber control · dashed non-sync · gaps denote crossings</text>')
    for b in s['boxes']:
        if b.get('boundary'):
            parts.append(f'<g class="node boundary" data-id="{esc(b["id"])}"><rect class="card" x="{b["x"]}" y="{b["y"]}" width="{b["width"]}" height="{b["height"]}" rx="12" fill="#e2e8f0" fill-opacity=".35" stroke="#64748b" stroke-dasharray="8 4"/><text x="{b["x"]+16}" y="{b["y"]+28}" font-size="16">{esc(nodes[b["id"]]["label"])}</text></g>')
    for i,r in enumerate(s['routes']):
        d = ' '.join(('M' if j == 0 else 'L') + f'{p[0]} {p[1]}' for j, p in enumerate(r['points']))
        dash = '' if r['kind']=='sync' else 'stroke-dasharray="6 4"' if r['kind']=='async' else 'stroke-dasharray="3 3"'
        parts.append(f'<g class="edge" data-edge="{esc(r["id"])}"><path d="{d}" fill="none" stroke="#f8fafc" stroke-width="9"/><path d="{d}" fill="none" stroke="{r["color"]}" stroke-width="{2 if r["kind"] in ("sync","async") else 1.5}" {dash} marker-end="url(#arrow-{i})"/>')
        px, py = r['labelX']-4,r['labelY']+11
        parts.append(f'<rect x="{px+4}" y="{py-11}" width="64" height="22" rx="6" fill="{r["color"]}"/><text x="{px+36}" y="{py+5}" text-anchor="middle" font-size="13" font-weight="700" fill="white">{esc(r["protocol"])}</text></g>')
    for b in s['boxes']:
        if b.get('boundary'):continue
        node = nodes[b['id']]
        role, accent, tint = theme(node)
        title_count = 1
        hh = 20 + title_count*22
        x,y,w = b['x'],b['y'],b['width']
        parts.append(f'<g class="node" data-id="{esc(b["id"], quote=True)}" tabindex="0" role="button" aria-label="{esc(node["label"], quote=True)}"><rect class="card" x="{x}" y="{y}" width="{w}" height="{b["height"]}" rx="10" fill="{tint}" stroke="{accent}" stroke-width="1.5"/><path d="M{x+10} {y} H{x+w-10} Q{x+w} {y} {x+w} {y+10} V{y+hh} H{x} V{y+10} Q{x} {y} {x+10} {y}Z" fill="{accent}"/>')
        for j, line in enumerate(b['lines']):
            ink = 'white' if j<title_count else '#1e293b'
            weight = '700' if j<title_count else '400'
            parts.append(f'<text x="{x+18}" y="{y+35+j*22}" font-size="16" font-weight="{weight}" fill="{ink}">{esc(line)}</text>')
        parts.append('</g>')
    return ''.join(parts) + '</svg>'


def drawio(model, s):
    doc = ET.Element('mxfile', host='Archi-Made-Easy')
    diagram = ET.SubElement(doc, 'diagram', id='restricted', name=model.get('mode', 'architecture'))
    root = ET.SubElement(ET.SubElement(diagram, 'mxGraphModel'), 'root')
    ET.SubElement(root, 'mxCell', id='0')
    ET.SubElement(root, 'mxCell', id='1', parent='0')
    ids = {n['id']: 'n-' + n['id'] for n in model['components']}
    nodes = {n['id']:n for n in model['components']}
    geometry_by_id = {b['id']:b for b in s['boxes']}
    for b in s['boxes']:
        parent = geometry_by_id.get(b.get('parent'))
        role, accent, tint = theme(nodes[b['id']])
        cell = ET.SubElement(root, 'mxCell', id=ids[b['id']], value='\n'.join(b['lines']), vertex='1', parent=ids[b['parent']] if parent else '1', style=f'rounded=1;whiteSpace=wrap;html=0;fontSize=16;fontColor=#1e293b;fillColor={tint};strokeColor={accent};strokeWidth=2;', semanticId=b['id'])
        ET.SubElement(cell, 'mxGeometry', x=str(b['x']-(parent['x'] if parent else 0)), y=str(b['y']-(parent['y'] if parent else 0)), width=str(b['width']), height=str(b['height']), attrib={'as': 'geometry'})
    byid = {b['id']:b for b in s['boxes']}
    for e, r in zip(model['relationships'], s['routes']):
        a, b = byid[e['from']], byid[e['to']]
        ports = f'exitX=1;entryX=0;exitY={(r["points"][0][1]-a["y"])/a["height"]};entryY={(r["points"][-1][1]-b["y"])/b["height"]};strokeColor={r["color"]};dashed={int(e["kind"]!="sync")};'
        cell = ET.SubElement(root, 'mxCell', id='e-' + e['id'], value=str(r['number']) + '. ' + e.get('label', e['kind']), edge='1', parent='1', source=ids[e['from']], target=ids[e['to']], style='edgeStyle=orthogonalEdgeStyle;rounded=0;html=0;endArrow=block;'+ports, semanticId=e['id'])
        geo = ET.SubElement(cell, 'mxGeometry', relative='1', attrib={'as': 'geometry'})
        points = ET.SubElement(geo, 'Array', attrib={'as': 'points'})
        for x, y in r['points'][1:-1]:
            ET.SubElement(points, 'mxPoint', x=str(x), y=str(y))
    return ET.tostring(doc, encoding='unicode')


PAGE = r'''<!doctype html><html lang="en"><meta charset="utf-8"><title>Archi-Made-Easy workbench</title>
<style>body{margin:0;font:15px Arial;color:#172033;background:#f1f5f9}header{padding:18px 20px;background:#0f172a;color:white;border-bottom:4px solid #8b5cf6;display:flex;gap:12px;flex-wrap:wrap}button,select,input{font:inherit;padding:9px;border:1px solid #cbd5e1;border-radius:7px;background:#fff;color:#0f172a}button{cursor:pointer}button:hover{background:#ede9fe}header strong{font-size:19px;letter-spacing:-.4px;margin-right:8px}main{display:grid;grid-template-columns:minmax(0,1fr) 300px;height:calc(100vh - 80px)}#canvas{overflow:auto;background:#f8fafc}#drawing{transform-origin:0 0}aside{padding:22px;overflow:auto;background:white;border-left:1px solid #dbeafe}aside h2{font-size:20px;margin:10px 0 18px}aside details{margin-top:18px;padding:12px;background:#f1f5f9;border-radius:8px}aside summary{cursor:pointer;color:#334155;font-weight:600}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:13px monospace}.node{cursor:pointer}.node.failed .card{fill:#fee2e2;stroke:#dc2626;stroke-width:4}.node.degraded .card{fill:#fef3c7;stroke:#d97706;stroke-width:4}.node.match .card{stroke:#2563eb;stroke-width:4}.node:focus{outline:none}.node:focus .card{stroke:#0f172a;stroke-width:4}</style>
<header><strong>Archi-Made-Easy</strong><select id="view" aria-label="Topology"></select><input id="search" placeholder="Search components"><button id="fit">Fit view</button><button id="minus">−</button><button id="plus">+</button><label><input type="checkbox" id="failure">Failure simulation</label></header><main><div id="canvas"><div id="drawing"></div></div><aside><span style="font-size:11px;font-weight:700;letter-spacing:1.6px;color:#6d28d9">ARCHITECTURE INSPECTOR</span><h2>Explore your system</h2><div id="summary" style="white-space:pre-wrap;line-height:1.6"></div><details><summary>Technical evidence and model</summary><pre id="detail"></pre></details><details><summary>Assessment scope</summary><p>Restricted-host renderer. WAF, full schema validation, availability and visual review: not performed. Containment is shown as scope text, not nested geometry. Colors identify roles, not verified security status.</p></details></aside></main>
<script>const tabs=__DATA__;const $=id=>document.getElementById(id);let current=0,zoom=1;
for(let i=0;i<tabs.length;i++){const o=document.createElement('option');o.value=i;o.textContent=(tabs[i].model.mode||'architecture')+' · '+tabs[i].title;$('view').append(o)}
function fit(){zoom=Math.min(1,Math.max(.65,($('canvas').clientWidth-20)/tabs[current].width));$('drawing').style.zoom=zoom} $('fit').onclick=fit;function show(){$('drawing').innerHTML=tabs[current].svg;fit();$('summary').textContent=tabs[current].title+'\n\n'+tabs[current].visibleEdges.map((e,i)=>(i+1)+'. '+(e.label||e.kind)).join('\n')+'\n\nSelect a component for its proposed controls and evidence. Failure analysis uses the entire model, including other views.';$('detail').textContent=JSON.stringify({view:tabs[current].title,note:'Scoped view; relationships outside this view remain in the full model. Failure simulation uses the full model.',flows:tabs[current].visibleEdges.map((e,i)=>({number:i+1,...e})),assumptions:tabs[current].model.assumptions},null,2)}
$('view').onchange=e=>{current=+e.target.value;show()};$('search').oninput=e=>document.querySelectorAll('.node').forEach(n=>n.classList.toggle('match',!!e.target.value&&n.textContent.toLowerCase().includes(e.target.value.toLowerCase())));
$('plus').onclick=()=>{$('drawing').style.zoom=zoom=Math.min(3,zoom*1.2)};$('minus').onclick=()=>{$('drawing').style.zoom=zoom=Math.max(.2,zoom/1.2)};
function inspect(e){const n=e.target.closest('.node');if(!n)return;const t=tabs[current],id=n.dataset.id,component=t.model.components.find(n=>n.id===id),sim=$('failure').checked?t.failures[id]:null;$('summary').textContent=component.label+'\n\n'+Object.entries(component.controls||{}).map(([k,v])=>k+': '+v).join('\n')+(sim?'\n\nUnavailable: '+sim.failed.join(', ')+'\nDegraded: '+sim.degraded.join(', '):'');$('detail').textContent=JSON.stringify({component,evidence:t.model.evidence?.filter(e=>component.evidence?.includes(e.id)),simulation:sim},null,2);document.querySelectorAll('.node').forEach(n=>{n.classList.toggle('failed',!!sim?.failed.includes(n.dataset.id));n.classList.toggle('degraded',!!sim?.degraded.includes(n.dataset.id))})}
$('drawing').onclick=inspect;$('drawing').onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();inspect(e)}};$('failure').onchange=show;show();</script></html>'''


def deliver(models, out):
    out.mkdir(parents=True, exist_ok=True)
    if any(out.iterdir()):
        raise ValueError('Use an empty output directory to preserve previous artifacts')
    tabs, files, png = [], [], []
    for i, model in enumerate(models):
        validate(model)
        scoped = view_models(model)
        s = scene(scoped[0][1])
        prefix = '' if i == len(models) - 1 else 'as-is-'
        artifacts = {prefix+'architecture-master.svg': svg(model, s), prefix+'architecture.svg': svg(model, s), prefix+'architecture.drawio': drawio(scoped[0][1], s), prefix+'casg-model.json': json.dumps(model, indent=2), prefix+'scene.json': json.dumps(s, indent=2)}
        for name, value in artifacts.items():
            (out/name).write_text(value, encoding='utf-8')
            files.append(name)
        failures = {n['id']: failure(model, [n['id']]) for n in model['components']}
        combined = ET.Element('mxfile', host='Archi-Made-Easy')
        measured_views = []
        for vi, (title, subset) in enumerate(scoped):
            measured = scene(subset)
            measured_views.append({'title':title, **measured})
            drawing = svg(model, measured)
            tabs.append({'model': model, 'svg': drawing, 'title': title, 'visibleEdges': subset['relationships'], 'width': measured['width'], 'failures': failures})
            page = ET.fromstring(drawio(subset, measured)).find('diagram')
            page.set('id', 'view-'+str(vi)); page.set('name', title); combined.append(page)
            name = prefix+f'view-{vi+1}.svg'
            (out/name).write_text(drawing, encoding='utf-8'); files.append(name)
        (out/(prefix+'view-scenes.json')).write_text(json.dumps(measured_views, indent=2), encoding='utf-8')
        files.append(prefix+'view-scenes.json')
        (out/(prefix+'architecture.drawio')).write_text(ET.tostring(combined, encoding='unicode'), encoding='utf-8')
    # Rasterize the actual master SVG, never reconstruct it as a different drawing.
    import shutil, subprocess
    for prefix in (['as-is-', ''] if len(models)>1 else ['']):
        source=out/(prefix+'architecture-master.svg'); destination=out/(prefix+'architecture-master.png')
        error='No installed CairoSVG, Resvg or Chromium rasterizer'
        try:
            import cairosvg
            cairosvg.svg2png(url=str(source),write_to=str(destination))
        except Exception as exc:
            error=str(exc)
        if not destination.exists():
            executable=shutil.which('resvg')
            browser=next((shutil.which(name) for name in ['chromium','chromium-browser','google-chrome'] if shutil.which(name)),None)
            command=[executable,str(source),str(destination)] if executable else [browser,'--headless','--disable-gpu','--hide-scrollbars',f'--screenshot={destination.resolve()}',f'--window-size={s["width"]},{s["height"]}',source.resolve().as_uri()] if browser else None
            if command:
                try:
                    result=subprocess.run(command,capture_output=True,timeout=30)
                    if result.returncode:error='Installed rasterizer failed'
                except (OSError,subprocess.TimeoutExpired) as exc:error=str(exc)
        if destination.exists():
            files.append(destination.name);png.append({'status':'generated','file':destination.name})
        else:png.append({'status':'not-generated','reason':error,'alternative':source.name})
    data = json.dumps(tabs).replace('<', '\\u003c').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')
    (out/'archi-workbench.html').write_text(PAGE.replace('__DATA__', data).replace('</body>', '').replace('</html>', '<script>'+Path(__file__).with_name('master-interactions.js').read_text(encoding='utf-8')+'</script></html>'), encoding='utf-8')
    files.insert(0, 'archi-workbench.html')
    receipt = {'renderer': 'python-restricted', 'files': files, 'png': png, 'checks': {'connectivity': 'passed', 'schema': 'not-performed', 'WAF': 'not-performed', 'visualReview': 'not-performed'}, 'limitations': ['Full master canvas; focus lenses change emphasis without hiding model elements.', 'Nested containment is rendered; complete semantic draw.io round-trip metadata is not implemented in fallback.', 'No automatic architectural remediation; supply an agent-authored target with --target.', 'No vendor icons, PDF, capacity simulation or SLA engine in fallback. Master PNG requires an installed SVG-capable rasterizer.']}
    (out/'receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    (out/'DELIVERABLES.md').write_text('# Generated artifacts\n\n'+'\n'.join(f'- [{name}]({name})' for name in files)+'\n\nPublish these as host-supported attachment/download links. PNG is optional; see receipt.json for missing formats.\n', encoding='utf-8')
    import zipfile
    with zipfile.ZipFile(out/'architecture-artifacts.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(out.iterdir()):
            if path.is_file() and path.suffix!='.zip':archive.write(path,path.name)
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('model', type=Path)
    parser.add_argument('--target', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    models = [json.loads(args.model.read_text(encoding='utf-8-sig'))]
    if args.target:
        target = json.loads(args.target.read_text(encoding='utf-8-sig'))
        if models[0].get('mode') != 'as-is' or target.get('mode') != 'target':
            parser.error('--target requires as-is source and target candidate modes')
        models.append(target)
    print(json.dumps(deliver(models, args.out)))
