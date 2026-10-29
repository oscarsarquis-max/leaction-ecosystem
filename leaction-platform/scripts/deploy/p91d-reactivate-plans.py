import json, os, subprocess, urllib.request
from pathlib import Path

def load_env(path):
    env = {}
    for line in Path(path).read_text(encoding='utf-8', errors='replace').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        k, v = line.split('=', 1)
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env

env = load_env('/var/www/leaction-platform/.env')
token = subprocess.check_output(
    ['node', '-e', "const j=require('jsonwebtoken');console.log(j.sign({email:'admin@actionhub.com.br'}, process.env.JWT_SECRET, {expiresIn:'15m'}))"],
    cwd='/var/www/leaction-platform/services/gateway-api',
    env={**os.environ, 'JWT_SECRET': env.get('JWT_SECRET') or ''},
    text=True,
).strip()
headers = {'Content-Type': 'application/json', 'Accept': 'application/json', 'Authorization': f'Bearer {token}'}

def req(method, path, body=None):
    data = None if body is None else json.dumps(body).encode()
    r = urllib.request.Request('http://127.0.0.1:4001' + path, data=data, headers=headers, method=method)
    with urllib.request.urlopen(r, timeout=20) as resp:
        return json.loads(resp.read().decode() or '{}')

listed = req('GET', '/admin/plans?app_id=lojadepaes')
out = []
for plan in listed.get('plans') or []:
    if plan.get('sku') not in {'LOJADEPAES_BIBLIOTECA_MENSAL', 'LOJADEPAES_BIBLIOTECA_CREDITOS'}:
        continue
    meta = dict(plan.get('meta_json') or {})
    meta['checkout_mode'] = 'subscription'
    meta['recurring_ready'] = True
    meta['periodicidade'] = 'mensal'
    meta['period_months'] = 1
    saved = req('PUT', f"/admin/plans/{plan['id']}", {
        'active': True,
        'meta_json': meta,
        'type': 'plan',
        'price': plan.get('price'),
        'currency': 'BRL',
    })
    row = saved.get('plan') or {}
    out.append({'sku': row.get('sku'), 'id': row.get('id'), 'active': row.get('active'), 'mode': (row.get('meta_json') or {}).get('checkout_mode')})
pub = req('GET', '/v1/catalog/lojadepaes')
print(json.dumps({'reactivated': out, 'public': [{k: p.get(k) for k in ('id','sku','price','credits')} | {'recurring': (p.get('meta_json') or {}).get('recurring')} for p in pub.get('plans') or []]}, indent=2, default=str))
