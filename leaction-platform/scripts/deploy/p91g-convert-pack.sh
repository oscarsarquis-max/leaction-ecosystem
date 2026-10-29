#!/usr/bin/env bash
set -euo pipefail
cd /var/www/leaction-platform

python3 - <<'PY'
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
api_key = env.get('HUB_ADMIN_API_KEY') or ''
jwt_secret = env.get('JWT_SECRET') or ''
base = 'http://127.0.0.1:4001'

headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
if api_key:
    headers['X-Admin-Api-Key'] = api_key
elif jwt_secret:
    token = subprocess.check_output(
        [
            'node', '-e',
            "const j=require('jsonwebtoken');"
            "console.log(j.sign({email:'admin@actionhub.com.br'}, process.env.JWT_SECRET, {expiresIn:'15m'}))",
        ],
        cwd='/var/www/leaction-platform/services/gateway-api',
        env={**os.environ, 'JWT_SECRET': jwt_secret},
        text=True,
    ).strip()
    headers['Authorization'] = f'Bearer {token}'
else:
    raise SystemExit('sem HUB_ADMIN_API_KEY nem JWT_SECRET para o editor oficial')

def req(method, path, body=None):
    data = None if body is None else json.dumps(body).encode()
    r = urllib.request.Request(base + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=20) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode()
        try:
            payload = json.loads(raw) if raw else {}
        except Exception:
            payload = {'error': raw[:300]}
        return exc.code, payload

status, listed = req('GET', '/admin/plans?app_id=lojadepaes')
if status != 200:
    raise SystemExit(f'admin/plans GET falhou {status} {listed}')

existing = {row.get('sku'): row for row in (listed.get('plans') or [])}
print('existing_skus', sorted(existing))

wanted = [
    {
        'app_id': 'lojadepaes',
        'name': 'Assinatura da Biblioteca',
        'type': 'plan',
        'sku': 'LOJADEPAES_BIBLIOTECA_MENSAL',
        'price': 19,
        'currency': 'BRL',
        'active': True,
        'features': [
            '20 consultas de IA por ciclo mensal',
            '10% de desconto em todos os produtos vendidos pela Loja enquanto a assinatura estiver vigente',
            '1 consulta de IA = 1 aprofundamento concluído',
            'A franquia mensal não acumula; artigos e calculadora ficam de fora',
        ],
        'meta_json': {
            'creditos': 20,
            'credits': 20,
            'periodicidade': 'mensal',
            'period_months': 1,
            'checkout_mode': 'subscription',
            'recurring': True,
            'recurring_ready': True,
            'display_order': 1,
            'direitos': {
                'assinatura': True,
                'biblioteca': True,
                'creditos': 20,
                'desconto_loja_pct': 10,
                'papel': 'principal',
            },
        },
    },
    {
        'app_id': 'lojadepaes',
        'name': 'Pacote adicional de consultas de IA',
        'type': 'credit_pack',
        'sku': 'LOJADEPAES_BIBLIOTECA_CREDITOS',
        'price': 10,
        'currency': 'BRL',
        'active': True,
        'features': [
            '10 consultas de IA por compra avulsa',
            'Não é assinatura e não renova automaticamente',
            'Não concede desconto de assinante, crédito de pão nem carimbo de fidelidade',
        ],
        'meta_json': {
            'creditos': 10,
            'credits': 10,
            'checkout_mode': 'hub_brick',
            'recurring': False,
            'display_order': 2,
            'direitos': {
                'assinatura': False,
                'biblioteca': True,
                'creditos': 10,
                'papel': 'pacote_avulso',
            },
        },
    },
]

report = []
for plan in wanted:
    sku = plan['sku']
    current = existing.get(sku)
    if current:
        body = {
            'name': plan['name'],
            'type': plan['type'],
            'sku': sku,
            'price': plan['price'],
            'currency': plan['currency'],
            'active': True,
            'features': plan['features'],
            'meta_json': plan['meta_json'],
        }
        code, payload = req('PUT', f"/admin/plans/{current['id']}", body)
        if code != 200:
            raise SystemExit(f'PUT {sku} falhou {code} {payload}')
        saved = payload.get('plan') or payload
        report.append({
            'action': 'updated',
            'sku': sku,
            'id': saved.get('id') or current['id'],
            'previous_type': current.get('type'),
            'new_type': saved.get('type') or plan['type'],
        })
    else:
        code, payload = req('POST', '/admin/plans', plan)
        if code not in (200, 201):
            raise SystemExit(f'POST {sku} falhou {code} {payload}')
        saved = payload.get('plan') or payload
        report.append({'action': 'created', 'sku': sku, 'id': saved.get('id'), 'new_type': plan['type']})

pub_status, pub = req('GET', '/v1/catalog/lojadepaes')
public_plans = {row.get('sku'): row for row in (pub.get('plans') or [])}
for row in report:
    live = public_plans.get(row['sku']) or {}
    row['public_price'] = live.get('price')
    row['public_type'] = live.get('type')
    row['public_checkout_mode'] = live.get('checkout_mode')
    row['public_recurring'] = live.get('recurring')
    row['published'] = bool(live)

print(json.dumps({
    'ok': True,
    'admin_list_status': status,
    'public_catalog_status': pub_status,
    'plans': report,
}, ensure_ascii=True, indent=2))
PY
