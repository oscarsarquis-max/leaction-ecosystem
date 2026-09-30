export const HOUSE_FIDELITY_COPY = {
  eyebrow: "Fidelidade da casa · participação gratuita",
  headline: "Seu quarto pedido traz um pão de presente.",
  headlineEmphasis: "de presente.",
  lead: "A cada 4 pedidos válidos no mês, ganhe um pão de 500 g da vitrine. Focaccias não participam.",
  invite: "Cadastre-se uma vez. Ao fechar seu pedido, identifique-se com a conta verificada para participar.",
  primaryCta: "Quero participar",
  secondaryCta: "Já tenho cadastro",
  footer:
    "Comprar continua simples: cadastro e CPF são opcionais. A contagem recomeça todo mês. Seus créditos conquistados permanecem.",
  howTitle: "Como funciona",
  howApproved:
    "A cada 4 pedidos válidos no mês, ganhe um pão de 500 g da vitrine. Focaccias não participam. Compra válida é a feita durante a campanha, com participação e identidade verificadas no fechamento, que esteja fechada e paga, e que inclua ao menos um pão da vitrine elegível. Fechada é o aceite da padaria; paga é o pagamento confirmado no servidor. Enviar o pedido, abrir o checkout ou gerar um Pix ainda não conta. Cada compra conta uma vez, mesmo com vários pães. Pão personalizado sozinho não gera carimbo. Frete, quando houver entrega, é cobrado à parte. Na virada do mês a contagem recomeça; créditos conquistados permanecem. Compras anteriores ou sem identificação não entram depois.",
  howRestart:
    "Na virada do mês a contagem de pedidos volta a zero. Os créditos já conquistados continuam disponíveis.",
  cpfHelp: "O CPF identifica sua participação. Ele não abre saldo sozinho e não fica na endereço da página.",
  privacy:
    "Cadastro e CPF são opcionais para comprar. Não usamos o CPF como senha e não inscrevemos você em avisos promocionais.",
  resumeHelp: "Use o e-mail do cadastro. Enviamos um código; o CPF não abre saldo sozinho.",
  verifyHelp: "Informe o código enviado ao e-mail. O cadastro só fica confirmado depois desta etapa.",
} as const;

export const STAMP_MARKS = [
  { id: "first", label: "1º pedido", gift: false },
  { id: "second", label: "2º pedido", gift: false },
  { id: "third", label: "3º pedido", gift: false },
  { id: "credit", label: "4º → crédito", gift: true },
] as const;

export type FidelityDemoState = "visitor" | "partial" | "credit";

export type HouseFidelityParticipant = {
  kind: "partial" | "credit";
  valid_orders: number;
  cycle_size: number;
  credits: number;
  progress_label: string;
  remaining_label: string;
  restart_label: string;
  credits_label: string;
};

export type HouseFidelityStatus = {
  campaign_active: boolean;
  preview: boolean;
  restart_at: string;
  restart_label: string;
  stamps: "neutral" | "progress";
  participant: HouseFidelityParticipant | null;
  pending_criteria?: string[];
  how_it_works?: string;
  benefit?: string;
  verified?: boolean;
  cpf_masked?: string | null;
  name?: string | null;
  can_redeem?: boolean;
  gaps?: { slug: string; name: string }[];
  ok?: boolean;
  needs_verification?: boolean;
  message?: string;
  contact_name?: string;
  contact_email?: string;
  confirmed?: boolean;
};

const DEMO_KEY = "lojadepaes_fidelity_demo";

export function onlyCpfDigits(value: string): string {
  return value.replace(/\D/g, "").slice(0, 11);
}

export function formatCpf(value: string): string {
  const digits = onlyCpfDigits(value);
  const part1 = digits.slice(0, 3);
  const part2 = digits.slice(3, 6);
  const part3 = digits.slice(6, 9);
  const part4 = digits.slice(9, 11);
  if (digits.length <= 3) {
    return part1;
  }
  if (digits.length <= 6) {
    return `${part1}.${part2}`;
  }
  if (digits.length <= 9) {
    return `${part1}.${part2}.${part3}`;
  }
  return `${part1}.${part2}.${part3}-${part4}`;
}

export function isValidCpf(value: string): boolean {
  const digits = onlyCpfDigits(value);
  if (digits.length !== 11 || /^(\d)\1{10}$/.test(digits)) {
    return false;
  }
  const numbers = digits.split("").map(Number);
  const check = (limit: number) => {
    const sum = numbers.slice(0, limit).reduce((total, number, index) => total + number * (limit + 1 - index), 0);
    const rest = (sum * 10) % 11;
    return (rest === 10 ? 0 : rest) === numbers[limit];
  };
  return check(9) && check(10);
}

export function parseDemoState(raw: string | null, preview: boolean): FidelityDemoState {
  if (!preview) {
    return "visitor";
  }
  const value = (raw ?? "").trim().toLowerCase();
  if (value === "partial" || value === "parcial") {
    return "partial";
  }
  if (value === "credit" || value === "credito" || value === "crédito") {
    return "credit";
  }
  return "visitor";
}

export function demoFromLocation(preview: boolean, search = window.location.search): FidelityDemoState {
  const query = parseDemoState(new URLSearchParams(search).get("fidelidade"), preview);
  if (query !== "visitor") {
    return query;
  }
  try {
    return parseDemoState(sessionStorage.getItem(DEMO_KEY), preview);
  } catch {
    return "visitor";
  }
}

export function rememberDemoState(state: FidelityDemoState, preview: boolean): void {
  if (!preview) {
    return;
  }
  try {
    sessionStorage.setItem(DEMO_KEY, state);
  } catch {
    /* ignore quota */
  }
}

export function filledStamps(participant: HouseFidelityParticipant | null): number {
  if (!participant) {
    return 0;
  }
  if (participant.kind === "credit") {
    return 4;
  }
  return Math.min(participant.valid_orders, 4);
}
