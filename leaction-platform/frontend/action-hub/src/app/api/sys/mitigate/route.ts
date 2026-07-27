import { spawn } from 'child_process';
import path from 'path';
import { NextResponse } from 'next/server';

import { resolveHubAdminFromRequest } from '@/lib/hub-admin-jwt';

type MitigateAction = 'restart';
type MitigateService = 'marketplace' | 'gateway';

const ALLOWED_SERVICES = new Set<MitigateService>(['marketplace', 'gateway']);

function mitigationEnabled(): boolean {
  const flag = String(process.env.HUB_ALLOW_LOCAL_MITIGATION || '')
    .trim()
    .toLowerCase();
  if (flag === '1' || flag === 'true' || flag === 'yes') return true;
  // Dev local: habilitado por padrão. Produção exige flag explícita.
  return process.env.NODE_ENV !== 'production';
}

function hubRoot(): string {
  // frontend/action-hub → leaction-platform
  return path.resolve(process.cwd(), '..', '..');
}

function runRestartScript(service: MitigateService): Promise<{
  ok: boolean;
  message: string;
  raw: string;
  exitCode: number | null;
}> {
  const script = path.join(hubRoot(), 'scripts', 'dev', 'restart-hub-service.ps1');
  const args = [
    '-NoProfile',
    '-ExecutionPolicy',
    'Bypass',
    '-File',
    script,
    '-Service',
    service,
  ];

  return new Promise((resolve) => {
    const child = spawn('powershell.exe', args, {
      cwd: hubRoot(),
      windowsHide: true,
      env: process.env,
    });

    let stdout = '';
    let stderr = '';
    child.stdout.on('data', (chunk) => {
      stdout += String(chunk);
    });
    child.stderr.on('data', (chunk) => {
      stderr += String(chunk);
    });
    child.on('error', (err) => {
      resolve({
        ok: false,
        message: err.message,
        raw: stderr || stdout,
        exitCode: null,
      });
    });
    child.on('close', (code) => {
      const lines = stdout
        .split(/\r?\n/)
        .map((l) => l.trim())
        .filter(Boolean);
      const jsonLine = [...lines].reverse().find((l) => l.startsWith('{') && l.includes('"ok"'));
      if (jsonLine) {
        try {
          const parsed = JSON.parse(jsonLine) as {
            ok?: boolean;
            message?: string;
          };
          resolve({
            ok: Boolean(parsed.ok),
            message: String(parsed.message || ''),
            raw: stdout + (stderr ? `\n${stderr}` : ''),
            exitCode: code,
          });
          return;
        } catch {
          /* fall through */
        }
      }
      resolve({
        ok: code === 0,
        message:
          code === 0
            ? 'Reinício concluído'
            : `Falha ao reiniciar (exit ${code}). ${stderr.slice(0, 200)}`,
        raw: stdout + (stderr ? `\n${stderr}` : ''),
        exitCode: code,
      });
    });
  });
}

/**
 * POST /api/sys/mitigate
 * Body: { action: 'restart', service: 'marketplace' | 'gateway' }
 * Admin JWT obrigatório. Só em local/dev (ou HUB_ALLOW_LOCAL_MITIGATION=1).
 */
export async function POST(request: Request) {
  const admin = await resolveHubAdminFromRequest(request);
  if (!admin) {
    return NextResponse.json(
      { ok: false, error: 'Não autorizado.' },
      { status: 401, headers: { 'Cache-Control': 'no-store' } }
    );
  }

  if (!mitigationEnabled()) {
    return NextResponse.json(
      {
        ok: false,
        error:
          'Mitigações locais desabilitadas em produção. Defina HUB_ALLOW_LOCAL_MITIGATION=1 se for intencional.',
      },
      { status: 403, headers: { 'Cache-Control': 'no-store' } }
    );
  }

  let body: { action?: string; service?: string } = {};
  try {
    body = (await request.json()) as { action?: string; service?: string };
  } catch {
    return NextResponse.json(
      { ok: false, error: 'JSON inválido' },
      { status: 400, headers: { 'Cache-Control': 'no-store' } }
    );
  }

  const action = String(body.action || '').trim() as MitigateAction;
  const service = String(body.service || '').trim() as MitigateService;

  if (action !== 'restart') {
    return NextResponse.json(
      { ok: false, error: "action inválida (use 'restart')" },
      { status: 400, headers: { 'Cache-Control': 'no-store' } }
    );
  }
  if (!ALLOWED_SERVICES.has(service)) {
    return NextResponse.json(
      {
        ok: false,
        error: `service inválido (use: ${[...ALLOWED_SERVICES].join(', ')})`,
      },
      { status: 400, headers: { 'Cache-Control': 'no-store' } }
    );
  }

  const result = await runRestartScript(service);
  return NextResponse.json(
    {
      ok: result.ok,
      action,
      service,
      message: result.message,
      exitCode: result.exitCode,
      by: admin.email,
    },
    {
      status: result.ok ? 200 : 500,
      headers: { 'Cache-Control': 'no-store' },
    }
  );
}
