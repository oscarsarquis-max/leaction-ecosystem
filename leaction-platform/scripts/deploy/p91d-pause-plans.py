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
jwt_secret = env.get('JWT_SECRET') or ''
token = subprocess.check_output(
    ['node', '-e', "const j=require('jsonwebtoken');console.log(j.sign({email:'admin@actionhub.com.br'}, process.env.JWT_SECRET, {expiresIn:'15m'}))"],
    cwd='/var/www/leaction-platform/services/gateway-api',
    env={**os.environ, 'JWT_SECRET': jwt_secret},
    text=True,
).strip()
headers = {'Content-Type': 'application/json', 'Accept': 'application/json', 'Authorization': f'Bearer {token}'}

def req(method, path, body=None):
    data = None if body is None else json.dumps(body).encode()
    r = urllib.request.Request('http://127.0.0.1:4001' + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=20) as resp:
            return resp.status, json.loads(resp.read().decode() or '{}')
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode() or '{}')

status, listed = req('GET', '/admin/plans?app_id=lojadepaes')
paused = []
for plan in listed.get('plans') or []:
    if plan.get('sku') in {'LOJADEPAES_BIBLIOTECA_MENSAL', 'LOJADEPAES_BIBLIOTECA_CREDITOS'}:
        meta = plan.get('meta_json') or {}
        meta['recurring_ready'] = False
        meta['checkout_mode'] = 'subscription'
        code, payload = req('PUT', f"/admin/plans/{plan['id']}", {
            'active': False,
            'meta_json': meta,
        })
        paused.append({'sku': plan['sku'], 'id': plan['id'], 'code': code, 'active': (payload.get('plan') or {}).get('active')})
pub = req('GET', '/v1/catalog/lojadepaes')
print(json.dumps({'admin': status, 'paused': paused, 'public_plans': len((pub[1] or {}).get('plans') or [])}, indent=2))
