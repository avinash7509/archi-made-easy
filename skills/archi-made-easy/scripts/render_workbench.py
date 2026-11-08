#!/usr/bin/env python3
"""Offline restricted-host renderer. Python 3.9+ stdlib; optional Pillow for PNG.
Not a substitute for the Node policy, schema, or availability engines.
"""
import argparse
import html
import json
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
    # Separate edge gutters and per-edge ports; horizontal segments never cross cards.
    edges = model['relationships']
    x = 70 + len(edges) * 22
    boxes, y = [], 130
    for n in model['components']:
        controls = ', '.join(k for k, v in n.get('controls', {}).items() if v is True) or 'Controls: unknown'
        rows = [n['label'], ' / '.join(filter(None, [n.get('provider'), n.get('service'), n['kind']])), ('Proposed: ' if model.get('mode') == 'target' else 'Declared: ') + controls]
        if n.get('parent'):
            rows.append('Scope: ' + n['parent'])
        if 'availability' in n:
            rows.append('Modeled availability input: ' + str(n['availability']) + ' (not contractual SLA)')
        lines = [line for row in rows for line in textwrap.wrap(row, 58)]
        degree = sum(int(e['from'] == n['id']) + int(e['to'] == n['id']) for e in edges)
        height = max(44 + len(lines) * 22, 36 + degree * 16)
        boxes.append({'id': n['id'], 'x': x, 'y': y, 'width': 620, 'height': height, 'lines': lines})
        y += height + 45
    byid = {b['id']: b for b in boxes}
    ports = {b['id']: 0 for b in boxes}
    routes = []
    for i, e in enumerate(edges):
        a, b = byid[e['from']], byid[e['to']]
        ay = a['y'] + 24 + ports[a['id']] * 16
        ports[a['id']] += 1
        by = b['y'] + 24 + ports[b['id']] * 16
        ports[b['id']] += 1
        lane = 35 + i * 22
        routes.append({'id': e['id'], 'points': [[x, ay], [lane, ay], [lane, by], [x, by]], 'number': i + 1, 'kind': e['kind']})
    return {'boxes': boxes, 'routes': routes, 'width': x + 660, 'height': y + 45}


def svg(model, s):
    esc = html.escape
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{s["width"]}" height="{s["height"]}" viewBox="0 0 {s["width"]} {s["height"]}" style="font-family:Arial,sans-serif"><rect width="100%" height="100%" fill="white"/><defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0 0 L10 5 L0 10" fill="#475569"/></marker></defs>', f'<text x="30" y="35" font-size="24">Archi-Made-Easy · {esc(model.get("mode", "unspecified"))}</text><text x="30" y="65" font-size="16">Restricted-host view · policy checks and visual review not performed</text><text x="30" y="92" font-size="16">Solid: sync · dashed: other flows · white gaps: crossing, not a junction</text>']
    for r in s['routes']:
        d = ' '.join(('M' if i == 0 else 'L') + f'{p[0]} {p[1]}' for i, p in enumerate(r['points']))
        dash = '' if r['kind'] == 'sync' else 'stroke-dasharray="7 5"'
        parts.append(f'<path d="{d}" fill="none" stroke="white" stroke-width="7"/><path d="{d}" fill="none" stroke="#475569" stroke-width="2" {dash} marker-end="url(#arrow)"/>')
        px, py = r['points'][0]
        parts.append(f'<rect x="{px-27}" y="{py-8}" width="22" height="16" fill="white"/><text x="{px-25}" y="{py+5}" font-size="13">{r["number"]}</text>')
    for b in s['boxes']:
        parts.append(f'<g class="node" data-id="{esc(b["id"], quote=True)}" tabindex="0" role="button" aria-label="{esc(b["lines"][0], quote=True)}"><rect x="{b["x"]}" y="{b["y"]}" width="620" height="{b["height"]}" rx="8" fill="#f8fafc" stroke="#94a3b8"/><path d="M{b["x"]+10} {b["y"]+10} h600" stroke="#2563eb" stroke-width="4"/>')
        for j, line in enumerate(b['lines']):
            parts.append(f'<text x="{b["x"]+18}" y="{b["y"]+35+j*22}" font-size="16">{esc(line)}</text>')
        parts.append('</g>')
    return ''.join(parts) + '</svg>'


def drawio(model, s):
    doc = ET.Element('mxfile', host='Archi-Made-Easy')
    diagram = ET.SubElement(doc, 'diagram', id='restricted', name=model.get('mode', 'architecture'))
    root = ET.SubElement(ET.SubElement(diagram, 'mxGraphModel'), 'root')
    ET.SubElement(root, 'mxCell', id='0')
    ET.SubElement(root, 'mxCell', id='1', parent='0')
    ids = {n['id']: 'n-' + n['id'] for n in model['components']}
    for b in s['boxes']:
        cell = ET.SubElement(root, 'mxCell', id=ids[b['id']], value='\n'.join(b['lines']), vertex='1', parent='1', style='rounded=1;whiteSpace=wrap;html=0;fontSize=16;fillColor=#f8fafc;strokeColor=#2563eb;', semanticId=b['id'])
        ET.SubElement(cell, 'mxGeometry', x=str(b['x']), y=str(b['y']), width='620', height=str(b['height']), attrib={'as': 'geometry'})
    for e, r in zip(model['relationships'], s['routes']):
        cell = ET.SubElement(root, 'mxCell', id='e-' + e['id'], value=str(r['number']) + '. ' + e.get('label', e['kind']), edge='1', parent='1', source=ids[e['from']], target=ids[e['to']], style='edgeStyle=orthogonalEdgeStyle;rounded=0;html=0;endArrow=block;', semanticId=e['id'])
        geo = ET.SubElement(cell, 'mxGeometry', relative='1', attrib={'as': 'geometry'})
        points = ET.SubElement(geo, 'Array', attrib={'as': 'points'})
        for x, y in r['points'][1:-1]:
            ET.SubElement(points, 'mxPoint', x=str(x), y=str(y))
    return ET.tostring(doc, encoding='unicode')


PAGE = '''<!doctype html><html lang="en"><meta charset="utf-8"><title>Archi-Made-Easy workbench</title>
<style>body{margin:0;font:16px Arial;color:#172033}header{padding:16px;background:#eef2ff;display:flex;gap:12px;flex-wrap:wrap}button,select,input{font:inherit;padding:8px}main{display:grid;grid-template-columns:1fr 360px;height:85vh}#canvas{overflow:auto}#drawing{transform-origin:0 0}aside{padding:20px;overflow:auto;border-left:1px solid #ddd}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:13px monospace}.node{cursor:pointer}.node.failed rect{fill:#fee2e2}.node.degraded rect{fill:#fef3c7}.node.match rect{stroke:#2563eb;stroke-width:4}</style>
<header><strong>Archi-Made-Easy</strong><select id="view" aria-label="Topology"></select><input id="search" placeholder="Search components"><button id="minus">−</button><button id="plus">+</button><label><input type="checkbox" id="failure">Failure simulation</label></header><main><div id="canvas"><div id="drawing"></div></div><aside><p>Restricted-host renderer. WAF, full schema validation, availability and visual review: not performed. Containment shown as scope text; not nested geometry.</p><pre id="detail"></pre></aside></main>
<script>const tabs=__DATA__;const $=id=>document.getElementById(id);let current=0,zoom=1;
for(let i=0;i<tabs.length;i++){const o=document.createElement('option');o.value=i;o.textContent=tabs[i].model.mode||'architecture';$('view').append(o)}
function show(){$('drawing').innerHTML=tabs[current].svg;$('detail').textContent=JSON.stringify({flows:tabs[current].model.relationships.map((e,i)=>({number:i+1,...e})),assumptions:tabs[current].model.assumptions},null,2)}
$('view').onchange=e=>{current=+e.target.value;show()};$('search').oninput=e=>document.querySelectorAll('.node').forEach(n=>n.classList.toggle('match',!!e.target.value&&n.textContent.toLowerCase().includes(e.target.value.toLowerCase())));
$('plus').onclick=()=>{$('drawing').style.zoom=zoom=Math.min(3,zoom*1.2)};$('minus').onclick=()=>{$('drawing').style.zoom=zoom=Math.max(.2,zoom/1.2)};
function inspect(e){const n=e.target.closest('.node');if(!n)return;const t=tabs[current],id=n.dataset.id,component=t.model.components.find(n=>n.id===id),sim=$('failure').checked?t.failures[id]:null;$('detail').textContent=JSON.stringify({component,evidence:t.model.evidence?.filter(e=>component.evidence?.includes(e.id)),simulation:sim},null,2);document.querySelectorAll('.node').forEach(n=>{n.classList.toggle('failed',!!sim?.failed.includes(n.dataset.id));n.classList.toggle('degraded',!!sim?.degraded.includes(n.dataset.id))})}
$('drawing').onclick=inspect;$('drawing').onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();inspect(e)}};$('failure').onchange=show;show();</script></html>'''


def deliver(models, out):
    out.mkdir(parents=True, exist_ok=True)
    if any(out.iterdir()):
        raise ValueError('Use an empty output directory to preserve previous artifacts')
    tabs, files, png = [], [], []
    for i, model in enumerate(models):
        validate(model)
        s = scene(model)
        prefix = '' if i == len(models) - 1 else 'as-is-'
        artifacts = {prefix+'architecture.svg': svg(model, s), prefix+'architecture.drawio': drawio(model, s), prefix+'casg-model.json': json.dumps(model, indent=2), prefix+'scene.json': json.dumps(s, indent=2)}
        for name, value in artifacts.items():
            (out/name).write_text(value, encoding='utf-8')
            files.append(name)
        tabs.append({'model': model, 'svg': artifacts[prefix+'architecture.svg'], 'failures': {n['id']: failure(model, [n['id']]) for n in model['components']}})
        try:
            from PIL import Image, ImageDraw, ImageFont
            image = Image.new('RGB', (s['width'], s['height']), 'white')
            draw = ImageDraw.Draw(image)
            font = ImageFont.truetype('DejaVuSans.ttf', 16)
            draw.text((30, 30), 'Archi-Made-Easy | restricted-host preview', fill='#172033', font=font)
            for r in s['routes']:
                pts = [tuple(p) for p in r['points']]
                draw.line(pts, fill='white', width=7)
                draw.line(pts, fill='#475569', width=2)
                x, y = pts[-1]
                draw.polygon([(x, y), (x-9, y-5), (x-9, y+5)], fill='#475569')
                draw.text((pts[0][0]-30, pts[0][1]-18), str(r['number']), fill='#172033', font=font)
            for b in s['boxes']:
                draw.rounded_rectangle((b['x'], b['y'], b['x']+620, b['y']+b['height']), radius=8, fill='#f8fafc', outline='#2563eb', width=2)
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
    receipt = {'renderer': 'python-restricted', 'files': files, 'png': png, 'checks': {'connectivity': 'passed', 'schema': 'not-performed', 'WAF': 'not-performed', 'visualReview': 'not-performed'}, 'limitations': ['Orthogonal overview with crossing gaps; dense graphs need scoped views.', 'Scope labels preserve containment facts; draw.io containers and full round-trip metadata are not implemented in fallback.', 'No automatic architectural remediation; supply an agent-authored target with --target.', 'No vendor icons, PDF, capacity simulation or SLA engine in fallback.']}
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
