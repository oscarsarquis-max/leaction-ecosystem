import { readFileSync } from 'fs';
import { join } from 'path';
import { NextResponse } from 'next/server';

function readVersion(): string {
  const fromEnv = String(
    process.env.APP_VERSION || process.env.ACTIONHUB_VERSION || ''
  ).trim();
  if (fromEnv) return fromEnv;
  // process.cwd() em prod = frontend/action-hub; VERSION fica na raiz leaction-platform
  const candidates = [
    join(process.cwd(), '..', '..', 'VERSION'),
    join(process.cwd(), 'VERSION'),
    join(process.cwd(), '..', 'VERSION'),
  ];
  for (const file of candidates) {
    try {
      const v = readFileSync(file, 'utf8').trim();
      if (v) return v;
    } catch {
      /* try next */
    }
  }
  return '0.0.0';
}

function readGitSha(): string {
  for (const key of ['GIT_SHA', 'SOURCE_COMMIT', 'GITHUB_SHA', 'COMMIT_SHA']) {
    const val = String(process.env[key] || '').trim();
    if (val) return val.slice(0, 12);
  }
  const candidates = [
    join(process.cwd(), '..', '..', 'GIT_SHA'),
    join(process.cwd(), 'GIT_SHA'),
  ];
  for (const file of candidates) {
    try {
      const v = readFileSync(file, 'utf8').trim();
      if (v) return v.slice(0, 12);
    } catch {
      /* try next */
    }
  }
  return 'unknown';
}

export async function GET() {
  return NextResponse.json(
    {
      ok: true,
      app: 'actionhub',
      service: 'action-hub',
      version: readVersion(),
      git_sha: readGitSha(),
    },
    { headers: { 'Cache-Control': 'no-store' } }
  );
}
