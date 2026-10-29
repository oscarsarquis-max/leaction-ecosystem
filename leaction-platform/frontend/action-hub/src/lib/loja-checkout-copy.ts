export type LojaCheckoutExperience = 'subscription' | 'pack' | 'bread';

export const LOJA_MANAGE_HREF = 'https://lojadepaes.com.br/#biblioteca';

export const LOJA_SUBSCRIPTION_CONSENT =
  'Ao confirmar a contratação, você autoriza a cobrança de R$ 19,00 por mês neste cartão. As 20 consultas de IA e o desconto de assinante ficam disponíveis após a confirmação do pagamento. Você poderá cancelar a renovação pelo gerenciamento da sua assinatura.';

export const LOJA_EMAIL_HINT =
  'Use o e-mail do seu cadastro na Loja de Pães. O código de acesso será enviado para esse endereço cadastrado.';

type OrderLike = {
  product_type?: string | null;
  product_name?: string | null;
};

export function resolveLojaExperience(
  brandId: string | null | undefined,
  checkoutMode: 'card' | 'subscription' | string | null | undefined,
  order?: OrderLike | null,
): LojaCheckoutExperience | null {
  if (brandId !== 'lojadepaes') return null;
  const productType = String(order?.product_type || '').toUpperCase();
  const name = String(order?.product_name || '').toLowerCase();
  const catalog = productType === 'HUB_CATALOG' || /consulta|biblioteca|pacote|assinatura/.test(name);
  if (checkoutMode === 'subscription' || (catalog && checkoutMode !== 'card')) {
    return 'subscription';
  }
  if (catalog || /pacote|consulta/.test(name)) {
    return 'pack';
  }
  return 'bread';
}

export function lojaCheckoutTitle(experience: LojaCheckoutExperience | 'plans'): string {
  if (experience === 'pack') return 'Suas consultas de IA';
  if (experience === 'plans') return 'Planos da Biblioteca';
  if (experience === 'bread') return 'Pagar seu pedido';
  return 'Sua assinatura da Biblioteca';
}

export function lojaCheckoutSubtitle(experience: LojaCheckoutExperience | 'plans'): string {
  if (experience === 'pack') return 'Compra avulsa de consultas de IA';
  if (experience === 'plans') return 'Planos da Biblioteca';
  if (experience === 'bread') return 'Pedido da fornada';
  return 'Assinatura mensal';
}

export function lojaPendingStatusLabel(experience: LojaCheckoutExperience, submitted: boolean): string {
  if (experience === 'pack') {
    return submitted ? 'Processando o pagamento' : 'Aguardando o pagamento';
  }
  if (experience === 'subscription') {
    return submitted
      ? 'Processando sua autorização'
      : 'Preencha o cartão para autorizar a cobrança mensal';
  }
  return submitted ? 'Processando o pagamento' : 'Aguardando pagamento';
}

export function lojaConsentBeforeCard(experience: LojaCheckoutExperience): string {
  if (experience === 'subscription') return LOJA_SUBSCRIPTION_CONSENT;
  if (experience === 'pack') {
    return 'Ao confirmar, você paga R$ 10,00 neste cartão por 10 consultas de IA avulsas. Não é assinatura e não renova sozinho.';
  }
  return 'Pagamento seguro pelo Mercado Pago. Use o cartão do titular da compra.';
}

export function lojaSuccessCopy(
  experience: LojaCheckoutExperience,
  outcome: 'paid' | 'authorized_pending_payment',
): { title: string; body: string } {
  if (experience === 'subscription' && outcome === 'authorized_pending_payment') {
    return {
      title: 'Assinatura autorizada. Aguardando confirmação do primeiro pagamento.',
      body: 'A autorização do cartão foi registrada. As 20 consultas de IA e o desconto de assinante só ficam disponíveis depois da confirmação do pagamento. O retorno do navegador não concede esses direitos.',
    };
  }
  if (experience === 'subscription') {
    return {
      title: 'Assinatura confirmada',
      body: 'O pagamento do ciclo foi confirmado. As consultas de IA e o desconto de assinante passam a valer conforme o contrato. Você pode gerenciar a renovação na Loja de Pães.',
    };
  }
  if (experience === 'pack') {
    return {
      title: 'Pagamento do pacote confirmado',
      body: 'As 10 consultas de IA avulsas entram depois da confirmação financeira. Este pacote não é assinatura e não renova sozinho.',
    };
  }
  return {
    title: 'Pagamento confirmado!',
    body: 'Recebemos o pagamento. A data da fornada só fica reservada depois do aceite da padaria. Você volta ao pedido em alguns segundos.',
  };
}
