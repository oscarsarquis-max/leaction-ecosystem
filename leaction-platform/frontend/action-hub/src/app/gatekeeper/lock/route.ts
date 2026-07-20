import { NextRequest, NextResponse } from 'next/server';
import {
  gatewayBase,
  isGatekeeperAdminEnabled,
  isValidMasterSecret,
  getProductionMasterKey,
} from '@/lib/gatekeeper';

export async function GET(req: NextRequest) {
  if (!isGatekeeperAdminEnabled()) {
    return new NextResponse(
      'Rotas de homologação disponíveis apenas em produção. Em dev, GATEKEEPER_ALLOW_DEV=true.',
      { status: 403 }
    );
  }
  if (!getProductionMasterKey() || !isValidMasterSecret(req.nextUrl.searchParams.get('secret'))) {
    return new NextResponse('Acesso negado.', { status: 403 });
  }
  const secret = encodeURIComponent(String(req.nextUrl.searchParams.get('secret') || ''));
  const res = await fetch(`${gatewayBase()}/gatekeeper/lock?secret=${secret}`, {
    cache: 'no-store',
  });
  const text = await res.text();
  return new NextResponse(text, {
    status: res.status,
    headers: { 'Content-Type': 'text/plain; charset=utf-8' },
  });
}
