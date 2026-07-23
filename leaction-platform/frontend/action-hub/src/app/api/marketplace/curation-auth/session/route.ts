import { NextResponse } from 'next/server';
import { cookies } from 'next/headers';

import {
  CURATION_AUTH_COOKIE,
  curationCredentialsConfigured,
  parseSessionToken,
} from '@/lib/marketplace-curation-auth';
import { resolveHubAdminFromRequest } from '@/lib/hub-admin-jwt';

export async function GET(request: Request) {
  const hub = await resolveHubAdminFromRequest(request);
  if (hub) {
    return NextResponse.json({
      authenticated: true,
      configured: true,
      via: 'hub_admin',
      user: hub.email,
    });
  }

  const jar = await cookies();
  const token = jar.get(CURATION_AUTH_COOKIE)?.value;
  const session = parseSessionToken(token);

  return NextResponse.json({
    authenticated: Boolean(session),
    configured: curationCredentialsConfigured() || Boolean((process.env.JWT_SECRET || '').trim()),
    via: session ? 'curation_cookie' : null,
    user: session?.user || null,
  });
}
