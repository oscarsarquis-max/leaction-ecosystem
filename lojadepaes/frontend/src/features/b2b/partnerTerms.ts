/**
 * Termos de parceria, apresentados e aceitos (check box) no formulário de adesão da página /b2b.
 * Ao mudar o texto, mudar a versão. O backend guarda no interessado a versão e a data do aceite.
 */
export const TERMS_VERSION = "2026-11-25";

export const TERMS_CHECKBOX =
  "Li os termos e autorizo a Loja de Pães a vincular a minha marca à loja e às ações promocionais descritas acima.";

export const TERMS: Array<{ title: string; text: string }> = [
  {
    title: "Sua marca na Loja",
    text: "Você autoriza a Loja de Pães a usar o nome, o logotipo, a história da marca e as fotos e descrições dos seus produtos na vitrine da Loja, na página da sua marca, nas combos com os pães da casa e nos pedidos.",
  },
  {
    title: "Ações promocionais",
    text: "Você autoriza o uso da sua marca e dos seus produtos nas ações de divulgação da Loja, sem custo para você: blog LePain (seções Insights e Right Now), receitas da semana feitas com o seu produto, Instagram @loja.de.paes e outras peças de divulgação da casa.",
  },
  {
    title: "Preço e taxa combo",
    text: "Você define o preço e o frete dos seus produtos. Em cada pedido vendido em combo, a taxa combo combinada com você é descontada da sua parte; o cliente não paga essa taxa. Qualquer mudança na taxa é avisada antes de valer.",
  },
  {
    title: "Pedidos e entrega",
    text: "Você confirma ou recusa cada pedido no prazo indicado no portal e entrega com a sua logística, nas regiões e no prazo que informar. Você responde pela qualidade do seu produto e pela sua venda.",
  },
  {
    title: "Atendimento",
    text: "O cliente é atendido pelo WhatsApp da Loja de Pães, que acompanha cada pedido de perto. Quando o assunto for o seu produto, a Loja aciona você para resolver.",
  },
  {
    title: "Sem fidelidade",
    text: "Não há contrato de fidelidade nem volume mínimo. Você pode sair quando quiser, avisando a Loja. Ao sair, sua marca e seus produtos deixam a vitrine; publicações já feitas, como posts do blog, podem permanecer como registro.",
  },
  {
    title: "Registro do aceite",
    text: "Guardamos a data e a hora do aceite, a versão destes termos e o e-mail informado no formulário. Se os termos mudarem, pediremos um novo aceite.",
  },
];
