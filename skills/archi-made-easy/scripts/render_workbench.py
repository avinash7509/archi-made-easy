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
    # Compact multi-column placement; route only through reserved row/column gutters.
    edges = model['relationships']
    nodes = model['components']
    cols = min(3, max(1, len(nodes)))
    gap = 100 + len(edges) * 6
    top_gap = 55 + len(edges) * 8
    boxes = []
    parent_names = model.get('_scopeLabels', {n['id']: n['label'] for n in nodes})
    for i, n in enumerate(nodes):
        controls = ', '.join(re.sub(r'(?<!^)(?=[A-Z])', ' ', k).lower() for k, v in n.get('controls', {}).items() if v is True)
        context = ' / '.join(filter(None, [n.get('service'), n['kind']]))
        lines = textwrap.wrap(n['label'], 28) + textwrap.wrap(context, 28)
        if n['kind'] != 'actor' and n['kind'] != 'boundary':
            control_lines = textwrap.wrap(('Proposed: ' if model.get('mode') == 'target' else 'Declared: ') + (controls or 'controls unspecified'), 28)
            lines += control_lines[:2]
            if len(control_lines) > 2:
                lines[-1] = lines[-1][:24] + ' ...'
        if n.get('parent'):
            lines += textwrap.wrap('Scope: ' + parent_names.get(n['parent'], n['parent']), 28)
        boxes.append({'id': n['id'], 'x': 60 + len(edges)*3 + (i % cols) * (300 + gap), 'y': 0, 'width': 300, 'height': max(48 + len(lines) * 22, 60 + 18*sum(e['from']==n['id'] or e['to']==n['id'] for e in edges)), 'lines': lines, 'row': i // cols})
    y = 180 + top_gap
    for row in range((len(boxes) + cols - 1) // cols):
        members = [b for b in boxes if b['row'] == row]
        height = max(b['height'] for b in members)
        for b in members:
            b['y'], b['height'] = y, height
        y += height + top_gap
    byid = {b['id']: b for b in boxes}
    routes = []
    ports = {}
    for i, e in enumerate(edges):
        a, b = byid[e['from']], byid[e['to']]
        ak, bk = (a['id'], 'out'), (b['id'], 'in')
        ay, by = a['y'] + 35 + 18*ports.get(ak, 0), b['y'] + 35 + 18*ports.get(bk, 0)
        ports[ak] = ports.get(ak, 0)+1
        ports[bk] = ports.get(bk, 0)+1
        sx, tx = a['x'] + a['width'], b['x']
        right, left = sx + 38 + i*3, tx - 38 - i*3
        lane = min(a['y'], b['y']) - 25 - i*8
        if a['row'] == b['row'] and b['x'] > a['x'] and b['x'] - a['x'] <= 300 + gap:
            mid = (sx + tx)/2
            points = [[sx, ay], [mid, ay], [mid, by], [tx, by]]
        else:
            points = [[sx, ay], [right, ay], [right, lane], [left, lane], [left, by], [tx, by]]
        label = e.get('label', '')
        color = '#7c3aed' if 'MCP' in label.upper() else '#0284c7' if 'REST' in label.upper() else {'control':'#b45309','telemetry':'#64748b','async':'#0f766e'}.get(e['kind'], '#475569')
        routes.append({'id': e['id'], 'points': points, 'number': i+1, 'kind': e['kind'], 'color': color})
    return {'boxes': boxes, 'routes': routes, 'width': max(1000, max(b['x']+b['width'] for b in boxes)+gap), 'height': y+20}


def view_models(model):
    # Explicit views first; partition large views rather than shrink text indefinitely.
    definitions = model.get('views') or [{'id':'overview','label':'Architecture overview','nodes':[n['id'] for n in model['components']]}]
    result = []
    for view in definitions:
        ids = view.get('nodes', [n['id'] for n in model['components']])
        for start in range(0, len(ids), 8):
            selected = set(ids[start:start+8])
            subset = dict(model)
            subset['_scopeLabels'] = {n['id']:n['label'] for n in model['components']}
            subset['components'] = [n for n in model['components'] if n['id'] in selected]
            subset['relationships'] = [e for e in model['relationships'] if e['from'] in selected and e['to'] in selected]
            title = view.get('label', view['id']) + (f' · part {start//8+1}' if len(ids)>8 else '')
            result.append((title, subset))
    covered = {e['id'] for _, subset in result for e in subset['relationships']}
    for e in model['relationships']:
        if e['id'] not in covered:
            subset = dict(model)
            subset['_scopeLabels'] = {n['id']:n['label'] for n in model['components']}
            subset['components'] = [n for n in model['components'] if n['id'] in (e['from'], e['to'])]
            subset['relationships'] = [e]
            result.append(('Connection · '+e.get('label', e['id']), subset))
    shown = {n['id'] for _, subset in result for n in subset['components']}
    missing = [n for n in model['components'] if n['id'] not in shown]
    for start in range(0, len(missing), 8):
        subset = dict(model)
        subset['_scopeLabels'] = {n['id']:n['label'] for n in model['components']}
        subset['components'] = missing[start:start+8]
        subset['relationships'] = []
        result.append(('Additional components', subset))
    return result


def theme(node):
    label = (node.get('label', '') + ' ' + node.get('service', '')).lower()
    kind = node.get('kind', '')
    if kind == 'boundary':
        return ('Trust scope', '#475569', '#e2e8f0')
    if kind == 'actor' or 'copilot' in label:
        return ('Experience', '#0f766e', '#ccfbf1')
    if kind in ('ai', 'llm') or 'orchestrat' in label:
        return ('Intelligence', '#7e22ce', '#f3e8ff')
    if kind == 'identity' or any(k in label for k in ('key vault', 'entra', 'identity', 'secret')):
        return ('Security', '#92400e', '#fef3c7')
    if any(k in label for k in ('monitor', 'telemetry', 'observability')):
        return ('Operations', '#0e7490', '#cffafe')
    if 'mcp' in label:
        return ('MCP protocol', '#5b21b6', '#ede9fe')
    if kind == 'api' or 'api management' in label:
        return ('API integration', '#1d4ed8', '#dbeafe')
    if any(k in label for k in ('sap', 'servicenow', 'salesforce')) or kind in ('database', 'storage', 'queue'):
        return ('Enterprise / data', '#166534', '#dcfce7')
    return ('Service', '#334155', '#f1f5f9')


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
    for i,r in enumerate(s['routes']):
        d = ' '.join(('M' if j == 0 else 'L') + f'{p[0]} {p[1]}' for j, p in enumerate(r['points']))
        dash = '' if r['kind'] == 'sync' else 'stroke-dasharray="8 5"'
        parts.append(f'<path d="{d}" fill="none" stroke="#f8fafc" stroke-width="9"/><path d="{d}" fill="none" stroke="{r["color"]}" stroke-width="3" {dash} marker-end="url(#arrow-{i})"/>')
        px, py = r['points'][0]
        parts.append(f'<rect x="{px+4}" y="{py-11}" width="26" height="22" rx="6" fill="{r["color"]}"/><text x="{px+17}" y="{py+5}" text-anchor="middle" font-size="13" font-weight="700" fill="white">{r["number"]}</text>')
    for b in s['boxes']:
        node = nodes[b['id']]
        role, accent, tint = theme(node)
        title_count = len(textwrap.wrap(node['label'],28))
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
    for b in s['boxes']:
        role, accent, tint = theme(nodes[b['id']])
        cell = ET.SubElement(root, 'mxCell', id=ids[b['id']], value='\n'.join(b['lines']), vertex='1', parent='1', style=f'rounded=1;whiteSpace=wrap;html=0;fontSize=16;fontColor=#1e293b;fillColor={tint};strokeColor={accent};strokeWidth=2;', semanticId=b['id'])
        ET.SubElement(cell, 'mxGeometry', x=str(b['x']), y=str(b['y']), width=str(b['width']), height=str(b['height']), attrib={'as': 'geometry'})
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
        artifacts = {prefix+'architecture.svg': svg(model, s), prefix+'architecture.drawio': drawio(scoped[0][1], s), prefix+'casg-model.json': json.dumps(model, indent=2), prefix+'scene.json': json.dumps(s, indent=2)}
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
        try:
            from PIL import Image, ImageDraw, ImageFont
            image = Image.new('RGB', (s['width'], s['height']), 'white')
            draw = ImageDraw.Draw(image)
            font = ImageFont.truetype('DejaVuSans.ttf', 16)
            draw.text((30, 30), 'Archi-Made-Easy | restricted-host preview', fill='#172033', font=font)
            for r in s['routes']:
                pts = [tuple(p) for p in r['points']]
                draw.line(pts, fill='white', width=7)
                draw.line(pts, fill=r['color'], width=2)
                x, y = pts[-1]
                draw.polygon([(x, y), (x-9, y-5), (x-9, y+5)], fill='#475569')
                draw.text((pts[0][0]-30, pts[0][1]-18), str(r['number']), fill='#172033', font=font)
            for b in s['boxes']:
                role, accent, tint = theme(next(n for n in model['components'] if n['id']==b['id']))
                draw.rounded_rectangle((b['x'], b['y'], b['x']+b['width'], b['y']+b['height']), radius=8, fill=tint, outline=accent, width=2)
                for j, line in enumerate(b['lines']):
                    draw.text((b['x']+18, b['y']+18+j*22), line, fill='#172033', font=font)
            name = prefix+'architecture.png'
            image.save(out/name)
            files.append(name)
            png.append({'status': 'generated', 'file': name, 'note': 'Screen-resolution preview; SVG is authoritative for flow styles. Not a 300-DPI print export.'})
        except (ImportError, OSError) as exc:
            png.append({'status': 'not-generated', 'reason': str(exc), 'alternative': prefix+'architecture.svg'})
    data = json.dumps(tabs).replace('<', '\\u003c').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')
    (out/'archi-workbench.html').write_text(PAGE.replace('__DATA__', data), encoding='utf-8')
    files.insert(0, 'archi-workbench.html')
    receipt = {'renderer': 'python-restricted', 'files': files, 'png': png, 'checks': {'connectivity': 'passed', 'schema': 'not-performed', 'WAF': 'not-performed', 'visualReview': 'not-performed'}, 'limitations': ['Compact scoped views with crossing gaps; cross-view relationships remain in the full CASG and inspector.', 'Scope labels preserve containment facts; draw.io containers and full round-trip metadata are not implemented in fallback.', 'No automatic architectural remediation; supply an agent-authored target with --target.', 'No vendor icons, PDF, capacity simulation or SLA engine in fallback.']}
    (out/'receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    (out/'DELIVERABLES.md').write_text('# Generated artifacts\n\n'+'\n'.join(f'- [{name}]({name})' for name in files)+'\n\nPublish these as host-supported attachment/download links. PNG is optional; see receipt.json for missing formats.\n', encoding='utf-8')
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
