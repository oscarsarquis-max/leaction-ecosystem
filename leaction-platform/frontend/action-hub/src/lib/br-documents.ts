/** Validação de CPF/CNPJ no browser — espelha gateway-api/domain/br-documents.js */

function onlyDigits(value: string): string {
  return String(value || '').replace(/\D/g, '');
}

function allSameDigits(digits: string): boolean {
  return /^(\d)\1+$/.test(digits);
}

function mod11(digits: string, weights: number[]): number {
  const sum = digits
    .slice(0, weights.length)
    .split('')
    .reduce((acc, ch, i) => acc + Number(ch) * weights[i], 0);
  const rest = sum % 11;
  return rest < 2 ? 0 : 11 - rest;
}

export function isValidCpf(raw: string): boolean {
  const d = onlyDigits(raw);
  if (d.length !== 11 || allSameDigits(d)) return false;
  if (mod11(d, [10, 9, 8, 7, 6, 5, 4, 3, 2]) !== Number(d[9])) return false;
  return mod11(d, [11, 10, 9, 8, 7, 6, 5, 4, 3, 2]) === Number(d[10]);
}

export function isValidCnpj(raw: string): boolean {
  const d = onlyDigits(raw);
  if (d.length !== 14 || allSameDigits(d)) return false;
  if (mod11(d, [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]) !== Number(d[12])) return false;
  return mod11(d, [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]) === Number(d[13]);
}

export function formatCpf(raw: string): string {
  const d = onlyDigits(raw).slice(0, 11);
  const p1 = d.slice(0, 3);
  const p2 = d.slice(3, 6);
  const p3 = d.slice(6, 9);
  const p4 = d.slice(9, 11);
  if (d.length <= 3) return p1;
  if (d.length <= 6) return `${p1}.${p2}`;
  if (d.length <= 9) return `${p1}.${p2}.${p3}`;
  return `${p1}.${p2}.${p3}-${p4}`;
}

export function formatCnpj(raw: string): string {
  const d = onlyDigits(raw).slice(0, 14);
  const p1 = d.slice(0, 2);
  const p2 = d.slice(2, 5);
  const p3 = d.slice(5, 8);
  const p4 = d.slice(8, 12);
  const p5 = d.slice(12, 14);
  if (d.length <= 2) return p1;
  if (d.length <= 5) return `${p1}.${p2}`;
  if (d.length <= 8) return `${p1}.${p2}.${p3}`;
  if (d.length <= 12) return `${p1}.${p2}.${p3}/${p4}`;
  return `${p1}.${p2}.${p3}/${p4}-${p5}`;
}

export function documentDigits(raw: string): string {
  return onlyDigits(raw);
}
