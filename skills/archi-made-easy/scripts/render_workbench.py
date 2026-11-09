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
    nodes=model['components']; edges=model['relationships']; boxes=[]; planes=[]
    bynode={n['id']:n for n in nodes}
    column_gap=max(95,max((len(semantic_label(e,bynode))*5.5+72 for e in edges),default=95))
    def descendants(id):
        return {id}.union(*(descendants(n['id']) for n in nodes if n.get('parent')==id))
    def rank(children):
        groups={n['id']:descendants(n['id']) for n in children}
        deps={n['id']:set() for n in children}
        for edge in edges:
            if edge.get('controls',{}).get('layoutBackchannel') is True:continue
            if edge['kind'] not in ('sync','async','replication') and not (edge['kind']=='control' and bynode[edge['to']].get('parent') and theme(bynode[edge['to']])[0]=='Security / identity'):continue
            if edge['kind']=='replication' and all(any(n['kind']=='boundary' and n.get('deployment',{}).get('scope')=='regional' and endpoint in groups[n['id']] for n in children) for endpoint in (edge['from'],edge['to'])):continue
            source=next((id for id,ids in groups.items() if edge['from'] in ids),None)
            target=next((id for id,ids in groups.items() if edge['to'] in ids),None)
            if source and target and source!=target:deps[target].add(source)
        result=[];pending=set(deps)
        while pending:
            ready=sorted((id for id in pending if not deps[id]&pending),key=lambda id:next(i for i,n in enumerate(children) if n['id']==id))
            if not ready:ready=[next(n['id'] for n in children if n['id'] in pending)]
            result.append(ready);pending.difference_update(ready)
        return result
    def place(parent,x,y):
        children=[n for n in nodes if n.get('parent')==parent]
        categories={'security':[],'core':[],'operations':[]}
        for n in children:
            category=theme(n)[0]
            plane='security' if category=='Security / identity' and parent is None else 'operations' if category=='Operations / telemetry' else 'core'
            categories[plane].append(n)
        cy=y;maxright=x
        for plane,members in categories.items():
            if not members:continue
            ox=x+(36 if plane!='core' else 0);oy=cy+(56 if plane!='core' else 0)
            cx=ox;bottom=oy
            layers=rank(members) if plane=='core' else [[n['id']] for n in members]
            band_bottom=oy
            for li,layer in enumerate(layers):
                if parent is not None and bynode[parent].get('deployment',{}).get('scope')!='regional' and plane=='core' and li and li%3==0:
                    cx=ox;oy=band_bottom+90
                ly=oy;layerwidth=0
                for id in layer:
                    n=bynode[id];compound=n['kind']=='boundary' or any(v.get('parent')==id for v in nodes)
                    degree=max(sum(e['from']==id for e in edges),sum(e['to']==id and e['kind']!='telemetry' for e in edges)+min(1,sum(e['to']==id and e['kind']=='telemetry' for e in edges)))
                    box={'id':id,'x':cx,'y':ly,'width':175,'height':max(60,12*(degree+1)), 'lines':[textwrap.shorten(n['label'],width=23,placeholder='…'),role(n)],'boundary':compound,'parent':parent,'row':ly}
                    boxes.append(box)
                    if compound:
                        w,h=place(id,cx+36,ly+56);box['width']=max(300,w+72);box['height']=max(150,h+92)
                    ly+=box['height']+90;layerwidth=max(layerwidth,box['width']);bottom=max(bottom,ly-90)
                cx+=layerwidth+column_gap;band_bottom=max(band_bottom,bottom)
            right=max((b['x']+b['width'] for b in boxes if b.get('parent')==parent and b['id'] in {n['id'] for n in members}),default=cx-110)
            if plane!='core':
                planes.append({'id':'plane-'+plane+'-'+str(parent),'label':'Identity & Security Plane' if plane=='security' else 'Operations & Telemetry Plane','plane':plane,'x':x,'y':cy,'width':right-x+36,'height':bottom-cy+36,'members':[n['id'] for n in members]})
                right+=36;bottom+=36
            maxright=max(maxright,right);cy=bottom+110
        return maxright-x,max(0,cy-y-110)
    width,height=place(None,80,120)
    byid={b['id']:b for b in boxes}
    # Visibility-grid routing avoids leaf interiors; shared lanes remain explicit.
    obstacles=[b for b in boxes if not b['boundary']]
    titles=[]
    for b in [*planes,*[dict(b,label=bynode[b['id']]['label']) for b in boxes if b['boundary']]]:
        titles.append({'x':b['x'],'y':b['y']-2,'width':min(b['width'],len(b['label'])*7+48),'height':48})
    obstacles+=titles
    bus_groups={}
    for e in edges:
        sink=bynode[e['to']]
        if e['kind']=='telemetry' or (e['kind']=='control' and sink.get('kind')=='identity' and not sink.get('parent')):
            key=(e['to'],e['kind'],e.get('auth'),e.get('protocol'))
            bus_groups.setdefault(key,[]).append(e['id'])
    bus_ids={id:'collector-'+ids[0] for ids in bus_groups.values() if len(ids)>=3 for id in ids}
    trunks={}
    routes=[]
    import heapq
    used=[]
    outgoing={id:[e for e in edges if e['from']==id] for id in byid}
    incoming={id:[e for e in edges if e['to']==id] for id in byid}
    for i,e in enumerate(model['relationships']):
        a,b=byid[e['from']],byid[e['to']]
        start=(a['x']+a['width'],a['y']+a['height']*(outgoing[e['from']].index(e)+1)/(len(outgoing[e['from']])+1))
        end=(b['x']-1,b['y']+b['height']*(incoming[e['to']].index(e)+1)/(len(incoming[e['to']])+1))
        bus=bus_ids.get(e['id']);tail=[]
        if bus:end=(b['x']-1,b['y']+b['height']/2)
        if bus in trunks:
            trunk=trunks[bus]
            # Join the nearest existing gutter corner. The semantic edge retains its full path.
            choices=[(abs(p[0]-start[0])+abs(p[1]-start[1]),j,p) for j,p in enumerate(trunk[1:-1],1)]
            if choices:
                _,j,join=min(choices);end=tuple(join);tail=trunk[j+1:]
        track=20+i*10
        xs=sorted(set([start[0],end[0]]+[v for n in boxes for offset in [*range(20,100,10),track] for v in (n['x']-offset,n['x']+n['width']+offset)]))
        ys=sorted(set([start[1],end[1]]+[v for n in boxes for offset in [*range(20,100,10),track] for v in (n['y']-offset,n['y']+n['height']+offset)]))
        xs=[x for x in xs if x>=20];ys=[y for y in ys if y>=90]
        def clear(p,q):
            for n in obstacles:
                if p[0]==q[0] and n['x']<p[0]<n['x']+n['width'] and max(p[1],q[1])>n['y'] and min(p[1],q[1])<n['y']+n['height']:return False
                if p[1]==q[1] and n['y']<p[1]<n['y']+n['height'] and max(p[0],q[0])>n['x'] and min(p[0],q[0])<n['x']+n['width']:return False
            for u,v,owner in used:
                if bus and owner==bus:continue
                if p[0]==q[0] and u[0]==v[0] and abs(p[0]-u[0])<9.99 and min(max(p[1],q[1]),max(u[1],v[1]))>max(min(p[1],q[1]),min(u[1],v[1])):return False
                if p[1]==q[1] and u[1]==v[1] and abs(p[1]-u[1])<9.99 and min(max(p[0],q[0]),max(u[0],v[0]))>max(min(p[0],q[0]),min(u[0],v[0])):return False
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
                if p0==start and not(q[0]>p0[0] and q[1]==p0[1]):continue
                if q==end and not tail and not(p0[0]<q[0] and q[1]==p0[1]):continue
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
        compressed=[]
        for point in points:
            while len(compressed)>1 and ((compressed[-2][0]==compressed[-1][0]==point[0]) or (compressed[-2][1]==compressed[-1][1]==point[1])):compressed.pop()
            compressed.append(point)
        points=compressed
        tap=list(points)
        if tail:points=points+tail
        used.extend((u,v,bus) for u,v in zip(points,points[1:]))
        if bus and bus not in trunks:trunks[bus]=points
        protocol=semantic_label(e,bynode)
        color={'async':'#0f766e','control':'#b45309','telemetry':'#64748b'}.get(e['kind'],'#7c3aed' if protocol=='MCP' else '#0284c7')
        routes.append({'id':e['id'],'points':points,'number':i+1,'kind':e['kind'],'color':color,'protocol':protocol,'labelWidth':max(64,min(156,len(protocol)*5.5+16)),'busId':bus,'tapPoints':tap,'sharedTail':bool(tail)})
    occupied=[]
    for r in sorted(routes,key=lambda r:sum(abs(a[0]-b[0])+abs(a[1]-b[1]) for a,b in zip(r['points'],r['points'][1:]))):
        if r['sharedTail']:continue
        half=r['labelWidth']/2
        candidates=[]
        for a,b in zip(r['points'],r['points'][1:]):
            for fraction in (.35,.65,.5,.2,.8,.1,.9):
                x=a[0]+(b[0]-a[0])*fraction-half;y=a[1]+(b[1]-a[1])*fraction-11
                candidates.append((x,y))
        for a,b in zip(r['points'],r['points'][1:]):
            distance=abs(b[0]-a[0])+abs(b[1]-a[1])
            for step in range(4,int(distance),4):
                candidates.append((a[0]+(b[0]-a[0])*step/distance-half,a[1]+(b[1]-a[1])*step/distance-11))
        candidates += [(x,y+offset) for offset in (-28,28,-56,56) for x,y in list(candidates)]
        def overlaps(a,b):return a[0]<b[0]+b[2] and a[0]+a[2]>b[0] and a[1]<b[1]+b[3] and a[1]+a[3]>b[1]
        for x,y in candidates:
            rectangle=(x,y,r['labelWidth'],22)
            if any(overlaps(rectangle,(b['x']-20,b['y']-20,b['width']+40,b['height']+40)) for b in obstacles):continue
            borders=[band for box in [*planes,*[b for b in boxes if b['boundary']]] for band in [(box['x']-4,box['y']-4,box['width']+8,8),(box['x']-4,box['y']+box['height']-4,box['width']+8,8),(box['x']-4,box['y'],8,box['height']),(box['x']+box['width']-4,box['y'],8,box['height'])]]
            if any(overlaps(rectangle,band) for band in borders):continue
            if any(overlaps(rectangle,other) for other in occupied):continue
            r['labelX'],r['labelY']=x,y;occupied.append((x-4,y-4,r['labelWidth']+8,30));break
        if 'labelX' not in r:
            r['labelX'],r['labelY']=r['points'][0][0]+8,r['points'][0][1]-11
            r['labelWarning']='Protocol label placement requires review'
    for route in routes:
        if route.get('sharedTail'):continue
        center=(route['labelX']+route['labelWidth']/2,route['labelY']+11)
        anchors=[]
        for a,b in zip(route['points'],route['points'][1:]):
            q=[min(max(center[0],min(a[0],b[0])),max(a[0],b[0])),min(max(center[1],min(a[1],b[1])),max(a[1],b[1]))]
            anchors.append((abs(q[0]-center[0])+abs(q[1]-center[1]),q))
        distance,anchor=min(anchors)
        if distance>11:route['labelAnchor']=anchor
    return {'boxes':boxes,'routes':routes,'planes':planes,'titleObstacles':titles,'width':max(1100,width+160,max((p[0] for r in routes for p in r['points']),default=0)+60),'height':max(height+200,max((p[1] for r in routes for p in r['points']),default=0)+60)}


def view_models(model):
    return [('Full Master Architecture',model)]


def semantic_label(edge,nodes):
    label=edge.get('label','').strip()
    if label and label.upper() not in ('HTTPS','HTTP','TLS'):
        return textwrap.shorten(label,width=24,placeholder='…')
    if edge['kind']=='telemetry':return 'Traces / metrics'
    if edge['kind']=='replication':return 'Replication'  # async is not implied
    target=nodes[edge['to']]
    intent={'identity':'Identity','secret':'Secrets','database':'Data','api':'API','gateway':'Ingress'}.get(target.get('kind'),'Request')
    if edge['kind']=='control':intent='Control'
    return (intent+' / '+(edge.get('protocol') or label or edge['kind']))[:24]


def role(node):
    if node.get('deployment',{}).get('posture'):return textwrap.shorten(node['deployment']['posture'],width=28,placeholder='…')
    raw=node.get('role') or node.get('service') or node.get('kind','service')
    names={'api-management':'API Gateway','api':'API Gateway','gateway':'API Gateway','service':'Application Service','identity':'Identity Provider','ai':'Agent Orchestrator','actor':'User / External Actor','database':'Database','storage':'Data Storage','queue':'Message Broker','monitor':'Observability Service','boundary':'Trust Boundary'}
    return textwrap.shorten(names.get(raw,raw.replace('-',' ').replace('_',' ').title()),width=28,placeholder='…')


def theme(node):
    kind=node.get('kind','').lower();label=(node.get('label','')+' '+node.get('service','')).lower()
    if kind=='boundary':return ('Boundary / scope','#6366f1','#f8fafc')
    if kind in ('actor','external'):return ('Actor / external','#94a3b8','#f8fafc')
    if kind in ('identity','security','secret') or any(w in label for w in ['key vault','kms','iam','certificate','entra']):return ('Security / identity','#ec4899','#fdf2f8')
    if kind in ('monitor','observability','management') or any(w in label for w in ['monitor','logging','siem','telemetry','apm']):return ('Operations / telemetry','#06b6d4','#ecfeff')
    if kind in ('api','gateway','edge','loadbalancer'):return ('Edge / gateway','#f59e0b','#fffbeb')
    if kind in ('queue','broker','stream','messaging'):return ('Messaging / broker','#f97316','#fff7ed')
    if kind in ('database','storage','cache'):return ('Database / storage','#8b5cf6','#f5f3ff')
    return ('Compute / workload','#10b981','#ecfdf5')


def rounded_path(points):
    if len(points)<2:return ''
    result=f'M {points[0][0]} {points[0][1]}'
    for i in range(1,len(points)-1):
        a,b,c=points[i-1],points[i],points[i+1]
        before=abs(b[0]-a[0])+abs(b[1]-a[1]);after=abs(c[0]-b[0])+abs(c[1]-b[1]);r=min(6,before/2,after/2)
        if not before or not after:continue
        p=[b[j]+(a[j]-b[j])*r/before for j in (0,1)];q=[b[j]+(c[j]-b[j])*r/after for j in (0,1)]
        result+=f' L {p[0]} {p[1]} Q {b[0]} {b[1]} {q[0]} {q[1]}'
    return result+f' L {points[-1][0]} {points[-1][1]}'


def boundary_style(label):
    text=label.lower()
    if 'region' in text:return '#94a3b8'
    if any(k in text for k in ['security','identity']):return '#ec4899'
    if any(k in text for k in ['operations','telemetry','monitor']):return '#06b6d4'
    if any(k in text for k in ['external','enterprise application']):return '#64748b'
    return '#6366f1'


def svg(model, s):
    esc = html.escape
    nodes = {n['id']:n for n in model['components']}
    roles = list(dict.fromkeys(theme(nodes[b['id']]) for b in s['boxes']))
    markers = ''.join(f'<marker id="arrow-{i}" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="8" markerHeight="8" markerUnits="userSpaceOnUse" orient="auto"><path d="M1 1 L7 4 L1 7" fill="none" stroke="{r["color"]}" stroke-width="1.5"/></marker>' for i,r in enumerate(s['routes']))
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{s["width"]}" height="{s["height"]}" viewBox="0 0 {s["width"]} {s["height"]}" style="font-family:Arial,sans-serif"><defs>{markers}<pattern id="draft-grid" width="20" height="20" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r=".8" fill="#e2e8f0"/></pattern></defs><rect width="100%" height="100%" fill="#f8f7f4"/><rect width="100%" height="100%" fill="url(#draft-grid)"/>', f'<text x="30" y="35" font-size="22" font-weight="600" fill="#0f172a">{esc(model.get("title","Archi-Made-Easy"))}</text><text x="30" y="64" font-size="13" fill="#64748b">{esc(model.get("mode","unspecified").upper())} · Full architecture · Logical planes do not imply network isolation</text>']
    containers=[dict(b,label=nodes[b['id']]['label']) for b in s['boxes'] if b.get('boundary')]+s.get('planes',[])
    for b in sorted(containers,key=lambda b:b['width']*b['height'],reverse=True):
        color=boundary_style(b['label']);synthetic='members' in b
        fill='#f1f5f9' if 'region' in b['label'].lower() else color
        opacity='.55' if 'region' in b['label'].lower() else '.025'
        attrs=f'data-plane="{b["plane"]}"' if synthetic else f'data-id="{esc(b["id"])}"'
        classes='plane' if synthetic else 'node boundary'
        title=textwrap.shorten(b['label'],width=max(20,int((b['width']-32)/7)),placeholder='…');pill=min(b['width']-24,len(title)*7+24)
        parts.append(f'<g class="{classes}" {attrs}><rect class="card" x="{b["x"]}" y="{b["y"]}" width="{b["width"]}" height="{b["height"]}" rx="12" fill="{fill}" fill-opacity="{opacity}" stroke="{color}" stroke-width="1" stroke-dasharray="6 4"/><rect x="{b["x"]+12}" y="{b["y"]+10}" width="{pill}" height="24" rx="6" fill="white" stroke="{color}" stroke-opacity=".25"/><text x="{b["x"]+24}" y="{b["y"]+26}" font-size="12" font-weight="600" fill="{color}">{esc(title)}</text></g>')
    for i,r in enumerate(s['routes']):
        d = rounded_path(r['tapPoints'] if r.get('sharedTail') else r['points'])
        marker='' if r.get('sharedTail') else f'marker-end="url(#arrow-{i})"'
        dash = '' if r['kind']=='sync' else 'stroke-dasharray="6 4"' if r['kind']=='async' else 'stroke-dasharray="3 3"'
        parts.append(f'<g class="edge" data-edge="{esc(r["id"])}" data-bus="{esc(r.get("busId") or "")}"><circle cx="{r["points"][0][0]}" cy="{r["points"][0][1]}" r="3.5" fill="{r["color"]}"/><path class="flow-path" d="{d}" fill="none" stroke="{r["color"]}" stroke-width="{2 if r["kind"] in ("sync","async") else 1.5}" {dash} {marker}/>')
        if r.get('sharedTail'):
            junction=r['tapPoints'][-1]
            parts.append(f'<circle cx="{junction[0]}" cy="{junction[1]}" r="2.5" fill="{r["color"]}"/></g>')
            continue
        px, py = r['labelX']-4,r['labelY']+11
        if r.get('labelAnchor'):
            ax,ay=r['labelAnchor'];cx=r['labelX']+r['labelWidth']/2
            parts.append(f'<path d="M {ax} {ay} L {cx} {py}" stroke="{r["color"]}" stroke-opacity=".35" stroke-width=".75" fill="none"/>')
        parts.append(f'<rect x="{px+4}" y="{py-11}" width="{r["labelWidth"]}" height="22" rx="6" fill="white" fill-opacity=".92" style="filter:drop-shadow(0 1px 2px rgba(0,0,0,.06))"/><text x="{px+4+r["labelWidth"]/2}" y="{py+5}" text-anchor="middle" font-size="9.5" font-weight="500" fill="#334155">{esc(r["protocol"])}</text></g>')
    for b in s['boxes']:
        if b.get('boundary'):continue
        node = nodes[b['id']]
        role, accent, tint = theme(node)
        x,y,w=b['x'],b['y'],b['width']
        parts.append(f'<g class="node" data-id="{esc(b["id"],quote=True)}" tabindex="0" role="button" aria-label="{esc(node["label"],quote=True)}"><rect class="card" x="{x}" y="{y}" width="{w}" height="{b["height"]}" rx="8" fill="{tint}" stroke="{accent}" stroke-width="1.5" style="filter:drop-shadow(0 2px 5px rgba(15,23,42,.06))"/><circle cx="{x+16}" cy="{y+12}" r="4" fill="none" stroke="{accent}"/><text x="{x+w/2}" y="{y+27}" text-anchor="middle" font-size="12.5" font-weight="600" fill="#0f172a">{esc(b["lines"][0])}</text><text x="{x+w/2}" y="{y+46}" text-anchor="middle" font-size="10.5" fill="#475569">{esc(b["lines"][1])}</text>')
        parts.append('</g>')
    return ''.join(parts) + '</svg>'


def drawio(model, s):
    doc = ET.Element('mxfile', host='Archi-Made-Easy')
    diagram = ET.SubElement(doc, 'diagram', id='restricted', name=model.get('mode', 'architecture'))
    root = ET.SubElement(ET.SubElement(diagram, 'mxGraphModel'), 'root')
    ET.SubElement(root, 'mxCell', id='0')
    ET.SubElement(root, 'mxCell', id='1', parent='0')
    for index,plane in enumerate(s.get('planes',[])):
        color=boundary_style(plane['label'])
        cell=ET.SubElement(root,'mxCell',id='visual-plane-'+str(index),value=plane['label'],vertex='1',parent='1',style=f'rounded=1;dashed=1;dashPattern=6 4;fillColor={color};fillOpacity=3;strokeColor={color};verticalAlign=top;align=left;spacing=12;fontSize=12;')
        ET.SubElement(cell,'mxGeometry',x=str(plane['x']),y=str(plane['y']),width=str(plane['width']),height=str(plane['height']),attrib={'as':'geometry'})
    ids = {n['id']: 'n-' + n['id'] for n in model['components']}
    nodes = {n['id']:n for n in model['components']}
    geometry_by_id = {b['id']:b for b in s['boxes']}
    for b in s['boxes']:
        parent = geometry_by_id.get(b.get('parent'))
        role, accent, tint = theme(nodes[b['id']])
        extra='dashed=1;dashPattern=6 4;fillOpacity=3;verticalAlign=top;align=left;spacing=12;' if b.get('boundary') else ''
        if b.get('boundary'):accent=boundary_style(nodes[b['id']]['label'])
        cell = ET.SubElement(root, 'mxCell', id=ids[b['id']], value='\n'.join(b['lines']), vertex='1', parent=ids[b['parent']] if parent else '1', style=f'rounded=1;whiteSpace=wrap;html=0;fontSize=13;fontColor=#1e293b;fillColor={tint};strokeColor={accent};strokeWidth=1.5;'+extra, semanticId=b['id'])
        ET.SubElement(cell, 'mxGeometry', x=str(b['x']-(parent['x'] if parent else 0)), y=str(b['y']-(parent['y'] if parent else 0)), width=str(b['width']), height=str(b['height']), attrib={'as': 'geometry'})
    byid = {b['id']:b for b in s['boxes']}
    for e, r in zip(model['relationships'], s['routes']):
        a, b = byid[e['from']], byid[e['to']]
        ports = f'exitX=1;entryX=0;exitY={(r["points"][0][1]-a["y"])/a["height"]};entryY={(r["points"][-1][1]-b["y"])/b["height"]};strokeColor={r["color"]};dashed={int(e["kind"]!="sync")};'
        cell = ET.SubElement(root, 'mxCell', id='e-' + e['id'], value=str(r['number']) + '. ' + e.get('label', e['kind']), edge='1', parent='1', source=ids[e['from']], target=ids[e['to']], style='edgeStyle=orthogonalEdgeStyle;rounded=1;arcSize=6;html=0;endArrow=open;'+ports, semanticId=e['id'])
        geo = ET.SubElement(cell, 'mxGeometry', relative='1', attrib={'as': 'geometry'})
        points = ET.SubElement(geo, 'Array', attrib={'as': 'points'})
        for x, y in r['points'][1:-1]:
            ET.SubElement(points, 'mxPoint', x=str(x), y=str(y))
    return ET.tostring(doc, encoding='unicode')


PAGE = r'''<!doctype html><html lang="en"><meta charset="utf-8"><title>Archi-Made-Easy workbench</title>
<style>body{margin:0;font:15px Arial;color:#172033;background:#f1f5f9}header{padding:18px 20px;background:#0f172a;color:white;border-bottom:4px solid #8b5cf6;display:flex;gap:12px;flex-wrap:wrap}button,select,input{font:inherit;padding:9px;border:1px solid #cbd5e1;border-radius:7px;background:#fff;color:#0f172a}button{cursor:pointer}button:hover{background:#ede9fe}header strong{font-size:19px;letter-spacing:-.4px;margin-right:8px}main{display:grid;grid-template-columns:minmax(0,1fr) 300px;height:calc(100vh - 80px)}#canvas{overflow:auto;background:#f8fafc}#drawing{transform-origin:0 0}aside{padding:22px;overflow:auto;background:white;border-left:1px solid #dbeafe}aside h2{font-size:20px;margin:10px 0 18px}aside details{margin-top:18px;padding:12px;background:#f1f5f9;border-radius:8px}aside summary{cursor:pointer;color:#334155;font-weight:600}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:13px monospace}.node{cursor:pointer}.node.failed .card{fill:#fee2e2;stroke:#dc2626;stroke-width:4}.node.degraded .card{fill:#fef3c7;stroke:#d97706;stroke-width:4}.node.match .card{stroke:#2563eb;stroke-width:4}.node:focus{outline:none}.node:focus .card{stroke:#0f172a;stroke-width:4}</style>
<header><strong>Archi-Made-Easy</strong><select id="view" aria-label="Topology"></select><input id="search" placeholder="Search components"><button id="fit">Fit view</button><button id="minus">−</button><button id="plus">+</button><label><input type="checkbox" id="failure">Failure simulation</label></header><main><div id="canvas"><div id="drawing"></div></div><aside><span style="font-size:11px;font-weight:700;letter-spacing:1.6px;color:#6d28d9">ARCHITECTURE INSPECTOR</span><h2>Explore your system</h2><div id="summary" style="white-space:pre-wrap;line-height:1.6"></div><details><summary>Technical evidence and model</summary><pre id="detail"></pre></details><details><summary>Assessment scope</summary><p>Restricted-host renderer. WAF, full schema validation, availability and visual review: not performed. Nested boundaries preserve modeled containment. Plane groupings organize the view; they are not additional security controls. Colors identify roles, not verified security status.</p></details></aside></main>
<script>const tabs=__DATA__;const $=id=>document.getElementById(id);let current=0,zoom=1;
for(let i=0;i<tabs.length;i++){const o=document.createElement('option');o.value=i;o.textContent=(tabs[i].model.mode||'architecture')+' · '+tabs[i].title;$('view').append(o)}
function fit(){zoom=Math.min(1,Math.max(.65,($('canvas').clientWidth-20)/tabs[current].width));$('drawing').style.zoom=zoom} $('fit').onclick=fit;function show(){$('drawing').innerHTML=tabs[current].svg;fit();$('summary').textContent='Select a card for its controls and evidence, or a sequence step below to focus a connection.';$('detail').textContent=JSON.stringify({view:tabs[current].title,note:'Scoped view; relationships outside this view remain in the full model. Failure simulation uses the full model.',flows:tabs[current].visibleEdges.map((e,i)=>({number:i+1,...e})),assumptions:tabs[current].model.assumptions},null,2)}
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
    receipt = {'renderer': 'python-restricted', 'files': files, 'png': png, 'presentationFindings': [{'edgeId':e['id'],'status':'warning','message':'Author intent plus protocol; display uses a generic intent fallback'} for m in models for e in m['relationships'] if (e.get('label') or e.get('protocol','')).upper() in ('HTTP','HTTPS','TLS')], 'checks': {'connectivity': 'passed', 'schema': 'not-performed', 'WAF': 'not-performed', 'visualReview': 'not-performed'}, 'limitations': ['Full master canvas; focus lenses change emphasis without hiding model elements.', 'Nested containment is rendered; complete semantic draw.io round-trip metadata is not implemented in fallback.', 'No automatic architectural remediation; supply an agent-authored target with --target.', 'No vendor icons, PDF, capacity simulation or SLA engine in fallback. Master PNG requires an installed SVG-capable rasterizer.']}
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
