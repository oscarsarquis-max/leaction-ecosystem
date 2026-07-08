import { NextResponse } from 'next/server';
import { cookies } from 'next/headers';

import { CURATION_AUTH_COOKIE } from '@/lib/marketplace-curation-auth';

export async function POST() {
  const jar = await cookies();
  jar.set(CURATION_AUTH_COOKIE, '', {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    path: '/',
    maxAge: 0,
  });

  return NextResponse.json({ authenticated: false });
}
