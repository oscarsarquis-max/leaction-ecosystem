import { NextResponse } from 'next/server';
import { cookies } from 'next/headers';

import {
  CURATION_AUTH_COOKIE,
  curationCredentialsConfigured,
  parseSessionToken,
} from '@/lib/marketplace-curation-auth';

export async function GET() {
  if (!curationCredentialsConfigured()) {
    return NextResponse.json({ authenticated: false, configured: false });
  }

  const jar = await cookies();
  const token = jar.get(CURATION_AUTH_COOKIE)?.value;
  const session = parseSessionToken(token);

  return NextResponse.json({
    authenticated: Boolean(session),
    configured: true,
    user: session?.user || null,
  });
}
